"""JWT token creation and validation."""

import json
import hmac
import hashlib
import base64
import os
import time
from typing import Any, Callable, Optional

_jwt_secret: Optional[str] = None

# Optional global getter for token_version validation.
# When set (by auth.py during app initialization), decode_token checks
# token_version against the DB for tokens that carry it.
_token_version_getter: Optional[Callable[[str], Optional[int]]] = None


def set_token_version_getter(fn: Callable[[str], Optional[int]]) -> None:
    """Set the global token_version lookup function. Called by auth.py on startup."""
    global _token_version_getter
    _token_version_getter = fn


def _get_user_version_from_db(user_id: str) -> Optional[int]:
    if _token_version_getter is None:
        return None
    return _token_version_getter(user_id)


def _get_secret() -> str:
    global _jwt_secret
    if _jwt_secret is None:
        _jwt_secret = os.environ.get("JWT_SECRET")
        if not _jwt_secret:
            raise RuntimeError(
                "JWT_SECRET environment variable is required. "
                "Set it in .env before starting the application."
            )
        if len(_jwt_secret) < 32:
            raise RuntimeError(
                f"JWT_SECRET must be at least 32 characters (got {len(_jwt_secret)}). "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
    return _jwt_secret


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_token(payload: dict[str, Any], expires_in: Optional[int] = None) -> str:
    """Create a signed JWT token. Default expiry from JWT_EXPIRY_HOURS env var (24h)."""
    if expires_in is None:
        hours = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))
        expires_in = hours * 3600
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {**payload, "iat": now, "exp": now + expires_in}

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(_get_secret().encode(), signing_input.encode(), hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)

    return f"{signing_input}.{signature_b64}"


def decode_token(token: str, get_user_token_version=None) -> Optional[dict[str, Any]]:
    """Decode and verify a JWT token. Returns payload or None if invalid.

    Validates token_version against the DB if:
    (a) get_user_token_version callback is passed, OR
    (b) the global _token_version_getter is set (set by auth.py on startup).

    Returns None if the user's token_version in the DB doesn't match the token's.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"

        expected_sig = hmac.new(
            _get_secret().encode(), signing_input.encode(), hashlib.sha256
        ).digest()
        actual_sig = _b64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64url_decode(payload_b64))
        if payload.get("exp", 0) < int(time.time()):
            return None

        if "token_version" in payload:
            # Use explicit callback if passed, otherwise fall back to global getter
            getter = (
                get_user_token_version
                if get_user_token_version is not None
                else _get_user_version_from_db
            )
            user_id = payload.get("sub")
            if user_id and getter is not None:
                current_version = getter(user_id)
                if current_version is not None and payload["token_version"] != current_version:
                    return None
        else:
            # Token carries no token_version — reject if the user's version > 1
            # (means password was reset since this token was issued).
            getter = (
                get_user_token_version
                if get_user_token_version is not None
                else _get_user_version_from_db
            )
            user_id = payload.get("sub")
            if user_id and getter is not None:
                current_version = getter(user_id)
                if current_version is not None and current_version > 1:
                    # User has been versioned (password reset) — reject unversioned old token
                    return None

        return payload
    except Exception:
        # Log exception type — payload is untrusted, don't log contents
        import logging

        logging.getLogger("auth.jwt").exception("jwt.decode_token.invalid_token")
        return None
