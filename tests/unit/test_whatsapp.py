"""Unit tests for WhatsApp connector and API routes.

Covers:
  1. WhatsAppClient demo mode when Twilio credentials are absent
  2. send_message returns status dict in demo mode
  3. send_questionnaire formats questionnaire message
  4. send_risk_alert formats alert message
  5. verify_webhook validates HMAC-SHA256 signature
  6. POST /api/whatsapp/send requires auth + editor role
  7. POST /api/whatsapp/send rejects missing supplier_id
  8. POST /api/whatsapp/send rejects missing message
  9. POST /api/whatsapp/send returns 404 for nonexistent supplier
  10. POST /api/whatsapp/send returns 403 for supplier in different org
  11. POST /api/whatsapp/questionnaire requires auth + editor role
  12. POST /api/whatsapp/alert requires auth + editor role
  13. POST /api/whatsapp/webhook accepts incoming messages (no auth required)
  14. All send/questionnaire/alert endpoints reject unauthenticated requests
"""
import hashlib
import hmac
import json
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.connectors.whatsapp import WhatsAppClient, verify_webhook
from src.db.database import get_connection, _execute, reset_database
from src.auth.jwt import create_token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fresh_db():
    """Reset and re-seed the database before every test."""
    reset_database()
    from src.db.seed import seed
    seed()
    from src.db.seed_emission_factors import seed_emission_factors
    seed_emission_factors()
    from src.db.seed_alert_thresholds import seed_alert_thresholds
    seed_alert_thresholds()
    from src.db.seed_templates import seed_templates
    seed_templates()


