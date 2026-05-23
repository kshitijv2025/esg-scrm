"""JWT token creation and validation."""

import json
import hmac
import hashlib
import base64
import os
import time
from typing import Any, Callable, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

_jwt_secret: Optional[str] = None

_KNOWN_WEAK_SECRETS = frozenset([
    "CHANGE_ME_generate_a_random_64_char_secret",
    "CHANGE_ME",
    "changeme",
    "secret",
    "your-secret-here",
    "insecure",
])

# Optional global getter for token_version validation.
# When set (by auth.py during app initialization), decode_token checks
# token_version against the DB for tokens that carry it.
_token_version_getter: Optional[Callable[[str], Optional[int]]] = None

# RSA key pair for RS256 tokens (asymmetric — private key signs, public key verifies)
_rsa_private_key: Optional[rsa.RSAPrivateKey] = None
_rsa_public_key: Optional[rsa.RSAPublicKey] = None


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
        if _jwt_secret in _KNOWN_WEAK_SECRETS:
            raise RuntimeError(
                "JWT_SECRET is a known insecure placeholder. "
                "Generate a real secret with: "
                'python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        if len(_jwt_secret) < 64:
            raise RuntimeError(
                f"JWT_SECRET must be at least 64 characters (got {len(_jwt_secret)}). "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
    return _jwt_secret


def _get_rsa_private_key() -> Optional[rsa.RSAPrivateKey]:
    """Load RSA private key from JWT_RSA_PRIVATE_KEY env var (PEM format).

    Supports two formats:
    - Direct PEM string in env var
    - File path in env var (path to PEM file)

    Returns None if not configured — signals HS256 fallback.
    """
    global _rsa_private_key
    if _rsa_private_key is not None:
        return _rsa_private_key

    pem_raw = os.environ.get("JWT_RSA_PRIVATE_KEY") or os.environ.get("JWT_RSA_PRIVATE_KEY_PATH")
    if not pem_raw:
        return None

    try:
        # Check if it's a file path
        if os.path.isfile(pem_raw):
            with open(pem_raw, "rb") as f:
                pem_bytes = f.read()
        else:
            # It's a raw PEM string — handle escaped newlines in env var
            pem_bytes = pem_raw.replace("\\n", "\n").encode("utf-8")

        _rsa_private_key = serialization.load_pem_private_key(
            pem_bytes, password=None, backend=default_backend()
        )
        return _rsa_private_key
    except Exception:
        import logging
        logging.getLogger("auth.jwt").exception("jwt._get_rsa_private_key.load_failed")
        return None


def _get_rsa_public_key() -> Optional[rsa.RSAPublicKey]:
    """Derive RSA public key from the private key."""
    global _rsa_public_key
    if _rsa_public_key is not None:
        return _rsa_public_key

    private_key = _get_rsa_private_key()
    if private_key is None:
        return None

    _rsa_public_key = private_key.public_key()
    return _rsa_public_key


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_token(payload: dict[str, Any], expires_in: Optional[int] = None) -> str:
    """Create a signed JWT token.

    Uses RS256 (RSA + SHA-256) when JWT_RSA_PRIVATE_KEY is configured.
    Falls back to HS256 for backward compatibility during migration.
    Default expiry from JWT_EXPIRY_HOURS env var (24h).
    """
    if expires_in is None:
        hours = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))
        expires_in = hours * 3600

    private_key = _get_rsa_private_key()
    if private_key is not None:
        header = {"alg": "RS256", "typ": "JWT"}
        algorithm = "RS256"
    else:
        header = {"alg": "HS256", "typ": "JWT"}
        algorithm = "HS256"

    now = int(time.time())
    payload = {**payload, "iat": now, "exp": now + expires_in}

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    signing_input = f"{header_b64}.{payload_b64}"

    if algorithm == "RS256":
        signature = private_key.sign(
            signing_input.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    else:
        signature = hmac.new(
            _get_secret().encode(), signing_input.encode(), hashlib.sha256
        ).digest()

    signature_b64 = _b64url_encode(signature)
    return f"{signing_input}.{signature_b64}"


def decode_token(token: str, get_user_token_version=None) -> Optional[dict[str, Any]]:
    """Decode and verify a JWT token. Returns payload or None if invalid.

    Supports both RS256 (asymmetric) and HS256 (symmetric) based on the token's
    alg header. token_version validation is also performed.

    Returns None if:
    - Signature verification fails
    - Token is expired
    - User's token_version in DB doesn't match the token's
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        actual_sig = _b64url_decode(signature_b64)

        # Decode header to determine algorithm
        try:
            header = json.loads(_b64url_decode(header_b64))
        except Exception:
            return None
        alg = header.get("alg", "HS256")

        if alg == "RS256":
            public_key = _get_rsa_public_key()
            if public_key is None:
                # RSA configured for signing but public key not available for verification
                import logging
                logging.getLogger("auth.jwt").warning("jwt.decode_token.rs256_but_no_public_key")
                return None
            try:
                public_key.verify(
                    actual_sig,
                    signing_input.encode("utf-8"),
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )
            except Exception:
                return None
        elif alg == "HS256":
            expected_sig = hmac.new(
                _get_secret().encode(), signing_input.encode(), hashlib.sha256
            ).digest()
            if not hmac.compare_digest(expected_sig, actual_sig):
                return None
        else:
            # Unknown algorithm
            import logging
            logging.getLogger("auth.jwt").warning("jwt.decode_token.unknown_alg", alg=alg)
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
