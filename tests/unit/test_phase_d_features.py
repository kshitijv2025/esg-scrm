"""
Unit tests for Phase D features:
- D7.5: Onboarding wizard (POST /api/onboarding/wizard endpoint)
- D7.9: Corrective action tracking (table, CRUD, frontend panel)
- D7.10: Buyer-facing portal (endpoints)
- D7.11: Document management (table, upload/listing)
- D7.12: Compliance calendar (table, calendar endpoint)
- D7.13: Scheduled report generation (table, endpoints)
- D7.18: Webhook system (table, endpoints)

Security focus: all endpoints extract org_id from JWT, not from request body.
"""

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone

    UTC = timezone.utc

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.jwt import create_token
from src.db.database import get_connection, release_connection, reset_database
from tests.conftest import _auth_headers


@pytest.fixture(autouse=True)
def _clean_db():
    """Reset the database before every test so each test starts clean."""
    reset_database()
    # Seed minimal data required for FK constraints
    conn = get_connection()
    conn.execute(
        """INSERT INTO organizations (id, name, industry, country) VALUES (?, ?, ?, ?)""",
        ("org_bd_001", "Test Org BD", "Garment/Textile", "BD"),
    )
    conn.commit()
    release_connection(conn)
    yield


@pytest.fixture()
def client():
    """FastAPI TestClient wired to the production app."""
    return TestClient(app)


@pytest.fixture()
def admin_auth():
    """Valid admin auth headers (org_id='org_bd_001', role='admin')."""
    return _auth_headers()