@pytest.fixture
def client():
    """Authenticated TestClient with admin role belonging to org_bd_001."""
    token = create_token({
        "sub": "usr_test_001",
        "org_id": "org_bd_001",
        "email": "test@test.com",
        "role": "admin",
    })
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture
def viewer_client():
    """Authenticated TestClient with viewer role (not an editor)."""
    token = create_token({
        "sub": "usr_viewer_001",
        "org_id": "org_bd_001",
        "email": "viewer@test.com",
        "role": "viewer",
    })
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture
def other_org_client():
    """Authenticated TestClient whose org does not own the seeded suppliers."""
    token = create_token({
        "sub": "usr_other_001",
        "org_id": "org_other_999",
        "email": "other@test.com",
        "role": "admin",
    })
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture
def no_phone_supplier():
    """Insert a supplier with no phone number for edge-case testing."""
    conn = get_connection()
    _execute(
        conn,
        """INSERT INTO suppliers
           (id, org_id, name, country, industry, tier, annual_spend_usd, phone)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("sup_nophone", "org_bd_001", "NoPhone Ltd.", "BD", "Testing",
         "tier3", 100000, ""),
    )


# ---------------------------------------------------------------------------
# 1. WhatsAppClient demo mode
# ---------------------------------------------------------------------------


class TestWhatsAppClientDemoMode:
    """When TWILIO_ACCOUNT_SID is not set the client enters demo mode."""

    def test_demo_mode_when_env_missing(self, monkeypatch):
        """Client self-identifies as demo when Twilio env vars are absent."""
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)
        # Re-instantiate to pick up the cleared env vars
        client = WhatsAppClient()
        assert client._demo is True

    def test_not_demo_when_all_creds_set(self, monkeypatch):
        """Client is NOT in demo mode when all three credentials are present."""
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest123")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "authtoken123")
        monkeypatch.setenv("TWILIO_WHATSAPP_NUMBER", "+1234567890")
        client = WhatsAppClient()
        assert client._demo is False


# ---------------------------------------------------------------------------
# 2. send_message returns status in demo mode
# ---------------------------------------------------------------------------


class TestSendMessageDemo:
    """In demo mode send_message returns a dict with status=demo."""

    def test_send_message_demo_status(self, monkeypatch):
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)
        client = WhatsAppClient()
        result = client.send_message("+880-171234567", "Hello supplier")
        assert result["status"] == "demo"
        assert "to" in result
        assert "body" in result
        assert result["body"] == "Hello supplier"

    def test_send_message_formats_phone(self, monkeypatch):
        """Phone numbers are prefixed with whatsapp:+."""
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)
        client = WhatsAppClient()
        result = client.send_message("880-171234567", "Test")
        assert result["to"] == "whatsapp:+880-171234567"

    def test_send_message_already_prefixed(self, monkeypatch):
        """Already-prefixed numbers are not double-prefixed."""
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)
        client = WhatsAppClient()
        result = client.send_message("whatsapp:+880-171234567", "Test")
        assert result["to"] == "whatsapp:+880-171234567"


# ---------------------------------------------------------------------------
# 3. send_questionnaire formats questionnaire message
# ---------------------------------------------------------------------------


class TestSendQuestionnaire:
    """send_questionnaire fetches supplier + template, formats, and sends."""

    def test_questionnaire_demo_success(self, monkeypatch):
        """Full questionnaire flow in demo mode with a seeded supplier."""
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)
        # Reset module-level client singleton so it picks up cleared env
        import src.api.routes.whatsapp as _wr
        _wr._client = WhatsAppClient()

        client = WhatsAppClient()
        result = client.send_questionnaire("sup_001")
        assert result["status"] == "demo"
        assert result["supplier_name"] == "Gujarat Cotton Traders"
        assert result["question_count"] > 0
        assert "template_name" in result

    def test_questionnaire_supplier_not_found(self, monkeypatch):
        """Returns error dict when supplier_id does not exist."""
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)
        client = WhatsAppClient()
        result = client.send_questionnaire("sup_nonexistent")
        assert result["status"] == "error"
        assert "not found" in result["detail"]

    def test_questionnaire_supplier_no_phone(self, monkeypatch, no_phone_supplier):
        """Returns error dict when supplier has no phone number."""
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)
        client = WhatsAppClient()
        result = client.send_questionnaire("sup_nophone")
        assert result["status"] == "error"
        assert "no phone number" in result["detail"]


# ---------------------------------------------------------------------------
# 4. send_risk_alert formats alert message
# ---------------------------------------------------------------------------


class TestSendRiskAlert:
    """send_risk_alert formats an alert and sends it to the supplier."""

    def test_risk_alert_demo_success(self, monkeypatch):
        """Alert is formatted and sent in demo mode."""
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)
        import src.api.routes.whatsapp as _wr
        _wr._client = WhatsAppClient()

        client = WhatsAppClient()
        result = client.send_risk_alert("sup_001", "Emissions exceeded threshold")
        assert result["status"] == "demo"
        assert result["supplier_name"] == "Gujarat Cotton Traders"
        assert "to" in result

    def test_risk_alert_supplier_not_found(self, monkeypatch):
        """Returns error dict when supplier does not exist."""
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)
        client = WhatsAppClient()
        result = client.send_risk_alert("sup_nonexistent", "Alert text")
        assert result["status"] == "error"
        assert "not found" in result["detail"]

    def test_risk_alert_no_phone(self, monkeypatch, no_phone_supplier):
        """Returns error when supplier has no phone number."""
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)
        client = WhatsAppClient()
        result = client.send_risk_alert("sup_nophone", "Alert text")
        assert result["status"] == "error"
        assert "no phone number" in result["detail"]


# ---------------------------------------------------------------------------
# 5. verify_webhook validates HMAC-SHA256 signature
# ---------------------------------------------------------------------------


class TestVerifyWebhook:
    """verify_webhook uses HMAC-SHA256 to validate Twilio signatures."""

    def test_valid_signature(self):
        """Correct signature returns True."""
        token = "test_auth_token_value"
        body = b"Body=Hello&From=whatsapp:%2B1234567890"
        expected = hmac.new(
            token.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        assert verify_webhook(token, body, expected) is True

    def test_invalid_signature(self):
        """Incorrect signature returns False."""
        token = "test_auth_token_value"
        body = b"Body=Hello&From=whatsapp:%2B1234567890"
        assert verify_webhook(token, body, "badsignature") is False

    def test_empty_token_returns_false(self):
        """Missing token returns False, not an error."""
        assert verify_webhook("", b"body", "sig") is False

    def test_empty_signature_returns_false(self):
        """Missing signature returns False."""
        assert verify_webhook("token", b"body", "") is False

    def test_wrong_body_returns_false(self):
        """Correct token+signature but different body returns False."""
        token = "test_auth_token_value"
        body = b"correct body"
        sig = hmac.new(
            token.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        assert verify_webhook(token, b"tampered body", sig) is False


# ---------------------------------------------------------------------------
# Helper: reset the module-level WhatsAppClient in the routes module
# ---------------------------------------------------------------------------


def _reset_route_client(monkeypatch):
    """Ensure the route module's singleton WhatsAppClient is in demo mode."""
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)
    import src.api.routes.whatsapp as _wr
    _wr._client = WhatsAppClient()


# ---------------------------------------------------------------------------
# 6. POST /api/whatsapp/send requires auth + editor role
# ---------------------------------------------------------------------------


