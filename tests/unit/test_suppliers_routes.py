"""Tests for suppliers API routes."""
import sys
sys.path.insert(0, "src")

from fastapi.testclient import TestClient
from src.api.main import app
from tests.conftest import _auth_headers

client = TestClient(app)


def test_list_suppliers():
    r = client.get("/api/suppliers/", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 7


def test_get_risk_ranked_suppliers():
    r = client.get("/api/suppliers/risk-ranked", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 7
    scores = [s["risk_score"] for s in data["suppliers"]]
    assert scores == sorted(scores)


def test_get_supplier_profile():
    r = client.get("/api/suppliers/sup_003/profile", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["supplier_id"] == "sup_003"
    assert data["name"] == "Bangladesh Dye House Ltd."
    assert "overall_risk_score" in data
    assert "risk_tier" in data
    assert "clusters" in data
    assert "ml_recommendations" in data
    assert len(data["ml_recommendations"]) >= 1
    for rec in data["ml_recommendations"]:
        assert isinstance(rec, str) and len(rec) > 10
    for key in ["labour_rights", "environment", "governance", "safety", "gender"]:
        assert key in data["clusters"]


def test_get_supplier_profile_not_found():
    r = client.get("/api/suppliers/nonexistent/profile", headers=_auth_headers())
    assert r.status_code == 404


def test_supplier_scope3():
    r = client.get("/api/suppliers/sup_001/scope3", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["supplier_name"] == "Gujarat Cotton Traders"
    assert "scope3_tco2e" in data
    assert "calculation_method" in data
