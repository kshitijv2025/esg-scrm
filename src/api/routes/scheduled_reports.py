"""
Scheduled Reports API — CRUD for scheduled report generation.
"""

from __future__ import annotations
from typing import Optional
import json
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

ALLOWED_SCHEDULES = {"monthly", "quarterly", "annual"}
ALLOWED_REPORT_TYPES = {
    "esg_summary",
    "emissions",
    "water",
    "waste",
    "supply_chain",
    "risk",
    "compliance",
    "custom",
}


def _report_to_dict(row: dict) -> dict:
    return {
        "id": row["id"],
        "org_id": row["org_id"],
        "name": row["name"],
        "description": row.get("description", ""),
        "report_type": row["report_type"],
        "schedule": row["schedule"],
        "next_run": row["next_run"],
        "last_run": row.get("last_run"),
        "is_active": bool(row.get("is_active")),
        "recipients": json.loads(row.get("recipients", "[]")),
        "created_at": row["created_at"],
        "created_by": row["created_by"],
    }


def _compute_next_run(schedule: str, from_date: Optional[str] = None) -> str:
    """Compute the next run date based on schedule."""
    if from_date:
        base = datetime.strptime(from_date[:10], "%Y-%m-%d")
    else:
        base = datetime.now(UTC)

    if schedule == "monthly":
        # Next month, same day
        month = base.month + 1 if base.month < 12 else 1
        year = base.year if base.month < 12 else base.year + 1
        day = min(base.day, [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        return datetime(year, month, day, tzinfo=UTC).isoformat()
    elif schedule == "quarterly":
        # Next quarter
        quarter_month = ((base.month - 1) // 3 + 1) * 3 + 1
        if quarter_month > 12:
            quarter_month -= 12
            year = base.year + 1
        else:
            year = base.year
        day = min(base.day, [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][quarter_month - 1])
        return datetime(year, quarter_month, day, tzinfo=UTC).isoformat()
    else:  # annual
        return datetime(base.year + 1, base.month, base.day, tzinfo=UTC).isoformat()


@router.get("")
def list_scheduled_reports(
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    user: dict = Depends(require_auth),
):
    """List scheduled reports for the org."""
    org_id = user["org_id"]
    conn = get_connection()
    try:
        query = "SELECT * FROM scheduled_reports WHERE org_id = ?"
        params = [org_id]

        if is_active is not None:
            query += " AND is_active = ?"
            params.append(1 if is_active else 0)

        query += " ORDER BY next_run ASC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        rows = conn.execute(query, params).fetchall()
        return {"reports": [_report_to_dict(dict(r)) for r in rows], "total": len(rows)}
    finally:
        release_connection(conn)


@router.get("/{report_id}")
def get_scheduled_report(report_id: str, user: dict = Depends(require_auth)):
    """Get a single scheduled report."""
    org_id = user["org_id"]
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM scheduled_reports WHERE id = ? AND org_id = ?",
            (report_id, org_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="not found")
        return _report_to_dict(dict(row))
    finally:
        release_connection(conn)


@router.post("")
def create_scheduled_report(
    payload: dict,
    user: dict = Depends(require_auth),
):
    """Create a new scheduled report. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    schedule = payload.get("schedule", "monthly")
    if schedule not in ALLOWED_SCHEDULES:
        raise HTTPException(
            status_code=400, detail=f"schedule must be one of {sorted(ALLOWED_SCHEDULES)}"
        )

    report_type = payload.get("report_type", "esg_summary")
    if report_type not in ALLOWED_REPORT_TYPES:
        raise HTTPException(
            status_code=400, detail=f"report_type must be one of {sorted(ALLOWED_REPORT_TYPES)}"
        )

    report_id = f"sr_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()
    next_run = _compute_next_run(schedule)
    recipients = json.dumps(payload.get("recipients", []))

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO scheduled_reports
               (id, org_id, name, description, report_type, schedule, next_run,
                is_active, recipients, created_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report_id,
                org_id,
                payload["name"],
                payload.get("description", ""),
                report_type,
                schedule,
                next_run,
                payload.get("is_active", 1),
                recipients,
                now,
                user.get("email", ""),
            ),
        )
        conn.commit()
    finally:
        release_connection(conn)

    return {"id": report_id, "next_run": next_run, "created_at": now}


@router.put("/{report_id}")
def update_scheduled_report(
    report_id: str,
    payload: dict,
    user: dict = Depends(require_auth),
):
    """Update a scheduled report. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT * FROM scheduled_reports WHERE id = ? AND org_id = ?",
            (report_id, org_id),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="not found")

        updates = []
        params = []

        for field in ["name", "description", "report_type", "schedule", "is_active", "recipients"]:
            if field in payload:
                if field == "recipients":
                    updates.append(f"{field} = ?")
                    params.append(json.dumps(payload[field]))
                elif field == "is_active":
                    updates.append(f"{field} = ?")
                    params.append(1 if payload[field] else 0)
                else:
                    updates.append(f"{field} = ?")
                    params.append(payload[field])

        # Recompute next_run if schedule changed
        if "schedule" in payload:
            updates.append("next_run = ?")
            params.append(_compute_next_run(payload["schedule"]))

        if updates:
            params.extend([report_id, org_id])
            conn.execute(
                f"UPDATE scheduled_reports SET {', '.join(updates)} WHERE id = ? AND org_id = ?",
                params,
            )
            conn.commit()

        return {"id": report_id, "updated_at": datetime.now(UTC).isoformat()}
    finally:
        release_connection(conn)


@router.delete("/{report_id}")
def delete_scheduled_report(report_id: str, user: dict = Depends(require_auth)):
    """Delete a scheduled report. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    conn = get_connection()
    try:
        result = conn.execute(
            "DELETE FROM scheduled_reports WHERE id = ? AND org_id = ?",
            (report_id, org_id),
        )
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="not found")
        return {"deleted": True}
    finally:
        release_connection(conn)


@router.post("/{report_id}/trigger")
def trigger_report(report_id: str, user: dict = Depends(require_auth)):
    """Manually trigger a report generation. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM scheduled_reports WHERE id = ? AND org_id = ?",
            (report_id, org_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="not found")

        now = datetime.now(UTC).isoformat()
        schedule = row["schedule"]

        # Update last_run and compute next_run
        conn.execute(
            "UPDATE scheduled_reports SET last_run = ?, next_run = ? WHERE id = ?",
            (now, _compute_next_run(schedule, now), report_id),
        )
        conn.commit()

        return {
            "id": report_id,
            "triggered_at": now,
            "next_run": _compute_next_run(schedule, now),
        }
    finally:
        release_connection(conn)
