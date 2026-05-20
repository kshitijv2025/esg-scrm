"""WhatsApp messaging API — send messages, questionnaires, and risk alerts to suppliers."""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import require_role, EDITOR_ROLES
from src.connectors.whatsapp import WhatsAppClient, verify_webhook
from src.db.database import (
    get_connection, release_connection, _fetchone, _execute, _fetchall,
    fetch_response_based_coverage, validate_response_value, fetch_supplier,
)
from src.ml.number_parsing import parse_number, detect_language

logger = logging.getLogger(__name__)

router = APIRouter()
webhook_router = APIRouter()

_client = WhatsAppClient()


def _verify_supplier_org(conn: Any, supplier_id: str, org_id: str) -> dict:
    """Fetch supplier and verify it belongs to the user's org."""
    supplier = _fetchone(
        conn,
        "SELECT id, name, phone, org_id FROM suppliers WHERE id = ?",
        (supplier_id,),
    )
    if supplier is None:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    if supplier["org_id"] != org_id:
        raise HTTPException(status_code=403, detail="Supplier does not belong to your organization")
    return supplier


@router.post("/send")
def send_message(body: dict, user: dict = Depends(require_auth)) -> dict[str, Any]:
    """Send a WhatsApp message to a supplier. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    supplier_id = body.get("supplier_id", "")
    message = body.get("message", "")

    if not supplier_id:
        raise HTTPException(status_code=400, detail="Missing required field: supplier_id")
    if not message:
        raise HTTPException(status_code=400, detail="Missing required field: message")

    conn = get_connection()
    try:
        supplier = _verify_supplier_org(conn, supplier_id, user["org_id"])

        phone = supplier["phone"]
        if not phone:
            raise HTTPException(
                status_code=400,
                detail=f"Supplier {supplier['name']} has no phone number on file",
            )

        result = _client.send_message(phone, message)

        _execute(
            conn,
            """INSERT INTO whatsapp_messages
               (org_id, supplier_id, direction, phone, body, twilio_message_sid)
               VALUES (?, ?, 'outbound', ?, ?, ?)""",
            (
                user["org_id"],
                supplier_id,
                _client._format_phone(phone),
                message,
                result.get("message_sid", ""),
            ),
        )

        return {
            "status": result["status"],
            "supplier_id": supplier_id,
            "supplier_name": supplier["name"],
            "message_sid": result.get("message_sid", ""),
        }
    finally:
        release_connection(conn)


@router.post("/questionnaire")
def send_questionnaire(body: dict, user: dict = Depends(require_auth)) -> dict[str, Any]:
    """Send an ESG questionnaire to a supplier via WhatsApp. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    supplier_id = body.get("supplier_id", "")
    if not supplier_id:
        raise HTTPException(status_code=400, detail="Missing required field: supplier_id")

    conn = get_connection()
    try:
        _verify_supplier_org(conn, supplier_id, user["org_id"])

        template_id = body.get("template_id", 0)

        result = _client.send_questionnaire(supplier_id, template_id=int(template_id))

        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("detail", "Unknown error"))

        return result
    finally:
        release_connection(conn)


