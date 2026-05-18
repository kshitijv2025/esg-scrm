"""Tests for authentication system — JWT, password hashing, auth routes."""
import sys
sys.path.insert(0, "src")

from fastapi.testclient import TestClient
from src.api.main import app
from src.auth.jwt import create_token, decode_token
from src.auth.password import hash_password, verify_password

client = TestClient(app)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("secret123")
        assert "$" in hashed
        assert verify_password("secret123", hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("secret123")
        assert not verify_password("wrong", hashed)

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("secret123")
        h2 = hash_password("secret123")
        assert h1 != h2

    def test_malformed_hash_returns_false(self):
        assert not verify_password("secret123", "not_a_hash")


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
        r = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User",
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["role"] == "admin"
        assert "id" in data["org"]

    def test_register_duplicate_email(self):
        client.post("/api/auth/register", json={
            "email": "dup@example.com",
            "password": "pass123",
            "full_name": "Dup User",
        })
        r = client.post("/api/auth/register", json={
            "email": "dup@example.com",
            "password": "pass456",
            "full_name": "Another User",
        })
        assert r.status_code == 409

    def test_login_success(self):
        client.post("/api/auth/register", json={
            "email": "login@example.com",
            "password": "loginpass",
            "full_name": "Login User",
        })
        r = client.post("/api/auth/login", json={
            "email": "login@example.com",
            "password": "loginpass",
        })
        assert r.status_code == 200
        assert "token" in r.json()

    def test_login_wrong_password(self):
        client.post("/api/auth/register", json={
            "email": "wrong@example.com",
            "password": "rightpass",
            "full_name": "Wrong User",
        })
        r = client.post("/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass",
        })
        assert r.status_code == 401

    def test_login_nonexistent_user(self):
        r = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "anything",
        })
        assert r.status_code == 401

    def test_me_with_valid_token(self):
        reg = client.post("/api/auth/register", json={
            "email": "me@example.com",
            "password": "mypass",
            "full_name": "Me User",
        }).json()
        r = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {reg['token']}",
        })
        assert r.status_code == 200
        assert r.json()["user"]["email"] == "me@example.com"

    def test_me_without_token(self):
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_refresh_token(self):
        reg = client.post("/api/auth/register", json={
            "email": "refresh@example.com",
            "password": "mypass",
            "full_name": "Refresh User",
        }).json()
        r = client.post("/api/auth/refresh", headers={
            "Authorization": f"Bearer {reg['token']}",
        })
        assert r.status_code == 200
        assert "token" in r.json()
