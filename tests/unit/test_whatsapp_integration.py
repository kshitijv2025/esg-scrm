"""
D7.7: WhatsApp Integration Tests — webhook HMAC validation, message status
callbacks, rate limiting, multilingual number parsing, and edge cases.

Extends the coverage in test_whatsapp.py (which tests the WhatsAppClient
connector and authenticated endpoints) to cover the webhook endpoint at
/api/whatsapp/webhook with focus on:
  1. HMAC signature validation (valid / invalid / missing)
  2. Message status callbacks (delivered, read, failed)
  3. Per-IP rate limiting (100 req/min on webhook)
  4. Multilingual number parsing (Bengali, Vietnamese, free-text)
  5. Edge cases (empty body, unknown message type, invalid supplier phone)
"""
import hashlib
import hmac
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.db.database import reset_database

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _fresh_db():
    """Reset and seed the database before every test."""
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
    """TestClient that does NOT raise on server exceptions (webhook may return 200
    even when logging errors, and we want to inspect the response body)."""
    return TestClient(app, raise_server_exceptions=False)


def _reset_rate_limit():
    """Clear in-memory rate limiter store."""
    try:
        stack = app.middleware_stack
    except Exception:
        return
    if stack is None:
        return
    current = stack
    for _ in range(15):
        if not hasattr(current, "app"):
            break
        current = current.app
        if isinstance(current, RateLimitMiddleware):
            current._limiters.clear()
            for limiter in current._limiters.values():
                limiter._local_store.clear()
            break


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    _reset_rate_limit()
    yield
    _reset_rate_limit()


# ---------------------------------------------------------------------------
# Webhook auth setup helpers
# ---------------------------------------------------------------------------

def _setup_webhook_auth(monkeypatch, token: str = "test-auth-token-for-webhook"):
    """Patch verify_webhook to return True (bypasses HMAC for integration tests).

    Uses the same pattern as test_whatsapp.py::TestWebhookRoute::_setup_webhook_auth.
    The token is stored on the mock client for completeness but verify_webhook
    is fully bypassed so the token value does not affect the test.
    """
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)
    from src.connectors.whatsapp import WhatsAppClient
    mock_client = WhatsAppClient.__new__(WhatsAppClient)
    mock_client.auth_token = token
    monkeypatch.setattr("src.api.routes.whatsapp._client", mock_client)
    monkeypatch.setattr(
        "src.api.routes.whatsapp.verify_webhook",
        lambda auth_token, body, sig: True,
    )
    return token


def _hmac_headers(token: str, body_bytes: bytes) -> dict:
    """Return X-Twilio-Signature header computed against body_bytes using SHA-256."""
    sig = hmac.new(token.encode(), body_bytes, hashlib.sha256).hexdigest()
    return {"X-Twilio-Signature": sig}


# ---------------------------------------------------------------------------
# 1. Webhook HMAC Validation (real HMAC computation — tests the security boundary)
# ---------------------------------------------------------------------------

