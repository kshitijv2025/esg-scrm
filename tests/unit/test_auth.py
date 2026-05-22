"""Tests for authentication system — JWT, password hashing, auth routes."""

import hashlib
import os
import sys
import uuid

sys.path.insert(0, "src")

import contextlib

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.auth import _rate_limit_store
from src.auth.jwt import create_token, decode_token
from src.auth.password import hash_password, needs_rehash, verify_password

client = TestClient(app)

# Strong passwords that satisfy the password-strength validator
_STRONG_PW = "Testpass1"


def _uid():
    return f"{uuid.uuid4().hex[:8]}"


def _verify_email(email):
    """Mark user as email-verified directly in the database."""
    from src.db.database import get_connection, release_connection

    conn = get_connection()
    try:
        conn.execute("UPDATE users SET email_verified = 1 WHERE email = ?", (email,))
        conn.commit()
    finally:
        release_connection(conn)


def _reset_middleware_rate_limiter():
    """Reset the RateLimitMiddleware's rate limit store by traversing the built middleware stack."""
    from src.api.main import app

    # Middleware stack is built lazily on first request.
    # Ensure it's built by triggering a dummy request.
    with contextlib.suppress(Exception):
        client.get("/api/health")

    if app.middleware_stack is None:
        return

    # Traverse stack.app.app... until we reach RateLimitMiddleware
    node = app.middleware_stack
    for _ in range(15):
        if hasattr(node, "reset_state") and callable(node.reset_state):
            node.reset_state()
            return
        if hasattr(node, "app"):
            node = node.app
        else:
            break


