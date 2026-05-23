"""
Questionnaire API — backed by SQLite database + questionnaire engine.
"""

from __future__ import annotations
from typing import Optional

import logging
import re

from fastapi import APIRouter, Depends, Body, HTTPException, Query

from src.api.middleware.auth import require_auth
from src.db.database import (
    fetch_suppliers,
    fetch_supplier,
    fetch_coverage_stats,
    fetch_response_based_coverage,
    get_connection,
    release_connection,
    _fetchall,
    _fetchone,
    _execute,
    is_postgres as _is_postgres,
    validate_response_value,
)
from src.supplier.questionnaire import (
    get_tier_questions,
    get_all_tiers,
    TIER_NAMES,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/suppliers")
def list_suppliers(
    user: dict = Depends(require_auth),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
):
    org_id = user["org_id"]
    suppliers = fetch_suppliers(org_id=org_id)
    return {"suppliers": suppliers, "total": len(suppliers)}


@router.get("/questionnaire/{qnr_id}")
def get_questionnaire(qnr_id: str, user: dict = Depends(require_auth)):
    """Get a questionnaire template with its questions and responses.

    Looks up the template by ID from questionnaire_templates, fetches
    questions from questionnaire_questions, responses from
    questionnaire_responses, and supplier info from suppliers.
    Progress is calculated from actual response data.
    """
    from fastapi import HTTPException

    org_id = user["org_id"]
    conn = get_connection()
    try:
        # 1. Fetch template
        template = _fetchone(
            conn,
            """
            SELECT id, org_id, name, description, tier, category, is_active,
                   created_at, updated_at
            FROM questionnaire_templates
            WHERE id = ?
        """,
            (qnr_id,),
        )
        if not template:
            raise HTTPException(status_code=404, detail="Questionnaire not found")

        # Org isolation: only allow access to templates belonging to this org
        # or global templates (org_id is empty/null)
        if template["org_id"] and template["org_id"] != org_id:
            raise HTTPException(status_code=404, detail="Questionnaire not found")

        template_id = template["id"]

        # 2. Fetch questions for this template
        question_rows = _fetchall(
            conn,
            """
            SELECT id, template_id, question_text, question_type, choices,
                   sort_order, required
            FROM questionnaire_questions
            WHERE template_id = ?
            ORDER BY sort_order
        """,
            (template_id,),
        )

        # 3. Fetch responses for these questions, scoped to this org
        # Responses use question_id as a text field; join to match by question id
        question_ids = [str(q["id"]) for q in question_rows]
        if question_ids:
            placeholders = ",".join("?" for _ in question_ids)
            response_rows = _fetchall(
                conn,
                f"""
                SELECT qr.supplier_id, qr.question_id, qr.response_text,
                       qr.response_value, qr.channel, qr.responded_at,
                       s.name as supplier_name
                FROM questionnaire_responses qr
                LEFT JOIN suppliers s ON qr.supplier_id = s.id
                WHERE qr.question_id IN ({placeholders})
                  AND qr.org_id = ?
                ORDER BY qr.responded_at
            """,
                (*question_ids, org_id),
            )
        else:
            response_rows = []

        # 4. Build a lookup: question_id -> list of responses
        response_map = {}
        responded_suppliers = set()
        for r in response_rows:
            qid = str(r["question_id"])
            response_map.setdefault(qid, []).append(r)
            responded_suppliers.add(r["supplier_id"])

        # 5. Assemble questions with response info
        questions_out = []
        answered_count = 0
        for idx, q in enumerate(question_rows):
            qid = str(q["id"])
            responses = response_map.get(qid, [])
            has_response = len(responses) > 0
            if has_response:
                answered_count += 1

            # Use the latest response for display
            latest = responses[-1] if responses else None
            questions_out.append(
                {
                    "id": q["id"],
                    "number": str(idx + 1),
                    "text": q["question_text"],
                    "question_type": q["question_type"],
                    "choices": q["choices"],
                    "sort_order": q["sort_order"],
                    "required": bool(q["required"]),
                    "answered": has_response,
                    "response_text": latest["response_text"] if latest else None,
                    "response_value": latest["response_value"] if latest else None,
                    "supplier_id": latest["supplier_id"] if latest else None,
                    "supplier_name": latest["supplier_name"] if latest else None,
                    "channel": latest["channel"] if latest else None,
                    "submitted_at": latest["responded_at"] if latest else None,
                }
            )

        total_questions = len(question_rows)
        pending = total_questions - answered_count

        # 6. Determine status from progress
        if answered_count == 0:
            status = "not_responded"
        elif answered_count < total_questions:
            status = "partially_responded"
        else:
            status = "completed"

        return {
            "id": template_id,
            "name": template["name"],
            "description": template["description"],
            "tier": template["tier"],
            "category": template["category"],
            "is_active": bool(template["is_active"]),
            "created_at": template["created_at"],
            "updated_at": template["updated_at"],
            "status": status,
            "responded_suppliers": len(responded_suppliers),
            "questions": questions_out,
            "progress": {
                "answered": answered_count,
                "total": total_questions,
                "pending": pending,
            },
        }
    finally:
        release_connection(conn)


@router.get("/suppliers/{supplier_id}")
def get_supplier_questionnaire_data(supplier_id: str, user: dict = Depends(require_auth)):
    """Get a supplier's questionnaire: questions with translations and existing responses.

    Used by SupplierEngagementTab for manual entry and response detail views.
    Fetches the active template for the supplier's tier, returns questions with
    text_bn/text_vi translations, and any existing responses for this supplier.

    Returns: { supplier, template, questions, responses, status }
    """
    from fastapi import HTTPException

    org_id = user["org_id"]

    # 1. Fetch supplier and verify org membership
    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if supplier.get("org_id") and supplier["org_id"] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    conn = get_connection()
    try:
        # 2. Resolve active template for this supplier's tier
        tier_map = {"tier1": 1, "tier2": 2, "tier3": 3, "tier4": 4}
        tier_str = str(supplier.get("tier", "tier1")).lower()
        tier_num = tier_map.get(tier_str, 1)

        template = _fetchone(
            conn,
            """
            SELECT * FROM questionnaire_templates
            WHERE tier = ? AND is_active = 1
              AND (org_id = ? OR org_id = '' OR org_id IS NULL)
            ORDER BY CASE WHEN org_id = ? THEN 0 ELSE 1 END, id
            LIMIT 1
        """,
            (tier_num, org_id, org_id),
        )

        if not template:
            return {
                "supplier": supplier,
                "template": None,
                "questions": [],
                "responses": [],
                "status": "no_template",
            }

        template_id = template["id"]

        # 3. Fetch questions with bilingual text
        country_code = supplier.get("country", "")
        question_rows = _fetchall(
            conn,
            """
            SELECT id, question_id, question_text, question_text_bn, question_text_vi,
                   question_type, choices, sort_order, required
            FROM questionnaire_questions
            WHERE template_id = ?
            ORDER BY sort_order
        """,
            (template_id,),
        )

        # 4. Fetch existing responses for this supplier
        response_rows = _fetchall(
            conn,
            """
            SELECT qr.*, qq.question_id as q_id
            FROM questionnaire_responses qr
            JOIN questionnaire_questions qq ON qr.question_id = qq.id
            WHERE qr.supplier_id = ? AND qq.template_id = ?
            ORDER BY qq.sort_order
        """,
            (supplier_id, template_id),
        )

        # Build response lookup: question_id -> latest response
        response_map: dict[str, dict] = {}
        for r in response_rows:
            q_id = str(r["question_id"])
            if q_id not in response_map:
                response_map[q_id] = r

        # 5. Build questions with response info
        questions_out = []
        answered_count = 0
        for q in question_rows:
            q_id = str(q["question_id"])
            resp = response_map.get(q_id)
            has_response = resp is not None
            if has_response:
                answered_count += 1

            # Auto-language dispatch for question text
            text = q["question_text"]
            if country_code in ("BD", "BGD") and q["question_text_bn"]:
                text = q["question_text_bn"]
            elif country_code in ("VN", "VNM") and q["question_text_vi"]:
                text = q["question_text_vi"]

            questions_out.append(
                {
                    "id": q["id"],
                    "question_id": q_id,
                    "text": text,
                    "text_en": q["question_text"],
                    "text_bn": q["question_text_bn"] or "",
                    "text_vi": q["question_text_vi"] or "",
                    "question_type": q["question_type"],
                    "choices": q["choices"],
                    "sort_order": q["sort_order"],
                    "required": bool(q["required"]),
                    "answered": has_response,
                    "responses": [resp] if resp else [],
                }
            )

        total_questions = len(question_rows)
        if answered_count == 0:
            status = "not_responded"
        elif answered_count < total_questions:
            status = "partially_responded"
        else:
            status = "completed"

        return {
            "supplier": supplier,
            "template": {
                "id": template["id"],
                "name": template["name"],
                "description": template["description"],
                "tier": template["tier"],
                "category": template["category"],
            },
            "questions": questions_out,
            "responses": response_rows,
            "status": status,
            "progress": {
                "answered": answered_count,
                "total": total_questions,
                "pending": total_questions - answered_count,
            },
        }
    finally:
        release_connection(conn)


@router.get("/whatsapp-preview/{supplier_id}")
def whatsapp_preview(supplier_id: str, user: dict = Depends(require_auth)):
    """Preview what the questionnaire looks like when sent via WhatsApp.

    Returns the WhatsApp message body, a sample supplier response, and
    the coverage impact of this supplier joining the responded pool.

    Steps:
      1. Look up supplier, verify org membership
      2. Find the latest active template for this org
      3. Build message_preview from questions (same format as WhatsAppClient._format_questionnaire)
      4. Build supplier_response_example from question types / units
      5. Compute coverage_impact (spend share + delta to spend-weighted coverage)
    """
    org_id = user["org_id"]

    # 1. Look up the supplier and verify it belongs to the user's org
    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if supplier.get("org_id") and supplier["org_id"] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    conn = get_connection()
    try:
        # 2. Find the latest active template for this org
        template_row = _fetchone(
            conn,
            """
            SELECT id, name, description, tier, category, is_active
            FROM questionnaire_templates
            WHERE (org_id = ? OR org_id = '' OR org_id IS NULL)
              AND is_active = 1
            ORDER BY CASE WHEN org_id = ? THEN 0 ELSE 1 END, created_at DESC
            LIMIT 1
        """,
            (org_id, org_id),
        )

        # 3. Build message_preview and supplier_response_example
        if not template_row:
            message_preview = (
                f"ESG Questionnaire\n\n"
                f"Dear {supplier['name']} Team,\n\n"
                f"No active questionnaire template is configured for your organisation. "
                f"Please contact your ESG team for next steps.\n\n"
                f"- ESG Platform"
            )
            supplier_response_example = ""
            coverage_impact = {
                "supplier_name": supplier["name"],
                "annual_spend": supplier.get("annual_spend_usd", 0) or 0.0,
                "coverage_added": "0.0%",
                "new_total_coverage": "0.0%",
            }
        else:
            template_id = template_row["id"]

            # Get questions with sort_order
            question_rows = _fetchall(
                conn,
                """
                SELECT id, question_text, question_type, choices, sort_order, required
                FROM questionnaire_questions
                WHERE template_id = ?
                ORDER BY sort_order
            """,
                (template_id,),
            )

            # Build message_preview using the same format as WhatsAppClient._format_questionnaire
            lines: list[str] = []
            response_parts: list[str] = []
            for i, q in enumerate(question_rows, 1):
                text = q["question_text"]
                qtype = q["question_type"]
                lines.append(f"{i}. {text}")
                if qtype == "number":
                    lines.append(f"   Reply: {i}. [value in unit]")
                elif qtype == "choice":
                    lines.append(f"   Reply: {i}. [your answer]")
                else:
                    lines.append(f"   Reply: {i}. [your answer]")

                # Build supplier_response_example from first few questions
                if i <= 5:
                    if qtype == "number":
                        response_parts.append(f"{i}. [number] [unit]")
                    elif qtype == "choice":
                        response_parts.append(f"{i}. [choice]")
                    else:
                        response_parts.append(f"{i}. [text answer]")

            message_preview = (
                f"ESG Questionnaire: {template_row['name']}\n\n"
                f"Dear {supplier['name']} Team,\n\n"
                f"Please respond to the following questions by replying with "
                f"the question number and your answer.\n\n"
                f"{chr(10).join(lines)}\n\n"
                f"- ESG Platform"
            )
            supplier_response_example = "\n".join(response_parts)

            # 4. Compute coverage_impact
            supplier_spend = supplier.get("annual_spend_usd", 0) or 0.0

            # Total org spend across all suppliers
            total_row = _fetchone(
                conn,
                """
                SELECT COALESCE(SUM(annual_spend_usd), 0) as total
                FROM suppliers WHERE org_id = ?
            """,
                (org_id,),
            )
            total_org_spend = total_row["total"] or 0.0

            current = fetch_response_based_coverage(org_id)
            current_coverage = current.get("spend_weighted_coverage_pct", 0.0)

            if total_org_spend > 0:
                coverage_added_pct = (supplier_spend / total_org_spend) * 100
            else:
                coverage_added_pct = 0.0

            new_total_coverage = current_coverage + coverage_added_pct

            coverage_impact = {
                "supplier_name": supplier["name"],
                "annual_spend": supplier_spend,
                "coverage_added": f"{coverage_added_pct:.1f}%",
                "new_total_coverage": f"{new_total_coverage:.1f}%",
            }

        logger.info(
            "whatsapp_preview.generated",
            extra={
                "org_id": org_id,
                "supplier_id": supplier_id,
                "template_id": template_row["id"] if template_row else None,
                "coverage_added_pct": coverage_impact["coverage_added"],
                "new_total_coverage": coverage_impact["new_total_coverage"],
            },
        )

        return {
            "message_preview": message_preview,
            "supplier_response_example": supplier_response_example,
            "coverage_impact": coverage_impact,
        }
    finally:
        release_connection(conn)


@router.get("/coverage")
def coverage_stats(user: dict = Depends(require_auth)):
    """Spend-weighted Scope 3 coverage calculator.

    Coverage is based on actual questionnaire_responses rows, not the
    questionnaire_status column.  A "responded" supplier is one with at
    least one row in questionnaire_responses for this org.
    """
    TARGET_COVERAGE_PCT = 60

    org_id = user["org_id"]
    coverage = fetch_response_based_coverage(org_id)

    spend_pct = coverage["spend_weighted_coverage_pct"]
    meets_target = spend_pct >= TARGET_COVERAGE_PCT

    return {
        "spend_weighted_coverage_pct": spend_pct,
        "headcount_coverage_pct": coverage["headcount_coverage_pct"],
        "total_spend_usd": coverage["total_spend_usd"],
        "covered_spend_usd": coverage["covered_spend_usd"],
        "total_suppliers": coverage["total_suppliers"],
        "responded_suppliers": coverage["responded_suppliers"],
        "target_coverage_pct": TARGET_COVERAGE_PCT,
        "meets_target": meets_target,
    }


@router.get("/coverage-stats")
def coverage_stats_v2(user: dict = Depends(require_auth)):
    org_id = user["org_id"]
    stats = fetch_coverage_stats(org_id=org_id)
    suppliers = fetch_suppliers(org_id=org_id)
    responded_spend = sum(
        s["annual_spend_usd"] for s in suppliers if s.get("questionnaire_status") == "responded"
    )
    total_spend = sum(s["annual_spend_usd"] for s in suppliers)
    return {
        "total_coverage": stats["spend_coverage_pct"],
        "headcount_coverage": stats["coverage_pct"],
        "responding_suppliers": stats["responding_suppliers"],
        "total_suppliers": stats["total_suppliers"],
        "total_spend_usd": total_spend,
        "covered_spend_usd": responded_spend,
    }


@router.get("/response-summary")
def response_summary(user: dict = Depends(require_auth)):
    """Aggregated response statistics for the engagement dashboard.

    Returns total_suppliers, total_responded, total_pending, response_rate,
    avg_confidence, by_channel breakdown, and org_id.
    """
    org_id = user["org_id"]
    conn = get_connection()
    try:
        total_suppliers_row = _fetchall(
            conn,
            """
            SELECT COUNT(*) as cnt FROM suppliers WHERE org_id = ?
        """,
            (org_id,),
        )
        total_suppliers = total_suppliers_row[0]["cnt"] if total_suppliers_row else 0

        responded_row = _fetchall(
            conn,
            """
            SELECT COUNT(DISTINCT supplier_id) as cnt
            FROM questionnaire_responses
            WHERE org_id = ?
        """,
            (org_id,),
        )
        total_responded = responded_row[0]["cnt"] if responded_row else 0
        # questionnaire_responses table does not have a confidence column;
        # avg_confidence defaults to 0 until the column is added.
        avg_confidence = 0.0

        channel_rows = _fetchall(
            conn,
            """
            SELECT channel, COUNT(*) as cnt
            FROM questionnaire_responses
            WHERE org_id = ?
            GROUP BY channel
        """,
            (org_id,),
        )
        by_channel = {}
        for row in channel_rows:
            by_channel[row["channel"]] = row["cnt"]

        total_pending = total_suppliers - total_responded
        response_rate = (
            round(total_responded / total_suppliers * 100, 1) if total_suppliers > 0 else 0
        )
    finally:
        release_connection(conn)

    return {
        "total_suppliers": total_suppliers,
        "total_responded": total_responded,
        "total_pending": total_pending,
        "response_rate": response_rate,
        "avg_confidence": round(avg_confidence, 2),
        "by_channel": by_channel,
        "org_id": org_id,
    }


@router.post("/send-email")
def send_questionnaire_by_email(
    body: dict,
    user: dict = Depends(require_auth),
):
    """Send an ESG questionnaire to a supplier via email.

    Falls back to email when WhatsApp is unavailable or when the supplier
    has no phone number on file. Sends a multipart HTML/text email with
    the questionnaire questions and reply instructions.

    Requires editor role.
    """
    from src.api.middleware.rbac import require_role, EDITOR_ROLES
    from src.connectors.email import get_email_client

    require_role(user, EDITOR_ROLES)

    supplier_id = body.get("supplier_id", "")
    if not supplier_id:
        raise HTTPException(status_code=400, detail="Missing required field: supplier_id")

    template_id = int(body.get("template_id", 0))
    org_id = user["org_id"]

    client = get_email_client()
    result = client.send_questionnaire(
        supplier_id=supplier_id,
        template_id=template_id,
        org_id=org_id,
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("detail", "Failed to send email"))

    return {
        "status": result.get("status"),
        "supplier_id": supplier_id,
        "supplier_name": result.get("supplier_name"),
        "to": result.get("to"),
        "template_name": result.get("template_name"),
        "question_count": result.get("question_count"),
        "smtp_message_id": result.get("smtp_message_id", ""),
    }


# ---------------------------------------------------------------------------
# POST /dispatch-bulk — Bulk questionnaire dispatch
# ---------------------------------------------------------------------------


@router.post("/dispatch-bulk")
def dispatch_bulk(
    body: dict,
    user: dict = Depends(require_auth),
):
    """Dispatch questionnaires to multiple suppliers in one call.

    Chooses the channel per supplier based on ``preferred_channel`` and
    phone availability: WhatsApp if the supplier has a phone number and
    ``preferred_channel`` is ``whatsapp``, otherwise email.

    Returns per-supplier status so the caller can display a summary
    of what succeeded and what failed.

    Requires editor role.
    """
    from src.api.middleware.rbac import require_role, EDITOR_ROLES
    from src.connectors.whatsapp import WhatsAppClient
    from src.connectors.email import get_email_client

    require_role(user, EDITOR_ROLES)

    supplier_ids = body.get("supplier_ids", [])
    template_id = int(body.get("template_id", 0))
    org_id = user["org_id"]

    if not supplier_ids:
        raise HTTPException(
            status_code=400, detail="supplier_ids is required and must be non-empty"
        )

    if not isinstance(supplier_ids, list):
        raise HTTPException(status_code=400, detail="supplier_ids must be a list")

    if len(supplier_ids) > 200:
        raise HTTPException(status_code=400, detail="supplier_ids may not exceed 200 per request")

    whatsapp_client = WhatsAppClient()
    email_client = get_email_client()

    conn = get_connection()
    results = []
    try:
        for sid in supplier_ids:
            supplier = _fetchone(
                conn,
                "SELECT id, name, phone, email, preferred_channel, org_id "
                "FROM suppliers WHERE id = ?",
                (sid,),
            )
            if not supplier:
                results.append(
                    {"supplier_id": sid, "status": "error", "detail": "Supplier not found"}
                )
                continue
            if supplier.get("org_id") and supplier["org_id"] != org_id:
                results.append({"supplier_id": sid, "status": "error", "detail": "Access denied"})
                continue

            phone = supplier.get("phone", "")
            channel = supplier.get("preferred_channel", "whatsapp")
            use_whatsapp = bool(phone and channel == "whatsapp")

            if use_whatsapp:
                result = whatsapp_client.send_questionnaire(
                    supplier_id=sid,
                    template_id=template_id,
                )
            else:
                result = email_client.send_questionnaire(
                    supplier_id=sid,
                    template_id=template_id,
                    org_id=org_id,
                )

            if result.get("status") in ("sent", "demo"):
                results.append(
                    {
                        "supplier_id": sid,
                        "supplier_name": supplier["name"],
                        "status": "dispatched",
                        "channel": "whatsapp" if use_whatsapp else "email",
                        "message_id": result.get("message_sid")
                        or result.get("smtp_message_id", ""),
                    }
                )
            else:
                results.append(
                    {
                        "supplier_id": sid,
                        "supplier_name": supplier["name"],
                        "status": "error",
                        "detail": result.get("detail", "Unknown error"),
                    }
                )
    finally:
        release_connection(conn)

    dispatched = sum(1 for r in results if r["status"] == "dispatched")
    errors = sum(1 for r in results if r["status"] == "error")

    logger.info(
        "dispatch_bulk.completed",
        extra={
            "org_id": org_id,
            "requested_by": user.get("sub", ""),
            "total": len(supplier_ids),
            "dispatched": dispatched,
            "errors": errors,
        },
    )

    return {
        "status": "ok",
        "total": len(supplier_ids),
        "dispatched": dispatched,
        "errors": errors,
        "results": results,
    }


@router.get("/non-responders")
def non_responders(user: dict = Depends(require_auth)):
    """List suppliers who haven't submitted any questionnaire responses.

    A supplier is a non-responder if their id is NOT in the set of distinct
    supplier_ids from questionnaire_responses for this org.
    Returns a flat list of supplier details.
    """
    org_id = user["org_id"]
    conn = get_connection()
    try:
        rows = _fetchall(
            conn,
            """
            SELECT s.id as supplier_id, s.name, s.country,
                   s.annual_spend_usd, s.tier
            FROM suppliers s
            WHERE s.org_id = ?
              AND s.id NOT IN (
                  SELECT DISTINCT supplier_id
                  FROM questionnaire_responses
                  WHERE org_id = ?
              )
            ORDER BY s.annual_spend_usd DESC
        """,
            (org_id, org_id),
        )
    finally:
        release_connection(conn)

    return rows


@router.get("/chasing-status")
def chasing_status(user: dict = Depends(require_auth)):
    """Return pending suppliers with their chase-workflow stage.

    Stages:
      - day 0-6: WhatsApp only (pending)
      - day 7-13: email reminder due
      - day 14+: risk flag raised

    Each row includes supplier info and the earliest WhatsApp message sent date.
    """
    org_id = user["org_id"]
    conn = get_connection()
    try:
        if _is_postgres():
            days_sql = """
                EXTRACT(EPOCH FROM (NOW() AT TIME ZONE 'UTC' - m.sent_at::TIMESTAMP)) / 86400.0
            """
        else:
            days_sql = """
                (julianday('now') - julianday(m.sent_at))
            """

        rows = _fetchall(
            conn,
            f"""
            SELECT
                s.id AS supplier_id,
                s.name,
                s.country,
                s.tier,
                s.questionnaire_status,
                m.sent_at,
                ({days_sql}) AS days_since_sent,
                CASE
                    WHEN ({days_sql}) >= 14 THEN 'risk_flag'
                    WHEN ({days_sql}) >= 7  THEN 'email_reminder'
                    ELSE 'whatsapp_pending'
                END AS stage
            FROM suppliers s
            LEFT JOIN whatsapp_messages m
                ON m.supplier_id = s.id
                AND m.org_id = s.org_id
            WHERE s.org_id = ?
              AND s.id NOT IN (
                  SELECT DISTINCT qr.supplier_id
                  FROM questionnaire_responses qr
                  WHERE qr.org_id = ?
              )
            ORDER BY ({days_sql}) DESC NULLS LAST
        """,
            (org_id, org_id),
        )
    finally:
        release_connection(conn)

    for row in rows:
        row["days_since_sent"] = round(row["days_since_sent"] or 0, 1)
    return rows


# ---------------------------------------------------------------------------
# POST /responses/manual — Manual data entry by staff
# ---------------------------------------------------------------------------


@router.post("/responses/manual")
def submit_manual_response(
    payload: dict = Body(...),
    user: dict = Depends(require_auth),
):
    """Record questionnaire responses entered manually by staff on behalf of a supplier.

    Staff enter responses collected via phone, email, or in-person on the
    supplier's behalf. Responses are stored with ``channel='manual'`` and
    ``confidence='LOW'`` since they could not be verified against the
    supplier's own submission.

    Accepts JSON body::

        {
            "supplier_id": "sup_001",
            "responses": [
                {"question_id": "1", "response_text": "...", "response_value": 123.4},
                ...
            ]
        }

    Each question_id is matched against questionnaire_questions.id.  If a
    supplier has already responded to a question, the prior response is
    replaced (upsert semantics).
    """
    from src.api.middleware.rbac import require_role, EDITOR_ROLES
    from fastapi import HTTPException

    require_role(user, EDITOR_ROLES)

    supplier_id = payload.get("supplier_id", "")
    responses = payload.get("responses", [])

    if not supplier_id:
        raise HTTPException(status_code=400, detail="supplier_id is required")
    if not isinstance(responses, list) or not responses:
        raise HTTPException(status_code=400, detail="responses must be a non-empty list")

    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if supplier.get("org_id") and supplier["org_id"] != user["org_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    org_id = user["org_id"]
    supplier_name = supplier.get("name", supplier_id)
    tier = supplier.get("tier", "tier3")
    tier_num = {"tier1": 1, "tier2": 2, "tier3": 3}.get(tier, 3)

    # Capture previous coverage before responses are entered
    prev_coverage = fetch_response_based_coverage(org_id)
    prev_coverage_pct = prev_coverage["spend_weighted_coverage_pct"]

    conn = get_connection()
    try:
        entered = 0
        for item in responses:
            question_id = str(item.get("question_id", ""))
            response_text = item.get("response_text", "")
            response_value = item.get("response_value")

            # Parse numeric value for validation
            numeric_value: Optional[float] = None
            try:
                if response_value is not None:
                    numeric_value = float(str(response_value).replace(",", ""))
            except (ValueError, TypeError):
                pass

            # Validate numeric responses against spend-based sanity bounds
            if numeric_value is not None:
                validation_status, validation_notes = validate_response_value(
                    supplier, question_id, numeric_value
                )
            else:
                validation_status, validation_notes = "verified", ""

            if _is_postgres():
                _execute(
                    conn,
                    """
                    INSERT INTO questionnaire_responses
                        (org_id, supplier_id, tier, question_id, response_text,
                         response_value, channel, validation_status, validation_notes,
                         responded_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'manual', ?, ?, NOW())
                    ON CONFLICT (org_id, supplier_id, question_id)
                    DO UPDATE SET
                        response_text = EXCLUDED.response_text,
                        response_value = EXCLUDED.response_value,
                        validation_status = EXCLUDED.validation_status,
                        validation_notes = EXCLUDED.validation_notes,
                        responded_at = NOW()
                """,
                    (
                        org_id,
                        supplier_id,
                        tier_num,
                        question_id,
                        response_text,
                        numeric_value,
                        validation_status,
                        validation_notes,
                    ),
                )
            else:
                # SQLite: delete existing row then insert (upsert without ON CONFLICT)
                _execute(
                    conn,
                    """
                    DELETE FROM questionnaire_responses
                    WHERE org_id = ? AND supplier_id = ? AND question_id = ?
                """,
                    (org_id, supplier_id, question_id),
                )
                _execute(
                    conn,
                    """
                    INSERT INTO questionnaire_responses
                        (org_id, supplier_id, tier, question_id, response_text,
                         response_value, channel, validation_status, validation_notes,
                         responded_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'manual', ?, ?,
                            datetime('now'))
                """,
                    (
                        org_id,
                        supplier_id,
                        tier_num,
                        question_id,
                        response_text,
                        numeric_value,
                        validation_status,
                        validation_notes,
                    ),
                )

            entered += 1

        _execute(
            conn,
            """
            UPDATE suppliers
            SET questionnaire_status = 'responded', updated_at = datetime('now')
            WHERE id = ?
        """,
            (supplier_id,),
        )

        # Send coverage notification after responses are recorded
        if entered > 0:
            _send_coverage_notification(org_id, supplier_name, prev_coverage_pct)

    finally:
        release_connection(conn)

    logger.info(
        "questionnaire.manual_response",
        extra={
            "org_id": org_id,
            "supplier_id": supplier_id,
            "response_count": entered,
            "entered_by": user.get("sub", ""),
        },
    )

    return {
        "status": "success",
        "supplier_id": supplier_id,
        "responses_entered": entered,
    }


@router.get("/responses/{supplier_id}")
def supplier_responses(supplier_id: str, user: dict = Depends(require_auth)):
    """Individual questionnaire responses for a supplier.

    Returns a flat list of responses joined with question text from
    questionnaire_questions. Org-scoped, verifies supplier belongs to org.
    """
    from fastapi import HTTPException

    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if supplier.get("org_id") and supplier["org_id"] != user["org_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    org_id = user["org_id"]
    conn = get_connection()
    try:
        rows = _fetchall(
            conn,
            """
            SELECT
                qr.question_id,
                qq.question_text,
                qr.response_value,
                qr.response_text,
                qr.channel,
                qr.responded_at as received_at
            FROM questionnaire_responses qr
            LEFT JOIN questionnaire_questions qq
                ON qr.question_id = CAST(qq.id AS TEXT)
            WHERE qr.supplier_id = ? AND qr.org_id = ?
            ORDER BY qr.responded_at
        """,
            (supplier_id, org_id),
        )
    finally:
        release_connection(conn)

    return rows


@router.get("/prefill/{supplier_id}")
def supplier_prefill(supplier_id: str, tier: int = 1, user: dict = Depends(require_auth)):
    """Pre-computed fill values for a supplier's questionnaire.

    Returns spend-based expected values and any existing Scope 3 records
    for the supplier, so the portal can pre-populate numeric fields
    with estimates and actual data rather than leaving them blank.

    Only org-scoped suppliers are accessible.
    """
    from fastapi import HTTPException

    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if supplier.get("org_id") and supplier["org_id"] != user["org_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    org_id = user["org_id"]
    spend = supplier.get("annual_spend_usd") or 0

    conn = get_connection()
    try:
        # Fetch any existing Scope 3 records for this supplier
        scope3_rows = _fetchall(
            conn,
            """
            SELECT category, annual_spend_usd, scope3_tco2e,
                   calculation_method, data_source, recorded_at
            FROM supplier_scope3
            WHERE supplier_id = ? AND org_id = ?
        """,
            (supplier_id, org_id),
        )
    finally:
        release_connection(conn)

    # Spend-based intensity factors for energy questions (same as validation)
    spend_intensity: dict[str, tuple[float, str]] = {
        "t1e_01": (0.5, "kWh"),  # electricity kWh per USD spend
        "t1e_02": (0.005, "L"),  # diesel litres per USD spend
    }

    prefill: dict[str, dict] = {}

    # Spend-based computed values
    if spend > 0:
        for qid, (intensity, unit) in spend_intensity.items():
            expected = spend * intensity
            prefill[qid] = {
                "value": expected,
                "unit": unit,
                "source": "computed:spend-based",
                "method": f"annual_spend_usd ({spend}) × intensity factor ({intensity} {unit}/USD)",
                "confidence": "medium",
            }

    # Actual Scope 1 / Scope 2 data from supplier records (overrides spend-based estimates)
    # GHG Protocol categories that map to Scope 1 and Scope 2 questionnaire questions
    scope1_qid = "t1e_03"  # "Have you measured your Scope 1 emissions?"
    scope2_qid = "t1e_04"  # "Have you measured your Scope 2 emissions?"
    scope1_cats = {"FUEL_COMBUSTION", "STATIONARY_COMBUSTION", "SCOPE1", "MOBILE_COMBUSTION"}
    scope2_cats = {"PURCHASED_GOODS", "PURCHASED_GOODS_SERVICES", "SCOPE2", "ELECTRICITY"}

    for row in scope3_rows:
        cat = str(row.get("category", "")).upper()
        tco2e = row.get("scope3_tco2e")
        if tco2e is None:
            continue
        if cat in scope2_cats:
            prefill[scope2_qid] = {
                "value": tco2e,
                "unit": "tCO2e",
                "source": "supplier_scope3",
                "method": row.get("calculation_method", "unknown"),
                "data_source": row.get("data_source", ""),
                "confidence": row.get("confidence", "LOW"),
            }
        elif cat in scope1_cats:
            prefill[scope1_qid] = {
                "value": tco2e,
                "unit": "tCO2e",
                "source": "supplier_scope3",
                "method": row.get("calculation_method", "unknown"),
                "data_source": row.get("data_source", ""),
                "confidence": row.get("confidence", "LOW"),
            }

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier.get("name", ""),
        "tier": tier,
        "annual_spend_usd": spend,
        "prefill": prefill,
        "scope3_records": scope3_rows,
    }


@router.get("/timeline/{supplier_id}")
def supplier_timeline(supplier_id: str, user: dict = Depends(require_auth)):
    """Historical response trajectory for a supplier.

    Returns period-over-period comparison of questionnaire responses,
    showing coverage trends and per-question value trajectories.

    Only org-scoped suppliers are accessible.
    """
    from fastapi import HTTPException

    supplier = fetch_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if supplier.get("org_id") and supplier["org_id"] != user["org_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    org_id = user["org_id"]
    conn = get_connection()
    try:
        # Fetch all responses for this supplier, ordered by time
        all_rows = _fetchall(
            conn,
            """
            SELECT
                qr.question_id,
                qr.response_value,
                qr.response_text,
                qr.validation_status,
                qr.responded_at
            FROM questionnaire_responses qr
            WHERE qr.supplier_id = ? AND qr.org_id = ?
            ORDER BY qr.responded_at
        """,
            (supplier_id, org_id),
        )
    finally:
        release_connection(conn)

    # Group rows by YYYY-MM period
    from collections import defaultdict

    periods_dict: dict[str, list] = defaultdict(list)
    for row in all_rows:
        responded_at = row.get("responded_at") or ""
        period = responded_at[:7] if responded_at else "unknown"
        periods_dict[period].append(row)

    # Build ordered period list (newest first)
    sorted_periods = sorted(periods_dict.keys(), reverse=True)

    # Build per-question value series across periods
    question_series: dict[str, dict[str, Optional[float]]] = defaultdict(dict)
    for period, rows in periods_dict.items():
        for row in rows:
            qid = row.get("question_id", "")
            if qid and row.get("response_value") is not None:
                question_series[qid][period] = row["response_value"]

    # Build period snapshots
    period_snapshots = []
    for period in sorted_periods:
        rows = periods_dict[period]
        unique_questions = len({r.get("question_id") for r in rows})
        # Coverage for this period: count of unique questions with responses
        # We'll compute a simple coverage ratio vs total possible questions
        period_snapshots.append(
            {
                "period": period,
                "responded_at": rows[0].get("responded_at", ""),
                "questions_answered": unique_questions,
                "total_responses": len(rows),
            }
        )

    # Build per-question trends
    trends = []
    for qid, series in sorted(question_series.items()):
        sorted_series_periods = sorted(series.keys(), reverse=True)  # newest first
        if len(sorted_series_periods) < 2:
            trajectory = "insufficient_data"
            change_pct = None
        else:
            latest_val = series[sorted_series_periods[0]]
            prev_val = series[sorted_series_periods[1]]
            if latest_val is None or prev_val is None or prev_val == 0:
                trajectory = "insufficient_data"
                change_pct = None
            else:
                change_pct = ((latest_val - prev_val) / abs(prev_val)) * 100
                if change_pct > 5:
                    trajectory = "up"
                elif change_pct < -5:
                    trajectory = "down"
                else:
                    trajectory = "stable"

        trends.append(
            {
                "question_id": qid,
                "trajectory": trajectory,
                "change_pct": change_pct,
                "latest_value": series.get(sorted_series_periods[0])
                if sorted_series_periods
                else None,
                "previous_value": series.get(sorted_series_periods[1])
                if len(sorted_series_periods) > 1
                else None,
                "period_count": len(sorted_series_periods),
            }
        )

    # Overall trajectory: compare coverage across periods
    overall_trajectory = "no_data"
    coverage_change_pct = None
    if len(period_snapshots) == 0:
        overall_trajectory = "no_data"
    elif len(period_snapshots) == 1:
        overall_trajectory = "insufficient_data"
    else:
        latest_qs = period_snapshots[0]["questions_answered"]
        earliest_qs = period_snapshots[-1]["questions_answered"]
        if earliest_qs > 0:
            coverage_change_pct = ((latest_qs - earliest_qs) / earliest_qs) * 100
            if coverage_change_pct > 10:
                overall_trajectory = "improving"
            elif coverage_change_pct < -10:
                overall_trajectory = "declining"
            else:
                overall_trajectory = "stable"
        else:
            overall_trajectory = "insufficient_data"

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier.get("name", ""),
        "periods": period_snapshots,
        "trends": trends,
        "summary": {
            "total_periods": len(period_snapshots),
            "coverage_change_pct": coverage_change_pct,
            "overall_trajectory": overall_trajectory,
        },
    }


@router.post("/resend")
def resend_questionnaire(
    payload: dict = Body(default={}),
    user: dict = Depends(require_auth),
):
    """Resend questionnaire to specified suppliers.

    Accepts JSON body: {"supplier_ids": [...], "template_id": "..."}.
    Logs the resend action and returns success. Actual WhatsApp sending
    is handled by the existing WhatsApp integration.
    """
    from src.db.database import _execute

    org_id = user["org_id"]
    supplier_ids = payload.get("supplier_ids", [])
    template_id = payload.get("template_id", "")

    # Validate supplier_ids belong to this org
    suppliers = fetch_suppliers(org_id=org_id)
    org_supplier_ids = {s["id"] for s in suppliers}
    target_ids = [sid for sid in supplier_ids if sid in org_supplier_ids]

    logger.info(
        "questionnaire.resend",
        extra={
            "org_id": org_id,
            "supplier_ids": target_ids,
            "template_id": template_id,
            "requested_by": user.get("sub", ""),
        },
    )

    conn = get_connection()
    try:
        for sid in target_ids:
            _execute(
                conn,
                """
                UPDATE suppliers
                SET questionnaire_status = 'pending',
                    questionnaire_sent_at = COALESCE(questionnaire_sent_at, datetime('now')),
                    updated_at = datetime('now')
                WHERE id = ?
            """,
                (sid,),
            )
    finally:
        release_connection(conn)

    return {
        "status": "success",
        "resent_count": len(target_ids),
        "supplier_ids": target_ids,
    }


# ---------------------------------------------------------------------------
# POST /chase — Automated escalation workflow
# ---------------------------------------------------------------------------


@router.post("/chase")
def run_chase_workflow(
    dry_run: bool = False,
    user: dict = Depends(require_auth),
):
    """Run the questionnaire chasing workflow for the org.

    Escalation timeline:
      - Day 0  : WhatsApp/email sent → questionnaire_status = 'pending'
      - Day 7+ : Email reminder sent (one time) if no response yet
      - Day 14+: Risk flag raised, questionnaire_status = 'non_responsive'

    This endpoint is intended to be called by an external scheduler (e.g. cron)
    on a daily cadence. Set dry_run=true to see what would happen without
    making any changes.

    Returns counts and details of suppliers acted upon at each tier.
    """
    from src.api.middleware.rbac import require_role, EDITOR_ROLES
    from src.connectors.email import get_email_client
    import uuid

    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    # Day thresholds
    EMAIL_REMINDER_DAYS = 7
    NONRESPONSIVE_DAYS = 14

    # Date arithmetic differs by dialect
    if _is_postgres():
        days_since_sql = """
            EXTRACT(EPOCH FROM (
                NOW() AT TIME ZONE 'UTC' - questionnaire_sent_at::TIMESTAMP
            )) / 86400.0
        """
    else:
        days_since_sql = """
            julianday('now') - julianday(questionnaire_sent_at)
        """

    conn = get_connection()
    try:
        # Find all pending suppliers with a sent timestamp
        pending = _fetchall(
            conn,
            f"""
            SELECT
                s.id,
                s.name,
                s.email,
                s.phone,
                s.preferred_channel,
                s.questionnaire_sent_at,
                s.email_reminder_sent,
                ({days_since_sql}) AS days_since_sent
            FROM suppliers s
            WHERE s.org_id = ?
              AND s.questionnaire_status = 'pending'
              AND s.questionnaire_sent_at IS NOT NULL
            ORDER BY s.questionnaire_sent_at ASC
        """,
            (org_id,),
        )

        email_reminders_sent = []
        email_reminder_errors = []
        nonresponsive = []
        already_email_reminded = []
        not_yet_due_for_email = []
        not_yet_due_for_nonresponsive = []

        email_client = get_email_client()

        for sup in pending:
            sid = sup["id"]
            days = float(sup["days_since_sent"]) if sup["days_since_sent"] else 0.0
            reminder_needed = sup["email_reminder_sent"] == 0 and days >= EMAIL_REMINDER_DAYS
            nonresponsive_needed = days >= NONRESPONSIVE_DAYS

            if not dry_run:
                if reminder_needed:
                    # Send email reminder
                    result = email_client.send_questionnaire(
                        supplier_id=sid,
                        template_id=0,
                        org_id=org_id,
                    )
                    if result.get("status") in ("sent", "demo"):
                        _execute(
                            conn,
                            """
                            UPDATE suppliers
                            SET email_reminder_sent = 1, updated_at = datetime('now')
                            WHERE id = ?
                        """,
                            (sid,),
                        )
                        email_reminders_sent.append(
                            {
                                "supplier_id": sid,
                                "supplier_name": sup["name"],
                                "days_since_sent": round(days, 1),
                                "channel": result.get("status", "unknown"),
                            }
                        )
                    else:
                        email_reminder_errors.append(
                            {
                                "supplier_id": sid,
                                "supplier_name": sup["name"],
                                "error": result.get("detail", "unknown error"),
                            }
                        )

                if nonresponsive_needed:
                    # Raise risk flag
                    flag_id = f"flag_nresp_{uuid.uuid4().hex[:8]}"
                    _execute(
                        conn,
                        """
                        INSERT INTO risk_flags
                            (id, org_id, factory_id, flag_text, cluster, severity,
                             days_overdue, priority_score, created_at, acknowledged)
                        VALUES (?, ?, 'factory_bd_001', ?, 'G5', 'WARNING',
                                ?, ?, datetime('now'), 0)
                    """,
                        (
                            flag_id,
                            org_id,
                            f"Supplier '{sup['name']}' has not responded to ESG questionnaire "
                            f"within {NONRESPONSIVE_DAYS} days of initial contact. "
                            f"Manual follow-up required.",
                            int(days),
                            min(3.0 + (days - NONRESPONSIVE_DAYS) * 0.1, 9.0),
                        ),
                    )
                    _execute(
                        conn,
                        """
                        UPDATE suppliers
                        SET questionnaire_status = 'non_responsive', updated_at = datetime('now')
                        WHERE id = ?
                    """,
                        (sid,),
                    )
                    nonresponsive.append(
                        {
                            "supplier_id": sid,
                            "supplier_name": sup["name"],
                            "days_since_sent": round(days, 1),
                        }
                    )

            else:
                # Dry-run: just classify
                if reminder_needed:
                    email_reminders_sent.append(
                        {
                            "supplier_id": sid,
                            "supplier_name": sup["name"],
                            "days_since_sent": round(days, 1),
                        }
                    )
                elif sup["email_reminder_sent"] == 1:
                    already_email_reminded.append(sid)
                else:
                    not_yet_due_for_email.append(
                        {
                            "supplier_id": sid,
                            "supplier_name": sup["name"],
                            "days_since_sent": round(days, 1),
                        }
                    )

                if nonresponsive_needed:
                    nonresponsive.append(
                        {
                            "supplier_id": sid,
                            "supplier_name": sup["name"],
                            "days_since_sent": round(days, 1),
                        }
                    )
                else:
                    not_yet_due_for_nonresponsive.append(
                        {
                            "supplier_id": sid,
                            "supplier_name": sup["name"],
                            "days_since_sent": round(days, 1),
                        }
                    )

        logger.info(
            "chase_workflow.completed",
            extra={
                "org_id": org_id,
                "dry_run": dry_run,
                "email_reminders_sent": len(email_reminders_sent),
                "nonresponsive_ flagged": len(nonresponsive),
                "email_reminder_errors": len(email_reminder_errors),
            },
        )

        return {
            "status": "ok",
            "dry_run": dry_run,
            "summary": {
                "pending_suppliers_checked": len(pending),
                "email_reminders_sent": len(email_reminders_sent),
                "email_reminder_errors": len(email_reminder_errors),
                "marked_nonresponsive": len(nonresponsive),
            },
            "email_reminders": email_reminders_sent,
            "email_reminder_errors": email_reminder_errors,
            "nonresponsive": nonresponsive,
        }
    finally:
        release_connection(conn)


@router.get("/tiers")
def list_tiers(user: dict = Depends(require_auth)):
    """List all 4 questionnaire tiers from the questionnaire engine."""
    tiers = get_all_tiers()
    return {
        "tiers": [
            {
                "tier": tier_num,
                "name": TIER_NAMES[tier_num],
                "description": f"{TIER_NAMES[tier_num]} questionnaire tier",
                "question_count": len(questions),
            }
            for tier_num, questions in tiers.items()
        ]
    }


@router.get("/tiers/{tier}")
def get_tier(tier: int, user: dict = Depends(require_auth)):
    """Get questions for a specific tier from the questionnaire engine."""
    questions = get_tier_questions(tier)
    if not questions:
        raise HTTPException(status_code=404, detail="tier not found")
    return {
        "tier": tier,
        "name": TIER_NAMES.get(tier, ""),
        "description": f"{TIER_NAMES.get(tier, '')} questionnaire tier",
        "questions": [
            {
                "id": q.id,
                "number": str(i + 1),
                "text": q.text,
                "response_type": "number" if q.unit else "yes_no",
                "unit": q.unit,
                "required": q.required,
            }
            for i, q in enumerate(questions)
        ],
    }


# ---------------------------------------------------------------------------
# POST /portal/link/{supplier_id} — Generate portal access link (editor/admin)
# ---------------------------------------------------------------------------


@router.post("/portal/link/{supplier_id}")
def generate_portal_link(
    supplier_id: str,
    days_valid: int = 7,
    user: dict = Depends(require_auth),
):
    """Generate a time-limited portal token for a supplier to submit questionnaire via web.

    The returned raw token is shown ONE TIME to the admin, who shares it with the
    supplier via an out-of-band channel (email, direct message). The token grants
    access to POST /portal/submit for the specified supplier only.

    Requires editor or admin role.
    """
    import uuid
    from datetime import datetime, timedelta
    from src.api.middleware.rbac import require_role, EDITOR_ROLES

    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    conn = get_connection()
    try:
        # Verify supplier exists and belongs to org
        supplier = _fetchone(
            conn,
            """
            SELECT id, name, questionnaire_status
            FROM suppliers
            WHERE id = ? AND org_id = ?
        """,
            (supplier_id, org_id),
        )

        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

        # Generate portal token
        raw_token = str(uuid.uuid4())
        expires_at = (datetime.utcnow() + timedelta(days=days_valid)).isoformat() + "Z"

        now_sql = "datetime('now')" if not _is_postgres() else "(NOW() AT TIME ZONE 'UTC')"

        _execute(
            conn,
            f"""
            UPDATE suppliers
            SET portal_token = ?,
                portal_token_expires = ?,
                updated_at = {now_sql}
            WHERE id = ?
        """,
            (raw_token, expires_at, supplier_id),
        )

        portal_url = f"/questionnaire/portal?token={raw_token}&supplier_id={supplier_id}"

        return {
            "status": "success",
            "portal_url": portal_url,
            "raw_token": raw_token,
            "expires_at": expires_at,
            "supplier_id": supplier_id,
            "supplier_name": supplier["name"],
            "days_valid": days_valid,
            "warning": "The raw token is shown only once. Share it securely with the supplier.",
        }
    finally:
        release_connection(conn)


# ---------------------------------------------------------------------------
# Coverage notification helper
# ---------------------------------------------------------------------------


def _send_coverage_notification(
    org_id: str,
    supplier_name: str,
    previous_coverage_pct: float,
) -> None:
    """Send a coverage improvement notification to the org admin.

    Called after a supplier submits questionnaire responses via any channel.
    """
    from src.connectors.email import get_email_client

    # Fetch updated coverage
    coverage = fetch_response_based_coverage(org_id)
    new_coverage_pct = coverage["spend_weighted_coverage_pct"]
    improvement = round(new_coverage_pct - previous_coverage_pct, 1)

    # Find the org admin
    conn = get_connection()
    try:
        admin = _fetchone(
            conn,
            """
            SELECT email FROM users
            WHERE org_id = ? AND role = 'admin' AND is_active = 1
            LIMIT 1
        """,
            (org_id,),
        )
        if not admin:
            logger.warning("coverage_notification.no_admin org_id=%s", org_id)
            return
        admin_email = admin["email"]
    finally:
        release_connection(conn)

    subject = f"ESG Platform — Supplier Response: {supplier_name} | Coverage {new_coverage_pct}%"
    text_body = f"""ESG Supplier Response Received

Supplier: {supplier_name}
Channel: web portal

Coverage Update:
  Spend-weighted coverage: {new_coverage_pct}% (was {previous_coverage_pct}%)
  Improvement: +{improvement}%
  Total suppliers responded: {coverage["responded_suppliers"]} of {coverage["total_suppliers"]}
  Covered spend: ${coverage["covered_spend_usd"]:,.0f} of ${coverage["total_spend_usd"]:,.0f}

Log in to view details: /questionnaires
"""
    html_body = f"""
<html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
<div style="background: #1a4731; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
  <h2 style="margin: 0;">ESG Supplier Response</h2>
</div>
<div style="border: 1px solid #ddd; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
  <p style="margin-top: 0;"><strong>Supplier:</strong> {supplier_name}</p>
  <p><strong>Channel:</strong> Web Portal</p>
  <hr style="margin: 20px 0;">
  <h3 style="color: #1a4731; margin-bottom: 16px;">Coverage Update</h3>
  <table style="width: 100%; border-collapse: collapse;">
    <tr>
      <td style="padding: 8px 0; color: #555;">Previous coverage</td>
      <td style="text-align: right; font-weight: bold;">{previous_coverage_pct}%</td>
    </tr>
    <tr>
      <td style="padding: 8px 0; color: #555;">New coverage</td>
      <td style="text-align: right; font-weight: bold; font-size: 1.2em;
            color: #1a4731;">{new_coverage_pct}%</td>
    </tr>
    <tr style="background: #e8f5e9;">
      <td style="padding: 8px 0;"><strong>Improvement</strong></td>
      <td style="text-align: right; font-weight: bold; color: #2e7d32;">+{improvement}%</td>
    </tr>
  </table>
  <hr style="margin: 20px 0;">
  <p style="color: #555; font-size: 0.9em;">
    {coverage["responded_suppliers"]} of {coverage["total_suppliers"]} suppliers responded &mdash;
    ${coverage["covered_spend_usd"]:,.0f} of ${coverage["total_spend_usd"]:,.0f} spend covered
  </p>
  <a href="/questionnaires" style="display: inline-block; background: #1a4731;
       color: white; padding: 10px 20px; text-decoration: none;
       border-radius: 4px; margin-top: 8px;">
    View Questionnaires
  </a>
</div>
</body></html>
"""
    email_client = get_email_client()
    result = email_client.send_email(
        to=admin_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        org_id=org_id,
        supplier_id=None,
    )
    logger.info(
        "coverage_notification.sent org_id=%s to=%s new_coverage=%.1f improvement=%.1f result=%s",
        org_id,
        admin_email,
        new_coverage_pct,
        improvement,
        result.get("status", "unknown"),
    )


# ---------------------------------------------------------------------------
# POST /portal/submit — Submit questionnaire via portal token (no JWT auth)
# ---------------------------------------------------------------------------


@router.post("/portal/submit")
def submit_portal_response(
    portal_token: str = Body(...),
    supplier_id: str = Body(...),
    responses: list = Body(...),
):
    """Submit questionnaire responses via the supplier web portal.

    This endpoint is token-authenticated (no JWT required). The token is
    validated against the supplier's portal_token_expires timestamp.

    Expected response shape:
        {"responses": [{"question_id": "q1", "response_text": "Yes"}]}
    """
    from datetime import datetime

    if not responses or not isinstance(responses, list):
        raise HTTPException(status_code=400, detail="responses must be a non-empty list")

    conn = get_connection()
    try:
        # Validate portal token
        supplier = _fetchone(
            conn,
            """
            SELECT id, org_id, name, portal_token, portal_token_expires,
                   questionnaire_status
            FROM suppliers
            WHERE id = ? AND portal_token = ? AND portal_token_expires IS NOT NULL
        """,
            (supplier_id, portal_token),
        )

        if not supplier:
            raise HTTPException(status_code=401, detail="Invalid or expired portal token")

        # Check expiry
        expires_str = supplier["portal_token_expires"]
        try:
            expires_at = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            if datetime.utcnow() > expires_at.replace(tzinfo=None):
                raise HTTPException(status_code=401, detail="Portal token has expired")
        except (ValueError, TypeError):
            raise HTTPException(status_code=401, detail="Invalid token expiry format")

        org_id = supplier["org_id"]
        supplier_name = supplier["name"]

        # Capture previous coverage before inserting responses
        prev_coverage = fetch_response_based_coverage(org_id)
        prev_coverage_pct = prev_coverage["spend_weighted_coverage_pct"]

        now_sql = "datetime('now')" if not _is_postgres() else "(NOW() AT TIME ZONE 'UTC')"

        # Determine tier from first response or default to 1
        tier = 1
        inserted = 0

        for resp in responses:
            if not isinstance(resp, dict):
                continue
            question_id = str(resp.get("question_id", ""))
            response_text = str(resp.get("response_text", "") or "")

            if not question_id:
                continue

            # Parse numeric value for validation
            response_value: Optional[float] = None
            try:
                cleaned = response_text.replace(",", "")
                response_value = float(cleaned)
            except (ValueError, TypeError):
                pass

            # Validate numeric responses against spend-based sanity bounds
            if response_value is not None:
                validation_status, validation_notes = validate_response_value(
                    supplier, question_id, response_value
                )
            else:
                validation_status, validation_notes = "verified", ""

            _execute(
                conn,
                f"""
                INSERT INTO questionnaire_responses
                    (org_id, supplier_id, tier, question_id, response_text, response_value,
                     responded_at, channel, validation_status, validation_notes)
                VALUES (?, ?, ?, ?, ?, ?, {now_sql}, 'web', ?, ?)
            """,
                (
                    org_id,
                    supplier_id,
                    tier,
                    question_id,
                    response_text,
                    response_value,
                    validation_status,
                    validation_notes,
                ),
            )
            inserted += 1

        # Update supplier status to indicate web submission
        _execute(
            conn,
            f"""
            UPDATE suppliers
            SET questionnaire_status = 'received',
                portal_token = NULL,
                portal_token_expires = NULL,
                updated_at = {now_sql}
            WHERE id = ?
        """,
            (supplier_id,),
        )

        # Send coverage notification after response is recorded
        if inserted > 0:
            _send_coverage_notification(org_id, supplier_name, prev_coverage_pct)

        return {
            "status": "success",
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "responses_received": inserted,
            "channel": "web",
        }
    finally:
        release_connection(conn)


@router.get("/whatsapp-template/{tier}")
def get_whatsapp_template(
    tier: int, supplier_id: str = "sup_001", user: dict = Depends(require_auth)
):
    """Generate WhatsApp message template for a tier + supplier."""
    questions = get_tier_questions(tier)
    if not questions:
        return {"error": "tier not found"}, 404

    supplier = fetch_supplier(supplier_id)
    supplier_name = supplier["name"] if supplier else "Supplier"

    lines = []
    for i, q in enumerate(questions, 1):
        lines.append(f"{i}. {q.text}")
        if q.unit:
            lines.append(f"   Example: {i}. [value in {q.unit}]")
        else:
            lines.append(f"   Example: {i}. Yes/No")

    message = f"""H&M Supplier ESG Update

Dear {supplier_name} Team,

Please complete {TIER_NAMES.get(tier, "")} of the H&M ESG data request for Q1 2025.

Reply with the question number followed by your answer.

{chr(10).join(lines)}

Due: April 15, 2025

Questions? Reply to this message.

- ESG Platform (on behalf of H&M)"""

    return {
        "tier": tier,
        "tier_name": TIER_NAMES.get(tier, ""),
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "channel": "whatsapp",
        "message": message,
    }


# ---------------------------------------------------------------------------
# B3.14: Auto-fill endpoint — GET /api/questionnaires/auto-fill/{template_id}/{supplier_id}
# ---------------------------------------------------------------------------


def _format_number(value: float, unit: str) -> str:
    """Format a number with commas and append the unit."""
    # Use integer format for whole numbers, float for decimals
    if value == round(value):
        formatted = f"{round(value):,}"
    else:
        formatted = f"{value:,.1f}"
    return f"{formatted} {unit}" if unit else formatted


def _format_currency(value: float) -> str:
    """Format a USD currency value with commas."""
    return f"${value:,.0f} USD"


# Keyword → (metric cluster, unit) mapping
_METRIC_KEYWORDS = [
    (re.compile(r"\benergy\b|kwh", re.IGNORECASE), "energy_kwh", "kWh"),
    (re.compile(r"\bwater\b|cubic meters", re.IGNORECASE), "water_m3", "m³"),
    (re.compile(r"\bemission\b|ghg|tco2", re.IGNORECASE), "emissions_tco2", "tCO2e"),
    (
        re.compile(r"\bwaste\b.*\btonnes\b|\btonnes\b.*\bwaste\b", re.IGNORECASE),
        "waste_tonnes",
        "tonnes",
    ),
]

# Supplier field keywords — more specific, avoid false matches
# Order matters: more specific matches first
_SUPPLIER_FIELD_KEYWORDS = [
    # "spend with us" / "annual spend" — NOT "waste" or other words containing "spend"
    (re.compile(r"\bspend\b", re.IGNORECASE), "annual_spend_usd", "currency"),
    # revenue has no mapping → intentionally NOT listed here so it falls through to not_applicable
    # country
    (re.compile(r"\bcountry\b", re.IGNORECASE), "country", "text"),
]


@router.get("/auto-fill/{template_id}/{supplier_id}")
def auto_fill_questionnaire(
    template_id: str,
    supplier_id: str,
    user: dict = Depends(require_auth),
):
    """Auto-fill questionnaire questions from supplier and metrics data.

    Maps question text keywords to supplier fields and metrics clusters,
    returning structured responses with source attribution.
    """
    org_id = user["org_id"]

    # Verify template exists and is accessible
    conn = get_connection()
    try:
        template = _fetchone(
            conn,
            "SELECT id FROM questionnaire_templates "
            "WHERE id = ? AND (org_id = ? OR org_id = '' OR org_id IS NULL)",
            (template_id, org_id),
        )
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Verify supplier exists and belongs to org
        supplier = fetch_supplier(supplier_id)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        if supplier.get("org_id") and supplier["org_id"] != org_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Fetch questions for template
        questions = _fetchall(
            conn,
            """
            SELECT question_id AS q_id, question_text AS text, question_type
            FROM questionnaire_questions
            WHERE template_id = ?
            ORDER BY sort_order
            """,
            (template_id,),
        )

        # Fetch metrics for org
        metrics = _fetchall(
            conn,
            "SELECT cluster, value, unit FROM metrics WHERE org_id = ?",
            (org_id,),
        )
        metrics_by_cluster = {m["cluster"]: m for m in metrics}

    finally:
        release_connection(conn)

    # Process each question
    result_questions = []
    auto_filled = 0
    not_applicable = 0
    needs_input = 0

    for q in questions:
        q_id = q["q_id"]
        text = q["text"]
        q_type = q["question_type"]

        # Choice questions: not_applicable (no keyword matching)
        if q_type == "choice":
            result_questions.append(
                {
                    "q_id": q_id,
                    "text": text,
                    "status": "not_applicable",
                    "value": None,
                    "source": None,
                }
            )
            not_applicable += 1
            continue

        # Try supplier field match
        matched = False
        for kw_regex, field, fmt in _SUPPLIER_FIELD_KEYWORDS:
            if kw_regex.search(text):
                value = supplier.get(field)
                if value is not None:
                    if fmt == "currency":
                        display_value = _format_currency(value)
                    else:
                        display_value = str(value)
                    result_questions.append(
                        {
                            "q_id": q_id,
                            "text": text,
                            "status": "auto_filled",
                            "value": display_value,
                            "source": f"suppliers.{field}",
                        }
                    )
                    auto_filled += 1
                else:
                    result_questions.append(
                        {
                            "q_id": q_id,
                            "text": text,
                            "status": "needs_input",
                            "value": None,
                            "source": None,
                        }
                    )
                    needs_input += 1
                matched = True
                break

        if matched:
            continue

        # Try metric cluster match
        for kw_regex, cluster, unit in _METRIC_KEYWORDS:
            if kw_regex.search(text):
                metric = metrics_by_cluster.get(cluster)
                if metric and metric["value"] is not None:
                    display_value = _format_number(metric["value"], unit)
                    result_questions.append(
                        {
                            "q_id": q_id,
                            "text": text,
                            "status": "auto_filled",
                            "value": display_value,
                            "source": f"metrics.{cluster}",
                        }
                    )
                    auto_filled += 1
                else:
                    result_questions.append(
                        {
                            "q_id": q_id,
                            "text": text,
                            "status": "needs_input",
                            "value": None,
                            "source": None,
                        }
                    )
                    needs_input += 1
                matched = True
                break

        if matched:
            continue

        # No keyword match → not_applicable
        result_questions.append(
            {"q_id": q_id, "text": text, "status": "not_applicable", "value": None, "source": None}
        )
        not_applicable += 1

    applicable = auto_filled + needs_input
    auto_fill_percentage = round((auto_filled / applicable * 100), 1) if applicable > 0 else 0.0

    return {
        "template_id": template_id,
        "supplier_id": supplier_id,
        "auto_fill_percentage": auto_fill_percentage,
        "questions": result_questions,
        "summary": {
            "auto_filled": auto_filled,
            "not_applicable": not_applicable,
            "needs_input": needs_input,
        },
    }
