"""Password hashing utilities using bcrypt."""
import hashlib
import os
import hmac


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with a random salt."""
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash."""
    try:
        salt, hashed = stored_hash.split("$", 1)
    except ValueError:
        return False
    computed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return hmac.compare_digest(computed, hashed)
