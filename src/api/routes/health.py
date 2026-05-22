"""
Enhanced health check — validates all infrastructure components.
"""

import logging
import os
import shutil
import time
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


def _check_database() -> dict[str, Any]:
    """Run SELECT 1 against PostgreSQL and measure latency."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return {"status": "down", "error": "DATABASE_URL not set"}

    is_postgres = db_url.startswith("postgresql://") or db_url.startswith("postgres://")

    start = time.perf_counter()
    try:
        if is_postgres:
            import psycopg2

            conn = psycopg2.connect(db_url)
            conn.execute("SELECT 1")
            conn.close()
        else:
            from src.db.database import get_connection, release_connection

            conn = get_connection()
            conn.execute("SELECT 1")
            release_connection(conn)
        latency_ms = (time.perf_counter() - start) * 1000
        return {"status": "up", "latency_ms": round(latency_ms, 2)}
    except Exception as e:
        logger.warning("health.database.error error=%s", e)
        return {"status": "down", "error": str(e)}


def _check_redis() -> dict[str, Any]:
    """Ping Redis and measure latency."""
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    start = time.perf_counter()
    try:
        import redis

        client = redis.from_url(redis_url, socket_connect_timeout=5)
        client.ping()
        latency_ms = (time.perf_counter() - start) * 1000
        client.close()
        return {"status": "up", "latency_ms": round(latency_ms, 2)}
    except Exception as e:
        logger.warning("health.redis.error error=%s", e)
        return {"status": "down", "error": str(e)}


def _check_mqtt() -> dict[str, Any]:
    """Check EMQX API health endpoint and measure latency."""
    emqx_host = os.environ.get("EMQX_HOST", "emqx")
    emqx_port = os.environ.get("EMQX_PORT", "18083")
    url = f"http://{emqx_host}:{emqx_port}/api/v5/health"
    start = time.perf_counter()
    try:
        import urllib.request

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
            latency_ms = (time.perf_counter() - start) * 1000
            if resp.status == 200:
                return {"status": "up", "latency_ms": round(latency_ms, 2)}
            return {"status": "down", "error": f"HTTP {resp.status}"}
    except Exception as e:
        logger.warning("health.mqtt.error error=%s", e)
        return {"status": "down", "error": str(e)}


def _check_disk() -> dict[str, Any]:
    """Check available disk space."""
    try:
        usage = shutil.disk_usage("/")
        free_gb = round(usage.free / (1024**3), 2)
        # Warn if free space is below 1GB
        if usage.free < 1024**3:
            return {"status": "low", "free_gb": free_gb, "error": "disk space critically low"}
        return {"status": "ok", "free_gb": free_gb}
    except Exception as e:
        logger.warning("health.disk.error error=%s", e)
        return {"status": "unknown", "error": str(e)}


@router.get("/health")
def health_check() -> dict[str, Any]:
    """
    Comprehensive health check covering all infrastructure components.

    Returns:
        JSON with overall status and per-component details including latency.
    """
    database = _check_database()
    redis = _check_redis()
    mqtt = _check_mqtt()
    disk = _check_disk()

    components = {
        "database": database,
        "redis": redis,
        "mqtt": mqtt,
        "disk": disk,
    }

    # Overall status is degraded if any component is not "up" or "ok"
    all_healthy = all(c.get("status") in ("up", "ok") for c in components.values())
    overall = "healthy" if all_healthy else "degraded"

    from src.api.main import app

    version = getattr(app, "version", "0.1.0")

    return {
        "status": overall,
        "components": components,
        "version": version,
    }
