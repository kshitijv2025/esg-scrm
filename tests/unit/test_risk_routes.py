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
    # D3.3: 4-chip format with G2/G3/G8/G5 clusters
    assert "G2_supply_chain" in data
    assert "G3_ethics" in data
    assert "G8_geopolitical" in data
    assert "G5_financial" in data
    for key in ["G2_supply_chain", "G3_ethics", "G8_geopolitical", "G5_financial"]:
        chip = data[key]
        assert "score" in chip
        assert "tier" in chip
        assert "trend" in chip
        assert "flags" in chip
        assert isinstance(chip["score"], int)
        assert chip["score"] >= 0
        assert chip["score"] <= 100


def test_get_risk_flags_no_filter():
    r = client.get("/api/risk/flags", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert "flags" in data
    assert "total" in data
    # D3.3: RiskFlag schema with title/detail/recommendation
    for flag in data["flags"]:
        assert "id" in flag
        assert "severity" in flag
        assert "cluster" in flag
        assert "cluster_name" in flag
        assert "title" in flag
        assert "detail" in flag
        assert "recommendation" in flag
        assert "acknowledged" in flag
        assert "created_at" in flag


def test_get_risk_flags_filter_acknowledged():
    r = client.get("/api/risk/flags?acknowledged=false", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    for flag in data["flags"]:
        assert flag["acknowledged"] is False
        # D3.3: non-CRITICAL flags should not be in a "critically exceeded" title
        if flag["severity"] != "CRITICAL":
            assert "critically exceeded" not in flag["title"].lower()


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
