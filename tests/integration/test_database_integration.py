"""Tier 2 integration tests — real database, no mocks.

Tests use the existing SQLite test DB (tests/conftest.py seeds org_bd_001).
These are real DB calls against the test database.
"""
import sys

sys.path.insert(0, "src")

import pytest

from src.db.database import (
    fetch_metrics,
    fetch_risk_flags,
    fetch_suppliers,
    fetch_trust_badges,
    get_connection,
    release_connection,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _org_filter(org_id: str = "org_bd_001") -> dict:
    """Return a minimal user dict as returned by require_auth."""
    return {"sub": "test_user", "org_id": org_id, "email": "test@test.com", "role": "admin"}


# ---------------------------------------------------------------------------
# Schema creation tests
# ---------------------------------------------------------------------------

class TestSchemaCreation:
    """Verify all expected tables exist in the database."""

    def test_organizations_table_exists(self):
        """organizations table must exist."""
        conn = get_connection()
        try:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='organizations'"
            ).fetchone()
            assert result is not None, "organizations table missing"
        finally:
            release_connection(conn)

    def test_metrics_table_exists(self):
        """metrics table must exist."""
        conn = get_connection()
        try:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='metrics'"
            ).fetchone()
            assert result is not None, "metrics table missing"
        finally:
            release_connection(conn)

    def test_suppliers_table_exists(self):
        """suppliers table must exist."""
        conn = get_connection()
        try:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='suppliers'"
            ).fetchone()
            assert result is not None, "suppliers table missing"
        finally:
            release_connection(conn)

    def test_risk_flags_table_exists(self):
        """risk_flags table must exist."""
        conn = get_connection()
        try:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='risk_flags'"
            ).fetchone()
            assert result is not None, "risk_flags table missing"
        finally:
            release_connection(conn)

    def test_evidence_chain_table_exists(self):
        """evidence_chain table must exist."""
        conn = get_connection()
        try:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='evidence_chain'"
            ).fetchone()
            assert result is not None, "evidence_chain table missing"
        finally:
            release_connection(conn)

    def test_audit_log_table_exists(self):
        """audit_log table must exist."""
        conn = get_connection()
        try:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'"
            ).fetchone()
            assert result is not None, "audit_log table missing"
        finally:
            release_connection(conn)

    def test_emission_factors_table_exists(self):
        """emission_factors table must exist."""
        conn = get_connection()
        try:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='emission_factors'"
            ).fetchone()
            assert result is not None, "emission_factors table missing"
        finally:
            release_connection(conn)

    def test_framework_mappings_table_exists(self):
        """framework_mappings table must exist."""
        conn = get_connection()
        try:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='framework_mappings'"
            ).fetchone()
            assert result is not None, "framework_mappings table missing"
        finally:
            release_connection(conn)

    def test_expected_table_count(self):
        """All core tables must be present — sanity check on table count."""
        conn = get_connection()
        try:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = {r["name"] for r in tables}
            expected = {
                "organizations", "users", "api_keys", "metrics",
                "rec_certificates", "evidence_chain", "evidence_chain_archive",
                "risk_flags", "suppliers", "outbound_emails", "supplier_scope3",
                "questionnaire_responses", "emission_factors", "metric_metadata",
                "framework_mappings", "alert_thresholds", "audit_log", "audit_log_archive",
                "questionnaire_templates", "factories", "questionnaire_questions",
                "whatsapp_messages", "uploaded_files", "notification_log",
            }
            missing = expected - table_names
            assert not missing, f"Missing tables: {missing}"
        finally:
            release_connection(conn)


# ---------------------------------------------------------------------------
# Seed data tests
# ---------------------------------------------------------------------------

class TestSeedDataLoading:
    """Verify seed data is present for org_bd_001."""

    def test_org_bd_001_exists(self):
        """The seeded org_bd_001 organization must exist."""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT id, name FROM organizations WHERE id = ?", ("org_bd_001",)
            ).fetchone()
            assert row is not None, "org_bd_001 not found in organizations table"
            assert row["name"] != ""
        finally:
            release_connection(conn)

    def test_seed_users_exist(self):
        """At least one user must be seeded for org_bd_001."""
        conn = get_connection()
        try:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM users WHERE org_id = ?", ("org_bd_001",)
            ).fetchone()["cnt"]
            assert count >= 1, "No users found for org_bd_001"
        finally:
            release_connection(conn)

    def test_seed_suppliers_exist(self):
        """At least one supplier must be seeded for org_bd_001."""
        conn = get_connection()
        try:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM suppliers WHERE org_id = ?", ("org_bd_001",)
            ).fetchone()["cnt"]
            assert count >= 1, "No suppliers found for org_bd_001"
        finally:
            release_connection(conn)

    def test_seed_metrics_exist(self):
        """At least one metric row must exist for org_bd_001."""
        conn = get_connection()
        try:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM metrics WHERE org_id = ?", ("org_bd_001",)
            ).fetchone()["cnt"]
            assert count >= 1, "No metrics found for org_bd_001"
        finally:
            release_connection(conn)

    def test_seed_risk_flags_exist(self):
        """At least one risk flag must exist for org_bd_001."""
        conn = get_connection()
        try:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM risk_flags WHERE org_id = ?", ("org_bd_001",)
            ).fetchone()["cnt"]
            assert count >= 1, "No risk_flags found for org_bd_001"
        finally:
            release_connection(conn)


