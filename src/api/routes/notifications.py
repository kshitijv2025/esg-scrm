"""
Notification log API — tracks outbound notifications across channels.
"""

from __future__ import annotations
from typing import Optional
import logging

from fastapi import APIRouter, Depends

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import EDITOR_ROLES, require_role
from src.connectors.email import get_email_client
from src.db.database import _execute, _fetchall, _fetchone, get_connection, release_connection

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/send-alert")
def send_alert_notification(
    alert_data: dict,
    user: dict = Depends(require_auth),
):
    """Send a risk alert as an email and log it to notification_log.

    Requires editor role or above.
    """
    require_role(user, EDITOR_ROLES)

    org_id = user["org_id"]
    channel = "email"
    severity = alert_data.get("severity", "WARNING")

    # Only send for CRITICAL and WARNING severity
    if severity not in ("CRITICAL", "WARNING"):
        return {
            "status": "skipped",
            "detail": f"Severity {severity} does not require email notification",
        }

    email_client = get_email_client()
    result = email_client.send_alert_email(alert_data=alert_data, org_id=org_id)

    # Log to notification_log
    status = "sent" if result.get("status") in ("sent", "demo") else "failed"
    recipient = result.get("to", "unknown")
    subject = f"[{severity}] ESG Risk Alert: {alert_data.get('cluster', 'Unknown')}"
    body_preview = alert_data.get("flag_text", "")[:200] if alert_data.get("flag_text") else ""

    _log_notification(
        org_id=org_id,
        user_id=user.get("id", ""),
        channel=channel,
        subject=subject,
        body_preview=body_preview,
        recipient=recipient,
        status=status,
    )

    logger.info(
        "notification.alert_sent",
        extra={
            "org_id": org_id,
            "severity": severity,
            "status": status,
            "channel": channel,
        },
    )

    return {
        "status": status,
        "smtp_message_id": result.get("smtp_message_id", ""),
        "recipient": recipient,
    }


@router.get("/history")
def get_notification_history(
    channel: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    user: dict = Depends(require_auth),
):
    """List recent notifications for the user's org.

    Returns paginated notification history, org-scoped.
    """
    org_id = user["org_id"]

    conn = get_connection()
    try:
        query = "SELECT * FROM notification_log WHERE org_id = ?"
        params: list = [org_id]

        if channel:
            query += " AND channel = ?"
            params.append(channel)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY sent_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        rows = _fetchall(conn, query, tuple(params))

        # Get total count
        count_query = "SELECT COUNT(*) as cnt FROM notification_log WHERE org_id = ?"
        count_params: list = [org_id]
        if channel:
            count_query += " AND channel = ?"
            count_params.append(channel)
        if status:
            count_query += " AND status = ?"
            count_params.append(status)

        total_row = _fetchone(conn, count_query, tuple(count_params))
        total = total_row["cnt"] if total_row else 0

        return {
            "notifications": rows,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    finally:
        release_connection(conn)


def _log_notification(
    org_id: str,
    user_id: str,
    channel: str,
    subject: str,
    body_preview: str,
    recipient: str,
    status: str,
) -> None:
    """Insert a notification log entry."""
    conn = get_connection()
    try:
        _execute(
            conn,
            """
            INSERT INTO notification_log
                (org_id, user_id, channel, subject, body_preview, recipient, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (org_id, user_id, channel, subject, body_preview, recipient, status),
        )
    finally:
        release_connection(conn)
