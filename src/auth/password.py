"""Password hashing utilities using bcrypt with SHA-256 migration support."""

import hashlib
import hmac
import re

import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Returns a bcrypt hash string (60 bytes, starts with ``$2b$``).
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash.

    Supports both bcrypt hashes and legacy SHA-256 hashes (``salt$hex``).
    Returns True if the password matches, False otherwise.
    """
    # Detect legacy SHA-256 hash: 64 hex chars after a ``$`` separator
    if _is_legacy_sha256_hash(stored_hash):
        return _verify_sha256(password, stored_hash)

    # bcrypt verification
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """Return True if the stored hash is a legacy SHA-256 hash that should be
    upgraded to bcrypt on next successful login."""
    return _is_legacy_sha256_hash(stored_hash)


def _is_legacy_sha256_hash(stored_hash: str) -> bool:
    """Detect SHA-256 hashes: format ``<salt_hex>$<64_hex_chars>``."""
    if "$" not in stored_hash:
        return False
    parts = stored_hash.split("$", 1)
    if len(parts) != 2:
        return False
    salt, hex_digest = parts
    # SHA-256 hex digest is exactly 64 hex characters
    return len(hex_digest) == 64 and bool(re.fullmatch(r"[0-9a-f]{64}", hex_digest))


def _verify_sha256(password: str, stored_hash: str) -> bool:
    """Verify against legacy SHA-256 hash."""
    try:
        salt, hashed = stored_hash.split("$", 1)
    except ValueError:
        return False
    computed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return hmac.compare_digest(computed, hashed)
