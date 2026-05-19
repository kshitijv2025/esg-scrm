"""JWT token creation and validation."""
import json
import hmac
import hashlib
import base64
import os
import time
from typing import Any, Optional

_jwt_secret: Optional[str] = None


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
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
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
    signature = hmac.new(
        _get_secret().encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    signature_b64 = _b64url_encode(signature)

    return f"{signing_input}.{signature_b64}"


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """Decode and verify a JWT token. Returns payload or None if invalid."""
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

        return payload
    except Exception:
        return None
