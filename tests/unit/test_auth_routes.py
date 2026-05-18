"""Tests for auth route security — password validation, duplicate registration,
login error messages, and RBAC error message hygiene."""
import sys
import uuid

sys.path.insert(0, "src")

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.auth import _rate_limit_store
from src.auth.jwt import create_token

client = TestClient(app)

# Passwords that satisfy the strength validator:
# >=8 chars, at least one uppercase, one lowercase, one digit
_STRONG_PW = "Testpass1"


def _uid():
    return f"{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def _clear_rate_limit():
    """Reset the in-memory rate limiter before every test."""
    _rate_limit_store.clear()
    yield


# ---------------------------------------------------------------------------
# Registration — password strength
# ---------------------------------------------------------------------------

class TestRegistrationPasswordStrength:
    """Weak passwords MUST be rejected with 422."""

    def test_short_password_returns_422(self):
        r = client.post("/api/auth/register", json={
            "email": f"short-{_uid()}@example.com",
            "password": "Ab1",
            "full_name": "Short PW",
        })
        assert r.status_code == 422

    def test_no_uppercase_returns_422(self):
        r = client.post("/api/auth/register", json={
            "email": f"noupper-{_uid()}@example.com",
            "password": "lowercase1",
            "full_name": "No Upper",
        })
        assert r.status_code == 422

    def test_no_lowercase_returns_422(self):
        r = client.post("/api/auth/register", json={
            "email": f"nolower-{_uid()}@example.com",
            "password": "UPPERCASE1",
            "full_name": "No Lower",
        })
        assert r.status_code == 422

    def test_no_digit_returns_422(self):
        r = client.post("/api/auth/register", json={
            "email": f"nodigit-{_uid()}@example.com",
            "password": "NoDigitsHere",
            "full_name": "No Digit",
        })
        assert r.status_code == 422

    def test_strong_password_succeeds(self):
        r = client.post("/api/auth/register", json={
            "email": f"strong-{_uid()}@example.com",
            "password": _STRONG_PW,
            "full_name": "Strong PW User",
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert data["user"]["email"].startswith("strong-")


# ---------------------------------------------------------------------------
# Registration — duplicate email
# ---------------------------------------------------------------------------

class TestRegistrationDuplicateEmail:
    """Duplicate registration MUST return 409 with a GENERIC message
    (NOT revealing that the email exists)."""

    def test_duplicate_email_returns_409(self):
        email = f"dup-{_uid()}@example.com"
        # First registration succeeds
        r1 = client.post("/api/auth/register", json={
            "email": email,
            "password": _STRONG_PW,
            "full_name": "First User",
        })
        assert r1.status_code == 200

        # Second registration with same email returns 409
        r2 = client.post("/api/auth/register", json={
            "email": email,
            "password": "Anotherpw1",
            "full_name": "Second User",
        })
        assert r2.status_code == 409

    def test_duplicate_email_message_is_generic(self):
        """The 409 message MUST NOT say 'Email already registered' or
        otherwise confirm the email exists in the system."""
        email = f"generic-{_uid()}@example.com"
        client.post("/api/auth/register", json={
            "email": email,
            "password": _STRONG_PW,
            "full_name": "First User",
        })
        r = client.post("/api/auth/register", json={
            "email": email,
            "password": "Anotherpw1",
            "full_name": "Second User",
        })
        assert r.status_code == 409
        detail = r.json()["detail"]
        # Must NOT contain the literal phrase that leaks email existence
        assert "already registered" not in detail.lower()
        assert "email exists" not in detail.lower()
        assert "user exists" not in detail.lower()
        assert "already taken" not in detail.lower()
        # The actual implementation uses "Registration failed. Please try again."
        assert len(detail) > 0


# ---------------------------------------------------------------------------
# Login — wrong password
# ---------------------------------------------------------------------------

class TestLoginWrongPassword:
    """Login with wrong password MUST return 401 with a generic message."""

    def test_wrong_password_returns_401(self):
        email = f"wrongpw-{_uid()}@example.com"
        client.post("/api/auth/register", json={
            "email": email,
            "password": _STRONG_PW,
            "full_name": "Wrong PW User",
        })
        r = client.post("/api/auth/login", json={
            "email": email,
            "password": "Wrongpass1",
        })
        assert r.status_code == 401

    def test_wrong_password_message_is_generic(self):
        """The 401 message MUST be 'Invalid email or password' and
        MUST NOT reveal which part (email vs password) was wrong."""
        email = f"genericpw-{_uid()}@example.com"
        client.post("/api/auth/register", json={
            "email": email,
            "password": _STRONG_PW,
            "full_name": "Generic PW User",
        })
        r = client.post("/api/auth/login", json={
            "email": email,
            "password": "Wrongpass1",
        })
        assert r.status_code == 401
        detail = r.json()["detail"]
        # Must contain the generic combined message
        assert "Invalid email or password" in detail
        # Must NOT separate the two failure modes
        assert "password incorrect" not in detail.lower()
        assert "wrong password" not in detail.lower()
        assert "user not found" not in detail.lower()
        assert "email not found" not in detail.lower()

    def test_nonexistent_user_same_message(self):
        """Login for a nonexistent user MUST return the same generic message
        as a wrong password — no user enumeration via error messages."""
        r = client.post("/api/auth/login", json={
            "email": f"nonexistent-{_uid()}@example.com",
            "password": _STRONG_PW,
        })
        assert r.status_code == 401
        detail = r.json()["detail"]
        assert "Invalid email or password" in detail


# ---------------------------------------------------------------------------
# RBAC error message hygiene
# ---------------------------------------------------------------------------

class TestRBACErrorMessageHygiene:
    """RBAC error messages MUST NOT contain role names."""

    def test_rbac_403_does_not_contain_role_names(self):
        """The 403 error from require_role must not leak the user's role
        or the required roles."""
        from fastapi import HTTPException
        from src.api.middleware.rbac import require_role, EDITOR_ROLES

        viewer_user = {"role": "viewer", "org_id": "org_bd_001"}
        with pytest.raises(HTTPException) as exc_info:
            require_role(viewer_user, EDITOR_ROLES)

        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail
        # Role names must not appear in the error detail
        assert "viewer" not in detail.lower()
        assert "admin" not in detail.lower()
        assert "editor" not in detail.lower()
        # Should contain generic message instead
        assert "Insufficient permissions" in detail

    def test_rbac_403_for_unknown_role_does_not_leak(self):
        from fastapi import HTTPException
        from src.api.middleware.rbac import require_role, ADMIN_ROLES

        unknown_user = {"role": "superuser"}
        with pytest.raises(HTTPException) as exc_info:
            require_role(unknown_user, ADMIN_ROLES)

        detail = exc_info.value.detail
        assert "superuser" not in detail
        assert "admin" not in detail.lower()
