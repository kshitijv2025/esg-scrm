"""Tests for GDPR data export and account deletion endpoints."""

import json
import uuid

try:
    from datetime import UTC, datetime, timedelta
except ImportError:
    from datetime import timezone, datetime, timedelta

    UTC = timezone.utc

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.jwt import create_token
from src.db.database import get_connection, release_connection, reset_database

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup_test_org():
    """Ensure test org and user exist in the DB."""
    reset_database()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO organizations (id, name, industry, plan) VALUES (?, ?, ?, ?)",
            (
                "org_bd_001",
                "Bangladesh Export Textiles Ltd.",
                "Garment manufacturing",
                "professional",
            ),
        )
        conn.execute(
            """INSERT OR IGNORE INTO users
               (id, org_id, email, password_hash, full_name, role, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                "usr_test_gdpr_001",
                "org_bd_001",
                "gdpr@test.com",
                "!test",
                "GDPR Test User",
                "admin",
                1,
            ),
        )
        conn.commit()
    finally:
        release_connection(conn)
    yield


def _auth_headers(user_id: str = "usr_test_gdpr_001", org_id: str = "org_bd_001") -> dict:
    token = create_token(
        {
            "sub": user_id,
            "org_id": org_id,
            "email": "gdpr@test.com",
            "role": "admin",
        }
    )
    return {"Authorization": f"Bearer {token}"}


class TestGdprExport:
    """POST /api/gdpr/export — create GDPR export job."""

    def test_returns_401_without_auth(self):
        resp = client.post("/api/gdpr/export")
        assert resp.status_code == 401

    def test_returns_export_job_with_download_url(self):
        resp = client.post("/api/gdpr/export", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "download_url" in data
        assert "expires_at" in data
        assert data["download_url"].startswith("/api/gdpr/export/")

    def test_creates_gdpr_export_jobs_record(self):
        job_id = None
        resp = client.post("/api/gdpr/export", headers=_auth_headers())
        assert resp.status_code == 200
        download_url = resp.json()["download_url"]
        job_id = download_url.split("/")[-1]

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT id, org_id, user_id, status FROM gdpr_export_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
            assert row is not None
            assert row["status"] == "ready"
            assert row["org_id"] == "org_bd_001"
        finally:
            release_connection(conn)

    def test_expires_at_is_7_days_from_now(self):
        resp = client.post("/api/gdpr/export", headers=_auth_headers())
        assert resp.status_code == 200
        expires_at = datetime.fromisoformat(resp.json()["expires_at"])
        now = datetime.now(UTC)
        delta = expires_at - now
        assert 6 <= delta.days <= 8  # within 7-day window


class TestGdprExportDownload:
    """GET /api/gdpr/export/{job_id} — download export file."""

    def test_returns_401_without_auth(self):
        resp = client.get("/api/gdpr/export/gdpr_nonexistent123")
        assert resp.status_code == 401

    def test_returns_404_for_nonexistent_job(self):
        resp = client.get("/api/gdpr/export/gdpr_nonexistent123", headers=_auth_headers())
        assert resp.status_code == 404

    def test_returns_403_if_job_belongs_to_other_user(self):
        # Create a job belonging to a different user
        conn = get_connection()
        try:
            other_user_id = "usr_other_001"
            conn.execute(
                """INSERT OR IGNORE INTO users
                   (id, org_id, email, password_hash, full_name, role, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (other_user_id, "org_bd_001", "other@test.com", "!test", "Other User", "admin", 1),
            )
            job_id = f"gdpr_{uuid.uuid4().hex[:12]}"
            conn.execute(
                "INSERT INTO gdpr_export_jobs (id, org_id, user_id, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    job_id,
                    "org_bd_001",
                    other_user_id,
                    "ready",
                    datetime.now(UTC).isoformat(),
                ),
            )
            # Write a temp file so the endpoint has something to read
            export_data = {"user": {"id": other_user_id}, "audit_log": []}
            file_path = f"/tmp/gdpr_export_{job_id}.json"
            with open(file_path, "w") as f:
                json.dump(export_data, f)
            conn.execute(
                "UPDATE gdpr_export_jobs SET file_path = ? WHERE id = ?",
                (file_path, job_id),
            )
            conn.commit()
        finally:
            release_connection(conn)

        resp = client.get(f"/api/gdpr/export/{job_id}", headers=_auth_headers())
        assert resp.status_code == 403

    def test_returns_400_if_job_not_ready(self):
        conn = get_connection()
        try:
            job_id = f"gdpr_{uuid.uuid4().hex[:12]}"
            conn.execute(
                "INSERT INTO gdpr_export_jobs (id, org_id, user_id, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    job_id,
                    "org_bd_001",
                    "usr_test_gdpr_001",
                    "processing",
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
        finally:
            release_connection(conn)

        resp = client.get(f"/api/gdpr/export/{job_id}", headers=_auth_headers())
        assert resp.status_code == 400
        assert "not ready" in resp.json()["detail"]

    def test_returns_410_if_export_expired(self):
        conn = get_connection()
        try:
            job_id = f"gdpr_{uuid.uuid4().hex[:12]}"
            past = (datetime.now(UTC) - timedelta(days=8)).isoformat()
            conn.execute(
                "INSERT INTO gdpr_export_jobs (id, org_id, user_id, status, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, "org_bd_001", "usr_test_gdpr_001", "ready", past, past),
            )
            conn.commit()
        finally:
            release_connection(conn)

        resp = client.get(f"/api/gdpr/export/{job_id}", headers=_auth_headers())
        assert resp.status_code == 410

    def test_returns_export_data_when_valid(self):
        conn = get_connection()
        try:
            job_id = f"gdpr_{uuid.uuid4().hex[:12]}"
            file_path = f"/tmp/gdpr_export_{job_id}.json"
            export_data = {
                "user": {"id": "usr_test_gdpr_001", "email": "gdpr@test.com"},
                "organization": {"id": "org_bd_001", "name": "Bangladesh Export Textiles Ltd."},
                "audit_log": [],
                "notifications": [],
            }
            with open(file_path, "w") as f:
                json.dump(export_data, f)
            expires = (datetime.now(UTC) + timedelta(days=7)).isoformat()
            conn.execute(
                "INSERT INTO gdpr_export_jobs (id, org_id, user_id, status, file_path, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    job_id,
                    "org_bd_001",
                    "usr_test_gdpr_001",
                    "ready",
                    file_path,
                    expires,
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
        finally:
            release_connection(conn)

        resp = client.get(f"/api/gdpr/export/{job_id}", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["id"] == "usr_test_gdpr_001"


class TestGdprAccountDeletion:
    """DELETE /api/gdpr/account — soft-delete user account."""

    def test_returns_401_without_auth(self):
        resp = client.delete("/api/gdpr/account")
        assert resp.status_code == 401

    def test_soft_deletes_account(self):
        resp = client.delete("/api/gdpr/account", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "scheduled for deletion" in data["message"]
        assert "deleted_at" in data

    def test_sets_deleted_email_and_redacted_name(self):
        client.delete("/api/gdpr/account", headers=_auth_headers())

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT email, full_name, is_active, password_hash FROM users WHERE id = ?",
                ("usr_test_gdpr_001",),
            ).fetchone()
            assert row is not None
            assert row["is_active"] == 0
            assert row["email"].startswith("deleted_")
            assert row["full_name"] == "Deleted User"
            assert row["password_hash"] == "!DELETED"
        finally:
            release_connection(conn)

    def test_returns_400_if_already_deleted(self):
        client.delete("/api/gdpr/account", headers=_auth_headers())  # first deletion
        resp = client.delete("/api/gdpr/account", headers=_auth_headers())  # second attempt
        assert resp.status_code == 400
        assert "already deleted" in resp.json()["detail"]
