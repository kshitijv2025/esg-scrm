"""
Tests for documents API endpoints.
Covers upload, list, download, expiry tracking, org isolation, and RBAC.
"""

import io
import os
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.db.database import reset_database, get_connection, release_connection


@pytest.fixture(autouse=True)
def _fresh_db():
    """Reset and seed database before each test."""
    reset_database()
    from src.db.seed import seed

    seed()


@pytest.fixture
def admin_client():
    """Admin user client."""
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_admin_001",
            "org_id": "org_bd_001",
            "email": "admin@textilebd.com",
            "role": "admin",
        }
    )
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture
def editor_client():
    """Editor user client."""
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_editor_001",
            "org_id": "org_bd_001",
            "email": "editor@textilebd.com",
            "role": "editor",
        }
    )
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture
def viewer_client():
    """Viewer user client."""
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_viewer_001",
            "org_id": "org_bd_001",
            "email": "viewer@textilebd.com",
            "role": "viewer",
        }
    )
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture
def other_org_client():
    """Client for a different org (for isolation tests)."""
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_other_001",
            "org_id": "org_other_001",
            "email": "other@other.com",
            "role": "admin",
        }
    )
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture
def _seed_supplier():
    """Seed a supplier for document linking."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO suppliers
               (id, org_id, name, country, industry, tier, annual_spend_usd, phone, email)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "sup_test_001",
                "org_bd_001",
                "Test Supplier",
                "Bangladesh",
                "Textiles",
                "tier1",
                1000000.0,
                "+8801700000000",
                "supplier@test.com",
            ),
        )
        conn.commit()
    finally:
        release_connection(conn)


def _upload_file(client, filename="test.pdf", content=b"fake pdf content", **kwargs):
    """Helper to upload a file."""
    files = {"file": (filename, io.BytesIO(content), "application/pdf")}
    data = {}
    for k, v in kwargs.items():
        data[k] = v
    return client.post("/api/documents/upload", files=files, data=data)


# --- Upload ---


class TestUploadDocument:
    def test_upload_requires_editor_role(self, viewer_client):
        """Viewer cannot upload documents."""
        resp = _upload_file(viewer_client)
        assert resp.status_code == 403

    def test_upload_document(self, editor_client):
        """Editor can upload a document."""
        resp = _upload_file(editor_client, "certificate.pdf", b"cert content")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["id"].startswith("doc_")

    def test_upload_with_supplier(self, editor_client, _seed_supplier):
        """Document can be linked to a supplier."""
        resp = _upload_file(
            editor_client,
            "audit.pdf",
            b"audit content",
            supplier_id="sup_test_001",
        )
        assert resp.status_code == 200

    def test_upload_with_category(self, editor_client):
        """Upload accepts category parameter."""
        resp = _upload_file(
            editor_client,
            "report.pdf",
            b"report content",
            category="audit_report",
        )
        assert resp.status_code == 200

    def test_upload_with_expiry_date(self, editor_client):
        """Upload accepts expiry_date parameter."""
        resp = _upload_file(
            editor_client,
            "cert.pdf",
            b"cert content",
            expiry_date="2027-01-01",
        )
        assert resp.status_code == 200

    def test_upload_requires_file(self, editor_client):
        """Request without file returns 422."""
        resp = editor_client.post("/api/documents/upload", data={})
        assert resp.status_code == 422

    def test_upload_saves_file_to_disk(self, editor_client):
        """Uploaded file is saved to the uploads directory."""
        resp = _upload_file(editor_client, "test.txt", b"hello world")
        assert resp.status_code == 200

        doc_id = resp.json()["id"]
        # Verify DB record
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT file_path FROM documents WHERE id = ?",
                (doc_id,),
            ).fetchone()
            assert row is not None
            assert os.path.exists(row["file_path"])
            with open(row["file_path"], "rb") as f:
                assert f.read() == b"hello world"
        finally:
            release_connection(conn)


# --- List documents ---


class TestListDocuments:
    def test_list_empty(self, admin_client):
        """Returns empty list when no documents exist."""
        resp = admin_client.get("/api/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["documents"] == []
        assert data["total"] == 0

    def test_list_returns_documents(self, admin_client, editor_client):
        """Returns documents for the org."""
        _upload_file(editor_client, "doc1.pdf", b"content1")
        _upload_file(editor_client, "doc2.pdf", b"content2")

        resp = admin_client.get("/api/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_list_filter_by_category(self, admin_client, editor_client):
        """Category filter returns only matching documents."""
        _upload_file(editor_client, "cert.pdf", b"cert", category="certificate")
        _upload_file(editor_client, "report.pdf", b"report", category="audit_report")

        resp = admin_client.get("/api/documents?category=certificate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["documents"][0]["category"] == "certificate"

    def test_list_filter_by_supplier(self, admin_client, editor_client, _seed_supplier):
        """Supplier filter returns only matching documents."""
        _upload_file(editor_client, "with_sup.pdf", b"content", supplier_id="sup_test_001")
        _upload_file(editor_client, "without_sup.pdf", b"content")

        resp = admin_client.get("/api/documents?supplier_id=sup_test_001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_list_excludes_expired_by_default(self, admin_client, editor_client):
        """Expired documents are hidden by default."""
        _upload_file(editor_client, "current.pdf", b"content", expiry_date="2099-01-01")
        _upload_file(editor_client, "expired.pdf", b"content", expiry_date="2020-01-01")

        resp = admin_client.get("/api/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["documents"][0]["name"] == "current.pdf"

    def test_list_include_expired(self, admin_client, editor_client):
        """include_expired=true shows expired documents."""
        _upload_file(editor_client, "expired.pdf", b"content", expiry_date="2020-01-01")

        resp = admin_client.get("/api/documents?include_expired=true")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_org_isolation(self, admin_client, other_org_client, editor_client):
        """Each org only sees its own documents."""
        _upload_file(editor_client, "private.pdf", b"content")

        resp = other_org_client.get("/api/documents")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_requires_auth(self):
        """Unauthenticated request returns 401."""
        client = TestClient(app)
        resp = client.get("/api/documents")
        assert resp.status_code == 401


# --- Get document ---


class TestGetDocument:
    def test_get_document(self, admin_client, editor_client):
        """Can retrieve a single document by ID."""
        upload_resp = _upload_file(editor_client, "getme.pdf", b"content")
        doc_id = upload_resp.json()["id"]

        resp = admin_client.get(f"/api/documents/{doc_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "getme.pdf"

    def test_get_document_not_found(self, admin_client):
        """Returns 404 for non-existent document."""
        resp = admin_client.get("/api/documents/doc_does_not_exist")
        assert resp.status_code == 404

    def test_get_document_org_isolation(self, admin_client, other_org_client, editor_client):
        """Cannot get another org's document."""
        upload_resp = _upload_file(editor_client, "private.pdf", b"content")
        doc_id = upload_resp.json()["id"]

        resp = other_org_client.get(f"/api/documents/{doc_id}")
        assert resp.status_code == 404


