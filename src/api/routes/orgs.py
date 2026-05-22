"""Organization API routes — multi-org user access, switching, membership, and invitations."""

import secrets
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, validator

from src.auth.jwt import create_token, decode_token
from src.db.database import get_connection, release_connection

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper: get auth payload
# ---------------------------------------------------------------------------


def _get_auth_payload(request: Request) -> Optional[dict]:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    return decode_token(token)


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class InviteUserRequest(BaseModel):
    email: str
    full_name: str
    role: str = "viewer"

    @validator("role")
    def _validate_role(cls, v: str) -> str:
        if v not in ("admin", "editor", "viewer"):
            raise ValueError("Role must be admin, editor, or viewer")
        return v


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
def list_orgs(request: Request):
    """List all organizations the current user belongs to.
    from __future__ import annotations
    from typing import Optional

        Returns the user's primary org from users.org_id plus all orgs from user_orgs.
        Each org includes the user's role in that org.
    """
    payload = _get_auth_payload(request)
    if not payload:
        raise HTTPException(401, "Valid token required")

    user_id = payload["sub"]
    conn = get_connection()
    try:
        # Get user's primary org from users table
        user_row = conn.execute(
            "SELECT org_id FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        primary_org_id = user_row["org_id"] if user_row else None

        # Get all org memberships from user_orgs table
        memberships = conn.execute(
            """SELECT uo.org_id, uo.role, uo.is_primary, uo.joined_at,
                      o.name, o.industry, o.country, o.plan, o.created_at
               FROM user_orgs uo
               JOIN organizations o ON o.id = uo.org_id
               WHERE uo.user_id = ?
               ORDER BY uo.is_primary DESC, uo.joined_at ASC""",
            (user_id,),
        ).fetchall()

        orgs = []
        seen_org_ids = set()

        # Add memberships from user_orgs
        for row in memberships:
            seen_org_ids.add(row["org_id"])
            orgs.append(
                {
                    "org_id": row["org_id"],
                    "name": row["name"],
                    "industry": row["industry"],
                    "country": row["country"],
                    "plan": row["plan"],
                    "role": row["role"],
                    "is_primary": bool(row["is_primary"]),
                    "joined_at": row["joined_at"],
                    "created_at": row["created_at"],
                }
            )

        # Add primary org if not already in the list (e.g., user has no user_orgs entry yet)
        if primary_org_id and primary_org_id not in seen_org_ids:
            org = conn.execute(
                "SELECT id, name, industry, country, plan, created_at "
                "FROM organizations WHERE id = ?",
                (primary_org_id,),
            ).fetchone()
            if org:
                # Determine role in primary org — check user_orgs first, fall back to users.role
                role_row = conn.execute(
                    "SELECT role FROM user_orgs WHERE user_id = ? AND org_id = ?",
                    (user_id, primary_org_id),
                ).fetchone()
                role = role_row["role"] if role_row else payload.get("role", "admin")
                orgs.insert(
                    0,
                    {
                        "org_id": org["id"],
                        "name": org["name"],
                        "industry": org["industry"],
                        "country": org["country"],
                        "plan": org["plan"],
                        "role": role,
                        "is_primary": True,
                        "joined_at": None,
                        "created_at": org["created_at"],
                    },
                )

        return {"orgs": orgs}
    finally:
        release_connection(conn)


@router.post("/{org_id}/switch")
def switch_org(org_id: str, request: Request):
    """Switch the user's active organization context.

    Updates the JWT's org_id claim and returns a new token.
    The user must be a member of the target org.
    """
    payload = _get_auth_payload(request)
    if not payload:
        raise HTTPException(401, "Valid token required")

    user_id = payload["sub"]

    conn = get_connection()
    try:
        # Check if user is a member of the target org
        membership = conn.execute(
            "SELECT role FROM user_orgs WHERE user_id = ? AND org_id = ?",
            (user_id, org_id),
        ).fetchone()

        # Also check if target org is user's primary org
        user_row = conn.execute(
            "SELECT org_id, email, role, token_version FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        is_primary_org = user_row and user_row["org_id"] == org_id

        if not membership and not is_primary_org:
            raise HTTPException(403, "You are not a member of this organization")

        # Determine role in target org
        role_in_target = (
            membership["role"] if membership else (user_row["role"] if user_row else "viewer")
        )
        target_email = user_row["email"] if user_row else payload.get("email", "")
        token_version = user_row["token_version"] if user_row else payload.get("token_version", 1)

        # Verify target org exists
        org = conn.execute(
            "SELECT id FROM organizations WHERE id = ?",
            (org_id,),
        ).fetchone()
        if not org:
            raise HTTPException(404, "Organization not found")

        # Create new token with updated org_id
        new_token = create_token(
            {
                "sub": user_id,
                "org_id": org_id,
                "email": target_email,
                "role": role_in_target,
                "token_version": token_version,
            }
        )

        return {
            "token": new_token,
            "org_id": org_id,
            "role": role_in_target,
        }
    finally:
        release_connection(conn)


@router.get("/{org_id}/members")
def list_org_members(org_id: str, request: Request):
    """List members of an organization.

    Returns users from user_orgs joined with users table for full details.
    Requires auth; user must be a member of the org.
    """
    payload = _get_auth_payload(request)
    if not payload:
        raise HTTPException(401, "Valid token required")

    user_id = payload["sub"]

    conn = get_connection()
    try:
        # Check if current user is a member of the org
        user_membership = conn.execute(
            "SELECT role FROM user_orgs WHERE user_id = ? AND org_id = ?",
            (user_id, org_id),
        ).fetchone()

        user_row = conn.execute(
            "SELECT org_id FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        is_primary_org = user_row and user_row["org_id"] == org_id

        if not user_membership and not is_primary_org:
            raise HTTPException(403, "You are not a member of this organization")

        # Verify org exists
        org = conn.execute(
            "SELECT id, name FROM organizations WHERE id = ?",
            (org_id,),
        ).fetchone()
        if not org:
            raise HTTPException(404, "Organization not found")

        # Get members from user_orgs joined with users
        members = conn.execute(
            """SELECT u.id, u.email, u.full_name, u.role AS user_role,
                      uo.role AS org_role, uo.is_primary, uo.joined_at,
                      u.invited_by, u.last_login
               FROM user_orgs uo
               JOIN users u ON u.id = uo.user_id
               WHERE uo.org_id = ?
               ORDER BY uo.is_primary DESC, uo.joined_at ASC""",
            (org_id,),
        ).fetchall()

        # Also get the primary user if org_id matches users.org_id
        primary_users = conn.execute(
            """SELECT u.id, u.email, u.full_name, u.role AS user_role,
                      u.org_id, u.last_login
               FROM users u
               WHERE u.org_id = ?
               AND u.id NOT IN (SELECT user_id FROM user_orgs WHERE org_id = ?)
               ORDER BY u.created_at ASC""",
            (org_id, org_id),
        ).fetchall()

        result = []
        for row in members:
            result.append(
                {
                    "user_id": row["id"],
                    "email": row["email"],
                    "full_name": row["full_name"],
                    "role": row["org_role"] if row["org_role"] else row["user_role"],
                    "is_primary": bool(row["is_primary"]),
                    "joined_at": row["joined_at"],
                    "invited_by": row["invited_by"],
                    "last_login": row["last_login"],
                }
            )

        for row in primary_users:
            result.append(
                {
                    "user_id": row["id"],
                    "email": row["email"],
                    "full_name": row["full_name"],
                    "role": row["user_role"],
                    "is_primary": True,
                    "joined_at": None,
                    "invited_by": None,
                    "last_login": row["last_login"],
                }
            )

        return {
            "org_id": org_id,
            "org_name": org["name"],
            "members": result,
        }
    finally:
        release_connection(conn)


@router.post("/{org_id}/invite")
def invite_org_user(org_id: str, body: InviteUserRequest, request: Request):
    """Invite a user to an organization.

    Creates a pending user record with invite_token.
    Requires auth; current user must be admin of the target org.
    """
    payload = _get_auth_payload(request)
    if not payload:
        raise HTTPException(401, "Valid token required")

    user_id = payload["sub"]

    conn = get_connection()
    try:
        # Check if current user is admin of the org
        membership = conn.execute(
            "SELECT role FROM user_orgs WHERE user_id = ? AND org_id = ?",
            (user_id, org_id),
        ).fetchone()

        user_row = conn.execute(
            "SELECT org_id, role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        is_primary_org = user_row and user_row["org_id"] == org_id

        if not membership and not is_primary_org:
            raise HTTPException(403, "You are not a member of this organization")

        # Check admin status
        current_role = (
            membership["role"] if membership else (user_row["role"] if user_row else "viewer")
        )
        if current_role != "admin":
            raise HTTPException(403, "Only admins can invite users")

        # Verify org exists
        org = conn.execute(
            "SELECT id FROM organizations WHERE id = ?",
            (org_id,),
        ).fetchone()
        if not org:
            raise HTTPException(404, "Organization not found")

        # Check for duplicate email in the org
        existing = conn.execute(
            """SELECT u.id FROM users u
               JOIN user_orgs uo ON u.id = uo.user_id
               WHERE u.email = ? AND uo.org_id = ?""",
            (body.email, org_id),
        ).fetchone()
        if existing:
            raise HTTPException(
                409, "A user with this email is already a member of this organization"
            )

        # Also check if email exists in the org via primary org link
        existing_primary = conn.execute(
            "SELECT id FROM users WHERE email = ? AND org_id = ?",
            (body.email, org_id),
        ).fetchone()
        if existing_primary:
            raise HTTPException(
                409, "A user with this email is already a member of this organization"
            )

        invite_token = secrets.token_urlsafe(48)
        new_user_id = f"usr_{uuid.uuid4().hex[:12]}"

        # Create an unusable password hash — user has not set password yet
        unusable_hash = "!" + secrets.token_urlsafe(32)

        conn.execute(
            """INSERT INTO users (id, org_id, email, password_hash, full_name, role,
                                  is_active, email_verified, invited_by, invite_token)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                new_user_id,
                org_id,
                body.email,
                unusable_hash,
                body.full_name,
                body.role,
                0,  # inactive until they accept invite
                0,  # not email verified yet
                user_id,
                invite_token,
            ),
        )

        # Add to user_orgs if user already exists (was previously a member or has account)
        # For new users, they don't get a user_orgs entry until they accept
        conn.commit()
    finally:
        release_connection(conn)

    return {
        "message": f"Invitation sent to {body.email}",
        "invite_token": invite_token,
        "user": {
            "id": new_user_id,
            "email": body.email,
            "full_name": body.full_name,
            "role": body.role,
        },
    }


@router.delete("/{org_id}/members/{target_user_id}")
def remove_org_member(org_id: str, target_user_id: str, request: Request):
    """Remove a user from an organization.

    Requires auth; current user must be admin of the target org.
    Cannot remove the last admin of an org.
    """
    payload = _get_auth_payload(request)
    if not payload:
        raise HTTPException(401, "Valid token required")

    user_id = payload["sub"]

    conn = get_connection()
    try:
        # Check if current user is admin of the org
        membership = conn.execute(
            "SELECT role FROM user_orgs WHERE user_id = ? AND org_id = ?",
            (user_id, org_id),
        ).fetchone()

        user_row = conn.execute(
            "SELECT org_id, role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        is_primary_org = user_row and user_row["org_id"] == org_id

        if not membership and not is_primary_org:
            raise HTTPException(403, "You are not a member of this organization")

        # Check admin status
        current_role = (
            membership["role"] if membership else (user_row["role"] if user_row else "viewer")
        )
        if current_role != "admin":
            raise HTTPException(403, "Only admins can remove members")

        # Verify org exists
        org = conn.execute(
            "SELECT id FROM organizations WHERE id = ?",
            (org_id,),
        ).fetchone()
        if not org:
            raise HTTPException(404, "Organization not found")

        # Check if target user is a member of the org
        target_membership = conn.execute(
            "SELECT role, is_primary FROM user_orgs WHERE user_id = ? AND org_id = ?",
            (target_user_id, org_id),
        ).fetchone()

        target_user = conn.execute(
            "SELECT id, org_id AS primary_org_id FROM users WHERE id = ?",
            (target_user_id,),
        ).fetchone()

        is_target_primary_org = target_user and target_user["primary_org_id"] == org_id

        if not target_membership and not is_target_primary_org:
            raise HTTPException(404, "User is not a member of this organization")

        # Cannot remove self
        if target_user_id == user_id:
            raise HTTPException(400, "Cannot remove yourself from the organization")

        # Check if target is the last admin
        if target_membership and target_membership["role"] == "admin":
            admin_count = conn.execute(
                """SELECT COUNT(*) as cnt FROM user_orgs
                   WHERE org_id = ? AND role = 'admin'""",
                (org_id,),
            ).fetchone()
            # Also count admins in primary org link
            primary_admin = conn.execute(
                "SELECT role FROM users WHERE id = ? AND org_id = ? AND role = 'admin'",
                (target_user_id, org_id),
            ).fetchone()

            total_admins = admin_count["cnt"] if admin_count else 0
            if primary_admin:
                total_admins += 1

            if total_admins <= 1:
                raise HTTPException(400, "Cannot remove the last admin of the organization")

        # Remove from user_orgs
        if target_membership:
            conn.execute(
                "DELETE FROM user_orgs WHERE user_id = ? AND org_id = ?",
                (target_user_id, org_id),
            )

        # If target's primary org is this org, deactivate the user
        if is_target_primary_org:
            conn.execute(
                "UPDATE users SET is_active = 0 WHERE id = ?",
                (target_user_id,),
            )

        conn.commit()

        return {"message": "User removed from organization"}
    finally:
        release_connection(conn)
