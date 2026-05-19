"""Tests for emission factors, framework mappings, alert thresholds, and audit log."""
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.db.database import reset_database, get_connection, _fetchall


@pytest.fixture(autouse=True)
def _fresh_db():
    reset_database()
    from src.db.seed import seed
    seed()
    from src.db.seed_emission_factors import seed_emission_factors
    seed_emission_factors()
    from src.db.seed_alert_thresholds import seed_alert_thresholds
    seed_alert_thresholds()


@pytest.fixture
def client():
    from src.auth.jwt import create_token
    token = create_token({
        "sub": "usr_admin_001",
        "org_id": "org_bd_001",
        "email": "admin@textilebd.com",
        "role": "admin",
    })
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


# --- Emission factors ---

class TestEmissionFactors:
    def test_list_all(self, client):
        resp = client.get("/api/emission-factors/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 40
        assert all("factor_name" in f for f in data["factors"])

    def test_filter_by_category(self, client):
        resp = client.get("/api/emission-factors/?category=grid_electricity")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 5
        assert all(f["category"] == "grid_electricity" for f in data["factors"])

    def test_filter_by_country(self, client):
        resp = client.get("/api/emission-factors/?country_code=BD")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert all(f["country_code"] == "BD" for f in data["factors"])

    def test_categories_endpoint(self, client):
        resp = client.get("/api/emission-factors/categories")
        assert resp.status_code == 200
        cats = resp.json()["categories"]
        assert "grid_electricity" in cats
        assert "scope3_spend" in cats

    def test_calculate_emissions(self, client):
        resp = client.get("/api/emission-factors/calculate?activity_value=1000&factor_name=Natural%20gas")
        assert resp.status_code == 200
        data = resp.json()
        assert data["calculated_emissions"] > 0
        assert "emissions_unit" in data

    def test_calculate_missing_factor(self, client):
        resp = client.get("/api/emission-factors/calculate?activity_value=100&factor_name=nonexistent")
        assert resp.status_code == 404


# --- Alert thresholds ---

class TestAlertThresholds:
    def test_list_thresholds(self, client):
        resp = client.get("/api/alerts/thresholds")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 15

    def test_filter_by_cluster(self, client):
        resp = client.get("/api/alerts/thresholds?cluster=energy")
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["cluster"] == "energy" for t in data["thresholds"])

    def test_create_threshold(self, client):
        resp = client.post("/api/alerts/thresholds", json={
            "cluster": "test_cluster",
            "metric_cluster": "test_metric",
            "operator": ">",
            "threshold_value": 100.0,
            "severity": "WARNING",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "created"

    def test_create_threshold_invalid_operator(self, client):
        resp = client.post("/api/alerts/thresholds", json={
            "cluster": "test",
            "metric_cluster": "test",
            "operator": "!=",
            "threshold_value": 100,
            "severity": "WARNING",
        })
        assert resp.status_code == 400

    def test_check_thresholds_triggered(self, client):
        resp = client.get("/api/alerts/check/energy?current_value=5000000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_triggered"] >= 1

    def test_check_thresholds_ok(self, client):
        resp = client.get("/api/alerts/check/energy?current_value=100")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_triggered"] == 0


# --- Audit log ---

class TestAuditLog:
    def test_create_and_list(self, client):
        resp = client.post("/api/audit/log", json={
            "org_id": "org_bd_001",
            "user_id": "usr_test",
            "action": "login",
            "resource_type": "session",
            "details": "Test login event",
        })
        assert resp.status_code == 200

        resp = client.get("/api/audit/log?org_id=org_bd_001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(e["action"] == "login" for e in data["entries"])

    def test_filter_by_action(self, client):
        client.post("/api/audit/log", json={
            "org_id": "org_bd_001", "user_id": "u1", "action": "create", "resource_type": "supplier",
        })
        client.post("/api/audit/log", json={
            "org_id": "org_bd_001", "user_id": "u1", "action": "delete", "resource_type": "supplier",
        })

        resp = client.get("/api/audit/log?action=create")
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["action"] == "create" for e in data["entries"])

    def test_missing_required_field(self, client):
        resp = client.post("/api/audit/log", json={"org_id": "org_bd_001"})
        assert resp.status_code == 400


# --- Seed data verification ---

class TestSeedData:
    def test_emission_factors_seeded(self):
        conn = get_connection()
        rows = _fetchall(conn, "SELECT COUNT(*) as cnt FROM emission_factors")
        assert rows[0]["cnt"] >= 40

    def test_alert_thresholds_seeded(self):
        conn = get_connection()
        rows = _fetchall(conn, "SELECT COUNT(*) as cnt FROM alert_thresholds")
        assert rows[0]["cnt"] >= 15

    def test_grid_factors_have_countries(self):
        conn = get_connection()
        rows = _fetchall(conn, "SELECT DISTINCT country_code FROM emission_factors WHERE category = 'grid_electricity'")
        codes = [r["country_code"] for r in rows]
        assert "BD" in codes
        assert "IN" in codes
        assert "VN" in codes

    def test_thresholds_have_valid_operators(self):
        conn = get_connection()
        rows = _fetchall(conn, "SELECT DISTINCT operator FROM alert_thresholds")
        ops = [r["operator"] for r in rows]
        for op in ops:
            assert op in (">", "<", ">=", "<=", "=")