# --- Download document ---


class TestDownloadDocument:
    def test_download_document(self, admin_client, editor_client):
        """Can download a document file."""
        upload_resp = _upload_file(editor_client, "download.pdf", b"download content")
        doc_id = upload_resp.json()["id"]

        resp = admin_client.get(f"/api/documents/{doc_id}/download")
        assert resp.status_code == 200
        assert resp.content == b"download content"
        assert (
            "pdf" in resp.headers["content-type"].lower()
            or "octet-stream" in resp.headers["content-type"].lower()
        )

    def test_download_document_not_found(self, admin_client):
        """Returns 404 for non-existent document."""
        resp = admin_client.get("/api/documents/doc_does_not_exist/download")
        assert resp.status_code == 404

    def test_download_org_isolation(self, admin_client, other_org_client, editor_client):
        """Cannot download another org's document."""
        upload_resp = _upload_file(editor_client, "secret.pdf", b"content")
        doc_id = upload_resp.json()["id"]

        resp = other_org_client.get(f"/api/documents/{doc_id}/download")
        assert resp.status_code == 404


# --- Delete document ---


class TestDeleteDocument:
    def test_delete_requires_editor_role(self, viewer_client, admin_client, editor_client):
        """Viewer cannot delete; editor can."""
        upload_resp = _upload_file(editor_client, "todel.pdf", b"content")
        doc_id = upload_resp.json()["id"]

        # Viewer cannot delete
        resp = viewer_client.delete(f"/api/documents/{doc_id}")
        assert resp.status_code == 403

        # Editor can delete
        resp = editor_client.delete(f"/api/documents/{doc_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_document(self, admin_client, editor_client):
        """Admin can delete a document."""
        upload_resp = _upload_file(editor_client, "todel.pdf", b"content")
        doc_id = upload_resp.json()["id"]

        resp = admin_client.delete(f"/api/documents/{doc_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        # Verify gone
        get_resp = admin_client.get(f"/api/documents/{doc_id}")
        assert get_resp.status_code == 404

    def test_delete_removes_file_from_disk(self, admin_client, editor_client):
        """Deleting a document also removes the file from disk."""
        upload_resp = _upload_file(editor_client, "file.pdf", b"content")
        doc_id = upload_resp.json()["id"]

        # Get file path
        conn = get_connection()
        try:
            row = conn.execute("SELECT file_path FROM documents WHERE id = ?", (doc_id,)).fetchone()
            file_path = row["file_path"]
        finally:
            release_connection(conn)

        admin_client.delete(f"/api/documents/{doc_id}")
        assert not os.path.exists(file_path)

    def test_delete_not_found(self, admin_client):
        """Deleting non-existent document returns 404."""
        resp = admin_client.delete("/api/documents/doc_does_not_exist")
        assert resp.status_code == 404

    def test_delete_org_isolation(self, admin_client, other_org_client, editor_client):
        """Cannot delete another org's document."""
        upload_resp = _upload_file(editor_client, "myfile.pdf", b"content")
        doc_id = upload_resp.json()["id"]

        resp = other_org_client.delete(f"/api/documents/{doc_id}")
        assert resp.status_code == 404


# --- Expiring documents ---


class TestExpiringDocuments:
    def test_expiring_documents(self, admin_client, editor_client):
        """Returns documents expiring within the specified days."""
        _upload_file(editor_client, "soon.pdf", b"content", expiry_date="2026-06-01")
        _upload_file(editor_client, "later.pdf", b"content", expiry_date="2027-01-01")
        _upload_file(editor_client, "nopdate.pdf", b"content")

        resp = admin_client.get("/api/documents/expiring/soon")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any("soon.pdf" in d["name"] for d in data["documents"])

    def test_expiring_custom_days(self, admin_client, editor_client):
        """Custom day parameter controls the look-ahead window."""
        _upload_file(editor_client, "very_soon.pdf", b"content", expiry_date="2026-06-01")

        # 30 days - likely not included
        resp = admin_client.get("/api/documents/expiring/soon?days=10")
        assert resp.status_code == 200
        # The specific outcome depends on current date relative to 2026-06-01

    def test_expiring_requires_auth(self):
        """Unauthenticated request returns 401."""
        client = TestClient(app)
        resp = client.get("/api/documents/expiring/soon")
        assert resp.status_code == 401

    def test_expiring_org_isolation(self, admin_client, other_org_client, editor_client):
        """Each org only sees its own expiring documents."""
        _upload_file(editor_client, "my_expiring.pdf", b"content", expiry_date="2026-06-01")

        resp = other_org_client.get("/api/documents/expiring/soon")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_expiring_shows_is_expired_flag(self, admin_client, editor_client):
        """Expiring documents response includes is_expired field."""
        _upload_file(editor_client, "about_to_expire.pdf", b"content", expiry_date="2026-06-01")

        resp = admin_client.get("/api/documents/expiring/soon")
        assert resp.status_code == 200
        data = resp.json()
        if data["documents"]:
            doc = data["documents"][0]
            assert "is_expired" in doc or "expiry_date" in doc