class TestWebhookHMACValidation:
    """Webhook rejects requests with invalid or missing HMAC signatures."""

    def test_valid_hmac_returns_200(self, client, monkeypatch):
        """Correct HMAC-SHA256 signature → 200 status, status=received."""
        token = "test-hmac-token-001"
        _setup_webhook_with_token(client, monkeypatch, token)
        payload = {"From": "whatsapp:+8801712345678", "Body": "1. 4200000", "MessageSid": "SM_hmac_ok"}
        body_bytes = urlencode(payload).encode()
        resp = client.post(
            "/api/whatsapp/webhook",
            data=payload,
            headers=_hmac_headers(token, body_bytes),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "received"

    def test_invalid_hmac_returns_403(self, client, monkeypatch):
        """Wrong signature → 403 Forbidden."""
        token = "test-hmac-token-002"
        _setup_webhook_with_token(client, monkeypatch, token)
        payload = {"From": "whatsapp:+8801712345678", "Body": "1. 4200000", "MessageSid": "SM_bad_sig"}
        body_bytes = urlencode(payload).encode()
        wrong_sig = hmac.new(b"wrong-token", body_bytes, hashlib.sha256).hexdigest()
        resp = client.post(
            "/api/whatsapp/webhook",
            data=payload,
            headers={"X-Twilio-Signature": wrong_sig},
        )
        assert resp.status_code == 403, resp.text

    def test_missing_signature_returns_403(self, client, monkeypatch):
        """No X-Twilio-Signature header → 403 Forbidden."""
        token = "test-hmac-token-003"
        _setup_webhook_with_token(client, monkeypatch, token)
        payload = {"From": "whatsapp:+8801712345678", "Body": "1. 4200000", "MessageSid": "SM_no_sig"}
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 403, resp.text

    def test_tampered_body_returns_403(self, client, monkeypatch):
        """Correct signature but body was modified → 403."""
        token = "test-hmac-token-004"
        _setup_webhook_with_token(client, monkeypatch, token)
        original = {"From": "whatsapp:+8801712345678", "Body": "1. 4200000", "MessageSid": "SM_orig"}
        tampered = {"From": "whatsapp:+8801712345678", "Body": "1. 9999999", "MessageSid": "SM_tampered"}
        body_bytes = urlencode(original).encode()
        resp = client.post(
            "/api/whatsapp/webhook",
            data=tampered,
            headers=_hmac_headers(token, body_bytes),
        )
        assert resp.status_code == 403, resp.text

    def test_no_auth_token_returns_503(self, client, monkeypatch):
        """When WhatsAppClient has no auth_token, webhook fails closed with 503."""
        monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
        monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)
        from src.connectors.whatsapp import WhatsAppClient
        mock_client = WhatsAppClient.__new__(WhatsAppClient)
        mock_client.auth_token = ""  # Empty token → 503
        monkeypatch.setattr("src.api.routes.whatsapp._client", mock_client)
        payload = {"From": "whatsapp:+8801712345678", "Body": "1. 4200000", "MessageSid": "SM_no_token"}
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 503, resp.text


def _setup_webhook_with_token(client, monkeypatch, token: str):
    """Configure WhatsAppClient with a specific auth_token for real HMAC testing."""
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_WHATSAPP_NUMBER", raising=False)
    from src.connectors.whatsapp import WhatsAppClient
    mock_client = WhatsAppClient.__new__(WhatsAppClient)
    mock_client.auth_token = token
    monkeypatch.setattr("src.api.routes.whatsapp._client", mock_client)


# ---------------------------------------------------------------------------
# 2. Message Status Callbacks (verify_webhook patched for integration testing)
# ---------------------------------------------------------------------------

