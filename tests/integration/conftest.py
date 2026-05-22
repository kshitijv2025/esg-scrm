"""Integration test fixtures — seeds the real database before tests."""

import logging
import os
import sys

sys.path.insert(0, "src")

import pytest

from src.db.database import get_connection, is_postgres, release_connection, reset_database
from src.db.seed import seed

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def _seed_database():
    """Reset and re-seed the database before each integration test.

    Uses PostgreSQL when DATABASE_URL starts with postgresql:// (CI/production).
    Falls back to SQLite for local dev only — this is a TEST-INFRA GAP
    that must be fixed by provisioning a test PostgreSQL instance.
    The fallback logs a warning so it's visible in CI output.
    """
    db_is_postgres = is_postgres()
    if db_is_postgres:
        logger.info("integration_tests_using_postgresql mode=postgres")
    else:
        logger.warning(
            "integration_tests_using_sqlite_fallback mode=sqlite "
            "detail=TEST-INFRA-GAP-Set-DATABASE_URL-postgresql-for-CI "
            "DATABASE_URL=%s",
            os.environ.get("DATABASE_URL", "(not set)"),
        )
    reset_database()  # drops and recreates clean schema
    seed()  # loads org_bd_001 seed data
    yield
    # No teardown — leave the DB as-is for post-test inspection
    release_connection(get_connection())