class TestSendRouteAuth:
    """The /send endpoint requires authentication and an editor-level role."""

    def test_send_requires_auth(self, monkeypatch):
        """Unauthenticated request returns 401."""
        _reset_route_client(monkeypatch)
        c = TestClient(app)
        resp = c.post("/api/whatsapp/send", json={
            "supplier_id": "sup_001",
            "message": "Hello",
        })
        assert resp.status_code == 401

    def test_send_requires_editor_role(self, viewer_client, monkeypatch):
        """A viewer (not admin/editor) gets 403."""
        _reset_route_client(monkeypatch)
        resp = viewer_client.post("/api/whatsapp/send", json={
            "supplier_id": "sup_001",
            "message": "Hello",
        })
        assert resp.status_code == 403

    def test_send_success_admin(self, client, monkeypatch):
        """Admin role can send successfully."""
        _reset_route_client(monkeypatch)
        resp = client.post("/api/whatsapp/send", json={
            "supplier_id": "sup_001",
            "message": "Hello supplier",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "demo"
        assert data["supplier_id"] == "sup_001"
        assert data["supplier_name"] == "Gujarat Cotton Traders"


# ---------------------------------------------------------------------------
# 7. POST /api/whatsapp/send rejects missing supplier_id
# ---------------------------------------------------------------------------


class TestSendRouteValidation:
    """Input validation on the /send endpoint."""

    def test_reject_missing_supplier_id(self, client, monkeypatch):
        _reset_route_client(monkeypatch)
        resp = client.post("/api/whatsapp/send", json={
            "message": "Hello",
        })
        assert resp.status_code == 400
        assert "supplier_id" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 8. POST /api/whatsapp/send rejects missing message
# ---------------------------------------------------------------------------


    def test_reject_missing_message(self, client, monkeypatch):
        _reset_route_client(monkeypatch)
        resp = client.post("/api/whatsapp/send", json={
            "supplier_id": "sup_001",
        })
        assert resp.status_code == 400
        assert "message" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 9. POST /api/whatsapp/send returns 404 for nonexistent supplier
# ---------------------------------------------------------------------------


    def test_404_for_nonexistent_supplier(self, client, monkeypatch):
        _reset_route_client(monkeypatch)
        resp = client.post("/api/whatsapp/send", json={
            "supplier_id": "sup_nonexistent",
            "message": "Hello",
        })
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 10. POST /api/whatsapp/send returns 403 for supplier in different org
# ---------------------------------------------------------------------------


    def test_403_for_wrong_org(self, other_org_client, monkeypatch):
        """Supplier belongs to org_bd_001; caller is in org_other_999."""
        _reset_route_client(monkeypatch)
        resp = other_org_client.post("/api/whatsapp/send", json={
            "supplier_id": "sup_001",
            "message": "Hello",
        })
        assert resp.status_code == 403
        assert "organization" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 11. POST /api/whatsapp/questionnaire requires auth + editor role
# ---------------------------------------------------------------------------


class TestQuestionnaireRouteAuth:
    """The /questionnaire endpoint requires auth and editor role."""

    def test_questionnaire_requires_auth(self, monkeypatch):
        _reset_route_client(monkeypatch)
        c = TestClient(app)
        resp = c.post("/api/whatsapp/questionnaire", json={
            "supplier_id": "sup_001",
        })
        assert resp.status_code == 401

    def test_questionnaire_requires_editor_role(self, viewer_client, monkeypatch):
        _reset_route_client(monkeypatch)
        resp = viewer_client.post("/api/whatsapp/questionnaire", json={
            "supplier_id": "sup_001",
        })
        assert resp.status_code == 403

    def test_questionnaire_success_admin(self, client, monkeypatch):
        _reset_route_client(monkeypatch)
        resp = client.post("/api/whatsapp/questionnaire", json={
            "supplier_id": "sup_001",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "demo"
        assert data["supplier_name"] == "Gujarat Cotton Traders"


# ---------------------------------------------------------------------------
# 12. POST /api/whatsapp/alert requires auth + editor role
# ---------------------------------------------------------------------------


class TestAlertRouteAuth:
    """The /alert endpoint requires auth and editor role."""

    def test_alert_requires_auth(self, monkeypatch):
        _reset_route_client(monkeypatch)
        c = TestClient(app)
        resp = c.post("/api/whatsapp/alert", json={
            "supplier_id": "sup_001",
            "alert_text": "Risk detected",
        })
        assert resp.status_code == 401

    def test_alert_requires_editor_role(self, viewer_client, monkeypatch):
        _reset_route_client(monkeypatch)
        resp = viewer_client.post("/api/whatsapp/alert", json={
            "supplier_id": "sup_001",
            "alert_text": "Risk detected",
        })
        assert resp.status_code == 403

    def test_alert_success_admin(self, client, monkeypatch):
        _reset_route_client(monkeypatch)
        resp = client.post("/api/whatsapp/alert", json={
            "supplier_id": "sup_001",
            "alert_text": "Emissions exceeded threshold",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "demo"
        assert data["supplier_name"] == "Gujarat Cotton Traders"


# ---------------------------------------------------------------------------
# 13. POST /api/whatsapp/webhook accepts incoming messages (no auth required)
# ---------------------------------------------------------------------------


class TestWebhookRoute:
    """The /webhook endpoint accepts incoming Twilio messages.

    Note: The whatsapp router is registered with ``dependencies=[Depends(require_auth)]``
    in ``main.py``, so every endpoint including /webhook needs a valid JWT to pass
    the router-level guard.  The endpoint function itself does not enforce role
    restrictions (no ``require_role`` call), distinguishing it from /send, /questionnaire,
    and /alert which additionally require an editor role.

    The webhook validates Twilio signatures. When the WhatsAppClient has no auth_token
    configured, the endpoint returns 503 (fail-closed) rather than accepting unsigned
    payloads.
    """

    @staticmethod
    def _setup_webhook_auth(monkeypatch):
        """Configure a mock WhatsAppClient with a valid auth_token and webhook verifier."""
        _reset_route_client(monkeypatch)
        from src.connectors.whatsapp import WhatsAppClient
        mock_client = WhatsAppClient.__new__(WhatsAppClient)
        mock_client.auth_token = "test-auth-token-for-webhook-verification"
        mock_client._from_number = "+1234567890"
        monkeypatch.setattr("src.api.routes.whatsapp._client", mock_client)
        monkeypatch.setattr(
            "src.api.routes.whatsapp.verify_webhook",
            lambda auth_token, body, sig: True,
        )
        return mock_client

    def test_webhook_receives_message(self, client, monkeypatch):
        """Webhook endpoint accepts and stores an incoming message."""
        self._setup_webhook_auth(monkeypatch)
        resp = client.post(
            "/api/whatsapp/webhook",
            data={
                "From": "whatsapp:+880-171234567",
                "Body": "1. 4200000",
                "MessageSid": "SM_test_001",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "received"

    def test_webhook_stores_inbound_message(self, client, monkeypatch):
        """Incoming message is stored in whatsapp_messages table."""
        self._setup_webhook_auth(monkeypatch)
        client.post(
            "/api/whatsapp/webhook",
            data={
                "From": "whatsapp:+91-9876543210",
                "Body": "1. 5000000",
                "MessageSid": "SM_test_002",
            },
        )
        conn = get_connection()
        from src.db.database import _fetchall
        rows = _fetchall(
            conn,
            "SELECT * FROM whatsapp_messages WHERE direction = 'inbound' AND twilio_message_sid = ?",
            ("SM_test_002",),
        )
        assert len(rows) >= 1
        assert rows[0]["body"] == "1. 5000000"

    def test_webhook_ignores_empty_from(self, client, monkeypatch):
        """Webhook returns 'ignored' when no From field is present."""
        self._setup_webhook_auth(monkeypatch)
        resp = client.post(
            "/api/whatsapp/webhook",
            data={
                "Body": "Hello",
                "MessageSid": "SM_test_003",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"


# ---------------------------------------------------------------------------
# 14. All send/questionnaire/alert endpoints reject unauthenticated requests
# ---------------------------------------------------------------------------


class TestUnauthenticatedRejection:
    """Every write endpoint except /webhook rejects missing credentials."""

    def test_send_unauthenticated(self, monkeypatch):
        _reset_route_client(monkeypatch)
        c = TestClient(app)
        resp = c.post("/api/whatsapp/send", json={
            "supplier_id": "sup_001",
            "message": "Hello",
        })
        assert resp.status_code == 401

    def test_questionnaire_unauthenticated(self, monkeypatch):
        _reset_route_client(monkeypatch)
        c = TestClient(app)
        resp = c.post("/api/whatsapp/questionnaire", json={
            "supplier_id": "sup_001",
        })
        assert resp.status_code == 401

    def test_alert_unauthenticated(self, monkeypatch):
        _reset_route_client(monkeypatch)
        c = TestClient(app)
        resp = c.post("/api/whatsapp/alert", json={
            "supplier_id": "sup_001",
            "alert_text": "Risk",
        })
        assert resp.status_code == 401
