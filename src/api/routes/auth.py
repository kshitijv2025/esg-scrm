"""Authentication API routes — register, login, refresh, profile."""

import re
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, validator

from src.auth.jwt import create_token, decode_token, set_token_version_getter
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
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
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
        verify_token = str(uuid.uuid4().hex)

        conn.execute(
            "INSERT INTO users (id, org_id, email, password_hash, full_name, role, "
            "email_verify_token) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, org_id, body.email, password_hash, body.full_name, "admin", verify_token),
        )
        conn.commit()
    finally:
        release_connection(conn)

    token = create_token(
        {
            "sub": user_id,
            "org_id": org_id,
            "email": body.email,
            "role": "admin",
            "token_version": 1,
        }
    )

    return {
        "user": {"id": user_id, "email": body.email, "full_name": body.full_name, "role": "admin"},
        "org": {
            "id": org_id,
            "name": org_name,
            "industry": body.industry or "",
            "country": body.country or "",
        },
        "token": token,
        "verify_token": verify_token,
    }


@router.post("/verify-email")
def verify_email(body: dict, request: Request):
    """Verify a user's email using the token sent during registration."""
    token = body.get("token", "")
    if not token:
        raise HTTPException(400, "Token is required")

    conn = get_connection()
    try:
        user = conn.execute(
            "SELECT id, email_verified FROM users WHERE email_verify_token = ?",
            (token,),
        ).fetchone()
        if not user:
            raise HTTPException(400, "Invalid or expired verification token")
        if user["email_verified"]:
            return {"status": "already_verified"}
        conn.execute(
            "UPDATE users SET email_verified = 1, email_verify_token = NULL WHERE id = ?",
            (user["id"],),
        )
        conn.commit()
    finally:
        release_connection(conn)

    return {"status": "verified"}


@router.post("/resend-verification")
def resend_verification(body: dict, request: Request):
    """Resend the verification email (generate a new verify token)."""
    email = body.get("email", "")
    if not email:
        raise HTTPException(400, "Email is required")

    conn = get_connection()
    try:
        user = conn.execute(
            "SELECT id, email_verified FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if not user:
            return {"status": "ok"}  # Don't reveal whether email exists
        if user["email_verified"]:
            return {"status": "already_verified"}
        verify_token = str(uuid.uuid4().hex)
        conn.execute(
            "UPDATE users SET email_verify_token = ? WHERE id = ?",
            (verify_token, user["id"]),
        )
        conn.commit()
    finally:
        release_connection(conn)

    return {"status": "ok", "verify_token": verify_token}


@router.post("/invite")
def invite_user(body: dict, request: Request):
    """Invite a new user to the organization. Requires admin role."""
    payload = _get_auth_payload(request)
    if not payload:
        raise HTTPException(401, "Valid token required")
    if payload.get("role") != "admin":
        raise HTTPException(403, "Admin role required")

    email = body.get("email", "")
    full_name = body.get("full_name", "")
    role = body.get("role", "viewer")
    if not email or not full_name:
        raise HTTPException(400, "email and full_name are required")

    conn = get_connection()
    try:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            raise HTTPException(409, "User with this email already exists")

        invite_token = str(uuid.uuid4().hex)
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        # password_hash is NOT NULL; accept_invite sets the real hash
        conn.execute(
            "INSERT INTO users (id, org_id, email, full_name, role, invite_token, "
            "password_hash, is_active, invited_by) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)",
            (
                user_id,
                payload["org_id"],
                email,
                full_name,
                role,
                invite_token,
                "PENDING_INVITE",
                payload["sub"],
            ),
        )
        conn.commit()
    finally:
        release_connection(conn)

    return {
        "user": {"id": user_id, "email": email, "full_name": full_name, "role": role},
        "invite_token": invite_token,
    }


class AcceptInviteRequest(BaseModel):
    token: str
    new_password: str

    @validator("new_password")
    def _validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @validator("new_password")
    def _validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


@router.post("/accept-invite")
def accept_invite(body: AcceptInviteRequest, request: Request):
    """Accept an invitation and set the user's password."""
    token = body.token
    new_password = body.new_password

    conn = get_connection()
    try:
        user = conn.execute(
            "SELECT id, org_id, email, full_name, role, token_version "
            "FROM users WHERE invite_token = ?",
            (token,),
        ).fetchone()
        if not user:
            raise HTTPException(400, "Invalid or expired invite token")

        password_hash = hash_password(new_password)
        conn.execute(
            "UPDATE users SET password_hash = ?, invite_token = NULL, "
            "is_active = 1, email_verified = 1 WHERE id = ?",
            (password_hash, user["id"]),
        )
        conn.commit()
    finally:
        release_connection(conn)

    jwt_token = create_token(
        {
            "sub": user["id"],
            "org_id": user["org_id"],
            "email": user["email"],
            "role": user["role"],
            "token_version": user["token_version"],
        }
    )
    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
        },
        "token": jwt_token,
    }


