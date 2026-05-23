"""
LINE Business API client for questionnaire dispatch.

Reads LINE_CHANNEL_ACCESS_TOKEN and LINE_USER_ID from environment
variables. Operates in demo mode when credentials are not configured.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

LINE_API_BASE = "https://api.line.me/v2"


class LINEClient:
    """LINE Messaging API client with demo-mode fallback.

    Demo mode is active when LINE_CHANNEL_ACCESS_TOKEN is unset.
    In demo mode, ``send_message`` logs the message and returns a
    ``demo`` status without making any API call.
    """

    def __init__(self) -> None:
        self.channel_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
        self.user_id = os.environ.get("LINE_USER_ID", "")
        self._demo = not bool(self.channel_token)

        if self._demo:
            logger.info("line_client.demo_mode channel_token_not_set")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_message(self, to: str, body: str) -> dict[str, Any]:
        """Send a text message to a LINE user via the Messaging API.

        Parameters
        ----------
        to : str
            LINE user ID of the recipient.
        body : str
            Plain-text message body (max 5000 chars per the LINE API).
        org_id : str
            Organisation ID for audit logging.
        supplier_id : str
            Supplier ID for audit logging.

        Returns
        -------
        dict
            ``{"status": "sent", "message_id": ...}`` on success,
            ``{"status": "demo", ...}`` in demo mode,
            ``{"status": "error", "detail": ...}`` on failure.
        """
        if self._demo:
            logger.info("line_client.send.demo to=%s body_len=%d", to, len(body))
            return {"status": "demo", "to": to, "body": body}

        url = f"{LINE_API_BASE}/bot/message/push"
        headers = {
            "Authorization": f"Bearer {self.channel_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "to": to,
            "messages": [{"type": "text", "text": body}],
        }

        logger.info("line_client.send.start to=%s body_len=%d", to, len(body))
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
        except Exception as exc:
            logger.error("line_client.send.error to=%s exc=%s", to, str(exc))
            return {"status": "error", "detail": str(exc), "to": to}

        if resp.status_code >= 400:
            logger.error(
                "line_client.send.error status=%d body=%s",
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
        message_id = data.get("messageId", "")
        logger.info("line_client.send.ok message_id=%s to=%s", message_id, to)
        return {"status": "sent", "message_id": message_id, "to": to}

    def send_questionnaire(
        self,
        supplier_id: str,
        template_id: int = 0,
        org_id: str = "",
    ) -> dict[str, Any]:
        """Send an ESG questionnaire to a supplier via LINE.

        Fetches the supplier's LINE user ID from the database, retrieves
        the questionnaire template, formats it as a text message, and sends it.

        Parameters
        ----------
        supplier_id : str
            The supplier's unique identifier.
        template_id : int, optional
            Questionnaire template ID. When ``0`` (default), selects the
            first active template for the org.
        org_id : str
            Organisation ID for audit logging.

        Returns
        -------
        dict
            Status, message ID, and metadata.
        """
        import json

        from src.db.database import _execute, _fetchone, get_connection, release_connection

        conn = get_connection()
        try:
            supplier = _fetchone(
                conn,
                "SELECT id, name, line_user_id, tier, org_id FROM suppliers WHERE id = ?",
                (supplier_id,),
            )
            if supplier is None:
                return {
                    "status": "error",
                    "detail": f"Supplier {supplier_id} not found",
                }

            line_user_id = supplier.get("line_user_id", "")
            if not line_user_id:
                return {
                    "status": "error",
                    "detail": f"Supplier {supplier['name']} has no LINE user ID on file",
                }

            template = self._resolve_template(
                conn, template_id, org_id or supplier.get("org_id", "")
            )
            if template is None:
                return {
                    "status": "error",
                    "detail": "No active questionnaire template found",
                }

            questions = json.loads(template["questions"])
            body = self._format_questionnaire(supplier["name"], questions, template["name"])

            result = self.send_message(line_user_id, body)

            if result.get("status") in ("sent", "demo"):
                _execute(
                    conn,
                    (
                        "UPDATE suppliers "
                        "SET questionnaire_status = 'pending', "
                        "questionnaire_sent_at = COALESCE(questionnaire_sent_at, datetime('now')), "
                        "updated_at = datetime('now') "
                        "WHERE id = ?"
                    ),
                    (supplier_id,),
                )

            return {
                "status": result.get("status", "error"),
                "message_id": result.get("message_id", ""),
                "to": line_user_id,
                "supplier_name": supplier["name"],
                "template_name": template["name"],
                "question_count": len(questions),
            }
        finally:
            release_connection(conn)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_template(self, conn: Any, template_id: int, org_id: str):
        """Select a questionnaire template."""
        from src.db.database import _fetchone

        if template_id > 0:
            row = _fetchone(
                conn,
                "SELECT id, name, questions, tier FROM questionnaire_templates WHERE id = ?",
                (template_id,),
            )
            return row

        row = _fetchone(
            conn,
            """
            SELECT id, name, questions, tier
            FROM questionnaire_templates
            WHERE (org_id = ? OR org_id = '' OR org_id IS NULL)
              AND is_active = 1
            ORDER BY CASE WHEN org_id = ? THEN 0 ELSE 1 END, created_at DESC
            LIMIT 1
            """,
            (org_id, org_id),
        )
        return row

    def _format_questionnaire(
        self, supplier_name: str, questions: list[dict], template_name: str
    ) -> str:
        """Build a human-readable LINE message body from questions."""
        lines: list[str] = []
        for i, q in enumerate(questions, 1):
            text = q.get("text", q.get("question", ""))
            unit = q.get("unit", "")
            lines.append(f"{i}. {text}")
            if unit:
                lines.append(f"   Reply: {i}. [value in {unit}]")
            else:
                lines.append(f"   Reply: {i}. [your answer]")

        return (
            f"ESG Questionnaire: {template_name}\n\n"
            f"Dear {supplier_name} Team,\n\n"
            f"Please respond to the following questions.\n\n"
            f"{chr(10).join(lines)}\n\n"
            f"- ESG Platform"
        )


# Singleton instance
_line_client: Optional[LINEClient] = None


def get_line_client() -> LINEClient:
    global _line_client
    if _line_client is None:
        _line_client = LINEClient()
    return _line_client
