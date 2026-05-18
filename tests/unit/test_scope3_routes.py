"""Tests for scope3 API routes."""
import sys
sys.path.insert(0, "src")

from fastapi.testclient import TestClient
from src.api.main import app
from tests.conftest import _auth_headers

client = TestClient(app)


def test_get_scope3_categories():
    r = client.get("/api/scope3/categories", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "categories" in data
    cats = data["categories"]
    assert len(cats) > 0
    for cat in cats:
        assert "id" in cat
        assert "name" in cat
        assert "respondents" in cat
        assert "total" in cat
        assert "coverage_pct" in cat
        assert "tco2e" in cat


def test_get_scope3_completeness():
    r = client.get("/api/scope3/completeness", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert "overall_coverage_pct" in data
    assert "total_respondents" in data
    assert "total_suppliers" in data
    assert "by_category" in data
    assert len(data["by_category"]) > 0
    assert 0 <= data["overall_coverage_pct"] <= 100
