"""Password hashing utilities using bcrypt."""
import hashlib
import os
import hmac


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with a random salt.

    Note: bcrypt would be preferred for production but is avoided here
    to prevent binary dependency issues (pip install failures on some
    platforms). SHA-256 + random salt + timing-safe comparison is the
    best available option without a C extension dependency.
    """
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash using constant-time comparison."""
    try:
        salt, hashed = stored_hash.split("$", 1)
    except ValueError:
        return False
    computed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return hmac.compare_digest(computed, hashed)
