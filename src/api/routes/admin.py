"""Admin API routes — user management, API keys, org settings, audit log."""
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.api.middleware.auth import require_auth
from src.db.database import get_connection, release_connection, insert_audit_log

router = APIRouter()


def _require_admin(user: dict) -> None:
    if user.get("role") != "admin":
        raise HTTPException(403, "Forbidden")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@router.get("/users")
def list_users(user: dict = Depends(require_auth)):
    """List all users in the same organization. Admin only."""
    _require_admin(user)

    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id, email, full_name, role, is_active, last_login, created_at
               FROM users WHERE org_id = ? ORDER BY created_at DESC""",
            (user["org_id"],),
        ).fetchall()
        return {
            "users": [
                {
                    "id": r["id"],
                    "email": r["email"],
                    "full_name": r["full_name"],
                    "role": r["role"],
                    "is_active": bool(r["is_active"]),
                    "last_login": r["last_login"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
        }
    finally:
        release_connection(conn)


class UpdateRoleRequest:
    def __init__(self, role: str):
        if role not in ("admin", "editor", "viewer"):
            raise HTTPException(400, "Role must be admin, editor, or viewer")
        self.role = role


@router.put("/users/{user_id}/role")
def update_user_role(user_id: str, body: dict, user: dict = Depends(require_auth)):
    """Change a user's role. Admin only."""
    _require_admin(user)

    role = body.get("role", "")
    if role not in ("admin", "editor", "viewer"):
        raise HTTPException(400, "Role must be admin, editor, or viewer")

    conn = get_connection()
    try:
        target = conn.execute(
            "SELECT id, role FROM users WHERE id = ? AND org_id = ?",
            (user_id, user["org_id"]),
        ).fetchone()
        if not target:
            raise HTTPException(404, "User not found")

        conn.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (role, user_id),
        )
        conn.commit()

        insert_audit_log(
            org_id=user["org_id"],
            user_id=user["sub"],
            action="role_change",
            resource_type="user",
            resource_id=user_id,
            details=f"Changed role from {target['role']} to {role}",
            ip_address="",
        )
    finally:
        release_connection(conn)

    return {"message": "Role updated"}


@router.delete("/users/{user_id}")
def deactivate_user(user_id: str, user: dict = Depends(require_auth)):
    """Deactivate a user. Admin only."""
    _require_admin(user)

    if user_id == user["sub"]:
        raise HTTPException(400, "Cannot deactivate your own account")

    conn = get_connection()
    try:
        target = conn.execute(
            "SELECT id, is_active FROM users WHERE id = ? AND org_id = ?",
            (user_id, user["org_id"]),
        ).fetchone()
        if not target:
            raise HTTPException(404, "User not found")

        conn.execute(
            "UPDATE users SET is_active = 0 WHERE id = ?",
            (user_id,),
        )
        conn.commit()

        insert_audit_log(
            org_id=user["org_id"],
            user_id=user["sub"],
            action="user_deactivate",
            resource_type="user",
            resource_id=user_id,
            details=f"Deactivated user {user_id}",
            ip_address="",
        )
    finally:
        release_connection(conn)

    return {"message": "User deactivated"}


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------

class OrgUpdateRequest:
    def __init__(self, name: str = "", industry: str = "", country: str = ""):
        self.name = name
        self.industry = industry
        self.country = country


@router.put("/org")
def update_org(body: dict, user: dict = Depends(require_auth)):
    """Update organization profile. Admin only."""
    _require_admin(user)

    name = body.get("name", "").strip()
    industry = body.get("industry", "").strip()
    country = body.get("country", "").strip()

    if not name:
        raise HTTPException(400, "Organization name is required")

    conn = get_connection()
    try:
        result = conn.execute(
            "UPDATE organizations SET name = ?, industry = ?, country = ? WHERE id = ?",
            (name, industry, country, user["org_id"]),
        )
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(404, "Organization not found")

        insert_audit_log(
            org_id=user["org_id"],
            user_id=user["sub"],
            action="org_update",
            resource_type="organization",
            resource_id=user["org_id"],
            details=f"Updated org: name={name}, industry={industry}, country={country}",
            ip_address="",
        )
    finally:
        release_connection(conn)

    return {"message": "Organization updated"}


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

