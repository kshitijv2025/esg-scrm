"""
Corrective Actions API — CRUD endpoints for tracking corrective actions from risk flags.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import EDITOR_ROLES, VIEWER_ROLES, require_role
from src.db.database import get_connection, release_connection

router = APIRouter()


def _action_to_dict(row: dict) -> dict:
    return {
        "id": row["id"],
        "org_id": row["org_id"],
        "supplier_id": row.get("supplier_id"),
        "flag_id": row.get("flag_id"),
        "title": row["title"],
        "description": row.get("description", ""),
        "status": row["status"],
        "priority": row["priority"],
        "assigned_to": row.get("assigned_to"),
        "deadline": row.get("deadline"),
        "completed_at": row.get("completed_at"),
        "completed_by": row.get("completed_by"),
        "created_at": row["created_at"],
        "updated_at": row.get("updated_at"),
    }


@router.get("")
def list_actions(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    supplier_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    user: dict = Depends(require_auth),
):
    """List corrective actions for the org, optionally filtered."""
    org_id = user["org_id"]
    conn = get_connection()
    try:
        query = "SELECT * FROM corrective_actions WHERE org_id = ?"
        params = [org_id]

        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        if supplier_id:
            query += " AND supplier_id = ?"
            params.append(supplier_id)

        query += " ORDER BY CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, created_at DESC"
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        rows = conn.execute(query, params).fetchall()
        return {"actions": [_action_to_dict(dict(r)) for r in rows], "total": len(rows)}
    finally:
        release_connection(conn)


@router.get("/{action_id}")
def get_action(action_id: str, user: dict = Depends(require_auth)):
    """Get a single corrective action by ID."""
    org_id = user["org_id"]
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM corrective_actions WHERE id = ? AND org_id = ?",
            (action_id, org_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="not found")
        return _action_to_dict(dict(row))
    finally:
        release_connection(conn)


@router.post("")
def create_action(
    payload: dict,
    user: dict = Depends(require_auth),
):
    """Create a new corrective action. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    action_id = f"ca_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO corrective_actions
               (id, org_id, supplier_id, flag_id, title, description, status, priority,
                assigned_to, deadline, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                action_id,
                org_id,
                payload.get("supplier_id"),
                payload.get("flag_id"),
                payload["title"],
                payload.get("description", ""),
                payload.get("status", "open"),
                payload.get("priority", "medium"),
                payload.get("assigned_to"),
                payload.get("deadline"),
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        release_connection(conn)

    return {"id": action_id, "created_at": now}


@router.put("/{action_id}")
def update_action(
    action_id: str,
    payload: dict,
    user: dict = Depends(require_auth),
):
    """Update a corrective action. Requires editor role."""
    require_role(user, EDITOR_ROLES)
    org_id = user["org_id"]

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT * FROM corrective_actions WHERE id = ? AND org_id = ?",
            (action_id, org_id),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="not found")

        updates = []
        params = []
        for field in ["title", "description", "status", "priority", "assigned_to", "deadline"]:
            if field in payload:
                updates.append(f"{field} = ?")
                params.append(payload[field])

        if payload.get("status") == "completed":
            updates.append("completed_at = ?")
            params.append(datetime.now(timezone.utc).isoformat())
            updates.append("completed_by = ?")
            params.append(user.get("email", ""))

        updates.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())

        params.extend([action_id, org_id])
        conn.execute(
            f"UPDATE corrective_actions SET {', '.join(updates)} WHERE id = ? AND org_id = ?",
            params,
        )
        conn.commit()
    finally:
        release_connection(conn)

    return {"id": action_id, "updated_at": datetime.now(timezone.utc).isoformat()}


@router.delete("/{action_id}")
def delete_action(action_id: str, user: dict = Depends(require_auth)):
    """Delete a corrective action. Requires admin role."""
    require_role(user, {"admin"})
    org_id = user["org_id"]

    conn = get_connection()
    try:
        result = conn.execute(
            "DELETE FROM corrective_actions WHERE id = ? AND org_id = ?",
            (action_id, org_id),
        )
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="not found")
        return {"deleted": True}
    finally:
        release_connection(conn)


@router.post("/{action_id}/escalate")
def escalate_action(action_id: str, user: dict = Depends(require_auth)):
    """Escalate an overdue corrective action by creating a new risk flag.

    Returns 400 if the action is not yet overdue.
    """
    org_id = user["org_id"]
    conn = get_connection()
    try:
        # Fetch the action
        row = conn.execute(
            "SELECT * FROM corrective_actions WHERE id = ? AND org_id = ?",
            (action_id, org_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="not found")

        action = dict(row)

        # Check if overdue
        deadline = action.get("deadline")
        if not deadline:
            raise HTTPException(
                status_code=400,
                detail="Action has no deadline — cannot determine if overdue",
            )

        today = datetime.now(timezone.utc).isoformat()[:10]
        if deadline >= today:
            raise HTTPException(
                status_code=400,
                detail="Action is not overdue yet — escalation only allowed after deadline passes",
            )

        # Action is overdue — create a new risk flag
        flag_id = f"flag_escalated_{uuid.uuid4().hex[:12]}"
        title = action.get("title", "Escalated corrective action")
        flag_text = (
            f"CORRECTIVE ACTION OVERDUE: {title}. "
            f"Original deadline was {deadline}. "
            f"Assigned to: {action.get('assigned_to') or 'unassigned'}."
        )

        # Determine severity from priority
        priority = action.get("priority", "medium")
        severity_map = {
            "critical": "CRITICAL",
            "high": "WARNING",
            "medium": "WARNING",
            "low": "INFO",
        }
        severity = severity_map.get(priority, "WARNING")

        conn.execute(
            """INSERT INTO risk_flags
               (id, org_id, factory_id, flag_text, cluster, severity, days_overdue, priority_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                flag_id,
                org_id,
                "factory_bd_001",
                flag_text,
                action.get("cluster", "G2"),
                severity,
                1,
                20.0,
            ),
        )
        conn.commit()

        return {
            "escalated": True,
            "message": "Overdue action escalated — new risk flag created",
            "flag_id": flag_id,
        }
    finally:
        release_connection(conn)
