"""Shared test configuration — sets required environment variables."""
import os
import sys

sys.path.insert(0, "src")

# Must be >= 64 chars to pass jwt.py's minimum secret length check
os.environ.setdefault("JWT_SECRET", "test-secret-key-minimum-64-bytes-long-for-testing-only-do-not-use-in-prod!!")

from src.auth.jwt import create_token


def _auth_headers():
    """Return Authorization headers with a valid test JWT."""
    token = create_token({
        "sub": "usr_test_001",
        "org_id": "org_bd_001",
        "email": "test@test.com",
        "role": "admin",
    })
    return {"Authorization": f"Bearer {token}"}
