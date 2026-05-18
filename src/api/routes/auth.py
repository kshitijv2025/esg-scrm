"""Authentication API routes — register, login, refresh, profile."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

from src.auth.jwt import create_token, decode_token
from src.auth.password import hash_password, verify_password
from src.db.database import get_connection

router = APIRouter()


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    org_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
def register(body: RegisterRequest):
    """Register a new user and organization."""
    conn = get_connection()

    existing = conn.execute("SELECT id FROM users WHERE email = ?", (body.email,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(409, "Email already registered")

    org_id = f"org_{uuid.uuid4().hex[:12]}"
    org_name = body.org_name or f"{body.full_name}'s Organization"

    conn.execute(
        "INSERT INTO organizations (id, name) VALUES (?, ?)",
        (org_id, org_name),
    )

    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    password_hash = hash_password(body.password)

    conn.execute(
        "INSERT INTO users (id, org_id, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, org_id, body.email, password_hash, body.full_name, "admin"),
    )
    conn.commit()
    conn.close()

    token = create_token({
        "sub": user_id,
        "org_id": org_id,
        "email": body.email,
        "role": "admin",
    })

    return {
        "user": {"id": user_id, "email": body.email, "full_name": body.full_name, "role": "admin"},
        "org": {"id": org_id, "name": org_name},
        "token": token,
    }


@router.post("/login")
def login(body: LoginRequest):
    """Authenticate user and return JWT token."""
    conn = get_connection()
    user = conn.execute(
        "SELECT id, org_id, email, password_hash, full_name, role, is_active FROM users WHERE email = ?",
        (body.email,),
    ).fetchone()
    conn.close()

    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")

    if not user["is_active"]:
        raise HTTPException(403, "Account is deactivated")

    token = create_token({
        "sub": user["id"],
        "org_id": user["org_id"],
        "email": user["email"],
        "role": user["role"],
    })

    conn = get_connection()
    conn.execute(
        "UPDATE users SET last_login = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), user["id"]),
    )
    conn.commit()
    conn.close()

    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
        },
        "token": token,
    }


@router.post("/refresh")
def refresh(request: Request):
    """Refresh an existing JWT token."""
    payload = _get_auth_payload(request)
    if not payload:
        raise HTTPException(401, "Valid token required")

    new_token = create_token({
        "sub": payload["sub"],
        "org_id": payload["org_id"],
        "email": payload["email"],
        "role": payload["role"],
    })
    return {"token": new_token}


@router.get("/me")
def me(request: Request):
    """Get current user profile."""
    payload = _get_auth_payload(request)
    if not payload:
        raise HTTPException(401, "Valid token required")

    conn = get_connection()
    user = conn.execute(
        "SELECT id, org_id, email, full_name, role, is_active, last_login FROM users WHERE id = ?",
        (payload["sub"],),
    ).fetchone()
    org = conn.execute(
        "SELECT id, name, industry FROM organizations WHERE id = ?",
        (payload["org_id"],),
    ).fetchone()
    conn.close()

    if not user:
        raise HTTPException(404, "User not found")

    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "last_login": user["last_login"],
        },
        "org": dict(org) if org else None,
    }


def _get_auth_payload(request: Request) -> Optional[dict]:
    """Extract and validate JWT from Authorization header."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    return decode_token(token)