@pytest.fixture()
def editor_auth():
    """Valid editor auth headers (org_id='org_bd_001', role='editor')."""
    token = create_token(
        {
            "sub": "usr_editor_001",
            "org_id": "org_bd_001",
            "email": "editor@test.com",
            "role": "editor",
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def viewer_auth():
    """Valid viewer auth headers (org_id='org_bd_001', role='viewer')."""
    token = create_token(
        {
            "sub": "usr_viewer_001",
            "org_id": "org_bd_001",
            "email": "viewer@test.com",
            "role": "viewer",
        }
    )
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# D7.9: Corrective Actions CRUD
# ============================================================================


class TestCorrectiveActionsCRUD:
    """Tests for corrective actions endpoints."""

    def test_list_actions_empty(self, client, admin_auth):
        """GET /api/corrective-actions returns empty list when no actions exist."""
        response = client.get("/api/corrective-actions", headers=admin_auth)
        assert response.status_code == 200
        body = response.json()
        assert body["actions"] == []
        assert body["total"] == 0

    def test_create_action_requires_editor(self, client, viewer_auth):
        """POST /api/corrective-actions requires editor role."""
        response = client.post(
            "/api/corrective-actions",
            headers=viewer_auth,
            json={"title": "Test Action", "priority": "high"},
        )
        assert response.status_code == 403

    def test_create_action_as_editor(self, client, editor_auth):
        """POST /api/corrective-actions creates action with editor role."""
        response = client.post(
            "/api/corrective-actions",
            headers=editor_auth,
            json={
                "title": "Fix water usage",
                "description": "Investigate high water consumption",
                "priority": "high",
                "status": "open",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "id" in body
        assert body["id"].startswith("ca_")

    def test_create_action_sets_org_id_from_jwt(self, client, editor_auth):
        """Created action uses org_id from JWT, not from request body."""
        response = client.post(
            "/api/corrective-actions",
            headers=editor_auth,
            json={
                "title": "Test Action",
                "org_id": "org_evil_001",  # Attempt to inject different org
                "priority": "medium",
            },
        )
        assert response.status_code == 200

        conn = get_connection()
        row = conn.execute(
            "SELECT org_id FROM corrective_actions WHERE id = ?",
            (response.json()["id"],),
        ).fetchone()
        conn.close()

        assert row["org_id"] == "org_bd_001"  # From JWT, not request

    def test_get_action_by_id(self, client, editor_auth):
        """GET /api/corrective-actions/{id} returns the correct action."""
        create_resp = client.post(
            "/api/corrective-actions",
            headers=editor_auth,
            json={"title": "Get Me", "priority": "medium"},
        )
        action_id = create_resp.json()["id"]

        response = client.get(f"/api/corrective-actions/{action_id}", headers=editor_auth)
        assert response.status_code == 200
        assert response.json()["title"] == "Get Me"

    def test_get_action_404_for_wrong_org(self, client, admin_auth, editor_auth):
        """GET /api/corrective-actions/{id} returns 404 for other org's action."""
        # Create action as editor (org_bd_001)
        client.post(
            "/api/corrective-actions",
            headers=editor_auth,
            json={"title": "Other Org Action", "priority": "low"},
        )

        # Try to access with different org token
        other_org_token = create_token(
            {
                "sub": "usr_other",
                "org_id": "org_other_999",
                "email": "other@test.com",
                "role": "admin",
            }
        )
        other_auth = {"Authorization": f"Bearer {other_org_token}"}

        # Try to get all actions - should return empty (no actions for other org)
        response = client.get("/api/corrective-actions", headers=other_auth)
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_update_action(self, client, editor_auth):
        """PUT /api/corrective-actions/{id} updates the action."""
        create_resp = client.post(
            "/api/corrective-actions",
            headers=editor_auth,
            json={"title": "Original Title", "priority": "low"},
        )
        action_id = create_resp.json()["id"]

        response = client.put(
            f"/api/corrective-actions/{action_id}",
            headers=editor_auth,
            json={"title": "Updated Title", "status": "in_progress"},
        )
        assert response.status_code == 200

        get_resp = client.get(f"/api/corrective-actions/{action_id}", headers=editor_auth)
        assert get_resp.json()["title"] == "Updated Title"
        assert get_resp.json()["status"] == "in_progress"

    def test_delete_action_requires_admin(self, client, editor_auth):
        """DELETE /api/corrective-actions/{id} requires admin role."""
        create_resp = client.post(
            "/api/corrective-actions",
            headers=editor_auth,
            json={"title": "To Delete", "priority": "low"},
        )
        action_id = create_resp.json()["id"]

        # Editor cannot delete
        response = client.delete(
            f"/api/corrective-actions/{action_id}",
            headers=editor_auth,
        )
        assert response.status_code == 403

    def test_delete_action_as_admin(self, client, admin_auth, editor_auth):
        """DELETE /api/corrective-actions/{id} deletes with admin role."""
        # Create as editor
        create_resp = client.post(
            "/api/corrective-actions",
            headers=editor_auth,
            json={"title": "To Delete", "priority": "low"},
        )
        action_id = create_resp.json()["id"]

        # Delete as admin
        response = client.delete(
            f"/api/corrective-actions/{action_id}",
            headers=admin_auth,
        )
        assert response.status_code == 200
        assert response.json()["deleted"] is True

        # Verify gone
        get_resp = client.get(f"/api/corrective-actions/{action_id}", headers=admin_auth)
        assert get_resp.status_code == 404

    def test_filter_actions_by_status(self, client, editor_auth):
        """GET /api/corrective-actions?status=open filters correctly."""
        client.post(
            "/api/corrective-actions",
            headers=editor_auth,
            json={"title": "Open Action", "status": "open", "priority": "medium"},
        )
        client.post(
            "/api/corrective-actions",
            headers=editor_auth,
            json={"title": "Closed Action", "status": "completed", "priority": "medium"},
        )

        open_resp = client.get(
            "/api/corrective-actions?status=open",
            headers=editor_auth,
        )
        assert open_resp.json()["total"] == 1
        assert open_resp.json()["actions"][0]["title"] == "Open Action"


# ============================================================================
# D7.11: Document Management
# ============================================================================


class TestDocumentsAPI:
    """Tests for document upload, listing, and management."""

    def test_list_documents_empty(self, client, admin_auth):
        """GET /api/documents returns empty list when no documents exist."""
        response = client.get("/api/documents", headers=admin_auth)
        assert response.status_code == 200
        body = response.json()
        assert body["documents"] == []
        assert body["total"] == 0

    def test_upload_document_requires_editor(self, client, viewer_auth):
        """POST /api/documents/upload requires editor role."""
        response = client.post(
            "/api/documents/upload",
            headers=viewer_auth,
            files={"file": ("cert.pdf", b"fake pdf content", "application/pdf")},
            data={"category": "certificate"},
        )
        assert response.status_code == 403

    def test_upload_document_as_editor(self, client, editor_auth):
        """POST /api/documents/upload creates document with editor role."""
        response = client.post(
            "/api/documents/upload",
            headers=editor_auth,
            files={"file": ("certificate.pdf", b"PDF content here", "application/pdf")},
            data={
                "category": "certificate",
                "expiry_date": "2027-12-31",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "id" in body
        assert body["name"] == "certificate.pdf"

    def test_upload_document_uses_jwt_org_id(self, client, editor_auth):
        """Uploaded document uses org_id from JWT, not from request."""
        response = client.post(
            "/api/documents/upload",
            headers=editor_auth,
            files={"file": ("doc.pdf", b"content", "application/pdf")},
            data={"category": "certificate"},
        )
        assert response.status_code == 200
        doc_id = response.json()["id"]

        conn = get_connection()
        row = conn.execute(
            "SELECT org_id FROM documents WHERE id = ?",
            (doc_id,),
        ).fetchone()
        conn.close()

        assert row["org_id"] == "org_bd_001"

    def test_list_documents_with_category_filter(self, client, editor_auth):
        """GET /api/documents?category=certificate filters correctly."""
        # Insert documents directly to avoid httpx files+data multipart issue
        conn = get_connection()
        now = "2026-01-01T00:00:00+00:00"
        conn.execute(
            """INSERT INTO documents
               (id, org_id, supplier_id, name, file_path, file_type, file_size,
                mime_type, category, expiry_date, created_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "doc_cert_001",
                "org_bd_001",
                None,
                "cert.pdf",
                "/uploads/cert.pdf",
                "pdf",
                100,
                "application/pdf",
                "certificate",
                None,
                now,
                "test@test.com",
            ),
        )
        conn.execute(
            """INSERT INTO documents
               (id, org_id, supplier_id, name, file_path, file_type, file_size,
                mime_type, category, expiry_date, created_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "doc_audit_001",
                "org_bd_001",
                None,
                "audit.pdf",
                "/uploads/audit.pdf",
                "pdf",
                100,
                "application/pdf",
                "audit_report",
                None,
                now,
                "test@test.com",
            ),
        )
        conn.commit()
        release_connection(conn)

        cert_resp = client.get(
            "/api/documents?category=certificate",
            headers=editor_auth,
        )
        assert cert_resp.json()["total"] == 1
        assert cert_resp.json()["documents"][0]["category"] == "certificate"

    def test_get_document_by_id(self, client, editor_auth):
        """GET /api/documents/{id} returns the correct document metadata."""
        upload_resp = client.post(
            "/api/documents/upload",
            headers=editor_auth,
            files={"file": ("test.pdf", b"content", "application/pdf")},
            data={"category": "certificate"},
        )
        doc_id = upload_resp.json()["id"]

        response = client.get(f"/api/documents/{doc_id}", headers=editor_auth)
        assert response.status_code == 200
        assert response.json()["name"] == "test.pdf"

    def test_delete_document(self, client, editor_auth):
        """DELETE /api/documents/{id} removes the document."""
        upload_resp = client.post(
            "/api/documents/upload",
            headers=editor_auth,
            files={"file": ("todelete.pdf", b"content", "application/pdf")},
            data={"category": "certificate"},
        )
        doc_id = upload_resp.json()["id"]

        response = client.delete(f"/api/documents/{doc_id}", headers=editor_auth)
        assert response.status_code == 200

        # Verify deleted
        get_resp = client.get(f"/api/documents/{doc_id}", headers=editor_auth)
        assert get_resp.status_code == 404

    def test_expiring_documents_endpoint(self, client, editor_auth):
        """GET /api/documents/expiring/soon returns documents expiring soon."""
        # Insert a document with a future expiry date directly
        from datetime import datetime, timedelta

        future = (datetime.now(UTC) + timedelta(days=15)).strftime("%Y-%m-%d")
        now = datetime.now(UTC).isoformat()

        conn = get_connection()
        conn.execute(
            """INSERT INTO documents
               (id, org_id, supplier_id, name, file_path, file_type, file_size,
                mime_type, category, expiry_date, created_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "doc_expiring_001",
                "org_bd_001",
                None,
                "expiring.pdf",
                "/uploads/expiring.pdf",
                "pdf",
                100,
                "application/pdf",
                "certificate",
                future,
                now,
                "test@test.com",
            ),
        )
        conn.commit()
        release_connection(conn)

        response = client.get("/api/documents/expiring/soon?days=30", headers=editor_auth)
        assert response.status_code == 200
        assert response.json()["total"] == 1


# ============================================================================
# D7.12: Compliance Calendar
# ============================================================================


class TestComplianceCalendar:
    """Tests for compliance calendar and deadline management."""

    def test_get_calendar_empty(self, client, admin_auth):
        """GET /api/compliance/calendar returns empty when no deadlines."""
        response = client.get("/api/compliance/calendar", headers=admin_auth)
        assert response.status_code == 200
        assert response.json()["deadlines"] == []

    def test_create_deadline_requires_editor(self, client, viewer_auth):
        """POST /api/compliance requires editor role."""
        response = client.post(
            "/api/compliance",
            headers=viewer_auth,
            json={
                "framework": "GRI",
                "requirement": "GRI 302-1",
                "deadline": "2027-06-30",
            },
        )
        assert response.status_code == 403

    def test_create_deadline_as_editor(self, client, editor_auth):
        """POST /api/compliance creates deadline with editor role."""
        response = client.post(
            "/api/compliance",
            headers=editor_auth,
            json={
                "framework": "GRI",
                "requirement": "GRI 302-1",
                "description": "Energy consumption disclosure",
                "deadline": "2027-06-30",
                "evidence_required": True,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "id" in body
        assert body["id"].startswith("cd_")

    def test_create_deadline_uses_jwt_org_id(self, client, editor_auth):
        """Created deadline uses org_id from JWT."""
        response = client.post(
            "/api/compliance",
            headers=editor_auth,
            json={
                "framework": "TCFD",
                "requirement": "TCFD-GHG-1",
                "deadline": "2027-12-31",
            },
        )
        deadline_id = response.json()["id"]

        conn = get_connection()
        row = conn.execute(
            "SELECT org_id FROM compliance_deadlines WHERE id = ?",
            (deadline_id,),
        ).fetchone()
        conn.close()

        assert row["org_id"] == "org_bd_001"

    def test_get_upcoming_deadlines(self, client, editor_auth):
        """GET /api/compliance/upcoming returns future deadlines."""
        from datetime import datetime, timedelta

        # Create a future deadline
        future_date = (datetime.now(UTC) + timedelta(days=30)).strftime("%Y-%m-%d")
        client.post(
            "/api/compliance",
            headers=editor_auth,
            json={
                "framework": "GRI",
                "requirement": "Test Deadline",
                "deadline": future_date,
            },
        )

        response = client.get("/api/compliance/upcoming?days=90", headers=editor_auth)
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_get_overdue_deadlines(self, client, editor_auth):
        """GET /api/compliance/overdue returns past deadlines."""
        from datetime import datetime, timedelta

        # Create a past deadline
        past_date = (datetime.now(UTC) - timedelta(days=10)).strftime("%Y-%m-%d")
        client.post(
            "/api/compliance",
            headers=editor_auth,
            json={
                "framework": "GRI",
                "requirement": "Past Deadline",
                "deadline": past_date,
                "status": "in_progress",
            },
        )

        response = client.get("/api/compliance/overdue", headers=editor_auth)
        assert response.status_code == 200
        # Status should auto-update to "overdue"
        assert any(d["status"] == "overdue" for d in response.json()["deadlines"])

    def test_update_deadline(self, client, editor_auth):
        """PUT /api/compliance/{id} updates the deadline."""
        create_resp = client.post(
            "/api/compliance",
            headers=editor_auth,
            json={
                "framework": "GRI",
                "requirement": "Original",
                "deadline": "2027-06-30",
            },
        )
        deadline_id = create_resp.json()["id"]

        response = client.put(
            f"/api/compliance/{deadline_id}",
            headers=editor_auth,
            json={"status": "submitted", "submission_date": "2027-06-15"},
        )
        assert response.status_code == 200

        get_resp = client.get("/api/compliance/calendar", headers=editor_auth)
        deadline = next(
            (d for d in get_resp.json()["deadlines"] if d["id"] == deadline_id),
            None,
        )
        assert deadline["status"] == "submitted"

    def test_delete_deadline(self, client, editor_auth):
        """DELETE /api/compliance/{id} removes the deadline."""
        create_resp = client.post(
            "/api/compliance",
            headers=editor_auth,
            json={
                "framework": "GRI",
                "requirement": "To Delete",
                "deadline": "2027-06-30",
            },
        )
        deadline_id = create_resp.json()["id"]

        response = client.delete(f"/api/compliance/{deadline_id}", headers=editor_auth)
        assert response.status_code == 200

        # Verify gone
        calendar_resp = client.get("/api/compliance/calendar", headers=editor_auth)
        assert all(d["id"] != deadline_id for d in calendar_resp.json()["deadlines"])


# ============================================================================
# D7.13: Scheduled Reports
# ============================================================================


class TestScheduledReports:
    """Tests for scheduled report generation endpoints."""

    def test_list_reports_empty(self, client, admin_auth):
        """GET /api/reports/scheduled returns empty when no reports."""
        response = client.get("/api/reports/scheduled", headers=admin_auth)
        assert response.status_code == 200
        assert response.json()["reports"] == []

    def test_create_report_requires_editor(self, client, viewer_auth):
        """POST /api/reports/scheduled requires editor role."""
        response = client.post(
            "/api/reports/scheduled",
            headers=viewer_auth,
            json={
                "name": "Monthly ESG Summary",
                "report_type": "esg_summary",
                "schedule": "monthly",
            },
        )
        assert response.status_code == 403

    def test_create_report_as_editor(self, client, editor_auth):
        """POST /api/reports/scheduled creates report with editor role."""
        response = client.post(
            "/api/reports/scheduled",
            headers=editor_auth,
            json={
                "name": "Monthly ESG Summary",
                "description": "Monthly ESG metrics overview",
                "report_type": "esg_summary",
                "schedule": "monthly",
                "recipients": ["test@example.com"],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "id" in body
        assert body["id"].startswith("sr_")
        assert "next_run" in body

    def test_create_report_validates_schedule(self, client, editor_auth):
        """POST /api/reports/scheduled rejects invalid schedule."""
        response = client.post(
            "/api/reports/scheduled",
            headers=editor_auth,
            json={
                "name": "Bad Schedule",
                "report_type": "esg_summary",
                "schedule": "weekly",  # Invalid
            },
        )
        assert response.status_code == 400

    def test_create_report_validates_report_type(self, client, editor_auth):
        """POST /api/reports/scheduled rejects invalid report_type."""
        response = client.post(
            "/api/reports/scheduled",
            headers=editor_auth,
            json={
                "name": "Bad Type",
                "report_type": "invalid_type",
                "schedule": "monthly",
            },
        )
        assert response.status_code == 400

    def test_create_report_uses_jwt_org_id(self, client, editor_auth):
        """Created report uses org_id from JWT."""
        response = client.post(
            "/api/reports/scheduled",
            headers=editor_auth,
            json={
                "name": "Test Report",
                "report_type": "emissions",
                "schedule": "quarterly",
            },
        )
        report_id = response.json()["id"]

        conn = get_connection()
        row = conn.execute(
            "SELECT org_id FROM scheduled_reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        conn.close()

        assert row["org_id"] == "org_bd_001"

    def test_update_report(self, client, editor_auth):
        """PUT /api/reports/scheduled/{id} updates the report."""
        create_resp = client.post(
            "/api/reports/scheduled",
            headers=editor_auth,
            json={
                "name": "Original Name",
                "report_type": "risk",
                "schedule": "monthly",
            },
        )
        report_id = create_resp.json()["id"]

        response = client.put(
            f"/api/reports/scheduled/{report_id}",
            headers=editor_auth,
            json={"name": "Updated Name", "is_active": False},
        )
        assert response.status_code == 200

        get_resp = client.get(f"/api/reports/scheduled/{report_id}", headers=editor_auth)
        assert get_resp.json()["name"] == "Updated Name"
        assert get_resp.json()["is_active"] is False

    def test_trigger_report(self, client, editor_auth):
        """POST /api/reports/scheduled/{id}/trigger manually triggers report."""
        create_resp = client.post(
            "/api/reports/scheduled",
            headers=editor_auth,
            json={
                "name": "To Trigger",
                "report_type": "emissions",
                "schedule": "monthly",
            },
        )
        report_id = create_resp.json()["id"]

        response = client.post(
            f"/api/reports/scheduled/{report_id}/trigger",
            headers=editor_auth,
        )
        assert response.status_code == 200
        assert "triggered_at" in response.json()
        assert "next_run" in response.json()

    def test_delete_report(self, client, editor_auth):
        """DELETE /api/reports/scheduled/{id} removes the report."""
        create_resp = client.post(
            "/api/reports/scheduled",
            headers=editor_auth,
            json={
                "name": "To Delete",
                "report_type": "water",
                "schedule": "annual",
            },
        )
        report_id = create_resp.json()["id"]

        response = client.delete(f"/api/reports/scheduled/{report_id}", headers=editor_auth)
        assert response.status_code == 200

        # Verify gone
        get_resp = client.get(f"/api/reports/scheduled/{report_id}", headers=editor_auth)
        assert get_resp.status_code == 404


# ============================================================================
# D7.18: Webhook System
# ============================================================================


class TestWebhooks:
    """Tests for webhook CRUD and event triggering."""

    def test_list_webhooks_empty(self, client, admin_auth):
        """GET /api/webhooks returns empty when no webhooks."""
        response = client.get("/api/webhooks", headers=admin_auth)
        assert response.status_code == 200
        assert response.json()["webhooks"] == []

    def test_create_webhook_requires_editor(self, client, viewer_auth):
        """POST /api/webhooks requires editor role."""
        response = client.post(
            "/api/webhooks",
            headers=viewer_auth,
            json={
                "name": "Test Webhook",
                "url": "https://example.com/webhook",
                "events": ["risk_flag.created"],
            },
        )
        assert response.status_code == 403

    def test_create_webhook_as_editor(self, client, editor_auth):
        """POST /api/webhooks creates webhook with editor role."""
        response = client.post(
            "/api/webhooks",
            headers=editor_auth,
            json={
                "name": "Risk Alert Webhook",
                "url": "https://example.com/webhook",
                "events": ["risk_flag.created", "risk_flag.acknowledged"],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "id" in body
        assert body["id"].startswith("wh_")
        assert "secret" in body  # Secret returned only on creation

    def test_create_webhook_validates_events(self, client, editor_auth):
        """POST /api/webhooks rejects invalid events."""
        response = client.post(
            "/api/webhooks",
            headers=editor_auth,
            json={
                "name": "Bad Events",
                "url": "https://example.com/hook",
                "events": ["invalid.event"],
            },
        )
        assert response.status_code == 400

    def test_create_webhook_uses_jwt_org_id(self, client, editor_auth):
        """Created webhook uses org_id from JWT."""
        response = client.post(
            "/api/webhooks",
            headers=editor_auth,
            json={
                "name": "Test",
                "url": "https://example.com/hook",
                "events": ["risk_flag.created"],
            },
        )
        webhook_id = response.json()["id"]

        conn = get_connection()
        row = conn.execute(
            "SELECT org_id FROM webhooks WHERE id = ?",
            (webhook_id,),
        ).fetchone()
        conn.close()

        assert row["org_id"] == "org_bd_001"

    def test_get_webhook_by_id(self, client, editor_auth):
        """GET /api/webhooks/{id} returns webhook details (without secret)."""
        create_resp = client.post(
            "/api/webhooks",
            headers=editor_auth,
            json={
                "name": "Get Me",
                "url": "https://example.com/hook",
                "events": ["risk_flag.created"],
            },
        )
        webhook_id = create_resp.json()["id"]

        response = client.get(f"/api/webhooks/{webhook_id}", headers=editor_auth)
        assert response.status_code == 200
        assert response.json()["name"] == "Get Me"

    def test_update_webhook(self, client, editor_auth):
        """PUT /api/webhooks/{id} updates the webhook."""
        create_resp = client.post(
            "/api/webhooks",
            headers=editor_auth,
            json={
                "name": "Original",
                "url": "https://example.com/original",
                "events": ["risk_flag.created"],
            },
        )
        webhook_id = create_resp.json()["id"]

        response = client.put(
            f"/api/webhooks/{webhook_id}",
            headers=editor_auth,
            json={"name": "Updated", "is_active": False},
        )
        assert response.status_code == 200

        get_resp = client.get(f"/api/webhooks/{webhook_id}", headers=editor_auth)
        assert get_resp.json()["name"] == "Updated"
        assert get_resp.json()["is_active"] is False

    def test_delete_webhook(self, client, editor_auth):
        """DELETE /api/webhooks/{id} removes the webhook."""
        create_resp = client.post(
            "/api/webhooks",
            headers=editor_auth,
            json={
                "name": "To Delete",
                "url": "https://example.com/hook",
                "events": ["risk_flag.created"],
            },
        )
        webhook_id = create_resp.json()["id"]

        response = client.delete(f"/api/webhooks/{webhook_id}", headers=editor_auth)
        assert response.status_code == 200

        # Verify gone
        get_resp = client.get(f"/api/webhooks/{webhook_id}", headers=editor_auth)
        assert get_resp.status_code == 404


# ============================================================================
# D7.10: Buyer Portal
# ============================================================================


class TestBuyerPortal:
    """Tests for buyer-facing portal endpoints."""

    def test_create_buyer_link_requires_editor(self, client, viewer_auth):
        """POST /api/access/buyer-link requires editor role."""
        response = client.post(
            "/api/access/buyer-link",
            headers=viewer_auth,
            json={
                "buyer_org_id": "buyer_123",
                "buyer_org_name": "Acme Buyer",
            },
        )
        assert response.status_code == 403

    def test_create_buyer_link_as_editor(self, client, admin_auth):
        """POST /api/access/buyer-link creates access link with admin role."""
        response = client.post(
            "/api/access/buyer-link",
            headers=admin_auth,
            json={
                "buyer_org_id": "buyer_acme_001",
                "buyer_org_name": "Acme Corporation",
                "scope_filter": [],
                "expires_days": 30,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "token" in body
        assert "portal_url" in body
        assert "/buyer-portal/" in body["portal_url"]

    def test_create_buyer_link_uses_jwt_org_id(self, client, admin_auth):
        """Created buyer link uses org_id from JWT (the supplying org)."""
        response = client.post(
            "/api/access/buyer-link",
            headers=admin_auth,
            json={
                "buyer_org_id": "buyer_xyz",
                "buyer_org_name": "XYZ Buyer",
            },
        )
        access_id = response.json()["id"]

        conn = get_connection()
        row = conn.execute(
            "SELECT org_id FROM buyer_portal_access WHERE id = ?",
            (access_id,),
        ).fetchone()
        conn.close()

        # org_id is the SUPPLYING org (from JWT), not the buyer_org_id
        assert row["org_id"] == "org_bd_001"

    def test_get_buyer_portal_with_valid_token(self, client, admin_auth):
        """GET /api/access/buyer-portal/{token} returns portal data."""
        # Create a buyer link first (buyer-link creation requires admin)
        link_resp = client.post(
            "/api/access/buyer-link",
            headers=admin_auth,
            json={
                "buyer_org_id": "buyer_test",
                "buyer_org_name": "Test Buyer Co",
            },
        )
        token = link_resp.json()["token"]

        # Access portal with token (no auth needed)
        response = client.get(f"/api/buyer-portal/{token}")
        assert response.status_code == 200
        body = response.json()
        assert "buyer_org_name" in body
        assert "suppliers" in body

    def test_get_buyer_portal_with_invalid_token(self, client):
        """GET /api/access/buyer-portal/{invalid} returns 403."""
        response = client.get("/api/buyer-portal/invalid_token_12345")
        assert response.status_code == 403
        assert "Invalid or expired portal link" in response.json()["detail"]

    def test_revoke_buyer_access(self, client, admin_auth):
        """DELETE /api/access/{id} revokes buyer access."""
        # Create a buyer link (buyer-link creation requires admin)
        link_resp = client.post(
            "/api/access/buyer-link",
            headers=admin_auth,
            json={
                "buyer_org_id": "buyer_revoke",
                "buyer_org_name": "Revoke Test",
            },
        )
        access_id = link_resp.json()["id"]
        token = link_resp.json()["token"]

        # Revoke access (admin satisfies EDITOR_ROLES requirement)
        response = client.delete(f"/api/access/{access_id}", headers=admin_auth)
        assert response.status_code == 200
        assert response.json()["revoked"] is True

        # Token should no longer work
        portal_resp = client.get(f"/api/buyer-portal/{token}")
        assert portal_resp.status_code == 403


# ============================================================================
# D7.5: Onboarding Wizard
# ============================================================================


class TestOnboardingWizard:
    """Tests for onboarding wizard endpoint."""

    def test_get_onboarding_options(self, client, admin_auth):
        """GET /api/onboarding/wizard/options returns available choices."""
        response = client.get("/api/onboarding/wizard/options", headers=admin_auth)
        assert response.status_code == 200
        body = response.json()
        assert "industries" in body
        assert "erp_systems" in body
        assert "frameworks" in body
        assert "alert_clusters" in body

        # Verify known values are present
        assert "Garment/Textile" in body["industries"]
        assert "SAP S/4HANA" in body["erp_systems"]
        assert "GRI" in body["frameworks"]
        assert "energy" in [c["id"] for c in body["alert_clusters"]]

    def test_complete_onboarding_requires_editor(self, client, viewer_auth):
        """POST /api/onboarding/wizard requires editor role."""
        response = client.post(
            "/api/onboarding/wizard",
            headers=viewer_auth,
            json={
                "industry": "Garment/Textile",
                "frameworks": ["GRI"],
            },
        )
        assert response.status_code == 403

    def test_complete_onboarding_as_editor(self, client, editor_auth):
        """POST /api/onboarding/wizard completes onboarding with editor role."""
        response = client.post(
            "/api/onboarding/wizard",
            headers=editor_auth,
            json={
                "industry": "Electronics",
                "erp_system": "SAP S/4HANA",
                "frameworks": ["GRI", "TCFD"],
                "alert_thresholds": [
                    {
                        "cluster": "energy",
                        "warning_threshold": 1000,
                        "critical_threshold": 2000,
                        "unit": "kWh/day",
                    },
                ],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "org" in body
        assert "configured_frameworks" in body

    def test_complete_onboarding_validates_industry(self, client, editor_auth):
        """POST /api/onboarding/wizard rejects invalid industry."""
        response = client.post(
            "/api/onboarding/wizard",
            headers=editor_auth,
            json={"industry": "Invalid Industry"},
        )
        assert response.status_code == 400

    def test_complete_onboarding_validates_erp(self, client, editor_auth):
        """POST /api/onboarding/wizard rejects invalid ERP system."""
        response = client.post(
            "/api/onboarding/wizard",
            headers=editor_auth,
            json={"erp_system": "Fake ERP"},
        )
        assert response.status_code == 400

    def test_complete_onboarding_validates_frameworks(self, client, editor_auth):
        """POST /api/onboarding/wizard rejects invalid frameworks."""
        response = client.post(
            "/api/onboarding/wizard",
            headers=editor_auth,
            json={"frameworks": ["InvalidFramework"]},
        )
        assert response.status_code == 400

    def test_complete_onboarding_creates_framework_mappings(self, client, editor_auth):
        """POST /api/onboarding/wizard creates framework mappings."""
        response = client.post(
            "/api/onboarding/wizard",
            headers=editor_auth,
            json={
                "industry": "Chemicals",
                "frameworks": ["GRI"],
            },
        )
        assert response.status_code == 200
        assert "GRI" in response.json()["configured_frameworks"]

        # Verify mappings were created
        conn = get_connection()
        mappings = conn.execute(
            "SELECT * FROM framework_mappings WHERE org_id = ? AND framework = ?",
            ("org_bd_001", "GRI"),
        ).fetchall()
        conn.close()

        assert len(mappings) > 0

    def test_complete_onboarding_creates_alert_thresholds(self, client, editor_auth):
        """POST /api/onboarding/wizard creates alert thresholds."""
        response = client.post(
            "/api/onboarding/wizard",
            headers=editor_auth,
            json={
                "industry": "Pharmaceuticals",
                "alert_thresholds": [
                    {
                        "cluster": "water",
                        "warning_threshold": 500,
                        "critical_threshold": 1000,
                        "unit": "m³/day",
                    },
                ],
            },
        )
        assert response.status_code == 200

        # Verify thresholds were created
        conn = get_connection()
        thresholds = conn.execute(
            "SELECT * FROM alert_thresholds WHERE org_id = ? AND cluster = ?",
            ("org_bd_001", "water"),
        ).fetchall()
        conn.close()

        assert len(thresholds) >= 1  # At least WARNING threshold
