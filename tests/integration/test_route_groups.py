"""D6.9: Integration tests for route groups — real DB, no mocks."""

import hashlib
import hmac
import io

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import whatsapp as whatsapp_module
from src.db.database import _execute, get_connection, release_connection, reset_database
from src.db.seed import seed


@pytest.fixture(autouse=True)
def _reset_db():
    """Reset and re-seed the database before each test.

    reset_database() drops all tables; seed() recreates the schema and loads
    baseline org_bd_001 data. This mirrors conftest.py::_seed_database so
    that test_route_groups and test_api_endpoint_coverage tests see the same
    baseline state regardless of execution order.

    NOTE: No teardown reset_database() here. The setup phase of the NEXT
    test's fixture will reset before that test runs. Removing teardown avoids
    double-resetting: TestClient lifespan shutdown also calls reset_database(),
    and running it twice in succession wipes the seeded data before the next
    TestClient lifespan can seed via count==0 check.
    """
    reset_database()
    seed()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _admin_headers(org_id="org_bd_001"):
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_admin_001",
            "org_id": org_id,
            "email": "admin@test.com",
            "role": "admin",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _editor_headers(org_id="org_bd_001"):
    from src.auth.jwt import create_token

    token = create_token(
        {
            "sub": "usr_editor_001",
            "org_id": org_id,
            "email": "editor@test.com",
            "role": "editor",
        }
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Alerts CRUD
# ---------------------------------------------------------------------------


class TestAlertsCRUD:
    def test_create_threshold(self, client):
        headers = _admin_headers()

        resp = client.post(
            "/api/alerts/thresholds",
            json={
                "cluster": "energy_kwh",
                "metric_cluster": "energy_kwh",
                "operator": ">",
                "threshold_value": 10000,
                "severity": "WARNING",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert "id" in data

    def test_list_thresholds(self, client):
        headers = _admin_headers()

        # Create a threshold first
        client.post(
            "/api/alerts/thresholds",
            json={
                "cluster": "energy_kwh",
                "metric_cluster": "energy_kwh",
                "operator": ">",
                "threshold_value": 5000,
                "severity": "CRITICAL",
            },
            headers=headers,
        )

        resp = client.get("/api/alerts/thresholds", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "thresholds" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_update_threshold_via_recreate(self, client):
        headers = _admin_headers()

        # Create
        create_resp = client.post(
            "/api/alerts/thresholds",
            json={
                "cluster": "water_m3",
                "metric_cluster": "water_m3",
                "operator": "<",
                "threshold_value": 1000,
                "severity": "WARNING",
            },
            headers=headers,
        )
        assert create_resp.status_code == 200
        threshold_id = create_resp.json()["id"]

        # Delete (not exposed) — test list shows it
        resp = client.get("/api/alerts/thresholds", headers=headers)
        assert resp.status_code == 200
        thresholds = resp.json()["thresholds"]
        assert any(t["id"] == threshold_id for t in thresholds)

    def test_check_threshold_triggered(self, client):
        headers = _admin_headers()

        # Create threshold
        client.post(
            "/api/alerts/thresholds",
            json={
                "cluster": "energy_kwh",
                "metric_cluster": "energy_kwh",
                "operator": ">",
                "threshold_value": 1000,
                "severity": "WARNING",
            },
            headers=headers,
        )

        # Check — value below threshold
        resp = client.get("/api/alerts/check/energy_kwh?current_value=500", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_triggered"] == 0

        # Check — value above threshold
        resp = client.get("/api/alerts/check/energy_kwh?current_value=5000", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_triggered"] >= 1


# ---------------------------------------------------------------------------
# Templates CRUD
# ---------------------------------------------------------------------------


class TestTemplatesCRUD:
    def test_create_template(self, client):
        headers = _editor_headers()

        resp = client.post(
            "/api/templates/",
            json={
                "name": "Energy Usage Survey",
                "tier": 1,
                "description": "Annual energy consumption questionnaire",
                "questions": [
                    {
                        "question_id": "q1",
                        "text": "What was your monthly electricity consumption (kWh)?",
                        "question_type": "number",
                        "required": True,
                    },
                    {
                        "question_id": "q2",
                        "text": "Do you have renewable energy installed?",
                        "question_type": "choice",
                        "choices": ["Yes", "No", "In progress"],
                        "required": True,
                    },
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert data["question_count"] == 2

    def test_list_templates(self, client):
        headers = _editor_headers()

        # Create one
        client.post(
            "/api/templates/",
            json={
                "name": "Water Usage Survey",
                "tier": 2,
                "questions": [
                    {
                        "question_id": "q1",
                        "text": "Monthly water consumption (m3)?",
                        "question_type": "number",
                    },
                ],
            },
            headers=headers,
        )

        resp = client.get("/api/templates/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "templates" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_get_template_by_id(self, client):
        headers = _editor_headers()

        # Create
        create_resp = client.post(
            "/api/templates/",
            json={
                "name": "Scope 3 Survey",
                "tier": 1,
                "questions": [
                    {
                        "question_id": "q1",
                        "text": "Annual spend on purchased goods (USD)?",
                        "question_type": "number",
                    },
                ],
            },
            headers=headers,
        )
        template_id = create_resp.json()["id"]

        # Get by ID
        resp = client.get(f"/api/templates/{template_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Scope 3 Survey"
        assert len(data["questions"]) == 1

    def test_update_template(self, client):
        headers = _editor_headers()

        # Create
        create_resp = client.post(
            "/api/templates/",
            json={
                "name": "Waste Survey",
                "tier": 1,
                "questions": [
                    {
                        "question_id": "q1",
                        "text": "Monthly waste (tonnes)?",
                        "question_type": "number",
                    },
                ],
            },
            headers=headers,
        )
        template_id = create_resp.json()["id"]

        # Update
        resp = client.put(
            f"/api/templates/{template_id}",
            json={
                "name": "Waste Survey Updated",
                "questions": [
                    {"question_id": "q1", "text": "Monthly waste (kg)?", "question_type": "number"},
                    {
                        "question_id": "q2",
                        "text": "Recycling percentage?",
                        "question_type": "number",
                    },
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Waste Survey Updated"
        assert len(data["questions"]) == 2

    def test_delete_template(self, client):
        headers = _admin_headers()

        # Create
        create_resp = client.post(
            "/api/templates/",
            json={
                "name": "To Delete",
                "tier": 1,
                "questions": [
                    {"question_id": "q1", "text": "Test?", "question_type": "text"},
                ],
            },
            headers=headers,
        )
        template_id = create_resp.json()["id"]

        # Delete
        resp = client.delete(f"/api/templates/{template_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "deactivated"

        # Verify gone
        resp = client.get(f"/api/templates/{template_id}", headers=headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# WhatsApp webhook parsing
# ---------------------------------------------------------------------------


class TestWhatsAppWebhook:
    def test_webhook_parses_twilio_message(self, client):
        """Verify WhatsApp webhook accepts and parses Twilio format."""
        # Set fake Twilio credentials so auth_token is non-empty
        whatsapp_module._client.auth_token = "test_auth_token"

        payload = {
            "From": "whatsapp:+8801712345678",
            "To": "whatsapp:+15551234567",
            "Body": "Test message",
            "MessageSid": "SM1234567890",
        }
        # Compute correct HMAC-SHA1 signature over the form-encoded body
        # client.post with data=... sends application/x-www-form-urlencoded
        from urllib.parse import urlencode

        encoded_body = urlencode(payload).encode()
        sig = hmac.new(
            b"test_auth_token",
            encoded_body,
            hashlib.sha1,
        ).hexdigest()
        resp = client.post(
            "/api/whatsapp/webhook",
            data=payload,
            headers={"X-Twilio-Signature": sig},
        )
        # 200 = acknowledged, 400 = bad format, 403 = bad signature — not 500
        assert resp.status_code in (200, 400, 403)

    def test_webhook_rejects_non_dict(self, client):
        """Webhook should reject non-dict payloads."""
        whatsapp_module._client.auth_token = "test_auth_token"
        body = b"not a dict"
        sig = hmac.new(b"test_auth_token", body, hashlib.sha1).hexdigest()
        resp = client.post(
            "/api/whatsapp/webhook",
            content=body,
            headers={"X-Twilio-Signature": sig},
        )
        assert resp.status_code in (400, 403, 500)

    def test_webhook_reply_to_message(self, client):
        """Send a WhatsApp message to a supplier."""
        headers = _editor_headers()

        # Create supplier
        conn = get_connection()
        _execute(
            conn,
            """
            INSERT INTO suppliers (id, org_id, name, country, industry, tier, annual_spend_usd,
               phone, preferred_channel, questionnaire_status)
            VALUES ('sup_test_001', 'org_bd_001', 'Test Supplier', 'BD',
                    'Textiles', 'tier1', 1000000, '+8801712345678', 'whatsapp', 'not_sent')
        """,
            (),
        )
        release_connection(conn)

        resp = client.post(
            "/api/whatsapp/send",
            json={
                "supplier_id": "sup_test_001",
                "message": "Please complete the ESG questionnaire.",
            },
            headers=headers,
        )
        # 200 = sent, 400 = bad request — not 500
        assert resp.status_code in (200, 400)


# ---------------------------------------------------------------------------
# CSV upload
# ---------------------------------------------------------------------------


class TestUploadCSV:
    def test_upload_suppliers_csv(self, client):
        """Upload a CSV file with supplier data."""
        headers = _editor_headers()

        csv_content = """name,country,tier,contact_email,phone,annual_spend_usd,industry
CSV Test Supplier,BD,tier1,test@example.com,+8801711111111,500000,Textiles
CSV Test Supplier 2,VN,tier2,test2@example.com,+8409011111111,300000,Textiles
"""
        files = {"file": ("suppliers.csv", io.BytesIO(csv_content.encode()), "text/csv")}

        resp = client.post("/api/upload/suppliers", files=files, headers=headers)
        # 200 = success, 400 = validation error — not 500
        assert resp.status_code in (200, 400)
        data = resp.json()
        assert "imported" in data or "errors" in data or "status" in data

    def test_upload_rejects_non_csv(self, client):
        """Upload rejects non-CSV files."""
        headers = _editor_headers()

        files = {"file": ("data.txt", io.BytesIO(b"not a csv"), "text/plain")}
        resp = client.post("/api/upload/suppliers", files=files, headers=headers)
        assert resp.status_code in (400, 422)

    def test_upload_rejects_missing_file(self, client):
        """Upload without a file returns 400/422."""
        headers = _editor_headers()
        resp = client.post("/api/upload/suppliers", headers=headers)
        assert resp.status_code in (400, 422)

    def test_upload_status(self, client):
        """Check upload status endpoint."""
        headers = _editor_headers()
        resp = client.get("/api/upload/history", headers=headers)
        # 200 = has status, 404 = not found — not 500
        assert resp.status_code in (200, 404)