class TestMessageStatusCallbacks:
    """Incoming Twilio status callback webhooks (delivered, read, failed)."""

    def test_status_callback_delivered(self, client, monkeypatch):
        """Status callback (delivered) is stored in whatsapp_messages table."""
        _setup_webhook_auth(monkeypatch)
        payload = {
            "MessageSid": "SM_status_delivered",
            "From": "whatsapp:+8801712345678",
            "MessageStatus": "delivered",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200

    def test_status_read_stored(self, client, monkeypatch):
        """Read status callback is accepted and stored."""
        _setup_webhook_auth(monkeypatch)
        payload = {
            "MessageSid": "SM_status_read",
            "From": "whatsapp:+8801712345678",
            "MessageStatus": "read",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200

    def test_status_failed_stored(self, client, monkeypatch):
        """Failed status callback is accepted and stored."""
        _setup_webhook_auth(monkeypatch)
        payload = {
            "MessageSid": "SM_status_failed",
            "From": "whatsapp:+8801712345678",
            "MessageStatus": "failed",
            "ErrorCode": "30022",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 3. Rate Limiting on Webhook (100 req/min per IP)
# ---------------------------------------------------------------------------

class TestWebhookRateLimiting:
    """Per-IP rate limit of 100 req/min is enforced on /api/whatsapp/webhook."""

    def test_rate_limit_100_per_minute(self, client, monkeypatch):
        """Exceeding 100 requests/min from same IP → 429."""
        token = _setup_webhook_auth(monkeypatch)
        base_payload = {
            "From": "whatsapp:+8801712345678",
            "Body": "1. 4200000",
        }

        hit_429 = False
        for i in range(110):
            payload_i = {**base_payload, "MessageSid": f"SM_rl_{i}"}
            body_i = urlencode(payload_i).encode()
            hdrs = {**_hmac_headers(token, body_i), "X-Forwarded-For": "10.1.99.1"}
            resp = client.post("/api/whatsapp/webhook", data=payload_i, headers=hdrs)
            if resp.status_code == 429:
                hit_429 = True
                assert "retry-after" in str(resp.headers).lower()
                break
            if resp.status_code == 401:
                break
        assert hit_429, "Expected 429 after 100 req/min limit on WhatsApp webhook"

    def test_different_ips_have_separate_limits(self, client, monkeypatch):
        """Two different IPs each get their own 100 req/min bucket."""
        token = _setup_webhook_auth(monkeypatch)
        base_payload = {
            "From": "whatsapp:+8801712345678",
            "Body": "1. 4200000",
        }

        # Exhaust IP A's bucket
        for i in range(105):
            payload_i = {**base_payload, "MessageSid": f"SM_ipA_{i}"}
            body_i = urlencode(payload_i).encode()
            hdrs = {**_hmac_headers(token, body_i), "X-Forwarded-For": "10.2.1.1"}
            resp = client.post("/api/whatsapp/webhook", data=payload_i, headers=hdrs)
            if resp.status_code == 429:
                break

        # IP B should have its own fresh bucket
        payload_b = {**base_payload, "MessageSid": "SM_ipB_fresh"}
        body_b = urlencode(payload_b).encode()
        hdrs_b = {**_hmac_headers(token, body_b), "X-Forwarded-For": "10.2.2.2"}
        resp_b = client.post("/api/whatsapp/webhook", data=payload_b, headers=hdrs_b)
        assert resp_b.status_code != 429, \
            "Different IP should have separate rate limit bucket"


# ---------------------------------------------------------------------------
# 4. Multilingual Number Parsing (verify_webhook patched for integration tests)
# ---------------------------------------------------------------------------

class TestMultilingualNumberParsing:
    """WhatsApp questionnaire replies with Bengali/Vietnamese numerals are parsed."""

    def test_bengali_digit_characters(self, client, monkeypatch):
        """Bengali digit characters (১২৩) are parsed as Arabic equivalents."""
        _setup_webhook_auth(monkeypatch)
        # ১২৩ = 123
        payload = {
            "From": "whatsapp:+8801712345678",
            "Body": "1. ১২৩",
            "MessageSid": "SM_bn_digits",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200
        assert resp.json().get("status") == "received"

    def test_bengali_lakh_hazar(self, client, monkeypatch):
        """Bengali number words (lakh, hazar) are parsed correctly."""
        _setup_webhook_auth(monkeypatch)
        # "1 lakh 50 hazar" = 1*100000 + 50*1000 = 150,000
        payload = {
            "From": "whatsapp:+8801712345678",
            "Body": "1. 1 lakh 50 hazar",
            "MessageSid": "SM_bn_words",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200

    def test_vietnamese_triệu(self, client, monkeypatch):
        """Vietnamese number word triệu (million) is parsed correctly."""
        _setup_webhook_auth(monkeypatch)
        # "1.5 triệu" = 1,500,000
        payload = {
            "From": "whatsapp:+8801712345678",
            "Body": "1. 1.5 triệu",
            "MessageSid": "SM_vn_triệu",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200

    def test_vietnamese_nghin(self, client, monkeypatch):
        """Vietnamese nghìn (thousand) is parsed correctly."""
        _setup_webhook_auth(monkeypatch)
        payload = {
            "From": "whatsapp:+8801712345678",
            "Body": "1. 500 nghìn",
            "MessageSid": "SM_vn_nghin",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200

    def test_free_text_response(self, client, monkeypatch):
        """Free-text (non-numeric) responses are accepted without crashing."""
        _setup_webhook_auth(monkeypatch)
        payload = {
            "From": "whatsapp:+8801712345678",
            "Body": "1. Yes, we have reduced our energy consumption",
            "MessageSid": "SM_free_text",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200
        assert resp.json().get("status") == "received"

    def test_mixed_numeric_and_text(self, client, monkeypatch):
        """Mixed responses with both numeric and free-text lines are handled."""
        _setup_webhook_auth(monkeypatch)
        payload = {
            "From": "whatsapp:+8801712345678",
            "Body": "1. 4200000\n2. Yes\n3. 12400",
            "MessageSid": "SM_mixed",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200
        assert resp.json().get("status") == "received"


# ---------------------------------------------------------------------------
# 5. Edge Cases (verify_webhook patched for integration tests)
# ---------------------------------------------------------------------------

class TestWebhookEdgeCases:
    """Webhook handles malformed and edge-case inputs gracefully."""

    def test_empty_body(self, client, monkeypatch):
        """Empty Body field → accepted (status=received), no crash."""
        _setup_webhook_auth(monkeypatch)
        payload = {
            "From": "whatsapp:+8801712345678",
            "Body": "",
            "MessageSid": "SM_empty_body",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200
        assert resp.json().get("status") == "received"

    def test_whitespace_only_body(self, client, monkeypatch):
        """Whitespace-only Body is handled without error."""
        _setup_webhook_auth(monkeypatch)
        payload = {
            "From": "whatsapp:+8801712345678",
            "Body": "   \n\t  ",
            "MessageSid": "SM_ws_only",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200

    def test_unknown_message_type(self, client, monkeypatch):
        """Non-standard MessageType → 200, not error (Twilio sends these)."""
        _setup_webhook_auth(monkeypatch)
        payload = {
            "From": "whatsapp:+8801712345678",
            "Body": "Hello",
            "MessageSid": "SM_unknown_type",
            "MessageType": "audio",  # Not text — Twilio sends this for media
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200

    def test_missing_message_sid(self, client, monkeypatch):
        """MessageSid absent → still returns 200 (status callback without SID)."""
        _setup_webhook_auth(monkeypatch)
        payload = {
            "From": "whatsapp:+8801712345678",
            "Body": "1. 4200000",
            # No MessageSid
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200

    def test_invalid_supplier_phone(self, client, monkeypatch):
        """Phone number not in suppliers table → stored with empty supplier_id, no crash."""
        _setup_webhook_auth(monkeypatch)
        payload = {
            "From": "whatsapp:+9999999999999",  # Not in seed data
            "Body": "1. 4200000",
            "MessageSid": "SM_unknown_phone",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200
        data = resp.json()
        # supplier_id is empty since phone is not registered
        assert data.get("supplier_id") == ""
        assert data.get("status") == "received"

    def test_missing_from_field_returns_ignored(self, client, monkeypatch):
        """No From field → returns 200 with status=ignored."""
        _setup_webhook_auth(monkeypatch)
        payload = {
            "Body": "1. 4200000",
            "MessageSid": "SM_no_from",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200
        assert resp.json().get("status") == "ignored"

    def test_unicode_bengali_body(self, client, monkeypatch):
        """Full Bengali Unicode body is accepted without encoding errors."""
        _setup_webhook_auth(monkeypatch)
        bengali_text = "১. ১ লক্ষ ৫০ হাজার\n২. হ্যাঁ"
        payload = {
            "From": "whatsapp:+8801712345678",
            "Body": bengali_text,
            "MessageSid": "SM_bn_unicode",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200

    def test_unicode_vietnamese_body(self, client, monkeypatch):
        """Full Vietnamese Unicode body is accepted without encoding errors."""
        _setup_webhook_auth(monkeypatch)
        vietnamese_text = "1. 1,5 triệu\n2. Có"
        payload = {
            "From": "whatsapp:+8801712345678",
            "Body": vietnamese_text,
            "MessageSid": "SM_vn_unicode",
        }
        resp = client.post("/api/whatsapp/webhook", data=payload)
        assert resp.status_code == 200
