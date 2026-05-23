"""
WhatsApp Business API client using Twilio.

Sends questionnaires, risk alerts, and ad-hoc messages to suppliers
via the WhatsApp Business API. Falls back to demo mode (no-op) when
Twilio credentials are not configured.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Any, Optional

import requests

from src.db.database import get_connection, release_connection, _fetchone, _execute

logger = logging.getLogger(__name__)

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"


class WhatsAppClient:
    """WhatsApp Business API client backed by Twilio.

    Reads TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_NUMBER
    from environment variables. When any of these are missing the client
    operates in demo mode -- ``send_message`` returns a status dict without
    making any HTTP calls.
    """

    def __init__(self) -> None:
        self.account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        self.from_number = os.environ.get("TWILIO_WHATSAPP_NUMBER", "")
        self._demo = not all([self.account_sid, self.auth_token, self.from_number])
        if self._demo:
            logger.info("whatsapp.demo_mode twilio_credentials_not_set")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_message(self, to: str, body: str) -> dict[str, Any]:
        """Send a WhatsApp message via the Twilio REST API.

        Parameters
        ----------
        to : str
            Recipient phone number. Automatically prefixed with
            ``whatsapp:+`` if not already in that format.
        body : str
            Plain-text message body.

        Returns
        -------
        dict
            ``{"status": "sent", "message_sid": ..., "to": ...}`` on
            success, or ``{"status": "demo", ...}`` when running without
            Twilio credentials.
        """
        to = self._format_phone(to)

        if self._demo:
            logger.info("whatsapp.send.demo to=%s body_len=%d", to, len(body))
            return {"status": "demo", "to": to, "body": body}

        url = f"{TWILIO_API_BASE}/Accounts/{self.account_sid}/Messages.json"
        payload = {
            "From": f"whatsapp:{self.from_number}",
            "To": to,
            "Body": body,
        }

        logger.info("whatsapp.send.start to=%s body_len=%d", to, len(body))
        resp = requests.post(
            url,
            data=payload,
            auth=(self.account_sid, self.auth_token),
            timeout=30,
        )

        if resp.status_code >= 400:
            logger.error(
                "whatsapp.send.error status=%d body=%s",
                resp.status_code,
                resp.text[:500],
            )
            return {
                "status": "error",
                "status_code": resp.status_code,
                "detail": resp.text[:500],
                "to": to,
            }

        data = resp.json()
        message_sid = data.get("sid", "")
        logger.info("whatsapp.send.ok sid=%s to=%s", message_sid, to)
        return {
            "status": "sent",
            "message_sid": message_sid,
            "to": to,
        }

    def send_questionnaire(self, supplier_id: str, template_id: int = 0) -> dict[str, Any]:
        """Send an ESG questionnaire to a supplier via WhatsApp.

        Fetches the supplier's phone number from the database, retrieves
        the questionnaire template, formats it as a WhatsApp message and
        sends it.

        Parameters
        ----------
        supplier_id : str
            The supplier's unique identifier.
        template_id : int, optional
            Questionnaire template ID. When ``0`` (default), selects the
            first active template for the supplier's tier.

        Returns
        -------
        dict
            Status, message ID, and the formatted message body.
        """
        conn = get_connection()
        try:
            supplier = _fetchone(
                conn,
                "SELECT id, name, phone, tier, org_id, country FROM suppliers WHERE id = ?",
                (supplier_id,),
            )
            if supplier is None:
                return {
                    "status": "error",
                    "detail": f"Supplier {supplier_id} not found",
                }

            phone = supplier["phone"]
            if not phone:
                return {
                    "status": "error",
                    "detail": f"Supplier {supplier['name']} has no phone number on file",
                }

            # Fetch template
            template = self._resolve_template(conn, template_id, supplier)
            if template is None:
                return {
                    "status": "error",
                    "detail": "No active questionnaire template found",
                }

            questions = json.loads(template["questions"])
            country_code = supplier.get("country", "")
            body = self._format_questionnaire(
                supplier["name"], questions, template["name"], country_code
            )

            result = self.send_message(phone, body)

            # Log outbound message
            _execute(
                conn,
                """INSERT INTO whatsapp_messages
                   (org_id, supplier_id, template_id, direction, phone, body, twilio_message_sid)
                   VALUES (?, ?, ?, 'outbound', ?, ?, ?)""",
                (
                    supplier.get("org_id", ""),
                    supplier_id,
                    template["id"],
                    self._format_phone(phone),
                    body,
                    result.get("message_sid", ""),
                ),
            )

            # Update supplier questionnaire status and record sent timestamp
            _execute(
                conn,
                (
                    "UPDATE suppliers "
                    "SET questionnaire_status = 'pending', "
                    "questionnaire_sent_at = datetime('now'), "
                    "updated_at = datetime('now') "
                    "WHERE id = ?"
                ),
                (supplier_id,),
            )

            return {
                "status": result["status"],
                "message_sid": result.get("message_sid", ""),
                "to": result.get("to", ""),
                "supplier_name": supplier["name"],
                "template_name": template["name"],
                "question_count": len(questions),
            }
        finally:
            release_connection(conn)

    def send_risk_alert(self, supplier_id: str, alert_text: str) -> dict[str, Any]:
        """Send a risk alert notification to a supplier via WhatsApp.

        Parameters
        ----------
        supplier_id : str
            The supplier's unique identifier.
        alert_text : str
            The alert message to send.

        Returns
        -------
        dict
            Delivery status and message metadata.
        """
        conn = get_connection()
        try:
            supplier = _fetchone(
                conn,
                "SELECT id, name, phone, org_id FROM suppliers WHERE id = ?",
                (supplier_id,),
            )
            if supplier is None:
                return {
                    "status": "error",
                    "detail": f"Supplier {supplier_id} not found",
                }

            phone = supplier["phone"]
            if not phone:
                return {
                    "status": "error",
                    "detail": f"Supplier {supplier['name']} has no phone number on file",
                }

            body = (
                f"ESG Risk Alert\n\n"
                f"Dear {supplier['name']} Team,\n\n"
                f"{alert_text}\n\n"
                f"Please review and respond at your earliest convenience.\n\n"
                f"- ESG Platform"
            )

            result = self.send_message(phone, body)

            _execute(
                conn,
                """INSERT INTO whatsapp_messages
                   (org_id, supplier_id, direction, phone, body, twilio_message_sid)
                   VALUES (?, ?, 'outbound', ?, ?, ?)""",
                (
                    supplier.get("org_id", ""),
                    supplier_id,
                    self._format_phone(phone),
                    body,
                    result.get("message_sid", ""),
                ),
            )

            return {
                "status": result["status"],
                "message_sid": result.get("message_sid", ""),
                "to": result.get("to", ""),
                "supplier_name": supplier["name"],
            }
        finally:
            release_connection(conn)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_phone(phone: str) -> str:
        """Ensure a phone number has the ``whatsapp:+`` prefix."""
        phone = phone.strip()
        if phone.startswith("whatsapp:"):
            return phone
        if not phone.startswith("+"):
            phone = f"+{phone}"
        return f"whatsapp:{phone}"

    @staticmethod
    def _resolve_template(conn: Any, template_id: int, supplier: dict) -> Optional[dict]:
        """Fetch a questionnaire template from the database.

        If *template_id* is 0, picks the first active template matching
        the supplier's tier.
        """
        if template_id:
            return _fetchone(
                conn,
                "SELECT * FROM questionnaire_templates WHERE id = ? AND is_active = 1",
                (template_id,),
            )

        tier_map = {"tier1": 1, "tier2": 2, "tier3": 3}
        tier_num = tier_map.get(supplier.get("tier", ""), 1)
        org_id = supplier.get("org_id", "")

        template = _fetchone(
            conn,
            (
                "SELECT * FROM questionnaire_templates "
                "WHERE tier = ? AND is_active = 1 AND (org_id = ? OR org_id = '') "
                "ORDER BY id LIMIT 1"
            ),
            (tier_num, org_id),
        )
        if template is None:
            template = _fetchone(
                conn,
                "SELECT * FROM questionnaire_templates WHERE is_active = 1 ORDER BY id LIMIT 1",
                (),
            )
        return template

    @staticmethod
    def _format_questionnaire(
        supplier_name: str, questions: list[dict], template_name: str, country_code: str = ""
    ) -> str:
        """Build a human-readable WhatsApp message body from questions.

        Selects translated question text when available for the supplier's country:
        - BD/BGD → Bengali (question_text_bn)
        - VN/VNM → Vietnamese (question_text_vi)
        Falls back to the default question text otherwise.
        """
        lines: list[str] = []
        for i, q in enumerate(questions, 1):
            text = q.get("text", q.get("question", ""))
            # Auto-language dispatch: prefer translated text when available
            if country_code in ("BD", "BGD") and q.get("text_bn"):
                text = q["text_bn"]
            elif country_code in ("VN", "VNM") and q.get("text_vi"):
                text = q["text_vi"]
            unit = q.get("unit", "")
            lines.append(f"{i}. {text}")
            if unit:
                lines.append(f"   Reply: {i}. [value in {unit}]")
            else:
                lines.append(f"   Reply: {i}. [your answer]")

        return (
            f"ESG Questionnaire: {template_name}\n\n"
            f"Dear {supplier_name} Team,\n\n"
            f"Please respond to the following questions by replying with "
            f"the question number and your answer.\n\n"
            f"{chr(10).join(lines)}\n\n"
            f"- ESG Platform"
        )


def verify_webhook(token: str, body: bytes, signature: str) -> bool:
    """Verify an incoming Twilio webhook request signature.

    Parameters
    ----------
    token : str
        The Twilio auth token used to compute the expected signature.
    body : bytes
        Raw request body bytes.
    signature : str
        The ``X-Twilio-Signature`` header from the incoming request.

    Returns
    -------
    bool
        ``True`` when the signature is valid, ``False`` otherwise.
    """
    if not token or not signature:
        return False

    expected = hmac.new(
        token.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
