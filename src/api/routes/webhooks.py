"""
Webhooks API — Create, list, delete outbound webhooks with retry logic.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import socket
import ipaddress
import time
import uuid
from typing import Optional
from urllib.parse import urlparse

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import timezone, datetime

    UTC = timezone.utc

import requests
from fastapi import APIRouter, Depends, HTTPException

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import EDITOR_ROLES, require_role
from src.db.database import get_connection, release_connection

router = APIRouter()

ALLOWED_EVENTS = {
    "risk_flag.created",
    "risk_flag.acknowledged",
    "corrective_action.created",
    "corrective_action.completed",
    "document.expiring",
    "compliance_deadline.approaching",
    "compliance_deadline.overdue",
    "supplier.created",
    "supplier.engagement_sent",
    "report.generated",
}

MAX_RETRIES = 3
RETRY_DELAYS = [60, 300, 900]  # 1min, 5min, 15min


def _generate_secret() -> str:
    """Generate a secure random secret for webhook signing."""
    return uuid.uuid4().hex + uuid.uuid4().hex[:16]


def _sign_payload(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


# Reserved/internal IP ranges that are not safe to dispatch to
_BLOCKED_IP_RANGES = (
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("::1/128"),  # Loopback IPv6
    ipaddress.ip_network("10.0.0.0/8"),  # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),  # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),  # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("0.0.0.0/8"),  # Current network
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("::ffff:0.0.0.0/96"),  # IPv4-mapped IPv6
)


def _is_safe_url(url: str) -> bool:
    """Return True if the URL resolves to a safe (non-internal) address."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # Resolve hostname to IP addresses
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in addr_info:
            if family == socket.AF_INET:
                ip = ipaddress.ip_address(sockaddr[0])
            elif family == socket.AF_INET6:
                ip = ipaddress.ip_address(sockaddr[0])
            else:
                continue
            # Check against blocked ranges
            for blocked in _BLOCKED_IP_RANGES:
                if ip in blocked:
                    return False
        return True
    except Exception:
        return False


def _webhook_to_dict(row: dict) -> dict:
    return {
        "id": row["id"],
        "org_id": row["org_id"],
        "name": row["name"],
        "url": row["url"],
        "events": json.loads(row.get("events", "[]")),
        "is_active": bool(row.get("is_active")),
        "retry_count": row.get("retry_count", 0),
        "last_triggered": row.get("last_triggered"),
        "last_status": row.get("last_status"),
        "created_at": row["created_at"],
        "created_by": row["created_by"],
    }


def _send_webhook_sync(webhook_id: str, event: str, payload: dict, org_id: str) -> dict:
    """Send a webhook synchronously. Used for testing and immediate delivery."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM webhooks WHERE id = ? AND org_id = ? AND is_active = 1",
            (webhook_id, org_id),
        ).fetchone()
        if not row:
            return {"status": "skipped", "reason": "webhook not found or inactive"}

        url = row["url"]
        secret = row["secret"]
        body = json.dumps(
            {"event": event, "data": payload, "timestamp": datetime.now(UTC).isoformat()}
        )
        signature = _sign_payload(body, secret)

        # SSRF guard: reject URLs resolving to internal/reserved IPs
        if not _is_safe_url(url):
            conn.execute(
                """UPDATE webhooks SET last_triggered = ?, last_status = ?,
                   last_response = ?, retry_count = retry_count + 1 WHERE id = ?""",
                (
                    datetime.now(UTC).isoformat(),
                    0,
                    "SSRF blocked: URL resolves to internal/reserved IP",
                    webhook_id,
                ),
            )
            conn.commit()
            return {
                "status": "error",
                "error": "SSRF blocked: URL resolves to internal/reserved IP",
            }

        try:
            response = requests.post(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    "X-Webhook-Event": event,
                },
                timeout=30,
            )
            status = response.status_code
            response_text = response.text[:500] if response.text else ""

            conn.execute(
                """UPDATE webhooks SET last_triggered = ?, last_status = ?,
                   last_response = ?, retry_count = 0 WHERE id = ?""",
                (datetime.now(UTC).isoformat(), status, response_text, webhook_id),
            )
            conn.commit()

            return {"status": status, "response": response_text}
        except requests.RequestException as e:
            conn.execute(
                """UPDATE webhooks SET last_triggered = ?, last_status = ?,
                   last_response = ?, retry_count = retry_count + 1 WHERE id = ?""",
                (datetime.now(UTC).isoformat(), 0, str(e)[:500], webhook_id),
            )
            conn.commit()
            return {"status": "error", "error": str(e)}
    finally:
        release_connection(conn)


def _deliver_webhook_background(
    webhook_id: str, event: str, payload: dict, org_id: str, attempt: int = 0
):
    """Background task to deliver webhook with retry logic."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM webhooks WHERE id = ? AND org_id = ? AND is_active = 1",
            (webhook_id, org_id),
        ).fetchone()
        if not row:
            return

        url = row["url"]
        secret = row["secret"]
        body = json.dumps(
            {"event": event, "data": payload, "timestamp": datetime.now(UTC).isoformat()}
        )
        signature = _sign_payload(body, secret)

        # SSRF guard: reject URLs resolving to internal/reserved IPs
        if not _is_safe_url(url):
            conn.execute(
                """UPDATE webhooks SET last_triggered = ?, last_status = ?,
                   last_response = ?, retry_count = retry_count + 1 WHERE id = ?""",
                (
                    datetime.now(UTC).isoformat(),
                    0,
                    "SSRF blocked: URL resolves to internal/reserved IP",
                    webhook_id,
                ),
            )
            conn.commit()
            return

        try:
            response = requests.post(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    "X-Webhook-Event": event,
                },
                timeout=30,
            )
            status = response.status_code
            response_text = response.text[:500] if response.text else ""

            conn.execute(
                """UPDATE webhooks SET last_triggered = ?, last_status = ?,
                   last_response = ?, retry_count = 0 WHERE id = ?""",
                (datetime.now(UTC).isoformat(), status, response_text, webhook_id),
            )
            conn.commit()

            if status >= 400 and attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
                _deliver_webhook_background(webhook_id, event, payload, org_id, attempt + 1)

        except requests.RequestException as e:
            conn.execute(
                """UPDATE webhooks SET last_triggered = ?, last_status = ?,
                   last_response = ?, retry_count = retry_count + 1 WHERE id = ?""",
                (datetime.now(UTC).isoformat(), 0, str(e)[:500], webhook_id),
            )
            conn.commit()

            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
                _deliver_webhook_background(webhook_id, event, payload, org_id, attempt + 1)
    finally:
        release_connection(conn)


