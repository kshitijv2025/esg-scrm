"""Shared test configuration — sets required environment variables."""
import os
import sys

sys.path.insert(0, "src")

os.environ.setdefault("JWT_SECRET", "test-secret-key-minimum-32-bytes!!")

from src.auth.jwt import create_token


def _auth_headers():
    """Return Authorization headers with a valid test JWT."""
    token = create_token({
        "sub": "usr_test_001",
        "org_id": "org_test_001",
        "email": "test@test.com",
        "role": "admin",
    })
    return {"Authorization": f"Bearer {token}"}
