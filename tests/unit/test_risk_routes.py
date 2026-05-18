"""Tests for risk API routes."""
import sys
sys.path.insert(0, "src")

from fastapi.testclient import TestClient
from src.api.main import app
from tests.conftest import _auth_headers

client = TestClient(app)


def test_get_risk_summary():
    r = client.get("/api/risk/summary", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "by_severity" in data
    assert data["by_severity"]["critical"] >= 0
    assert data["by_severity"]["warning"] >= 0
    assert data["by_severity"]["info"] >= 0


def test_get_risk_flags_no_filter():
    r = client.get("/api/risk/flags", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert "flags" in data
    assert "total" in data


def test_get_risk_flags_filter_acknowledged():
    r = client.get("/api/risk/flags?acknowledged=false", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    for flag in data["flags"]:
        assert flag["acknowledged"] is False


def test_get_risk_scorecard():
    r = client.get("/api/risk/scorecard", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert "quadrants" in data
    ids = {q["id"] for q in data["quadrants"]}
    assert ids == {"G2", "G5", "G8", "G3"}
    for q in data["quadrants"]:
        assert "score" in q
        assert "tier" in q
        assert "trend" in q
        assert "active_flags" in q


def test_get_risk_geopolitical():
    r = client.get("/api/risk/geopolitical", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert "countries" in data
    assert "total" in data
    assert data["total"] == 6
    for row in data["countries"]:
        assert "country_code" in row
        assert "political_stability" in row
        assert "trade_exposure" in row
        assert "currency_volatility" in row
        assert "overall_score" in row


def test_acknowledge_flag_not_found():
    r = client.post("/api/risk/flags/nonexistent-id/acknowledge", headers=_auth_headers())
    assert r.status_code == 404
