"""
WeChat Work (WeCom) API client for questionnaire dispatch.

Reads WECOM_CORP_ID, WECOM_AGENT_ID, and WECOM_SECRET from environment
variables. Operates in demo mode when credentials are not configured.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

WECOM_API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"


class WeChatClient:
    """WeChat Work / WeCom API client with demo-mode fallback.

    Demo mode is active when any of WECOM_CORP_ID / WECOM_AGENT_ID /
    WECOM_SECRET is unset. In demo mode, ``send_message`` logs the message
    and returns a ``demo`` status without making any API call.
    """

    def __init__(self) -> None:
        self.corp_id = os.environ.get("WECOM_CORP_ID", "")
        self.agent_id = os.environ.get("WECOM_AGENT_ID", "")
        self.secret = os.environ.get("WECOM_SECRET", "")
        self._demo = not all([self.corp_id, self.agent_id, self.secret])
        self._access_token: Optional[str] = None

        if self._demo:
            logger.info("wechat_client.demo_mode credentials_not_set")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _get_access_token(self) -> Optional[str]:
        """Fetch (and cache) an access token for the WeChat Work API."""
        if self._demo:
            return None

        if self._access_token is not None:
            return self._access_token

        url = f"{WECOM_API_BASE}/gettoken"
        params = {"corpid": self.corp_id, "corpsecret": self.secret}
        try:
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            token = data.get("access_token")
            if token:
                self._access_token = token
            return token
        except Exception as exc:
            logger.error("wechat_client.token.error exc=%s", str(exc))
            return None

    def send_message(self, to: str, body: str) -> dict[str, Any]:
        """Send a text message to a WeChat Work user via the messaging API.

        Parameters
        ----------
        to : str
            WeChat user ID or party ID (depending on ``to_type``).
        body : str
            Plain-text message body.
        to_type : int, optional
            1 = user ID, 2 = party ID. Defaults to 1.

        Returns
        -------
        dict
            ``{"status": "sent", "msgid": ...}`` on success,
            ``{"status": "demo", ...}`` in demo mode,
            ``{"status": "error", "detail": ...}`` on failure.
        """
        if self._demo:
            logger.info("wechat_client.send.demo to=%s body_len=%d", to, len(body))
            return {"status": "demo", "to": to, "body": body}

        token = self._get_access_token()
        if not token:
            return {"status": "error", "detail": "Failed to obtain access token", "to": to}

        url = f"{WECOM_API_BASE}/message/send"
        params = {"access_token": token}
        payload = {
            "touser": to,
            "agentid": self.agent_id,
            "msgtype": "text",
            "text": {"content": body},
        }

        logger.info("wechat_client.send.start to=%s body_len=%d", to, len(body))
        try:
            resp = requests.post(url, params=params, json=payload, timeout=30)
        except Exception as exc:
            logger.error("wechat_client.send.error to=%s exc=%s", to, str(exc))
            return {"status": "error", "detail": str(exc), "to": to}

        data = resp.json()
        errcode = data.get("errcode", 0)
        if errcode != 0:
            logger.error(
                "wechat_client.send.error errcode=%d errmsg=%s",
                errcode,
                data.get("errmsg", ""),
            )
            return {
                "status": "error",
                "errcode": errcode,
                "detail": data.get("errmsg", ""),
                "to": to,
            }

        msgid = data.get("msgid", "")
        logger.info("wechat_client.send.ok msgid=%s to=%s", msgid, to)
        return {"status": "sent", "msgid": msgid, "to": to}

    def send_questionnaire(
        self,
        supplier_id: str,
        template_id: int = 0,
        org_id: str = "",
    ) -> dict[str, Any]:
        """Send an ESG questionnaire to a supplier via WeChat Work.

        Fetches the supplier's WeChat user ID from the database, retrieves
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
                "SELECT id, name, wechat_user_id, tier, org_id FROM suppliers WHERE id = ?",
                (supplier_id,),
            )
            if supplier is None:
                return {
                    "status": "error",
                    "detail": f"Supplier {supplier_id} not found",
                }

            wechat_user_id = supplier.get("wechat_user_id", "")
            if not wechat_user_id:
                return {
                    "status": "error",
                    "detail": f"Supplier {supplier['name']} has no WeChat user ID on file",
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

            result = self.send_message(wechat_user_id, body)

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
                "msgid": result.get("msgid", ""),
                "to": wechat_user_id,
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
        """Build a human-readable WeChat message body from questions."""
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
_wechat_client: Optional[WeChatClient] = None


def get_wechat_client() -> WeChatClient:
    global _wechat_client
    if _wechat_client is None:
        _wechat_client = WeChatClient()
    return _wechat_client