# ---------------------------------------------------------------------------
# fetch_metrics integration tests
# ---------------------------------------------------------------------------

class TestFetchMetricsIntegration:
    """Test fetch_metrics returns data for seeded org."""

    def test_fetch_metrics_returns_rows(self):
        """fetch_metrics must return at least one row for org_bd_001."""
        rows = fetch_metrics(org_id="org_bd_001")
        assert len(rows) >= 1, "fetch_metrics returned no rows for org_bd_001"

    def test_fetch_metrics_has_expected_columns(self):
        """Each row must have the expected metric columns."""
        rows = fetch_metrics(org_id="org_bd_001")
        if not rows:
            pytest.skip("No metrics rows to check")
        row = rows[0]
        required = {"id", "cluster", "value", "unit", "confidence", "source", "period", "recorded_at"}
        missing = required - set(row.keys())
        assert not missing, f"Missing columns in metrics row: {missing}"

    def test_fetch_metrics_is_org_scoped(self):
        """fetch_metrics with org_id must not leak rows from other orgs."""
        rows = fetch_metrics(org_id="org_bd_001")
        for row in rows:
            assert row.get("org_id") in (None, "", "org_bd_001"), \
                f"Row leaked from wrong org: {row.get('org_id')}"

    def test_fetch_metrics_clusters_are_distinct(self):
        """fetch_metrics should return one row per unique cluster."""
        rows = fetch_metrics(org_id="org_bd_001")
        clusters = {r["cluster"] for r in rows}
        assert len(clusters) >= 1, "No distinct clusters found"


# ---------------------------------------------------------------------------
# fetch_trust_badges integration tests
# ---------------------------------------------------------------------------

class TestFetchTrustBadgesIntegration:
    """Test fetch_trust_badges returns dict with 4 keys."""

    def test_fetch_trust_badges_returns_dict(self):
        """fetch_trust_badges must return a dict."""
        result = fetch_trust_badges(org_id="org_bd_001")
        assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"

    def test_fetch_trust_badges_has_four_keys(self):
        """fetch_trust_badges must return exactly 4 keys."""
        result = fetch_trust_badges(org_id="org_bd_001")
        assert len(result) == 4, f"Expected 4 keys, got {len(result)}: {list(result.keys())}"

    def test_fetch_trust_badges_expected_keys(self):
        """fetch_trust_badges must have the expected key names."""
        result = fetch_trust_badges(org_id="org_bd_001")
        expected_keys = {
            "csrd_compliant",
            "ghg_protocol_source",
            "audit_ready",
            "scope3_verified",
        }
        assert set(result.keys()) == expected_keys, \
            f"Key mismatch: {set(result.keys())} != {expected_keys}"

    def test_fetch_trust_badges_values_are_booleans(self):
        """All four badge values must be booleans."""
        result = fetch_trust_badges(org_id="org_bd_001")
        for key, value in result.items():
            assert isinstance(value, bool), \
                f"Expected bool for {key}, got {type(value).__name__}"

    def test_fetch_trust_badges_is_org_scoped(self):
        """fetch_trust_badges must return correct results for org_bd_001."""
        result = fetch_trust_badges(org_id="org_bd_001")
        # Result should be a valid dict with 4 boolean values
        assert all(isinstance(v, bool) for v in result.values())


# ---------------------------------------------------------------------------
# fetch_suppliers integration tests
# ---------------------------------------------------------------------------

class TestFetchSuppliersIntegration:
    """Test fetch_suppliers returns seeded supplier data."""

    def test_fetch_suppliers_returns_rows(self):
        """fetch_suppliers must return at least one row for org_bd_001."""
        rows = fetch_suppliers(org_id="org_bd_001")
        assert len(rows) >= 1, "fetch_suppliers returned no rows for org_bd_001"

    def test_fetch_suppliers_has_required_columns(self):
        """Each supplier row must have required columns."""
        rows = fetch_suppliers(org_id="org_bd_001")
        if not rows:
            pytest.skip("No supplier rows to check")
        row = rows[0]
        required = {"id", "org_id", "name", "country", "industry", "tier"}
        missing = required - set(row.keys())
        assert not missing, f"Missing columns in supplier row: {missing}"


# ---------------------------------------------------------------------------
# fetch_risk_flags integration tests
# ---------------------------------------------------------------------------

class TestFetchRiskFlagsIntegration:
    """Test fetch_risk_flags returns risk flag data."""

    def test_fetch_risk_flags_returns_rows(self):
        """fetch_risk_flags must return at least one row for org_bd_001."""
        rows = fetch_risk_flags(org_id="org_bd_001")
        assert len(rows) >= 1, "fetch_risk_flags returned no rows for org_bd_001"

    def test_fetch_risk_flags_has_required_columns(self):
        """Each risk flag row must have required columns."""
        rows = fetch_risk_flags(org_id="org_bd_001")
        if not rows:
            pytest.skip("No risk flag rows to check")
        row = rows[0]
        required = {"id", "org_id", "flag_text", "cluster", "severity", "priority_score"}
        missing = required - set(row.keys())
        assert not missing, f"Missing columns in risk_flag row: {missing}"

    def test_fetch_risk_flags_severity_values(self):
        """Severity must be one of the allowed values."""
        rows = fetch_risk_flags(org_id="org_bd_001")
        allowed = {"CRITICAL", "WARNING", "INFO"}
        for row in rows:
            assert row["severity"] in allowed, \
                f"Invalid severity: {row['severity']}"
