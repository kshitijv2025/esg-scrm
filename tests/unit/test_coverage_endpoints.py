"""Tests for coverage calculator and questionnaire B3.1 endpoints."""
import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    from src.auth.jwt import create_token
    token = create_token({
        "sub": "usr_test_001",
        "org_id": "org_bd_001",
        "email": "test@test.com",
        "role": "admin",
    })
    return {"Authorization": f"Bearer {token}"}


class TestCoverageStats:
    def test_coverage_returns_spend_weighted(self, client, auth_headers):
        resp = client.get("/api/questionnaires/coverage", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "spend_weighted_coverage_pct" in data
        assert "headcount_coverage_pct" in data
        assert "responded_suppliers" in data
        assert "total_suppliers" in data
        assert "total_spend_usd" in data
        assert "covered_spend_usd" in data
        assert "target_coverage_pct" in data
        assert "meets_target" in data

    def test_coverage_stats_v2_has_spend_coverage(self, client, auth_headers):
        resp = client.get("/api/questionnaires/coverage-stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_coverage" in data
        assert "headcount_coverage" in data
        assert "total_spend_usd" in data
        assert "covered_spend_usd" in data

    def test_coverage_stats_no_hardcoded_previous(self, client, auth_headers):
        """Ensure previous_coverage is not hardcoded 64.0 (zero-tolerance Rule 2)."""
        resp = client.get("/api/questionnaires/coverage-stats", headers=auth_headers)
        data = resp.json()
        assert "previous_coverage" not in data

    def test_coverage_percentages_are_valid(self, client, auth_headers):
        resp = client.get("/api/questionnaires/coverage-stats", headers=auth_headers)
        data = resp.json()
        assert 0 <= data["total_coverage"] <= 100
        assert 0 <= data["headcount_coverage"] <= 100


class TestResponseSummary:
    def test_response_summary_structure(self, client, auth_headers):
        resp = client.get("/api/questionnaires/response-summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_suppliers" in data
        assert "total_responded" in data
        assert "total_pending" in data
        assert "response_rate" in data
        assert "avg_confidence" in data
        assert "by_channel" in data
        assert "org_id" in data

    def test_response_summary_percentages_valid(self, client, auth_headers):
        resp = client.get("/api/questionnaires/response-summary", headers=auth_headers)
        data = resp.json()
        assert 0 <= data["response_rate"] <= 100

    def test_response_summary_spend_matches(self, client, auth_headers):
        resp = client.get("/api/questionnaires/response-summary", headers=auth_headers)
        data = resp.json()
        assert data["total_responded"] + data["total_pending"] == data["total_suppliers"]


class TestNonResponders:
    def test_non_responders_structure(self, client, auth_headers):
        resp = client.get("/api/questionnaires/non-responders", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert "supplier_id" in data[0]
            assert "name" in data[0]
            assert "country" in data[0]
            assert "annual_spend_usd" in data[0]
            assert "tier" in data[0]

    def test_non_responders_sorted_by_spend_desc(self, client, auth_headers):
        resp = client.get("/api/questionnaires/non-responders", headers=auth_headers)
        data = resp.json()
        spends = [s["annual_spend_usd"] for s in data]
        assert spends == sorted(spends, reverse=True)


class TestResend:
    def test_resend_requires_auth(self, client):
        resp = client.post("/api/questionnaires/resend")
        assert resp.status_code in (401, 403)

    def test_resend_returns_count(self, client, auth_headers):
        resp = client.post("/api/questionnaires/resend", json={}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "resent_count" in data
        assert "supplier_ids" in data
        assert "status" in data


class TestSupplierResponses:
    def test_responses_for_nonexistent_supplier(self, client, auth_headers):
        resp = client.get("/api/questionnaires/responses/nonexistent", headers=auth_headers)
        assert resp.status_code == 404

    def test_responses_for_existing_supplier(self, client, auth_headers):
        # sup_001 is a seeded supplier that has questionnaire responses
        resp = client.get("/api/questionnaires/responses/sup_001", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert "question_id" in data[0]
            assert "response_value" in data[0]
            assert "response_text" in data[0]
            assert "channel" in data[0]
            assert "received_at" in data[0]
