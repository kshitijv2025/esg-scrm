"""
Email client — SMTP wrapper for questionnaire dispatch and alerts.

Reads SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
from environment variables. Operates in demo mode (log-only, no SMTP
call) when credentials are not configured.
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from src.db.database import _execute, _fetchone, get_connection, release_connection

logger = logging.getLogger(__name__)


class EmailClient:
    """SMTP email client with demo-mode fallback.

    Demo mode is active when any of SMTP_HOST / SMTP_USER / SMTP_PASSWORD
    is unset. In demo mode, ``send_email`` logs the message and returns a
    ``demo`` status without making any SMTP connection.
    """

    def __init__(self) -> None:
        self.host = os.environ.get("SMTP_HOST", "")
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.user = os.environ.get("SMTP_USER", "")
        self.password = os.environ.get("SMTP_PASSWORD", "")
        self.from_address = os.environ.get("SMTP_FROM", self.user)
        self._demo = not all([self.host, self.user, self.password])

        if self._demo:
            logger.info("email_client.demo_mode smtp_credentials_not_set")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str,
        org_id: str = "",
        supplier_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send a multipart HTML/text email via SMTP.

        Logs the outbound message to ``outbound_emails`` for audit
        trail regardless of demo or live mode.

        Parameters
        ----------
        to : str
            Recipient email address.
        subject : str
            Email subject line.
        html_body : str
            HTML email body.
        text_body : str
            Plain-text fallback body.
        org_id : str
            Organisation ID for audit logging.
        supplier_id : str
            Supplier ID for audit logging.

        Returns
        -------
        dict
            ``{"status": "sent", "smtp_message_id": ...}`` on success,
            ``{"status": "demo", ...}`` in demo mode,
            ``{"status": "error", "detail": ...}`` on failure.
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_address
        msg["To"] = to
        msg["Message-ID"] = f"<{uuid.uuid4().hex}@email>"

        part_text = MIMEText(text_body, "plain")
        part_html = MIMEText(html_body, "html")
        msg.attach(part_text)
        msg.attach(part_html)

        if self._demo:
            logger.info(
                "email_client.send.demo to=%s subject=%s body_len=%d",
                to,
                subject,
                len(html_body),
            )
            smtp_id = f"demo-{uuid.uuid4().hex[:8]}"
        else:
            try:
                with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                    server.ehlo()
                    server.starttls()
                    server.login(self.user, self.password)
                    server.sendmail(self.from_address, [to], msg.as_string())
                smtp_id = msg["Message-ID"]
                logger.info("email_client.send.ok to=%s message_id=%s", to, smtp_id)
            except Exception as exc:  # pragma: no cover — network errors
                logger.error("email_client.send.error to=%s exc=%s", to, str(exc))
                return {
                    "status": "error",
                    "detail": str(exc),
                    "to": to,
                }

        # Always log — demo and live
        self._log_outbound(
            org_id=org_id,
            supplier_id=supplier_id,
            to_address=to,
            subject=subject,
            body=text_body,
            smtp_message_id=smtp_id,
        )

        return {
            "status": "sent" if not self._demo else "demo",
            "smtp_message_id": smtp_id,
            "to": to,
        }

    def send_questionnaire(
        self,
        supplier_id: str,
        template_id: int = 0,
        org_id: str = "",
    ) -> dict[str, Any]:
        """Send an ESG questionnaire to a supplier via email.

        Fetches the supplier's email from the database, retrieves the
        questionnaire template and questions, formats them as a multipart
        email, and sends it.

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
        conn = get_connection()
        try:
            supplier = _fetchone(
                conn,
                "SELECT id, name, email, tier, org_id FROM suppliers WHERE id = ?",
                (supplier_id,),
            )
            if supplier is None:
                return {
                    "status": "error",
                    "detail": f"Supplier {supplier_id} not found",
                }

            email_address = supplier.get("email", "")
            if not email_address:
                return {
                    "status": "error",
                    "detail": f"Supplier {supplier['name']} has no email address on file",
                }

            template = self._resolve_template(conn, template_id, org_id)
            if template is None:
                return {
                    "status": "error",
                    "detail": "No active questionnaire template found",
                }

            questions = json.loads(template["questions"])
            html_body, text_body = self._format_questionnaire(
                supplier["name"], questions, template["name"]
            )

            subject = f"ESG Questionnaire: {template['name']}"

            result = self.send_email(
                to=email_address,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                org_id=org_id or supplier.get("org_id", ""),
                supplier_id=supplier_id,
            )

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
                "smtp_message_id": result.get("smtp_message_id", ""),
                "to": email_address,
                "supplier_name": supplier["name"],
                "template_name": template["name"],
                "question_count": len(questions),
            }
        finally:
            release_connection(conn)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_template(self, conn: Any, template_id: int, org_id: str) -> Optional[dict]:
        """Select a questionnaire template.

        If ``template_id > 0`` the template is looked up by ID.
        Otherwise the first active template for the org is selected.
        """
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
    ) -> tuple[str, str]:
        """Build HTML and plain-text email bodies from questions."""

        def format_q(q: dict, idx: int) -> str:
            text = q.get("text", q.get("question", ""))
            unit = q.get("unit", "")
            reply_hint = f" [value in {unit}]" if unit else " [your answer]"
            return f"{idx}. {text}\n   Reply: {idx}:{reply_hint}"

        text_lines: list[str] = []
        html_lines: list[str] = []

        for i, q in enumerate(questions, 1):
            text_lines.append(format_q(q, i))
            q_text = q.get("text", q.get("question", ""))
            q_unit = q.get("unit", "")
            html_lines.append(
                f"<li><strong>Q{i}:</strong> {q_text}"
                + (
                    f" <em>(reply format: {i}: [value in {q_unit}])</em>"
                    if q_unit
                    else f" <em>(reply format: {i}: [your answer])</em>"
                )
                + "</li>"
            )

        intro = (
            f"Dear {supplier_name} Team,\n\n"
            "Please respond to the following ESG questionnaire by replying to "
            "this email with the question number and your answer.\n"
        )

        html_intro = (
            f"<p>Dear <strong>{supplier_name}</strong> Team,</p>"
            "<p>Please respond to the following ESG questionnaire by replying to "
            "this email with the question number and your answer.</p>"
        )

        text_body = (
            f"ESG Questionnaire: {template_name}\n"
            + "=" * 50
            + "\n\n"
            + intro
            + "\n".join(text_lines)
            + "\n\n- ESG Platform"
        )

        html_body = (
            f"<html><body>"
            f"<h2>ESG Questionnaire: {template_name}</h2>"
            + html_intro
            + "<ol>"
            + "".join(f"<li>{_line}</li>" for _line in html_lines)
            + "</ol>"
            "<hr><p><em>- ESG Platform</em></p></body></html>"
        )

        return html_body, text_body

    def _log_outbound(
        self,
        org_id: str,
        supplier_id: str,
        to_address: str,
        subject: str,
        body: str,
        smtp_message_id: str,
    ) -> None:
        """Record outbound email in ``outbound_emails`` for audit trail."""
        conn = get_connection()
        try:
            _execute(
                conn,
                """
                INSERT INTO outbound_emails
                    (org_id, supplier_id, direction, to_address, subject, body, smtp_message_id)
                VALUES (?, ?, 'outbound', ?, ?, ?, ?)
                """,
                (org_id, supplier_id, to_address, subject, body, smtp_message_id),
            )
        finally:
            release_connection(conn)

    def send_alert_email(
        self,
        alert_data: dict,
        org_id: str = "",
    ) -> dict[str, Any]:
        """Send a risk alert notification email.

        Formats a risk alert (CRITICAL/WARNING severity) as a multipart
        email and sends it to the configured alert recipient.

        Parameters
        ----------
        alert_data : dict
            Alert details with keys: severity, flag_text, cluster,
            supplier_name, days_overdue, priority_score.
        org_id : str
            Organisation ID for audit logging.

        Returns
        -------
        dict
            ``{"status": "sent", "smtp_message_id": ...}`` on success,
            ``{"status": "demo", ...}`` in demo mode,
            ``{"status": "error", "detail": ...}`` on failure.
        """
        severity = alert_data.get("severity", "WARNING")
        flag_text = alert_data.get("flag_text", "Risk alert triggered")
        cluster = alert_data.get("cluster", "Unknown")
        supplier_name = alert_data.get("supplier_name", "Unknown Supplier")
        days_overdue = alert_data.get("days_overdue", 0)
        priority_score = alert_data.get("priority_score", 0.0)

        # Build email subject
        subject = f"[{severity}] ESG Risk Alert: {cluster}"
        _sev_color = "#dc2626" if severity == "CRITICAL" else "#d97706"

        # Build HTML body
        html_body = f"""
        <html><body>
        <h2 style="color: {_sev_color}">
            {severity} Risk Alert
        </h2>
        <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
            <tr>
                <td style="padding: 8px; font-weight: bold; width: 140px;">Severity</td>
                <td style="padding: 8px; color: {_sev_color}; font-weight: bold;">
                    {severity}
                </td>
            </tr>
            <tr style="background: #f9f9f9;">
                <td style="padding: 8px; font-weight: bold;">Cluster</td>
                <td style="padding: 8px;">{cluster}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">Supplier</td>
                <td style="padding: 8px;">{supplier_name}</td>
            </tr>
            <tr style="background: #f9f9f9;">
                <td style="padding: 8px; font-weight: bold;">Priority Score</td>
                <td style="padding: 8px;">{priority_score:.1f}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">Days Overdue</td>
                <td style="padding: 8px;">{days_overdue}</td>
            </tr>
            <tr style="background: #f9f9f9;">
                <td style="padding: 8px; font-weight: bold; vertical-align: top;">
                    Alert Message
                </td>
                <td style="padding: 8px;">{flag_text}</td>
            </tr>
        </table>
        <p style="margin-top: 20px;">
            Please review this alert in the ESG+SCRM platform.
        </p>
        <hr>
        <p style="color: #666; font-size: 12px;">
            This is an automated alert from ESG+SCRM Platform.
        </p>
        </body></html>
        """

        # Build plain-text body
        text_body = f"""
ESG Risk Alert - {severity}
=======================
Severity: {severity}
Cluster: {cluster}
Supplier: {supplier_name}
Priority Score: {priority_score:.1f}
Days Overdue: {days_overdue}

Alert Message:
{flag_text}

Please review this alert in the ESG+SCRM platform.
---
Automated alert from ESG+SCRM Platform.
        """.strip()

        # Send to the configured alert recipient (SMTP_FROM or user)
        to_address = os.environ.get("ALERT_EMAIL_RECIPIENT", self.from_address)

        return self.send_email(
            to=to_address,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            org_id=org_id,
        )


# Singleton instance
_email_client: Optional[EmailClient] = None


def get_email_client() -> EmailClient:
    global _email_client
    if _email_client is None:
        _email_client = EmailClient()
    return _email_client
