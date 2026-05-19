"""Audit log API — action trail for compliance."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from src.api.middleware.auth import require_auth
from src.api.middleware.rbac import require_role, VIEWER_ROLES, EDITOR_ROLES
from src.db.database import get_connection, release_connection, _fetchall, _execute, insert_audit_log

router = APIRouter()


@router.get("/log")
def list_audit_log(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    user: dict = Depends(require_auth),
):
    """Query audit log entries. Filtered to requesting user's org."""
    effective_org = user["org_id"]
    conn = get_connection()
    try:
        query = "SELECT * FROM audit_log WHERE 1=1"
        params: list = []

        if effective_org:
            query += " AND org_id = ?"
            params.append(effective_org)
        if action:
            query += " AND action = ?"
            params.append(action)
        if resource_type:
            query += " AND resource_type = ?"
            params.append(resource_type)
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        entries = _fetchall(conn, query, tuple(params))
        return {"entries": entries, "total": len(entries)}
    finally:
        release_connection(conn)


@router.post("/log")
def create_audit_entry(
    body: dict,
    user: dict = Depends(require_auth),
):
    """Record an audit log entry. Requires editor role or above."""
    require_role(user, EDITOR_ROLES)
    required = ["action", "resource_type"]
    for field in required:
        if field not in body:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    insert_audit_log(
        org_id=user["org_id"],
        user_id=user["sub"],
        action=body["action"],
        resource_type=body["resource_type"],
        resource_id=body.get("resource_id", ""),
        details=body.get("details", ""),
        ip_address=body.get("ip_address", ""),
    )

    return {"status": "recorded"}
