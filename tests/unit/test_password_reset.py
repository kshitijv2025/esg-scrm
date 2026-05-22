"""Tests for password reset and token invalidation (A4.3, A4.4)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.auth import _rate_limit_store
from src.auth.jwt import create_token, decode_token
from src.db.database import get_connection, release_connection


def _register_user(client, email, password="TestPassword123", name="Test User"):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": name,
        },
    )
    # Auto-verify email so tests can proceed
    verify_token = resp.json().get("verify_token")
    if verify_token:
        from src.db.database import get_connection, release_connection

        conn = get_connection()
        try:
            conn.execute("UPDATE users SET email_verified = 1 WHERE email = ?", (email,))
            conn.commit()
        finally:
            release_connection(conn)
    return resp


@pytest.fixture(autouse=True)
def _clear_rate_limit():
    _rate_limit_store.clear()
    # Reset middleware rate limiter state (same pattern as test_auth.py)
    if app.middleware_stack is not None:
        node = app.middleware_stack
        for _ in range(15):
            if hasattr(node, "reset_state") and callable(node.reset_state):
                node.reset_state()
                break
            if hasattr(node, "app"):
                node = node.app
            else:
                break
    yield
    _rate_limit_store.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_token(
        {
            "sub": "usr_test_001",
            "org_id": "org_bd_001",
            "email": "test@test.com",
            "role": "admin",
        }
    )
    return {"Authorization": f"Bearer {token}"}


class TestForgotPassword:
    def test_forgot_password_returns_success(self, client):
        email = f"forgot_{uuid.uuid4().hex[:8]}@test.com"
        _register_user(client, email)
        resp = client.post("/api/auth/forgot-password", json={"email": email})
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_forgot_password_nonexistent_email_returns_success(self, client):
        """Prevents email enumeration — always returns success."""
        resp = client.post(
            "/api/auth/forgot-password",
            json={
                "email": f"noone_{uuid.uuid4().hex[:8]}@test.com",
            },
        )
        assert resp.status_code == 200

    def test_forgot_password_rate_limited(self, client):
        email = f"rl_{uuid.uuid4().hex[:8]}@test.com"
        for _ in range(6):
            client.post("/api/auth/forgot-password", json={"email": email})
        resp = client.post("/api/auth/forgot-password", json={"email": email})
        assert resp.status_code == 429


class TestResetPassword:
    def test_reset_with_invalid_token(self, client):
        resp = client.post(
            "/api/auth/reset-password",
            json={
                "token": "invalid_token_12345",
                "new_password": "NewSecure123",
            },
        )
        assert resp.status_code == 400

    def test_reset_rejects_weak_password(self, client):
        resp = client.post(
            "/api/auth/reset-password",
            json={
                "token": "any_token",
                "new_password": "weak",
            },
        )
        assert resp.status_code == 422


class TestTokenVersion:
    def test_token_without_version_still_valid(self):
        """Backward compatibility — tokens without token_version still decode."""
        token = create_token(
            {
                "sub": "usr_test_001",
                "org_id": "org_bd_001",
                "email": "test@test.com",
                "role": "admin",
            }
        )
        payload = decode_token(token)
        assert payload is not None
        assert "token_version" not in payload

    def test_token_with_version_decodes(self, client):
        """Tokens with token_version decode when user exists and matches."""
        email = f"tv_{uuid.uuid4().hex[:8]}@test.com"
        resp = _register_user(client, email)
        user_id = resp.json()["user"]["id"]

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT token_version FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            current_version = row["token_version"]
        finally:
            release_connection(conn)

        token = create_token(
            {
                "sub": user_id,
                "org_id": resp.json()["org"]["id"],
                "email": email,
                "role": "admin",
                "token_version": current_version,
            }
        )
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("token_version") == current_version

    def test_stale_version_rejected(self, client):
        """Tokens with stale token_version are rejected."""
        email = f"stale_{uuid.uuid4().hex[:8]}@test.com"
        resp = _register_user(client, email)
        user_id = resp.json()["user"]["id"]
        org_id = resp.json()["org"]["id"]

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT token_version FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            current_version = row["token_version"]
        finally:
            release_connection(conn)

        stale_version = current_version + 999
        token = create_token(
            {
                "sub": user_id,
                "org_id": org_id,
                "email": email,
                "role": "admin",
                "token_version": stale_version,
            }
        )
        payload = decode_token(token)
        assert payload is None

    def test_expired_token_rejected(self):
        """Expired tokens are rejected regardless of version."""
        token = create_token(
            {
                "sub": "usr_test_001",
                "org_id": "org_bd_001",
                "email": "test@test.com",
                "role": "admin",
            },
            expires_in=-1,
        )
        payload = decode_token(token)
        assert payload is None


class TestPasswordResetFlow:
    def test_full_reset_flow(self, client):
        """End-to-end: register → forgot → reset → login with new password."""
        import uuid

        email = f"reset_test_{uuid.uuid4().hex[:8]}@test.com"

        # Register (auto-verified via helper)
        resp = _register_user(client, email, "OldPassword123", "Reset Test User")
        assert resp.status_code == 200
        old_token = resp.json()["token"]

        # Forgot password
        resp = client.post("/api/auth/forgot-password", json={"email": email})
        assert resp.status_code == 200

        # Get the reset token from DB
        from src.db.database import get_connection, release_connection

        conn = get_connection()
        try:
            row = conn.execute("SELECT reset_token FROM users WHERE email = ?", (email,)).fetchone()
        finally:
            release_connection(conn)
        assert row is not None
        reset_token = row["reset_token"]
        assert reset_token is not None

        # Reset password
        resp = client.post(
            "/api/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "NewPassword456",
            },
        )
        assert resp.status_code == 200

        # Old token should be invalid (token_version bumped)
        old_payload = decode_token(old_token)
        assert old_payload is None

        # Login with new password
        resp = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "NewPassword456",
            },
        )
        assert resp.status_code == 200
        new_token = resp.json()["token"]
        assert decode_token(new_token) is not None

        # Old password should fail
        resp = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "OldPassword123",
            },
        )
        assert resp.status_code == 401
