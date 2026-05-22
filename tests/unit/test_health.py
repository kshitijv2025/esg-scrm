"""
Tests for the enhanced health check endpoint.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def client():
    """Build a test client for the health router."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.api.routes.health import router

    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


class TestHealthEndpoint:
    """Test suite for GET /api/health."""

    def test_health_returns_all_components(self, client):
        """Health response must include database, redis, mqtt, and disk."""
        with (
            patch("src.api.routes.health._check_database") as mock_db,
            patch("src.api.routes.health._check_redis") as mock_redis,
            patch("src.api.routes.health._check_mqtt") as mock_mqtt,
            patch("src.api.routes.health._check_disk") as mock_disk,
        ):
            mock_db.return_value = {"status": "up", "latency_ms": 5.0}
            mock_redis.return_value = {"status": "up", "latency_ms": 1.0}
            mock_mqtt.return_value = {"status": "up", "latency_ms": 12.0}
            mock_disk.return_value = {"status": "ok", "free_gb": 45.2}

            response = client.get("/api/health")
            assert response.status_code == 200

            data = response.json()
            assert "status" in data
            assert "components" in data
            assert "version" in data

            components = data["components"]
            assert "database" in components
            assert "redis" in components
            assert "mqtt" in components
            assert "disk" in components

    def test_health_returns_200_when_all_healthy(self, client):
        """HTTP 200 when every component is up or ok."""
        with (
            patch("src.api.routes.health._check_database") as mock_db,
            patch("src.api.routes.health._check_redis") as mock_redis,
            patch("src.api.routes.health._check_mqtt") as mock_mqtt,
            patch("src.api.routes.health._check_disk") as mock_disk,
        ):
            mock_db.return_value = {"status": "up", "latency_ms": 5.0}
            mock_redis.return_value = {"status": "up", "latency_ms": 1.0}
            mock_mqtt.return_value = {"status": "up", "latency_ms": 12.0}
            mock_disk.return_value = {"status": "ok", "free_gb": 45.2}

            response = client.get("/api/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    def test_health_returns_degraded_when_database_down(self, client):
        """Overall status is degraded when database is down."""
        with (
            patch("src.api.routes.health._check_database") as mock_db,
            patch("src.api.routes.health._check_redis") as mock_redis,
            patch("src.api.routes.health._check_mqtt") as mock_mqtt,
            patch("src.api.routes.health._check_disk") as mock_disk,
        ):
            mock_db.return_value = {"status": "down", "error": "connection refused"}
            mock_redis.return_value = {"status": "up", "latency_ms": 1.0}
            mock_mqtt.return_value = {"status": "up", "latency_ms": 12.0}
            mock_disk.return_value = {"status": "ok", "free_gb": 45.2}

            response = client.get("/api/health")
            assert response.status_code == 200
            assert response.json()["status"] == "degraded"
            assert response.json()["components"]["database"]["status"] == "down"

    def test_health_returns_degraded_when_redis_down(self, client):
        """Overall status is degraded when Redis is down."""
        with (
            patch("src.api.routes.health._check_database") as mock_db,
            patch("src.api.routes.health._check_redis") as mock_redis,
            patch("src.api.routes.health._check_mqtt") as mock_mqtt,
            patch("src.api.routes.health._check_disk") as mock_disk,
        ):
            mock_db.return_value = {"status": "up", "latency_ms": 5.0}
            mock_redis.return_value = {"status": "down", "error": "connection refused"}
            mock_mqtt.return_value = {"status": "up", "latency_ms": 12.0}
            mock_disk.return_value = {"status": "ok", "free_gb": 45.2}

            response = client.get("/api/health")
            assert response.status_code == 200
            assert response.json()["status"] == "degraded"
            assert response.json()["components"]["redis"]["status"] == "down"

    def test_health_returns_degraded_when_mqtt_down(self, client):
        """Overall status is degraded when MQTT/EMQX is down."""
        with (
            patch("src.api.routes.health._check_database") as mock_db,
            patch("src.api.routes.health._check_redis") as mock_redis,
            patch("src.api.routes.health._check_mqtt") as mock_mqtt,
            patch("src.api.routes.health._check_disk") as mock_disk,
        ):
            mock_db.return_value = {"status": "up", "latency_ms": 5.0}
            mock_redis.return_value = {"status": "up", "latency_ms": 1.0}
            mock_mqtt.return_value = {"status": "down", "error": "EMQX unreachable"}
            mock_disk.return_value = {"status": "ok", "free_gb": 45.2}

            response = client.get("/api/health")
            assert response.status_code == 200
            assert response.json()["status"] == "degraded"
            assert response.json()["components"]["mqtt"]["status"] == "down"

    def test_health_returns_degraded_when_disk_low(self, client):
        """Overall status is degraded when disk space is critically low."""
        with (
            patch("src.api.routes.health._check_database") as mock_db,
            patch("src.api.routes.health._check_redis") as mock_redis,
            patch("src.api.routes.health._check_mqtt") as mock_mqtt,
            patch("src.api.routes.health._check_disk") as mock_disk,
        ):
            mock_db.return_value = {"status": "up", "latency_ms": 5.0}
            mock_redis.return_value = {"status": "up", "latency_ms": 1.0}
            mock_mqtt.return_value = {"status": "up", "latency_ms": 12.0}
            mock_disk.return_value = {
                "status": "low",
                "free_gb": 0.5,
                "error": "disk space critically low",
            }

            response = client.get("/api/health")
            assert response.status_code == 200
            assert response.json()["status"] == "degraded"
            assert response.json()["components"]["disk"]["status"] == "low"

    def test_health_includes_latency_for_up_components(self, client):
        """Up components must include latency_ms in the response."""
        with (
            patch("src.api.routes.health._check_database") as mock_db,
            patch("src.api.routes.health._check_redis") as mock_redis,
            patch("src.api.routes.health._check_mqtt") as mock_mqtt,
            patch("src.api.routes.health._check_disk") as mock_disk,
        ):
            mock_db.return_value = {"status": "up", "latency_ms": 5.0}
            mock_redis.return_value = {"status": "up", "latency_ms": 1.0}
            mock_mqtt.return_value = {"status": "up", "latency_ms": 12.0}
            mock_disk.return_value = {"status": "ok", "free_gb": 45.2}

            response = client.get("/api/health")
            data = response.json()

            assert "latency_ms" in data["components"]["database"]
            assert "latency_ms" in data["components"]["redis"]
            assert "latency_ms" in data["components"]["mqtt"]
            assert data["components"]["database"]["latency_ms"] == 5.0


class TestDatabaseCheck:
    """Unit tests for _check_database helper."""

    def test_database_check_postgres_returns_up_on_success(self):
        """SELECT 1 succeeds against PostgreSQL."""
        from src.api.routes.health import _check_database

        with (
            patch.dict(
                "os.environ", {"DATABASE_URL": "postgresql://esg:esg@localhost:5432/esgscrm"}
            ),
            patch("psycopg2.connect") as mock_connect,
        ):
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            result = _check_database()
            assert result["status"] == "up"
            assert "latency_ms" in result

    def test_database_check_returns_down_on_failure(self):
        """Connection failure returns down with error."""
        from src.api.routes.health import _check_database

        with (
            patch.dict(
                "os.environ", {"DATABASE_URL": "postgresql://esg:esg@localhost:5432/esgscrm"}
            ),
            patch("psycopg2.connect") as mock_connect,
        ):
            mock_connect.side_effect = Exception("connection refused")
            result = _check_database()
            assert result["status"] == "down"
            assert "error" in result


class TestRedisCheck:
    """Unit tests for _check_redis helper."""

    def test_redis_check_returns_up_on_success(self):
        """Redis ping succeeds."""
        from src.api.routes.health import _check_redis

        mock_redis_module = MagicMock()
        mock_client = MagicMock()
        mock_redis_module.from_url.return_value = mock_client

        with patch.dict("sys.modules", {"redis": mock_redis_module}):
            result = _check_redis()
            assert result["status"] == "up"
            assert "latency_ms" in result

    def test_redis_check_returns_down_on_failure(self):
        """Redis connection failure returns down."""
        from src.api.routes.health import _check_redis

        mock_redis_module = MagicMock()
        mock_redis_module.from_url.side_effect = Exception("connection refused")

        with patch.dict("sys.modules", {"redis": mock_redis_module}):
            result = _check_redis()
            assert result["status"] == "down"
            assert "error" in result


class TestMqttCheck:
    """Unit tests for _check_mqtt helper."""

    def test_mqtt_check_returns_up_on_200(self):
        """EMQX health endpoint returns 200."""
        from src.api.routes.health import _check_mqtt

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response
            result = _check_mqtt()
            assert result["status"] == "up"
            assert "latency_ms" in result

    def test_mqtt_check_returns_down_on_error(self):
        """EMQX unreachable returns down."""
        from src.api.routes.health import _check_mqtt

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("connection refused")
            result = _check_mqtt()
            assert result["status"] == "down"
            assert "error" in result


class TestDiskCheck:
    """Unit tests for _check_disk helper."""

    def test_disk_check_returns_ok_with_sufficient_space(self):
        """Disk with >1GB free returns ok."""
        from src.api.routes.health import _check_disk

        with patch("src.api.routes.health.shutil") as mock_shutil:
            mock_usage = MagicMock()
            mock_usage.free = 50 * 1024**3  # 50 GB
            mock_shutil.disk_usage.return_value = mock_usage
            result = _check_disk()
            assert result["status"] == "ok"
            assert "free_gb" in result

    def test_disk_check_returns_low_when_below_1gb(self):
        """Disk with <1GB free returns low status."""
        from src.api.routes.health import _check_disk

        with patch("src.api.routes.health.shutil") as mock_shutil:
            mock_usage = MagicMock()
            mock_usage.free = 512 * 1024**2  # 512 MB
            mock_shutil.disk_usage.return_value = mock_usage
            result = _check_disk()
            assert result["status"] == "low"
            assert "error" in result
