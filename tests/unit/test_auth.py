"""Tests for authentication system — JWT, password hashing, auth routes."""
import hashlib
import os
import sys
import uuid
sys.path.insert(0, "src")

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


@pytest.fixture(autouse=True)
def _clear_rate_limit():
    """Reset the in-memory rate limiter before every test."""
    _rate_limit_store.clear()
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
        r = client.post("/api/auth/register", json={
            "email": email,
            "password": _STRONG_PW,
            "full_name": "Test User",
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert data["user"]["email"] == email
        assert data["user"]["role"] == "admin"
        assert "id" in data["org"]

    def test_register_duplicate_email(self):
        email = f"dup-{_uid()}@example.com"
        client.post("/api/auth/register", json={
            "email": email,
            "password": _STRONG_PW,
            "full_name": "Dup User",
        })
        r = client.post("/api/auth/register", json={
            "email": email,
            "password": "Anotherpw1",
            "full_name": "Another User",
        })
        assert r.status_code == 409

    def test_login_success(self):
        email = f"login-{_uid()}@example.com"
        client.post("/api/auth/register", json={
            "email": email,
            "password": "Loginpass1",
            "full_name": "Login User",
        })
        r = client.post("/api/auth/login", json={
            "email": email,
            "password": "Loginpass1",
        })
        assert r.status_code == 200
        assert "token" in r.json()

    def test_login_wrong_password(self):
        email = f"wrong-{_uid()}@example.com"
        client.post("/api/auth/register", json={
            "email": email,
            "password": "Rightpass1",
            "full_name": "Wrong User",
        })
        r = client.post("/api/auth/login", json={
            "email": email,
            "password": "Wrongpass1",
        })
        assert r.status_code == 401

    def test_login_nonexistent_user(self):
        r = client.post("/api/auth/login", json={
            "email": f"noone-{_uid()}@example.com",
            "password": "Anything1",
        })
        assert r.status_code == 401

    def test_me_with_valid_token(self):
        email = f"me-{_uid()}@example.com"
        reg = client.post("/api/auth/register", json={
            "email": email,
            "password": "Mepass001",
            "full_name": "Me User",
        }).json()
        r = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {reg['token']}",
        })
        assert r.status_code == 200
        assert r.json()["user"]["email"] == email

    def test_me_without_token(self):
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_refresh_token(self):
        email = f"refresh-{_uid()}@example.com"
        reg = client.post("/api/auth/register", json={
            "email": email,
            "password": "Refpass001",
            "full_name": "Refresh User",
        }).json()
        r = client.post("/api/auth/refresh", headers={
            "Authorization": f"Bearer {reg['token']}",
        })
        assert r.status_code == 200
        assert "token" in r.json()

    # ----- Password strength validation tests -----

    def test_register_weak_password_rejected(self):
        r = client.post("/api/auth/register", json={
            "email": f"weak-{_uid()}@example.com",
            "password": "short",
            "full_name": "Weak Pw User",
        })
        assert r.status_code == 422

    def test_register_no_uppercase_rejected(self):
        r = client.post("/api/auth/register", json={
            "email": f"noupper-{_uid()}@example.com",
            "password": "lowercase1",
            "full_name": "No Upper",
        })
        assert r.status_code == 422

    def test_register_no_digit_rejected(self):
        r = client.post("/api/auth/register", json={
            "email": f"nodigit-{_uid()}@example.com",
            "password": "NoDigitsHere",
            "full_name": "No Digit",
        })
        assert r.status_code == 422

    # ----- Rate limiting tests -----

    def test_rate_limit_on_register(self):
        for i in range(5):
            r = client.post("/api/auth/register", json={
                "email": f"rl-{_uid()}-{i}@example.com",
                "password": "Rlimitpw1",
                "full_name": f"Rate User {i}",
            })
            assert r.status_code == 200
        # 6th request should be rate-limited
        r = client.post("/api/auth/register", json={
            "email": f"rl-{_uid()}-6@example.com",
            "password": "Rlimitpw1",
            "full_name": "Rate User 6",
        })
        assert r.status_code == 429
        assert "Too many requests" in r.json()["detail"]

    def test_rate_limit_on_login(self):
        email = f"rllogin-{_uid()}@example.com"
        client.post("/api/auth/register", json={
            "email": email,
            "password": "Rlloginpw1",
            "full_name": "RL Login User",
        })
        _rate_limit_store.clear()  # reset after register consumed a slot
        for i in range(5):
            r = client.post("/api/auth/login", json={
                "email": email,
                "password": "Rlloginpw1",
            })
            assert r.status_code == 200
        # 6th request should be rate-limited
        r = client.post("/api/auth/login", json={
            "email": email,
            "password": "Rlloginpw1",
        })
        assert r.status_code == 429
        assert "Too many requests" in r.json()["detail"]
