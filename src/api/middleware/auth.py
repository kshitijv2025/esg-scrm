"""
Auth dependency for FastAPI routes.

Usage:
    from src.api.middleware.auth import require_auth

    @router.get("/protected")
    def protected_route(user: dict = Depends(require_auth)):
        tenant_id = user["org_id"]
"""

from fastapi import HTTPException, Request
from typing import Optional

from src.auth.jwt import decode_token


def _extract_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def require_auth(request: Request) -> dict:
    """FastAPI dependency that validates JWT and returns user payload.

    Returns dict with keys: sub, org_id, email, role.
    Raises HTTPException 401 if token is missing or invalid.
    """
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Send Authorization: Bearer <token>",
        )

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    return {
        "sub": payload["sub"],
        "org_id": payload["org_id"],
        "email": payload["email"],
        "role": payload["role"],
    }


def optional_auth(request: Request) -> Optional[dict]:
    """Like require_auth but returns None instead of raising when no token present.

    Use for endpoints that work for both authenticated and anonymous users.
    """
    token = _extract_token(request)
    if not token:
        return None
    return decode_token(token)