@router.post("/alert")
def send_alert(body: dict, user: dict = Depends(require_auth)) -> dict[str, Any]:
    """Send a risk alert to a supplier via WhatsApp. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    supplier_id = body.get("supplier_id", "")
    alert_text = body.get("alert_text", "")

    if not supplier_id:
        raise HTTPException(status_code=400, detail="Missing required field: supplier_id")
    if not alert_text:
        raise HTTPException(status_code=400, detail="Missing required field: alert_text")

    conn = get_connection()
    try:
        _verify_supplier_org(conn, supplier_id, user["org_id"])

        result = _client.send_risk_alert(supplier_id, alert_text)

        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("detail", "Unknown error"))

        return result
    finally:
        release_connection(conn)


@webhook_router.post("/webhook")
async def webhook(request: Request) -> dict[str, Any]:
    """Receive incoming WhatsApp messages and replies from Twilio webhooks.

    Validates the webhook signature, stores the incoming message in the
    ``whatsapp_messages`` table, and attempts to parse questionnaire
    responses.
    """
    raw_body = await request.body()
    sig = request.headers.get("X-Twilio-Signature", "")

    auth_token = _client.auth_token
    if not auth_token:
        logger.error("whatsapp.webhook.no_auth_token")
        raise HTTPException(status_code=503, detail="Webhook not configured — auth token missing")
    if not verify_webhook(auth_token, raw_body, sig):
        logger.warning("whatsapp.webhook.invalid_signature")
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    form_data = await request.form()

    from_number = str(form_data.get("From", ""))
    body_text = str(form_data.get("Body", ""))
    message_sid = str(form_data.get("MessageSid", ""))

    if not from_number:
        logger.warning("whatsapp.webhook.missing_from")
        return {"status": "ignored", "reason": "no sender"}

    # Strip whatsapp: prefix for lookup
    phone = from_number.replace("whatsapp:", "")

    # Look up supplier by phone number
    conn = get_connection()
    try:
        supplier = _fetchone(
            conn,
            "SELECT id, name, org_id FROM suppliers WHERE phone = ? OR phone = ?",
            (phone, from_number),
        )

        supplier_id = supplier["id"] if supplier else ""
        supplier_name = supplier.get("name", "") if supplier else ""
        org_id = supplier.get("org_id", "") if supplier else ""

        # Store the incoming message
        _execute(
            conn,
            """INSERT INTO whatsapp_messages
               (org_id, supplier_id, direction, phone, body, twilio_message_sid)
               VALUES (?, ?, 'inbound', ?, ?, ?)""",
            (org_id, supplier_id, from_number, body_text, message_sid),
        )
        logger.info(
            "whatsapp.webhook.received from=%s supplier=%s sid=%s",
            from_number,
            supplier_id,
            message_sid,
        )

        # Attempt to parse questionnaire responses
        prev_coverage_pct = 0.0
        stored_count = 0
        discarded_count = 0
        if supplier_id and body_text:
            # Capture previous coverage before response is recorded
            prev_cov = fetch_response_based_coverage(org_id)
            prev_coverage_pct = prev_cov.get("spend_weighted_coverage_pct", 0.0)

            parse_result = _parse_questionnaire_response(conn, supplier_id, body_text, org_id, supplier)
            stored_count = parse_result.get("stored_count", 0)
            discarded_count = parse_result.get("discarded_count", 0)

            # Send coverage notification after response recorded
            if supplier_name and prev_coverage_pct is not None:
                from src.api.routes.questionnaires import _send_coverage_notification
                _send_coverage_notification(org_id, supplier_name, prev_coverage_pct)

        return {
            "status": "received",
            "supplier_id": supplier_id,
            "stored_count": stored_count,
            "discarded_count": discarded_count,
        }
    finally:
        release_connection(conn)


def _parse_questionnaire_response(
    conn: Any,
    supplier_id: str,
    body_text: str,
    org_id: str,
    supplier: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Parse a questionnaire response from a WhatsApp reply.

    Accepts replies in the format ``"<number>. <answer>"`` per line.
    For example::

        1. 4200000
        2. 12400
        3. Yes

    Each numeric response is validated against spend-based sanity bounds
    (see ``validate_response_value``).  Results are stored with
    ``validation_status`` and ``validation_notes`` populated.

    Returns a dict with ``stored_count`` and ``discarded_count``.
    """
    # Fetch supplier if not provided (used for spend-based validation)
    if supplier is None:
        supplier = fetch_supplier(supplier_id)

    # Detect language for number parsing based on supplier's country
    # (suppliers.country stores ISO 2-letter code: BD, VN, TH, etc.)
    country_code = supplier.get("country") if supplier else None
    number_lang = detect_language(country_code)

    # Resolve the template that was actually sent to this supplier
    last_outbound = _fetchone(
        conn,
        """SELECT template_id FROM whatsapp_messages
           WHERE supplier_id = ? AND direction = 'outbound'
           ORDER BY created_at DESC LIMIT 1""",
        (supplier_id,),
    )

    template_id = last_outbound["template_id"] if last_outbound else 0

    # Build the set of valid question IDs for this template
    valid_question_ids: set[str] = set()
    if template_id:
        rows = _fetchall(
            conn,
            "SELECT id FROM questionnaire_questions WHERE template_id = ?",
            (template_id,),
        )
        # questionnaire_questions.id is integer; question_id in responses is 'q1', 'q2', ...
        valid_question_ids = {f"q{row['id']}" for row in rows}

    lines = body_text.strip().splitlines()
    stored_count = 0
    discarded_count = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match patterns like "1. answer" or "1) answer"
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue

        number_part = parts[0].rstrip(".)")
        if not number_part.isdigit():
            continue

        question_num = int(number_part)
        answer = parts[1].strip()
        question_id = f"q{question_num}"

        # Validate: skip if template_id is known but question_id is not in it
        if valid_question_ids and question_id not in valid_question_ids:
            logger.warning(
                "whatsapp.questionnaire_response.discarded",
                question_id=question_id,
                template_id=template_id,
                supplier_id=supplier_id,
                answer_preview=answer[:50],
            )
            discarded_count += 1
            continue

        # Try to parse as a numeric value using language-aware parser
        # (handles Bengali: shat/hazar/lakh/crore; Vietnamese: ngh×n/triệu/tỷ)
        response_value: float | None = None
        parsed = parse_number(answer, language=number_lang)
        if parsed is not None:
            response_value = parsed

        # Validate numeric responses against spend-based sanity bounds
        if response_value is not None and supplier:
            validation_status, validation_notes = validate_response_value(
                supplier, question_id, response_value
            )
        else:
            validation_status, validation_notes = "verified", ""

        # Check if a response already exists for this question
        existing = _fetchone(
            conn,
            "SELECT id FROM questionnaire_responses WHERE supplier_id = ? AND question_id = ?",
            (supplier_id, question_id),
        )

        if existing:
            _execute(
                conn,
                """UPDATE questionnaire_responses
                   SET response_text = ?, response_value = ?, responded_at = datetime('now'),
                       channel = 'whatsapp', validation_status = ?, validation_notes = ?
                   WHERE supplier_id = ? AND question_id = ?""",
                (answer, response_value, validation_status, validation_notes,
                 supplier_id, question_id),
            )
        else:
            _execute(
                conn,
                """INSERT INTO questionnaire_responses
                   (org_id, supplier_id, tier, question_id, response_text, response_value,
                    channel, validation_status, validation_notes)
                   VALUES (?, ?, 1, ?, ?, ?, 'whatsapp', ?, ?)""",
                (org_id, supplier_id, question_id, answer, response_value,
                 validation_status, validation_notes),
            )

        stored_count += 1

    if stored_count > 0:
        _execute(
            conn,
            "UPDATE suppliers SET questionnaire_status = 'responded', updated_at = datetime('now') WHERE id = ?",
            (supplier_id,),
        )
        logger.info(
            "whatsapp.questionnaire_parsed supplier=%s stored=%d discarded=%d",
            supplier_id,
            stored_count,
            discarded_count,
        )

    return {"stored_count": stored_count, "discarded_count": discarded_count}