@router.get("/api-keys")
def list_api_keys(user: dict = Depends(require_auth)):
    """List API keys for the organization. Admin only."""
    _require_admin(user)

    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id, name, key_prefix, last_used, created_at
               FROM api_keys WHERE org_id = ? ORDER BY created_at DESC""",
            (user["org_id"],),
        ).fetchall()
        return {
            "keys": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "key": r["key_prefix"] + "..." if r["key_prefix"] else r["id"][:8] + "...",
                    "last_used_at": r["last_used"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
        }
    finally:
        release_connection(conn)


@router.post("/api-keys")
def create_api_key(body: dict, user: dict = Depends(require_auth)):
    """Generate a new API key. Admin only."""
    _require_admin(user)

    raw_key = f"esg_{secrets.token_urlsafe(32)}"
    key_id = f"key_{uuid.uuid4().hex[:12]}"
    name = body.get("name", "Unnamed key")

    # Store a SHA-256 hash of the key, not the key itself
    import hashlib
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    # Store first 8 chars of raw key as prefix for display
    key_prefix = raw_key[:8]

    conn = get_connection()
    try:
        # Add key_prefix column if it doesn't exist (for existing tables)
        try:
            conn.execute("ALTER TABLE api_keys ADD COLUMN key_prefix TEXT")
        except Exception:
            pass  # Column already exists

        conn.execute(
            """INSERT INTO api_keys (id, org_id, user_id, key_hash, key_prefix, name)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (key_id, user["org_id"], user["sub"], key_hash, key_prefix, name),
        )
        conn.commit()

        insert_audit_log(
            org_id=user["org_id"],
            user_id=user["sub"],
            action="api_key_create",
            resource_type="api_key",
            resource_id=key_id,
            details=f"Created API key: {name}",
            ip_address="",
        )
    finally:
        release_connection(conn)

    return {"id": key_id, "key": raw_key, "name": name}


@router.delete("/api-keys/{key_id}")
def revoke_api_key(key_id: str, user: dict = Depends(require_auth)):
    """Revoke an API key. Admin only."""
    _require_admin(user)

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM api_keys WHERE id = ? AND org_id = ?",
            (key_id, user["org_id"]),
        ).fetchone()
        if not row:
            raise HTTPException(404, "API key not found")

        conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        conn.commit()

        insert_audit_log(
            org_id=user["org_id"],
            user_id=user["sub"],
            action="api_key_revoke",
            resource_type="api_key",
            resource_id=key_id,
            details=f"Revoked API key {key_id}",
            ip_address="",
        )
    finally:
        release_connection(conn)

    return {"message": "API key revoked"}


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

@router.get("/audit-log")
def list_audit_log(
    page: int = 1,
    page_size: int = 20,
    user: str = None,
    action: str = None,
    start_date: str = None,
    end_date: str = None,
    _user: dict = Depends(require_auth),
):
    """Query audit log with filters. Admin only."""
    # Note: the `user` param shadows the auth user — rename for clarity
    auth_user = _user
    _require_admin(auth_user)

    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20
    skip = (page - 1) * page_size

    conn = get_connection()
    try:
        # Build query
        query = "SELECT * FROM audit_log WHERE org_id = ?"
        count_query = "SELECT COUNT(*) as cnt FROM audit_log WHERE org_id = ?"
        params = [auth_user["org_id"]]
        count_params = [auth_user["org_id"]]

        if action:
            query += " AND action = ?"
            count_query += " AND action = ?"
            params.append(action)
            count_params.append(action)

        if user:
            # Filter by user email prefix
            query += " AND user_id = ?"
            count_query += " AND user_id = ?"
            params.append(user)
            count_params.append(user)

        if start_date:
            query += " AND date(created_at) >= date(?)"
            count_query += " AND date(created_at) >= date(?)"
            params.append(start_date)
            count_params.append(start_date)

        if end_date:
            query += " AND date(created_at) <= date(?)"
            count_query += " AND date(created_at) <= date(?)"
            params.append(end_date)
            count_params.append(end_date)

        # Get total count
        total = conn.execute(count_query, count_params).fetchone()["cnt"]

        # Get page
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([page_size, skip])

        rows = conn.execute(query, params).fetchall()

        # Enrich with user email
        user_ids = list({r["user_id"] for r in rows})
        emails = {}
        if user_ids:
            placeholders = ",".join(["?"] * len(user_ids))
            email_rows = conn.execute(
                f"SELECT id, email FROM users WHERE id IN ({placeholders})",
                user_ids,
            ).fetchall()
            emails = {r["id"]: r["email"] for r in email_rows}

        logs = [
            {
                "id": r["id"],
                "user_email": emails.get(r["user_id"], r["user_id"]),
                "action": r["action"],
                "resource_type": r["resource_type"],
                "resource_id": r["resource_id"],
                "details": r["details"],
                "ip_address": r["ip_address"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

        return {"logs": logs, "total": total, "page": page, "page_size": page_size}
    finally:
        release_connection(conn)