@pytest.fixture(autouse=True)
def _clear_rate_limit():
    """Reset all in-memory rate limiters before every test."""
    _rate_limit_store.clear()
    _reset_middleware_rate_limiter()
    yield


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password(_STRONG_PW)
        assert hashed.startswith("$2b$")
        assert verify_password(_STRONG_PW, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password(_STRONG_PW)
        assert not verify_password("Wrongpass1", hashed)

    def test_different_hashes_for_same_password(self):
        h1 = hash_password(_STRONG_PW)
        h2 = hash_password(_STRONG_PW)
        assert h1 != h2

    def test_malformed_hash_returns_false(self):
        assert not verify_password(_STRONG_PW, "not_a_hash")

    def test_bcrypt_hash_is_60_bytes(self):
        hashed = hash_password(_STRONG_PW)
        assert len(hashed) == 60

    def test_needs_rehash_detects_legacy_sha256(self):
        salt = os.urandom(16).hex()
        digest = hashlib.sha256(f"{salt}{_STRONG_PW}".encode()).hexdigest()
        legacy = f"{salt}${digest}"
        assert needs_rehash(legacy)

    def test_needs_rehash_returns_false_for_bcrypt(self):
        hashed = hash_password(_STRONG_PW)
        assert not needs_rehash(hashed)

    def test_verify_legacy_sha256_hash(self):
        salt = os.urandom(16).hex()
        digest = hashlib.sha256(f"{salt}{_STRONG_PW}".encode()).hexdigest()
        legacy = f"{salt}${digest}"
        assert verify_password(_STRONG_PW, legacy)
        assert not verify_password("Wrongpass1", legacy)


class TestJWT:
    def test_create_and_decode(self):
        token = create_token({"sub": "user_1", "role": "admin"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user_1"
        assert payload["role"] == "admin"
        assert "exp" in payload

    def test_expired_token_returns_none(self):
        token = create_token({"sub": "user_1"}, expires_in=-1)
        assert decode_token(token) is None

    def test_tampered_token_returns_none(self):
        token = create_token({"sub": "user_1"})
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None

    def test_invalid_format_returns_none(self):
        assert decode_token("not.a.valid.token") is None
        assert decode_token("") is None
        assert decode_token("abc") is None


class TestAuthRoutes:
    def test_register_new_user(self):
        email = f"test-{_uid()}@example.com"
        r = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": _STRONG_PW,
                "full_name": "Test User",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert data["user"]["email"] == email
        assert data["user"]["role"] == "admin"
        assert "id" in data["org"]

    def test_register_duplicate_email(self):
        email = f"dup-{_uid()}@example.com"
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": _STRONG_PW,
                "full_name": "Dup User",
            },
        )
        r = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Anotherpw1",
                "full_name": "Another User",
            },
        )
        assert r.status_code == 409

    def test_login_success(self):
        email = f"login-{_uid()}@example.com"
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Loginpass1",
                "full_name": "Login User",
            },
        )
        _verify_email(email)
        r = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "Loginpass1",
            },
        )
        assert r.status_code == 200
        assert "token" in r.json()

    def test_login_wrong_password(self):
        email = f"wrong-{_uid()}@example.com"
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Rightpass1",
                "full_name": "Wrong User",
            },
        )
        r = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "Wrongpass1",
            },
        )
        assert r.status_code == 401

    def test_login_nonexistent_user(self):
        r = client.post(
            "/api/auth/login",
            json={
                "email": f"noone-{_uid()}@example.com",
                "password": "Anything1",
            },
        )
        assert r.status_code == 401

    def test_me_with_valid_token(self):
        email = f"me-{_uid()}@example.com"
        reg = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Mepass001",
                "full_name": "Me User",
            },
        ).json()
        r = client.get(
            "/api/auth/me",
            headers={
                "Authorization": f"Bearer {reg['token']}",
            },
        )
        assert r.status_code == 200
        assert r.json()["user"]["email"] == email

    def test_me_without_token(self):
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_refresh_token(self):
        email = f"refresh-{_uid()}@example.com"
        reg = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Refpass001",
                "full_name": "Refresh User",
            },
        ).json()
        r = client.post(
            "/api/auth/refresh",
            headers={
                "Authorization": f"Bearer {reg['token']}",
            },
        )
        assert r.status_code == 200
        assert "token" in r.json()

    # ----- Password strength validation tests -----

    def test_register_weak_password_rejected(self):
        r = client.post(
            "/api/auth/register",
            json={
                "email": f"weak-{_uid()}@example.com",
                "password": "short",
                "full_name": "Weak Pw User",
            },
        )
        assert r.status_code == 422

    def test_register_no_uppercase_rejected(self):
        r = client.post(
            "/api/auth/register",
            json={
                "email": f"noupper-{_uid()}@example.com",
                "password": "lowercase1",
                "full_name": "No Upper",
            },
        )
        assert r.status_code == 422

    def test_register_no_digit_rejected(self):
        r = client.post(
            "/api/auth/register",
            json={
                "email": f"nodigit-{_uid()}@example.com",
                "password": "NoDigitsHere",
                "full_name": "No Digit",
            },
        )
        assert r.status_code == 422

    # ----- Rate limiting tests -----

    def test_rate_limit_on_register(self):
        for i in range(5):
            r = client.post(
                "/api/auth/register",
                json={
                    "email": f"rl-{_uid()}-{i}@example.com",
                    "password": "Rlimitpw1",
                    "full_name": f"Rate User {i}",
                },
            )
            assert r.status_code == 200
        # 6th request should be rate-limited
        r = client.post(
            "/api/auth/register",
            json={
                "email": f"rl-{_uid()}-6@example.com",
                "password": "Rlimitpw1",
                "full_name": "Rate User 6",
            },
        )
        assert r.status_code == 429
        assert "Too many requests" in r.json()["detail"]

    def test_rate_limit_on_login(self):
        email = f"rllogin-{_uid()}@example.com"
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Rlloginpw1",
                "full_name": "RL Login User",
            },
        )
        _verify_email(email)
        _rate_limit_store.clear()  # reset after register consumed a slot
        for _i in range(5):
            r = client.post(
                "/api/auth/login",
                json={
                    "email": email,
                    "password": "Rlloginpw1",
                },
            )
            assert r.status_code == 200
        # 6th request should be rate-limited
        r = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "Rlloginpw1",
            },
        )
        assert r.status_code == 429
        assert "Too many requests" in r.json()["detail"]

    # ----- Email verification tests -----

    def test_login_blocked_before_verification(self):
        email = f"unverified-{_uid()}@example.com"
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Unverpass1",
                "full_name": "Unverified User",
            },
        )
        r = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "Unverpass1",
            },
        )
        assert r.status_code == 403
        assert "verify" in r.json()["detail"].lower()

    def test_verify_email_allows_login(self):
        email = f"verify-{_uid()}@example.com"
        reg = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Verifypass1",
                "full_name": "Verify User",
            },
        ).json()
        verify_token = reg["verify_token"]
        r = client.post("/api/auth/verify-email", json={"token": verify_token})
        assert r.status_code == 200
        r = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "Verifypass1",
            },
        )
        assert r.status_code == 200
        assert "token" in r.json()

    def test_verify_email_invalid_token(self):
        r = client.post("/api/auth/verify-email", json={"token": "invalid_token"})
        assert r.status_code == 400

    def test_resend_verification(self):
        email = f"resend-{_uid()}@example.com"
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Resendpass1",
                "full_name": "Resend User",
            },
        )
        r = client.post("/api/auth/resend-verification", json={"email": email})
        assert r.status_code == 200

    def test_resend_verification_nonexistent_email(self):
        r = client.post(
            "/api/auth/resend-verification",
            json={
                "email": f"noone-{_uid()}@example.com",
            },
        )
        assert r.status_code == 200

    # ----- User invitation tests -----

    def _admin_headers(self):
        """Register an admin user and return auth headers."""
        email = f"admin-{_uid()}@example.com"
        reg = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Adminpass1",
                "full_name": "Admin User",
            },
        ).json()
        _verify_email(email)
        return {"Authorization": f"Bearer {reg['token']}"}, reg

    def _viewer_headers(self):
        """Create a viewer user via invite and return auth headers."""
        admin_h, admin_data = self._admin_headers()
        invited_email = f"viewer-{_uid()}@example.com"
        inv = client.post(
            "/api/auth/invite",
            json={
                "email": invited_email,
                "full_name": "Viewer User",
                "role": "viewer",
            },
            headers=admin_h,
        ).json()
        client.post(
            "/api/auth/accept-invite",
            json={
                "token": inv["invite_token"],
                "new_password": "Viewerpass1",
            },
        )
        # Build token with viewer role directly
        token = create_token(
            {
                "sub": inv["user"]["id"],
                "org_id": admin_data["org"]["id"],
                "email": invited_email,
                "role": "viewer",
                "token_version": 2,
            }
        )
        return {"Authorization": f"Bearer {token}"}

    def test_invite_user_success(self):
        admin_h, admin_data = self._admin_headers()
        invited_email = f"invited-{_uid()}@example.com"
        r = client.post(
            "/api/auth/invite",
            json={
                "email": invited_email,
                "full_name": "Invited User",
                "role": "editor",
            },
            headers=admin_h,
        )
        assert r.status_code == 200
        data = r.json()
        assert "invite_token" in data
        assert data["user"]["email"] == invited_email
        assert data["user"]["role"] == "editor"
        assert data["user"]["full_name"] == "Invited User"

    def test_invite_user_non_admin_forbidden(self):
        admin_h, admin_data = self._admin_headers()
        # Create a viewer via invite
        invited_email = f"viewer-{_uid()}@example.com"
        inv = client.post(
            "/api/auth/invite",
            json={
                "email": invited_email,
                "full_name": "Viewer User",
                "role": "viewer",
            },
            headers=admin_h,
        ).json()

        # Accept the invite so the user becomes active
        client.post(
            "/api/auth/accept-invite",
            json={
                "token": inv["invite_token"],
                "new_password": "Viewerpass1",
            },
        )

        # Now create a token for this viewer user
        viewer_token = create_token(
            {
                "sub": inv["user"]["id"],
                "org_id": admin_data["org"]["id"],
                "email": invited_email,
                "role": "viewer",
                "token_version": 1,
            }
        )
        viewer_h = {"Authorization": f"Bearer {viewer_token}"}

        # Viewer tries to invite — should be forbidden
        r = client.post(
            "/api/auth/invite",
            json={
                "email": f"someone-{_uid()}@example.com",
                "full_name": "Someone",
                "role": "viewer",
            },
            headers=viewer_h,
        )
        assert r.status_code == 403

    def test_accept_invite_success(self):
        admin_h, _ = self._admin_headers()
        invited_email = f"accept-{_uid()}@example.com"
        inv = client.post(
            "/api/auth/invite",
            json={
                "email": invited_email,
                "full_name": "Accept User",
                "role": "editor",
            },
            headers=admin_h,
        ).json()

        r = client.post(
            "/api/auth/accept-invite",
            json={
                "token": inv["invite_token"],
                "new_password": "Accepted1",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert data["user"]["email"] == invited_email
        assert data["user"]["role"] == "editor"

    def test_accept_invite_invalid_token(self):
        r = client.post(
            "/api/auth/accept-invite",
            json={
                "token": "nonexistent_token",
                "new_password": "Validpass1",
            },
        )
        assert r.status_code == 400
        assert "Invalid or expired invite token" in r.json()["detail"]

    def test_accept_invite_weak_password(self):
        admin_h, _ = self._admin_headers()
        invited_email = f"weak-{_uid()}@example.com"
        inv = client.post(
            "/api/auth/invite",
            json={
                "email": invited_email,
                "full_name": "Weak Pw",
                "role": "viewer",
            },
            headers=admin_h,
        ).json()

        r = client.post(
            "/api/auth/accept-invite",
            json={
                "token": inv["invite_token"],
                "new_password": "short",
            },
        )
        assert r.status_code == 422

    def test_accept_invite_activates_user(self):
        admin_h, _ = self._admin_headers()
        invited_email = f"activate-{_uid()}@example.com"
        inv = client.post(
            "/api/auth/invite",
            json={
                "email": invited_email,
                "full_name": "Activate User",
                "role": "viewer",
            },
            headers=admin_h,
        ).json()

        # Accept the invite
        client.post(
            "/api/auth/accept-invite",
            json={
                "token": inv["invite_token"],
                "new_password": "Activated1",
            },
        )

        # Verify the user is active by logging in
        r = client.post(
            "/api/auth/login",
            json={
                "email": invited_email,
                "password": "Activated1",
            },
        )
        assert r.status_code == 200
        assert "token" in r.json()

    def test_invite_creates_inactive_user(self):
        admin_h, _ = self._admin_headers()
        invited_email = f"inactive-{_uid()}@example.com"
        client.post(
            "/api/auth/invite",
            json={
                "email": invited_email,
                "full_name": "Inactive User",
                "role": "viewer",
            },
            headers=admin_h,
        ).json()

        # Verify user exists but is inactive by checking login fails
        r = client.post(
            "/api/auth/login",
            json={
                "email": invited_email,
                "password": "Somepass1",
            },
        )
        # Should be 401 (wrong password or inactive) not 200
        assert r.status_code in (401, 403)

        # Also directly verify in the database
        from src.db.database import get_connection, release_connection

        conn = get_connection()
        try:
            user = conn.execute(
                "SELECT is_active, invited_by, invite_token FROM users WHERE email = ?",
                (invited_email,),
            ).fetchone()
            assert user is not None
            assert user["is_active"] == 0
            assert user["invite_token"] is not None
            assert user["invited_by"] is not None
        finally:
            release_connection(conn)