def trigger_webhooks(org_id: str, event: str, payload: dict, background: bool = True):
    """Trigger all webhooks subscribed to an event."""
    if event not in ALLOWED_EVENTS:
        return

    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id FROM webhooks WHERE org_id = ? AND is_active = 1
               AND events LIKE ?""",
            (org_id, f"%{event}%"),
        ).fetchall()

        for row in rows:
            if background:
                trigger_webhook_background(row["id"], event, payload, org_id)
            else:
                _send_webhook_sync(row["id"], event, payload, org_id)
    finally:
        release_connection(conn)


def trigger_webhook_background(webhook_id: str, event: str, payload: dict, org_id: str):
    """Background task wrapper for webhook delivery."""
    import threading

    thread = threading.Thread(
        target=_deliver_webhook_background, args=(webhook_id, event, payload, org_id)
    )
    thread.daemon = True
    thread.start()


@router.get("")
def list_webhooks(
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    user: dict = Depends(require_auth),
):
    """List webhooks for the org."""
    org_id = user["org_id"]
    conn = get_connection()
    try:
        query = "SELECT * FROM webhooks WHERE org_id = ?"
        params = [org_id]

        if is_active is not None:
            query += " AND is_active = ?"
            params.append(1 if is_active else 0)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        rows = conn.execute(query, params).fetchall()
        return {"webhooks": [_webhook_to_dict(dict(r)) for r in rows], "total": len(rows)}
    finally:
        release_connection(conn)


@router.get("/{webhook_id}")
def get_webhook(webhook_id: str, user: dict = Depends(require_auth)):
    """Get a single webhook."""
    org_id = user["org_id"]
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM webhooks WHERE id = ? AND org_id = ?",
            (webhook_id, org_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="not found")
        return _webhook_to_dict(dict(row))
    finally:
        release_connection(conn)


@router.post("")
def create_webhook(
    payload: dict,
    user: dict = Depends(require_auth),
):
    """Create a new webhook. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    events = payload.get("events", [])
    for e in events:
        if e not in ALLOWED_EVENTS:
            raise HTTPException(
                status_code=400,
                detail=f"event '{e}' not allowed. Must be one of {sorted(ALLOWED_EVENTS)}",
            )

    webhook_id = f"wh_{uuid.uuid4().hex[:12]}"
    secret = _generate_secret()
    now = datetime.now(UTC).isoformat()

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO webhooks
               (id, org_id, name, url, events, secret, is_active, created_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                webhook_id,
                org_id,
                payload["name"],
                payload["url"],
                json.dumps(events),
                secret,
                payload.get("is_active", 1),
                now,
                user.get("email", ""),
            ),
        )
        conn.commit()
    finally:
        release_connection(conn)

    return {"id": webhook_id, "secret": secret, "created_at": now}


@router.put("/{webhook_id}")
def update_webhook(
    webhook_id: str,
    payload: dict,
    user: dict = Depends(require_auth),
):
    """Update a webhook. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT * FROM webhooks WHERE id = ? AND org_id = ?",
            (webhook_id, org_id),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="not found")

        updates = []
        params = []

        for field in ["name", "url", "is_active"]:
            if field in payload:
                updates.append(f"{field} = ?")
                params.append(
                    payload[field] if field != "is_active" else (1 if payload[field] else 0)
                )

        if "events" in payload:
            events = payload["events"]
            for e in events:
                if e not in ALLOWED_EVENTS:
                    raise HTTPException(status_code=400, detail=f"event '{e}' not allowed")
            updates.append("events = ?")
            params.append(json.dumps(events))

        if updates:
            params.extend([webhook_id, org_id])
            conn.execute(
                f"UPDATE webhooks SET {', '.join(updates)} WHERE id = ? AND org_id = ?",
                params,
            )
            conn.commit()

        return {"id": webhook_id, "updated_at": datetime.now(UTC).isoformat()}
    finally:
        release_connection(conn)


@router.delete("/{webhook_id}")
def delete_webhook(webhook_id: str, user: dict = Depends(require_auth)):
    """Delete a webhook. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    conn = get_connection()
    try:
        result = conn.execute(
            "DELETE FROM webhooks WHERE id = ? AND org_id = ?",
            (webhook_id, org_id),
        )
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="not found")
        return {"deleted": True}
    finally:
        release_connection(conn)


@router.post("/{webhook_id}/test")
def test_webhook(webhook_id: str, user: dict = Depends(require_auth)):
    """Send a test webhook. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    result = _send_webhook_sync(
        webhook_id,
        "test",
        {"message": "This is a test webhook", "org_id": org_id},
        org_id,
    )
    return {"webhook_id": webhook_id, "result": result}
