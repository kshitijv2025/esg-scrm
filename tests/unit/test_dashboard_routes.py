"""Tests for dashboard API routes — live metrics, trends, and alerts."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.jwt import create_token
from src.db.database import reset_database

client = TestClient(app)


@pytest.fixture(autouse=True)
def _seed_fresh_db():
    """Reset and re-seed database for every test to ensure deterministic data."""
    reset_database()
    from src.db.seed import seed

    seed()


def _admin_headers() -> dict:
    token = create_token(
        {
            "sub": "usr_test_001",
            "org_id": "org_bd_001",
            "email": "test@test.com",
            "role": "admin",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _viewer_headers() -> dict:
    token = create_token(
        {
            "sub": "usr_viewer_001",
            "org_id": "org_bd_001",
            "email": "viewer@test.com",
            "role": "viewer",
        }
    )
    return {"Authorization": f"Bearer {token}"}


class TestLiveMetrics:
    """GET /api/dashboard/live"""

    def test_returns_200_with_metrics(self):
        resp = client.get("/api/dashboard/live", headers=_admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data
        assert "updated_at" in data
        assert "org_id" in data
        assert data["org_id"] == "org_bd_001"

    def test_metrics_contain_expected_clusters(self):
        resp = client.get("/api/dashboard/live", headers=_admin_headers())
        assert resp.status_code == 200
        metrics = resp.json()["metrics"]
        # The seed data should produce at least these clusters
        expected = ["energy_kwh", "emissions_tco2", "water_m3"]
        for cluster in expected:
            assert cluster in metrics, f"Missing cluster: {cluster}"

    def test_metric_has_required_fields(self):
        resp = client.get("/api/dashboard/live", headers=_admin_headers())
        assert resp.status_code == 200
        metrics = resp.json()["metrics"]
        energy = metrics.get("energy_kwh", {})
        required_fields = [
            "value",
            "unit",
            "confidence",
            "trend",
            "source",
            "period",
            "hash",
            "chain_valid",
        ]
        for field in required_fields:
            assert field in energy, f"energy_kwh missing field: {field}"

    def test_hash_chain_valid_field_is_boolean(self):
        resp = client.get("/api/dashboard/live", headers=_admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["hash_chain_valid"], bool)

    def test_without_auth_returns_401(self):
        resp = client.get("/api/dashboard/live")
        assert resp.status_code == 401

    def test_viewer_can_read_live_metrics(self):
        resp = client.get("/api/dashboard/live", headers=_viewer_headers())
        assert resp.status_code == 200


class TestTrendsByMetric:
    """GET /api/dashboard/trends/{metric_type}"""

    def test_energy_trends_returns_200(self):
        resp = client.get(
            "/api/dashboard/trends/energy_kwh",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metric_type"] == "energy_kwh"
        assert "data" in data
        assert data["unit"] == "kWh"

    def test_emissions_trends_returns_200(self):
        resp = client.get(
            "/api/dashboard/trends/emissions_tco2",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metric_type"] == "emissions_tco2"
        assert data["unit"] == "tCO2e"

    def test_water_trends_returns_200(self):
        resp = client.get(
            "/api/dashboard/trends/water_m3",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["metric_type"] == "water_m3"
        assert data["unit"] == "m³"

    def test_trend_data_points_have_month_and_value(self):
        resp = client.get(
            "/api/dashboard/trends/energy_kwh",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data_points = resp.json()["data"]
        assert len(data_points) >= 1
        for point in data_points:
            assert "month" in point
            assert "value" in point

    def test_trends_without_auth_returns_401(self):
        resp = client.get("/api/dashboard/trends/energy_kwh")
        assert resp.status_code == 401


class TestAllTrends:
    """GET /api/dashboard/trends (no metric_type = all trends combined)"""

    def test_returns_200_with_all_trends(self):
        resp = client.get("/api/dashboard/trends", headers=_admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "trends" in data
        assert len(data["trends"]) >= 1

    def test_all_trend_entries_have_expected_keys(self):
        resp = client.get("/api/dashboard/trends", headers=_admin_headers())
        assert resp.status_code == 200
        trends = resp.json()["trends"]
        for entry in trends:
            assert "month" in entry
            assert "energy" in entry
            assert "emissions" in entry
            assert "water" in entry

    def test_all_trends_without_auth_returns_401(self):
        resp = client.get("/api/dashboard/trends")
        assert resp.status_code == 401


class TestAlerts:
    """GET /api/dashboard/alerts"""

    def test_returns_200_with_alerts(self):
        resp = client.get("/api/dashboard/alerts", headers=_admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        assert "total" in data
        assert isinstance(data["total"], int)

    def test_alert_entries_have_expected_fields(self):
        resp = client.get("/api/dashboard/alerts", headers=_admin_headers())
        assert resp.status_code == 200
        alerts = resp.json()["alerts"]
        if len(alerts) > 0:
            alert = alerts[0]
            expected_fields = [
                "id",
                "metric_type",
                "message",
                "severity",
                "triggered_at",
                "acknowledged",
            ]
            for field in expected_fields:
                assert field in alert, f"Alert missing field: {field}"

    def test_alerts_without_auth_returns_401(self):
        resp = client.get("/api/dashboard/alerts")
        assert resp.status_code == 401

    def test_viewer_can_read_alerts(self):
        resp = client.get("/api/dashboard/alerts", headers=_viewer_headers())
        assert resp.status_code == 200


class TestOperationsSummary:
    """GET /api/dashboard/operations-summary"""

    def test_returns_200_with_summary(self):
        resp = client.get(
            "/api/dashboard/operations-summary",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "clusters" in data
        assert "org_id" in data
        assert "period" in data
        assert "updated_at" in data

    def test_clusters_have_required_fields(self):
        resp = client.get(
            "/api/dashboard/operations-summary",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        clusters = resp.json()["clusters"]
        assert len(clusters) >= 1
        for _cluster_key, cluster in clusters.items():
            assert "value" in cluster
            assert "unit" in cluster
            assert "confidence" in cluster
            assert "hash" in cluster
            assert "chain_valid" in cluster
