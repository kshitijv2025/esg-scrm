"""Authentication API routes — register, login, refresh, profile."""
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, validator

from src.auth.jwt import create_token, decode_token
from src.auth.password import hash_password, needs_rehash, verify_password
from src.db.database import get_connection, release_connection

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory rate limiter — sliding window per client IP (bounded)
# ---------------------------------------------------------------------------
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_IPS = 10_000  # bound to prevent unbounded growth


def _check_rate_limit(ip: str) -> bool:
    """Return True if the request is allowed, False if rate-limited."""
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW
    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if t > cutoff]
    if len(_rate_limit_store[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit_store[ip].append(now)
    # Evict stale IPs when store exceeds max size
    if len(_rate_limit_store) > RATE_LIMIT_MAX_IPS:
        stale = [k for k, v in _rate_limit_store.items() if not v]
        for k in stale:
            del _rate_limit_store[k]
    return True


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    org_name: Optional[str] = None
    industry: Optional[str] = ""
    country: Optional[str] = ""

    @validator("password")
    def _validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError(
                "Password must be at least 8 characters long"
            )
        if not re.search(r"[A-Z]", v):
            raise ValueError(
                "Password must contain at least one uppercase letter"
            )
        if not re.search(r"[a-z]", v):
            raise ValueError(
                "Password must contain at least one lowercase letter"
            )
        if not re.search(r"\d", v):
            raise ValueError(
                "Password must contain at least one digit"
            )
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
def register(body: RegisterRequest, request: Request):
    """Register a new user and organization."""
    if not _check_rate_limit(request.client.host):
        raise HTTPException(429, "Too many requests. Try again later.")

    conn = get_connection()
    try:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (body.email,)).fetchone()
        if existing:
            raise HTTPException(409, "Registration failed. Please try again.")

        org_id = f"org_{uuid.uuid4().hex[:12]}"
        org_name = body.org_name or f"{body.full_name}'s Organization"

        conn.execute(
            "INSERT INTO organizations (id, name, industry, country) VALUES (?, ?, ?, ?)",
            (org_id, org_name, body.industry or "", body.country or ""),
        )

        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        password_hash = hash_password(body.password)

        conn.execute(
            "INSERT INTO users (id, org_id, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, org_id, body.email, password_hash, body.full_name, "admin"),
        )
        conn.commit()
    finally:
        release_connection(conn)

    token = create_token({
        "sub": user_id,
        "org_id": org_id,
        "email": body.email,
        "role": "admin",
    })

    return {
        "user": {"id": user_id, "email": body.email, "full_name": body.full_name, "role": "admin"},
        "org": {"id": org_id, "name": org_name, "industry": body.industry or "", "country": body.country or ""},
        "token": token,
    }


@router.post("/login")
def login(body: LoginRequest, request: Request):
    """Authenticate user and return JWT token."""
    if not _check_rate_limit(request.client.host):
        raise HTTPException(429, "Too many requests. Try again later.")

    conn = get_connection()
    try:
        user = conn.execute(
            "SELECT id, org_id, email, password_hash, full_name, role, is_active FROM users WHERE email = ?",
            (body.email,),
        ).fetchone()

        if not user or not verify_password(body.password, user["password_hash"]):
            raise HTTPException(401, "Invalid email or password")

        # Migrate legacy SHA-256 hashes to bcrypt on successful login
        if needs_rehash(user["password_hash"]):
            new_hash = hash_password(body.password)
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, user["id"]),
            )

        if not user["is_active"]:
            raise HTTPException(403, "Account is deactivated")

        token = create_token({
            "sub": user["id"],
            "org_id": user["org_id"],
            "email": user["email"],
            "role": user["role"],
        })

        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), user["id"]),
        )
        conn.commit()
    finally:
        release_connection(conn)

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
    try:
        user = conn.execute(
            "SELECT id, org_id, email, full_name, role, is_active, last_login FROM users WHERE id = ?",
            (payload["sub"],),
        ).fetchone()
        org = conn.execute(
            "SELECT id, name, industry, country FROM organizations WHERE id = ?",
            (payload["org_id"],),
        ).fetchone()
    finally:
        release_connection(conn)

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