@router.post("/login")
def login(body: LoginRequest, request: Request):
    """Authenticate user and return JWT token."""
    if not _check_rate_limit(request.client.host):
        raise HTTPException(429, "Too many requests. Try again later.")

    conn = get_connection()
    try:
        user = conn.execute(
            "SELECT id, org_id, email, password_hash, full_name, role, is_active, "
            "email_verified, token_version FROM users WHERE email = ?",
            (body.email,),
        ).fetchone()

        if not user or not verify_password(body.password, user["password_hash"]):
            raise HTTPException(401, "Invalid email or password")

        if not user["email_verified"]:
            raise HTTPException(403, "Please verify your email before logging in")

        # Migrate legacy SHA-256 hashes to bcrypt on successful login
        if needs_rehash(user["password_hash"]):
            new_hash = hash_password(body.password)
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, user["id"]),
            )

        if not user["is_active"]:
            raise HTTPException(403, "Account is deactivated")

        token = create_token(
            {
                "sub": user["id"],
                "org_id": user["org_id"],
                "email": user["email"],
                "role": user["role"],
                "token_version": user["token_version"],
            }
        )

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

    new_token = create_token(
        {
            "sub": payload["sub"],
            "org_id": payload["org_id"],
            "email": payload["email"],
            "role": payload["role"],
            "token_version": payload.get("token_version", 1),
        }
    )
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
            "SELECT id, org_id, email, full_name, role, is_active, last_login "
            "FROM users WHERE id = ?",
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


@router.post("/logout")
def logout(request: Request):
    """Logout endpoint — client should discard token. Always returns 200."""
    return {"status": "ok"}


def _get_user_token_version(user_id: str) -> Optional[int]:
    """Return the user's current token_version from DB, or None if user not found."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT token_version FROM users WHERE id = ?", (user_id,)).fetchone()
        return row["token_version"] if row else None
    finally:
        release_connection(conn)


# Wire the global getter so decode_token() checks token_version automatically
# even when called without an explicit callback (e.g. in tests that call decode_token directly).
set_token_version_getter(_get_user_token_version)


def _get_auth_payload(request: Request) -> Optional[dict]:
    """Extract and validate JWT from Authorization header."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    return decode_token(token)


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, request: Request):
    """Initiate password reset — generates a reset token.

    Always returns 200 to prevent email enumeration."""
    if not _check_rate_limit(request.client.host):
        raise HTTPException(429, "Too many requests. Try again later.")

    conn = get_connection()
    try:
        user = conn.execute("SELECT id FROM users WHERE email = ?", (body.email,)).fetchone()
        if user:
            reset_token = uuid.uuid4().hex
            # Token valid for 15 minutes
            expires = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
            conn.execute(
                "UPDATE users SET reset_token = ?, reset_token_expires = ? WHERE email = ?",
                (reset_token, expires, body.email),
            )
            conn.commit()
    finally:
        release_connection(conn)

    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, request: Request):
    """Reset password using a valid reset token."""
    conn = get_connection()
    try:
        user = conn.execute(
            "SELECT id, reset_token_expires FROM users WHERE reset_token = ?",
            (body.token,),
        ).fetchone()

        if not user:
            raise HTTPException(400, "Invalid or expired reset token.")

        if user["reset_token_expires"]:
            expiry = datetime.fromisoformat(user["reset_token_expires"])
            if datetime.now(timezone.utc) >= expiry:
                raise HTTPException(400, "Invalid or expired reset token.")

        new_hash = hash_password(body.new_password)
        new_token_version = 1  # default if column is NULL

        # Bump token_version in the same transaction
        conn.execute(
            "UPDATE users SET password_hash = ?, reset_token = NULL, "
            "reset_token_expires = NULL, token_version = token_version + 1, "
            "is_active = 1, email_verified = 1 WHERE reset_token = ?",
            (new_hash, body.token),
        )

        # Get the updated token_version using user_id we already have
        row = conn.execute(
            "SELECT token_version FROM users WHERE id = ?",
            (user["id"],),
        ).fetchone()
        if row:
            new_token_version = row["token_version"]

        conn.commit()
    finally:
        release_connection(conn)

    return {"message": "Password has been reset successfully.", "token_version": new_token_version}
