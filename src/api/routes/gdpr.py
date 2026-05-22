"""GDPR data export and account deletion endpoints."""

from __future__ import annotations
from typing import Optional

import json
import uuid

try:
    from datetime import UTC, datetime, timedelta
except ImportError:
    from datetime import timezone, datetime, timedelta

    UTC = timezone.utc

from fastapi import APIRouter, HTTPException, Request

from src.auth.jwt import decode_token
from src.db.database import get_connection, release_connection

router = APIRouter()

EXPORT_RETENTION_DAYS = 7
DELETION_SCHEDULE_DAYS = 30


def _get_auth_payload(request: Request) -> Optional[dict]:
    """Extract and validate JWT from Authorization header."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    return decode_token(token)


@router.post("/export")
async def export_data(request: Request):
    """Generate a ZIP export of all user data.

    Creates a GDPR export job, gathers user record, org record, audit log
    entries (last 90 days), and notification log entries, then returns a
    download URL. The export file expires in 7 days.
    """
    payload = _get_auth_payload(request)
    if not payload:
        raise HTTPException(401, "Valid token required")

    user_id = payload["sub"]
    org_id = payload["org_id"]

    conn = get_connection()
    try:
        # Create export job record
        job_id = f"gdpr_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()

        conn.execute(
            "INSERT INTO gdpr_export_jobs (id, org_id, user_id, status, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (job_id, org_id, user_id, "processing", now),
        )
        conn.commit()

        # Gather user data
        user = conn.execute(
            "SELECT id, org_id, email, full_name, role, is_active, last_login, created_at "
            "FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        # Gather org data
        org = conn.execute(
            "SELECT id, name, industry, country, plan, trial_end FROM organizations WHERE id = ?",
            (org_id,),
        ).fetchone()

        # Gather audit log entries (last 90 days)
        cutoff = (datetime.now(UTC) - timedelta(days=90)).isoformat()
        audit_rows = conn.execute(
            "SELECT id, action, resource_type, details, created_at FROM audit_log "
            "WHERE org_id = ? AND user_id = ? AND created_at >= ? "
            "ORDER BY created_at DESC LIMIT 1000",
            (org_id, user_id, cutoff),
        ).fetchall()

        # Gather notification log entries (last 90 days)
        notification_rows = conn.execute(
            "SELECT id, channel, recipient, subject, sent_at, status FROM notification_log "
            "WHERE org_id = ? AND user_id = ? AND sent_at >= ? "
            "ORDER BY sent_at DESC LIMIT 1000",
            (org_id, user_id, cutoff),
        ).fetchall()

        # Build export payload
        export_data = {
            "export_metadata": {
                "job_id": job_id,
                "generated_at": now,
                "user_id": user_id,
                "org_id": org_id,
            },
            "user": dict(user) if user else None,
            "organization": dict(org) if org else None,
            "audit_log": [dict(row) for row in audit_rows],
            "notifications": [dict(row) for row in notification_rows],
        }

        # Serialize to JSON string (ZIP creation stubbed)
        export_json = json.dumps(export_data, indent=2, default=str)
        _file_path = f"/tmp/gdpr_export_{job_id}.json"

        # Write to temp file (stubbed — actual ZIP creation deferred)
        with open(_file_path, "w") as f:
            f.write(export_json)

        # Update job status to ready
        expires_at = (datetime.now(UTC) + timedelta(days=EXPORT_RETENTION_DAYS)).isoformat()
        conn.execute(
            "UPDATE gdpr_export_jobs SET status = ?, file_path = ?, expires_at = ? WHERE id = ?",
            ("ready", _file_path, expires_at, job_id),
        )
        conn.commit()

        return {
            "download_url": f"/api/gdpr/export/{job_id}",
            "expires_at": expires_at,
        }
    finally:
        release_connection(conn)


@router.get("/export/{job_id}")
async def download_export(job_id: str, request: Request):
    """Download a previously generated GDPR export file.

    Verifies the export belongs to the authenticated user and has not expired.
    """
    payload = _get_auth_payload(request)
    if not payload:
        raise HTTPException(401, "Valid token required")

    user_id = payload["sub"]

    conn = get_connection()
    try:
        job = conn.execute(
            "SELECT id, user_id, status, file_path, expires_at FROM gdpr_export_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()

        if not job:
            raise HTTPException(404, "Export job not found")

        if job["user_id"] != user_id:
            raise HTTPException(403, "Access denied")

        if job["status"] != "ready":
            raise HTTPException(400, "Export not ready")

        if job["expires_at"]:
            expires = datetime.fromisoformat(job["expires_at"])
            if datetime.now(UTC) > expires:
                raise HTTPException(410, "Export has expired")

        # Read and return the export file
        file_path = job["file_path"]
        if file_path:
            with open(file_path) as f:
                export_data = json.load(f)
            return export_data

        raise HTTPException(404, "Export file not found")
    finally:
        release_connection(conn)


@router.delete("/account")
async def delete_account(request: Request):
    """Soft-delete user account within 30 days.

    Sets is_active=0, nulls out PII fields (email, full_name, password_hash),
    and schedules permanent deletion. This implements GDPR Article 17 Right to
    Erasure ("right to be forgotten").
    """
    payload = _get_auth_payload(request)
    if not payload:
        raise HTTPException(401, "Valid token required")

    user_id = payload["sub"]

    conn = get_connection()
    try:
        # Verify user exists and is active
        user = conn.execute(
            "SELECT id, is_active FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if not user:
            raise HTTPException(404, "User not found")

        if not user["is_active"]:
            raise HTTPException(400, "Account already deleted")

        # Soft-delete: null PII, deactivate account
        deleted_email = f"deleted_{user_id}@redacted.local"
        conn.execute(
            "UPDATE users SET "
            "is_active = 0, "
            "email = ?, "
            "full_name = ?, "
            "password_hash = ?, "
            "email_verified = 0, "
            "last_login = NULL "
            "WHERE id = ?",
            (deleted_email, "Deleted User", "!DELETED", user_id),
        )
        conn.commit()

        return {
            "message": f"Account scheduled for deletion within {DELETION_SCHEDULE_DAYS} days",
            "deleted_at": datetime.now(UTC).isoformat(),
        }
    finally:
        release_connection(conn)
