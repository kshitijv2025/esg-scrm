"""
Compliance Calendar API — Track compliance deadlines across frameworks.
"""

from __future__ import annotations
from typing import Optional
import uuid

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import timezone, datetime

    UTC = timezone.utc

from fastapi import APIRouter, Depends, HTTPException

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import EDITOR_ROLES, require_role
from src.db.database import get_connection, release_connection

router = APIRouter()

ALLOWED_FRAMEWORKS = {"ghg_protocol", "esrs", "csrd", "gri", "tcfd", "issb"}
ALLOWED_COMPLIANCE_STATUSES = {
    "upcoming",
    "in_progress",
    "due",
    "completed",
    "submitted",
    "overdue",
}


def _deadline_to_dict(row: dict) -> dict:
    today = datetime.now(UTC).isoformat()[:10]
    deadline = row.get("deadline", "")
    status = row["status"]

    # Auto-update overdue status
    if status not in ("completed", "submitted") and deadline and deadline < today:
        status = "overdue"

    return {
        "id": row["id"],
        "org_id": row["org_id"],
        "framework": row["framework"],
        "requirement": row["requirement"],
        "description": row.get("description", ""),
        "deadline": deadline,
        "status": status,
        "submission_date": row.get("submission_date"),
        "evidence_required": bool(row.get("evidence_required")),
        "created_at": row["created_at"],
        "updated_at": row.get("updated_at"),
        "days_until_deadline": (
            (datetime.strptime(deadline, "%Y-%m-%d").date() - datetime.now(UTC).date()).days
            if deadline and status not in ("completed", "submitted", "overdue")
            else None
        ),
    }


@router.get("/calendar")
def get_calendar(
    framework: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    user: dict = Depends(require_auth),
):
    """Get compliance calendar events for the org."""
    org_id = user["org_id"]
    conn = get_connection()
    try:
        query = "SELECT * FROM compliance_deadlines WHERE org_id = ?"
        params = [org_id]

        if framework:
            query += " AND framework = ?"
            params.append(framework)
        if status:
            query += " AND status = ?"
            params.append(status)
        if from_date:
            query += " AND deadline >= ?"
            params.append(from_date)
        if to_date:
            query += " AND deadline <= ?"
            params.append(to_date)

        query += " ORDER BY deadline ASC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        rows = conn.execute(query, params).fetchall()
        return {
            "deadlines": [_deadline_to_dict(dict(r)) for r in rows],
            "total": len(rows),
        }
    finally:
        release_connection(conn)


@router.get("/upcoming")
def get_upcoming_deadlines(
    days: int = 90,
    user: dict = Depends(require_auth),
):
    """Get upcoming compliance deadlines within the next N days."""
    org_id = user["org_id"]
    from datetime import timedelta

    today = datetime.now(UTC).isoformat()[:10]
    future = (datetime.now(UTC) + timedelta(days=days)).isoformat()[:10]

    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM compliance_deadlines
               WHERE org_id = ? AND status NOT IN ('completed', 'submitted')
               AND deadline >= ? AND deadline <= ?
               ORDER BY deadline ASC""",
            (org_id, today, future),
        ).fetchall()
        return {
            "deadlines": [_deadline_to_dict(dict(r)) for r in rows],
            "total": len(rows),
        }
    finally:
        release_connection(conn)


@router.get("/overdue")
def get_overdue_deadlines(user: dict = Depends(require_auth)):
    """Get all overdue compliance deadlines."""
    org_id = user["org_id"]
    today = datetime.now(UTC).isoformat()[:10]

    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM compliance_deadlines
               WHERE org_id = ? AND status NOT IN ('completed', 'submitted')
               AND deadline < ?
               ORDER BY deadline ASC""",
            (org_id, today),
        ).fetchall()
        return {
            "deadlines": [_deadline_to_dict(dict(r)) for r in rows],
            "total": len(rows),
        }
    finally:
        release_connection(conn)


@router.post("")
def create_deadline(
    payload: dict,
    user: dict = Depends(require_auth),
):
    """Create a new compliance deadline. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    framework = payload.get("framework", "")
    status = payload.get("status", "upcoming")
    if framework.lower() not in ALLOWED_FRAMEWORKS:
        raise HTTPException(400, f"framework must be one of {sorted(ALLOWED_FRAMEWORKS)}")
    if status not in ALLOWED_COMPLIANCE_STATUSES:
        raise HTTPException(400, f"status must be one of {sorted(ALLOWED_COMPLIANCE_STATUSES)}")

    deadline_id = f"cd_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO compliance_deadlines
               (id, org_id, framework, requirement, description, deadline, status,
                evidence_required, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                deadline_id,
                org_id,
                framework,
                payload["requirement"],
                payload.get("description", ""),
                payload["deadline"],
                status,
                payload.get("evidence_required", 1),
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        release_connection(conn)

    return {"id": deadline_id, "created_at": now}


@router.put("/{deadline_id}")
def update_deadline(
    deadline_id: str,
    payload: dict,
    user: dict = Depends(require_auth),
):
    """Update a compliance deadline. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    # Validate enum fields against allowlists
    if "framework" in payload and payload["framework"].lower() not in ALLOWED_FRAMEWORKS:
        raise HTTPException(400, f"framework must be one of {sorted(ALLOWED_FRAMEWORKS)}")
    if "status" in payload and payload["status"] not in ALLOWED_COMPLIANCE_STATUSES:
        raise HTTPException(400, f"status must be one of {sorted(ALLOWED_COMPLIANCE_STATUSES)}")

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT * FROM compliance_deadlines WHERE id = ? AND org_id = ?",
            (deadline_id, org_id),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="not found")

        updates = []
        params = []
        for field in [
            "framework",
            "requirement",
            "description",
            "deadline",
            "status",
            "submission_date",
            "evidence_required",
        ]:
            if field in payload:
                updates.append(f"{field} = ?")
                params.append(payload[field])

        updates.append("updated_at = ?")
        params.append(datetime.now(UTC).isoformat())

        params.extend([deadline_id, org_id])
        conn.execute(
            f"UPDATE compliance_deadlines SET {', '.join(updates)} WHERE id = ? AND org_id = ?",
            params,
        )
        conn.commit()
    finally:
        release_connection(conn)

    return {"id": deadline_id, "updated_at": datetime.now(UTC).isoformat()}


@router.delete("/{deadline_id}")
def delete_deadline(deadline_id: str, user: dict = Depends(require_auth)):
    """Delete a compliance deadline. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    conn = get_connection()
    try:
        result = conn.execute(
            "DELETE FROM compliance_deadlines WHERE id = ? AND org_id = ?",
            (deadline_id, org_id),
        )
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="not found")
        return {"deleted": True}
    finally:
        release_connection(conn)
