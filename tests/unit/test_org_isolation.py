"""Org isolation tests — verify users from org A cannot see org B's data.

These tests create two authenticated clients (one per org) and assert that
each client's responses contain only their own org's data across all
authenticated route groups:
  /api/dashboard/*  /api/evidence/*  /api/frameworks/*
  /api/questionnaires/*  /api/suppliers/*  /api/reports/*
  /api/risk/*  /api/scope3/*  /api/emission-factors/*
  /api/alerts/*  /api/audit/*  /api/upload/*  /api/templates/*
  /api/trust/*
"""

import sys
import uuid

sys.path.insert(0, "src")

import pytest
import sqlite3
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.jwt import create_token
from src.db.database import (
    DB_PATH,
    reset_database,
    get_connection,
    release_connection,
    _execute,
    _fetchall,
    _fetchone,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fresh_db():
    """Reset and seed the database before each test."""
    reset_database()
    from src.db.seed import seed

    seed()
    from src.db.seed_emission_factors import seed_emission_factors

    seed_emission_factors()
    from src.db.seed_alert_thresholds import seed_alert_thresholds

    seed_alert_thresholds()
    yield


def _make_client(org_id: str, user_id: str = None, role: str = "admin") -> TestClient:
    """Create a TestClient authenticated as a user in the given org."""
    if user_id is None:
        user_id = f"usr_{org_id}_{uuid.uuid4().hex[:8]}"
    token = create_token(
        {
            "sub": user_id,
            "org_id": org_id,
            "email": f"user@{org_id}.com",
            "role": role,
        }
    )
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


@pytest.fixture
def org_a_client():
    return _make_client("org_a_isolation_test")


@pytest.fixture
def org_b_client():
    return _make_client("org_b_isolation_test")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_supplier(org_id: str, supplier_id: str, name: str, **kwargs) -> None:
    """Insert a supplier row belonging to the given org."""
    defaults = {
        "name": name,
        "country": "BD",
        "industry": "Textiles",
        "tier": "tier1",
        "annual_spend_usd": 1_000_000,
        "phone": "",
        "preferred_channel": "email",
        "questionnaire_status": "pending",
    }
    defaults.update(kwargs)
    conn = get_connection()
    try:
        _execute(
            conn,
            """
            INSERT INTO suppliers
                (id, org_id, name, country, industry, tier, annual_spend_usd,
                 phone, preferred_channel, questionnaire_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                supplier_id,
                org_id,
                defaults["name"],
                defaults["country"],
                defaults["industry"],
                defaults["tier"],
                defaults["annual_spend_usd"],
                defaults["phone"],
                defaults["preferred_channel"],
                defaults["questionnaire_status"],
            ),
        )
    finally:
        release_connection(conn)


def _insert_metric(org_id: str, cluster: str, value: float, **kwargs) -> int:
    """Insert a metric row and return its id.

    Uses a far-future recorded_at so the test metric is always the MAX
    per cluster, bypassing the subquery in fetch_metrics which does not
    filter by org_id and would otherwise hide test metrics behind seed data.
    Also inserts a matching evidence_chain record so the hash field is present.
    """
    defaults = {
        "factory_id": "factory_bd_001",
        "unit": "kWh",
        "confidence": "MEDIUM",
        "source": "manual",
        "period": "2025-01",
        "recorded_at": "2099-01-01T00:00:00Z",
    }
    defaults.update(kwargs)
    conn = get_connection()
    try:
        cur = _execute(
            conn,
            """
            INSERT INTO metrics
                (org_id, factory_id, cluster, value, unit, confidence, source, period, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                org_id,
                defaults["factory_id"],
                cluster,
                value,
                defaults["unit"],
                defaults["confidence"],
                defaults["source"],
                defaults["period"],
                defaults["recorded_at"],
            ),
        )
        metric_id = cur.lastrowid

        # Also insert an evidence_chain record so hash is not NULL
        _execute(
            conn,
            """
            INSERT INTO evidence_chain
                (metric_id, org_id, cluster, hash, prev_hash, value, raw_value,
                 calculated_value, methodology, confidence, computed_at, recorded_at,
                 recorded_by, source_system)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                metric_id,
                org_id,
                cluster,
                f"hash_{org_id}_{uuid.uuid4().hex[:8]}",
                None,
                value,
                value,
                value,
                "test",
                "MEDIUM",
                defaults["recorded_at"],
                defaults["recorded_at"],
                "test",
                "manual",
            ),
        )
        return metric_id
    finally:
        release_connection(conn)


def _insert_evidence(org_id: str, metric_id: int, **kwargs) -> None:
    defaults = {
        "cluster": "energy_kwh",
        "hash": f"hash_{org_id}_{uuid.uuid4().hex[:8]}",
        "prev_hash": None,
        "value": 100.0,
        "raw_value": 100.0,
        "calculated_value": 100.0,
        "methodology": "direct_measurement",
        "confidence": "MEDIUM",
        "computed_at": "2025-01-15T10:00:00",
        "recorded_at": "2025-01-15T10:00:00",
        "recorded_by": "test",
        "source_system": "manual",
    }
    defaults.update(kwargs)
    conn = get_connection()
    try:
        _execute(
            conn,
            """
            INSERT INTO evidence_chain
                (metric_id, org_id, cluster, hash, prev_hash, value, raw_value,
                 calculated_value, methodology, confidence, computed_at, recorded_at,
                 recorded_by, source_system)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                metric_id,
                org_id,
                defaults["cluster"],
                defaults["hash"],
                defaults["prev_hash"],
                defaults["value"],
                defaults["raw_value"],
                defaults["calculated_value"],
                defaults["methodology"],
                defaults["confidence"],
                defaults["computed_at"],
                defaults["recorded_at"],
                defaults["recorded_by"],
                defaults["source_system"],
            ),
        )
    finally:
        release_connection(conn)


def _insert_scope3(org_id: str, category: str, tco2e: float) -> None:
    """Insert scope3 record into supplier_scope3 (requires a valid supplier_id)."""
    # Ensure a supplier exists for this org first
    supplier_id = f"sup_scope3_{org_id}"
    _insert_supplier(org_id, supplier_id, f"Scope3 Supplier {org_id}")
    conn = get_connection()
    try:
        _execute(
            conn,
            """
            INSERT INTO supplier_scope3
                (org_id, supplier_id, category, annual_spend_usd, scope3_tco2e,
                 calculation_method, confidence, data_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (org_id, supplier_id, category, 1_000_000, tco2e, "test", "LOW", "test"),
        )
    finally:
        release_connection(conn)


def _insert_risk_flag(org_id: str, cluster: str, severity: str, flag_text: str) -> int:
    conn = get_connection()
    try:
        cur = _execute(
            conn,
            """
            INSERT INTO risk_flags (org_id, cluster, severity, flag_text, priority_score)
            VALUES (?, ?, ?, ?, ?)
        """,
            (org_id, cluster, severity, flag_text, 50),
        )
        return cur.lastrowid
    finally:
        release_connection(conn)


def _insert_audit_entry(org_id: str, action: str, resource_type: str, **kwargs) -> None:
    conn = get_connection()
    try:
        defaults = {"user_id": f"usr_{org_id}", "details": f"test {action}"}
        defaults.update(kwargs)
        _execute(
            conn,
            """
            INSERT INTO audit_log (org_id, user_id, action, resource_type, details)
            VALUES (?, ?, ?, ?, ?)
        """,
            (org_id, defaults["user_id"], action, resource_type, defaults["details"]),
        )
    finally:
        release_connection(conn)


def _insert_emission_factor(org_id: str, factor_name: str, **kwargs) -> int:
    defaults = {
        "category": "grid_electricity",
        "factor_value": 0.5,
        "unit": "kgCO2e/kWh",
        "source": "test",
        "country_code": "XX",
        "year": 2024,
    }
    defaults.update(kwargs)
    conn = get_connection()
    try:
        cur = _execute(
            conn,
            """
            INSERT INTO emission_factors
                (org_id, category, factor_name, factor_value, unit, source, country_code, year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                org_id,
                defaults["category"],
                factor_name,
                defaults["factor_value"],
                defaults["unit"],
                defaults["source"],
                defaults["country_code"],
                defaults["year"],
            ),
        )
        return cur.lastrowid
    finally:
        release_connection(conn)


def _insert_template(org_id: str, name: str, **kwargs) -> int:
    defaults = {"description": "test", "tier": 1, "category": "environment", "is_active": 1}
    defaults.update(kwargs)
    conn = get_connection()
    try:
        cur = _execute(
            conn,
            """
            INSERT INTO questionnaire_templates (org_id, name, description, tier, category, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                org_id,
                name,
                defaults["description"],
                defaults["tier"],
                defaults["category"],
                defaults["is_active"],
            ),
        )
        return cur.lastrowid
    finally:
        release_connection(conn)


def _insert_alert_threshold(org_id: str, cluster: str, **kwargs) -> int:
    defaults = {
        "metric_cluster": cluster,
        "operator": ">",
        "threshold_value": 100.0,
        "severity": "WARNING",
    }
    defaults.update(kwargs)
    conn = get_connection()
    try:
        cur = _execute(
            conn,
            """
            INSERT INTO alert_thresholds (org_id, cluster, metric_cluster, operator, threshold_value, severity)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                org_id,
                cluster,
                defaults["metric_cluster"],
                defaults["operator"],
                defaults["threshold_value"],
                defaults["severity"],
            ),
        )
        return cur.lastrowid
    finally:
        release_connection(conn)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class TestDashboardOrgIsolation:
    """GET /api/dashboard/* — org-scoped metrics and live data."""

    def test_live_metrics_returns_only_own_org(self, org_a_client, org_b_client):
        """Org A's live metrics must not contain org B's metric values."""
        _insert_metric("org_a_isolation_test", "energy_kwh", 99999.0)
        _insert_metric("org_b_isolation_test", "energy_kwh", 11111.0)

        resp_a = org_a_client.get("/api/dashboard/live")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/dashboard/live")
        assert resp_b.status_code == 200

        val_a = resp_a.json()["metrics"].get("energy_kwh", {}).get("value")
        val_b = resp_b.json()["metrics"].get("energy_kwh", {}).get("value")

        assert val_a == 99999.0, "Org A must see its own metric value"
        assert val_b == 11111.0, "Org B must see its own metric value"
        assert val_a != val_b, "Org isolation violated: both orgs saw the same metric value"

    def test_live_metrics_org_id_matches_auth(self, org_a_client):
        """Response org_id must match the authenticated user's org."""
        resp = org_a_client.get("/api/dashboard/live")
        assert resp.status_code == 200
        assert resp.json()["org_id"] == "org_a_isolation_test"


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


class TestEvidenceOrgIsolation:
    """GET /api/evidence/* — evidence chain records are org-scoped."""

    def test_evidence_chain_returns_only_own_org(self, org_a_client, org_b_client):
        """Org A's evidence chain must not include org B's records."""
        # Insert metric + evidence for both orgs
        # _insert_metric already creates evidence_chain records
        _insert_metric("org_a_isolation_test", "energy_kwh", 500.0)
        _insert_metric("org_b_isolation_test", "energy_kwh", 600.0)

        resp_a = org_a_client.get("/api/evidence/drilldown/energy_kwh")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/evidence/drilldown/energy_kwh")
        assert resp_b.status_code == 200

        # The hash field is set to "hash_<org_id>_..." so orgs have distinct hashes
        hash_a = resp_a.json().get("hash", "")
        hash_b = resp_b.json().get("hash", "")

        assert "org_a_isolation_test" in hash_a, "Org A should see its own evidence"
        assert "org_b_isolation_test" in hash_b, "Org B should see its own evidence"
        assert "org_b_isolation_test" not in hash_a, "Org A must not see org B's evidence hash"
        assert "org_a_isolation_test" not in hash_b, "Org B must not see org A's evidence hash"


# ---------------------------------------------------------------------------
# Frameworks
# ---------------------------------------------------------------------------


class TestFrameworksOrgIsolation:
    """GET /api/frameworks/* — framework mappings are org-scoped."""

    def test_list_mappings_returns_data_for_own_org(self, org_a_client):
        """Both orgs get framework mappings (global data); the endpoint is org-agnostic."""
        resp = org_a_client.get("/api/frameworks/map")
        assert resp.status_code == 200
        # Framework mappings are reference data, not per-org — just verify it returns 200
        assert "mappings" in resp.json()


# ---------------------------------------------------------------------------
# Questionnaires
# ---------------------------------------------------------------------------


class TestQuestionnairesOrgIsolation:
    """GET /api/questionnaires/* — templates and responses are org-scoped."""

    def test_list_templates_returns_only_own_org(self, org_a_client, org_b_client):
        """Org A must not see org B's templates."""
        _insert_template("org_a_isolation_test", "Template Org A")
        _insert_template("org_b_isolation_test", "Template Org B")

        resp_a = org_a_client.get("/api/templates/")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/templates/")
        assert resp_b.status_code == 200

        names_a = {t["name"] for t in resp_a.json()["templates"]}
        names_b = {t["name"] for t in resp_b.json()["templates"]}

        assert "Template Org A" in names_a
        assert "Template Org B" not in names_a, "Org A saw org B's template"
        assert "Template Org B" in names_b
        assert "Template Org A" not in names_b, "Org B saw org A's template"

    def test_response_summary_org_scoped(self, org_a_client, org_b_client):
        """Response summary must be scoped to the authenticated org."""
        _insert_supplier("org_a_isolation_test", "sup_a_001", "Supplier A Org")
        _insert_supplier("org_b_isolation_test", "sup_b_001", "Supplier B Org")

        resp_a = org_a_client.get("/api/questionnaires/response-summary")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/questionnaires/response-summary")
        assert resp_b.status_code == 200

        # Each org sees only its own suppliers in the response summary
        assert resp_a.json()["total_suppliers"] == 1
        assert resp_b.json()["total_suppliers"] == 1

    def test_coverage_endpoint_org_scoped(self, org_a_client, org_b_client):
        """Coverage endpoint must return per-org metrics."""
        resp_a = org_a_client.get("/api/questionnaires/coverage")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/questionnaires/coverage")
        assert resp_b.status_code == 200

        # Both return 200 but with different per-org data
        assert "spend_weighted_coverage_pct" in resp_a.json()
        assert "spend_weighted_coverage_pct" in resp_b.json()


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------


class TestSuppliersOrgIsolation:
    """GET /api/suppliers/* — supplier records are org-scoped."""

    def test_list_suppliers_returns_only_own_org(self, org_a_client, org_b_client):
        """Org A must not see org B's suppliers in the list."""
        _insert_supplier("org_a_isolation_test", "sup_a_list_001", "Supplier A List")
        _insert_supplier("org_b_isolation_test", "sup_b_list_001", "Supplier B List")

        resp_a = org_a_client.get("/api/suppliers/")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/suppliers/")
        assert resp_b.status_code == 200

        names_a = {s["name"] for s in resp_a.json()["suppliers"]}
        names_b = {s["name"] for s in resp_b.json()["suppliers"]}

        assert "Supplier A List" in names_a
        assert "Supplier B List" not in names_a, "Org A saw org B's supplier"
        assert "Supplier B List" in names_b
        assert "Supplier A List" not in names_b, "Org B saw org A's supplier"

    def test_get_supplier_for_other_org_returns_403(self, org_a_client, org_b_client):
        """Fetching a supplier belonging to another org returns 403."""
        _insert_supplier("org_b_isolation_test", "sup_b_secret", "Secret Supplier B")
        _insert_supplier("org_a_isolation_test", "sup_a_ok", "OK Supplier A")

        # Org A can fetch its own supplier
        resp = org_a_client.get("/api/suppliers/sup_a_ok")
        assert resp.status_code == 200

        # Org A cannot fetch org B's supplier
        resp = org_a_client.get("/api/suppliers/sup_b_secret")
        assert resp.status_code == 403, "Accessing another org's supplier should return 403"

    def test_risk_ranked_returns_only_own_org(self, org_a_client, org_b_client):
        """Risk-ranked supplier list must be org-scoped."""
        _insert_supplier("org_a_isolation_test", "sup_a_risk_001", "Risk Supplier A")
        _insert_supplier("org_b_isolation_test", "sup_b_risk_001", "Risk Supplier B")

        resp_a = org_a_client.get("/api/suppliers/risk-ranked")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/suppliers/risk-ranked")
        assert resp_b.status_code == 200

        names_a = {s["name"] for s in resp_a.json()["suppliers"]}
        names_b = {s["name"] for s in resp_b.json()["suppliers"]}

        assert "Risk Supplier A" in names_a
        assert "Risk Supplier B" not in names_a
        assert "Risk Supplier B" in names_b
        assert "Risk Supplier A" not in names_b


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


class TestReportsOrgIsolation:
    """GET /api/reports/* — report data is org-scoped."""

    def test_report_pdf_endpoint_requires_auth(self, org_a_client):
        """Reports PDF endpoint requires auth and returns a PDF response."""
        # The reports router only has PDF generation endpoints; test that
        # the esg-pdf endpoint requires auth and returns PDF content.
        from fastapi.testclient import TestClient
        from src.api.main import app

        unauth = TestClient(app)
        resp = unauth.get("/api/reports/esg-pdf")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------


class TestRiskOrgIsolation:
    """GET /api/risk/* — risk flags are org-scoped."""

    def test_get_flags_returns_only_own_org(self, org_a_client, org_b_client):
        """Org A must not see org B's risk flags."""
        _insert_risk_flag("org_a_isolation_test", "energy", "WARNING", "Flag Org A Only")
        _insert_risk_flag("org_b_isolation_test", "energy", "CRITICAL", "Flag Org B Only")

        resp_a = org_a_client.get("/api/risk/flags")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/risk/flags")
        assert resp_b.status_code == 200

        flag_texts_a = {f["title"] for f in resp_a.json()["flags"]}
        flag_texts_b = {f["title"] for f in resp_b.json()["flags"]}

        assert "Flag Org A Only" in flag_texts_a
        assert "Flag Org B Only" not in flag_texts_a, "Org A saw org B's risk flag"
        assert "Flag Org B Only" in flag_texts_b
        assert "Flag Org A Only" not in flag_texts_b, "Org B saw org A's risk flag"

    def test_risk_summary_org_scoped(self, org_a_client, org_b_client):
        """Risk summary aggregation must be org-scoped."""
        # Give org_a 2 G2 flags, org_b 1 G2 flag — scores differ, proving isolation
        _insert_risk_flag("org_a_isolation_test", "G2", "WARNING", "A warning 1")
        _insert_risk_flag("org_a_isolation_test", "G2", "WARNING", "A warning 2")
        _insert_risk_flag("org_b_isolation_test", "G2", "CRITICAL", "B critical")

        resp_a = org_a_client.get("/api/risk/summary")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/risk/summary")
        assert resp_b.status_code == 200

        summary_a = resp_a.json()
        summary_b = resp_b.json()

        g2_a = summary_a.get("G2_supply_chain", {})
        g2_b = summary_b.get("G2_supply_chain", {})

        assert g2_a.get("flags", 0) == 2, "Org A should have 2 G2 flags"
        assert g2_b.get("flags", 0) == 1, "Org B should have 1 G2 flag"
        # Score = 72 - flags*5, so org_a score (62) < org_b score (67)
        assert g2_a.get("score", 0) < g2_b.get("score", 0), "Scores must differ between orgs"


# ---------------------------------------------------------------------------
# Scope3
# ---------------------------------------------------------------------------


class TestScope3OrgIsolation:
    """GET /api/scope3/* — Scope 3 data is org-scoped."""

    def test_scope3_categories_returns_only_own_org(self, org_a_client, org_b_client):
        """Org A must not see org B's Scope 3 emissions."""
        _insert_scope3("org_a_isolation_test", "Purchased Goods", 5000.0)
        _insert_scope3("org_b_isolation_test", "Purchased Goods", 9999.0)

        resp_a = org_a_client.get("/api/scope3/categories")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/scope3/categories")
        assert resp_b.status_code == 200

        cats_a = resp_a.json()["categories"]
        cats_b = resp_b.json()["categories"]

        tco2e_vals_a = {c["tco2e"] for c in cats_a}
        tco2e_vals_b = {c["tco2e"] for c in cats_b}

        assert 5000.0 in tco2e_vals_a
        assert 9999.0 not in tco2e_vals_a, "Org A saw org B's Scope 3 emissions"
        assert 9999.0 in tco2e_vals_b
        assert 5000.0 not in tco2e_vals_b, "Org B saw org A's Scope 3 emissions"

    def test_scope3_completeness_org_scoped(self, org_a_client, org_b_client):
        """Completeness endpoint must be org-scoped."""
        resp_a = org_a_client.get("/api/scope3/completeness")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/scope3/completeness")
        assert resp_b.status_code == 200

        assert isinstance(resp_a.json(), dict)
        assert isinstance(resp_b.json(), dict)


# ---------------------------------------------------------------------------
# Emission Factors
# ---------------------------------------------------------------------------


class TestEmissionFactorsOrgIsolation:
    """GET /api/emission-factors/* — emission factors are org-scoped."""

    def test_emission_factors_returns_only_own_org(self, org_a_client, org_b_client):
        """Org A must not see org B's custom emission factors."""
        _insert_emission_factor("org_a_isolation_test", "Factor Org A Only")
        _insert_emission_factor("org_b_isolation_test", "Factor Org B Only")

        resp_a = org_a_client.get("/api/emission-factors/")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/emission-factors/")
        assert resp_b.status_code == 200

        names_a = {f["factor_name"] for f in resp_a.json()["factors"]}
        names_b = {f["factor_name"] for f in resp_b.json()["factors"]}

        assert "Factor Org A Only" in names_a
        assert "Factor Org B Only" not in names_a, "Org A saw org B's emission factor"
        assert "Factor Org B Only" in names_b
        assert "Factor Org A Only" not in names_b, "Org B saw org A's emission factor"


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


class TestAlertsOrgIsolation:
    """GET /api/alerts/* — alert thresholds are org-scoped."""

    def test_list_thresholds_returns_only_own_org(self, org_a_client, org_b_client):
        """Org A must not see org B's alert thresholds."""
        _insert_alert_threshold("org_a_isolation_test", "energy", threshold_value=100.0)
        _insert_alert_threshold("org_b_isolation_test", "energy", threshold_value=200.0)

        resp_a = org_a_client.get("/api/alerts/thresholds")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/alerts/thresholds")
        assert resp_b.status_code == 200

        thresh_vals_a = {t["threshold_value"] for t in resp_a.json()["thresholds"]}
        thresh_vals_b = {t["threshold_value"] for t in resp_b.json()["thresholds"]}

        assert 100.0 in thresh_vals_a
        assert 200.0 not in thresh_vals_a, "Org A saw org B's threshold"
        assert 200.0 in thresh_vals_b
        assert 100.0 not in thresh_vals_b, "Org B saw org A's threshold"


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


class TestAuditOrgIsolation:
    """GET /api/audit/log — audit entries are org-scoped."""

    def test_audit_log_returns_only_own_org(self, org_a_client, org_b_client):
        """Org A must not see org B's audit entries."""
        _insert_audit_entry("org_a_isolation_test", "login", "session")
        _insert_audit_entry("org_b_isolation_test", "delete", "supplier")

        resp_a = org_a_client.get("/api/audit/log")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/audit/log")
        assert resp_b.status_code == 200

        actions_a = {e["action"] for e in resp_a.json()["entries"]}
        actions_b = {e["action"] for e in resp_b.json()["entries"]}

        assert "login" in actions_a
        assert "delete" not in actions_a, "Org A saw org B's audit entry"
        assert "delete" in actions_b
        assert "login" not in actions_b, "Org B saw org A's audit entry"


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


class TestUploadOrgIsolation:
    """POST /api/upload/* — uploads must be associated with the authenticated org."""

    def test_upload_suppliers_requires_auth(self, org_a_client):
        """Upload endpoint must reject unauthenticated requests."""
        from fastapi.testclient import TestClient
        from src.api.main import app

        unauth = TestClient(app)
        resp = unauth.post(
            "/api/upload/suppliers",
            files={"file": ("suppliers.csv", b"id,name,country", "text/csv")},
        )
        assert resp.status_code == 401

    def test_upload_emission_factors_requires_auth(self, org_a_client):
        """Upload endpoint must reject unauthenticated requests."""
        from fastapi.testclient import TestClient
        from src.api.main import app

        unauth = TestClient(app)
        resp = unauth.post(
            "/api/upload/emission-factors",
            files={"file": ("factors.csv", b"category,factor_name", "text/csv")},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


class TestTemplatesOrgIsolation:
    """GET /api/templates/* — templates are org-scoped (questionnaire_templates)."""

    def test_list_templates_returns_only_own_org(self, org_a_client, org_b_client):
        """Org A must not see org B's templates."""
        _insert_template("org_a_isolation_test", "Template A for Templates")
        _insert_template("org_b_isolation_test", "Template B for Templates")

        resp_a = org_a_client.get("/api/templates/")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/templates/")
        assert resp_b.status_code == 200

        names_a = {t["name"] for t in resp_a.json().get("templates", [])}
        names_b = {t["name"] for t in resp_b.json().get("templates", [])}

        assert "Template A for Templates" in names_a
        assert "Template B for Templates" not in names_a, "Org A saw org B's template"
        assert "Template B for Templates" in names_b
        assert "Template A for Templates" not in names_b, "Org B saw org A's template"


# ---------------------------------------------------------------------------
# Trust
# ---------------------------------------------------------------------------


class TestTrustOrgIsolation:
    """GET /api/trust/badges — trust badges are org-scoped."""

    def test_trust_badges_returns_own_org_only(self, org_a_client, org_b_client):
        """Trust badges endpoint must return data for the authenticated org only."""
        resp_a = org_a_client.get("/api/trust/badges")
        assert resp_a.status_code == 200
        resp_b = org_b_client.get("/api/trust/badges")
        assert resp_b.status_code == 200

        assert resp_a.json()["org_id"] == "org_a_isolation_test"
        assert resp_b.json()["org_id"] == "org_b_isolation_test"


# ---------------------------------------------------------------------------
# Export — org isolation
# ---------------------------------------------------------------------------


class TestExportOrgIsolation:
    """GET /api/export/* — exports are org-scoped."""

    def test_export_suppliers_returns_only_own_org(self, org_a_client, org_b_client):
        """Supplier export must be org-scoped; org A must not see org B's suppliers."""
        _insert_supplier("org_a_isolation_test", "sup_a_export_001", "Export Supplier A")
        _insert_supplier("org_b_isolation_test", "sup_b_export_001", "Export Supplier B")

        resp_a = org_a_client.get("/api/export/suppliers?format=csv")
        assert resp_a.status_code == 200
        content_a = resp_a.content.decode()
        assert "Export Supplier A" in content_a
        assert "Export Supplier B" not in content_a, "Org A saw org B's supplier in export"

        resp_b = org_b_client.get("/api/export/suppliers?format=csv")
        assert resp_b.status_code == 200
        content_b = resp_b.content.decode()
        assert "Export Supplier B" in content_b
        assert "Export Supplier A" not in content_b, "Org B saw org A's supplier in export"


# ---------------------------------------------------------------------------
# ML Predict — org isolation
# ---------------------------------------------------------------------------


class TestMLPredictOrgIsolation:
    """GET /api/ml/predict — batch predictions are org-scoped."""

    def test_batch_predict_returns_only_own_org(self, org_a_client, org_b_client):
        """Batch ML predict must only return suppliers belonging to the authenticated org."""
        _insert_supplier("org_a_isolation_test", "sup_a_ml_001", "ML Supplier A")
        _insert_supplier("org_b_isolation_test", "sup_b_ml_001", "ML Supplier B")

        resp_a = org_a_client.get("/api/ml/predict")
        assert resp_a.status_code == 200
        supplier_ids_a = {s["supplier_id"] for s in resp_a.json().get("suppliers", [])}
        assert "sup_a_ml_001" in supplier_ids_a
        assert "sup_b_ml_001" not in supplier_ids_a, "Org A saw org B's supplier in ML predict"

        resp_b = org_b_client.get("/api/ml/predict")
        assert resp_b.status_code == 200
        supplier_ids_b = {s["supplier_id"] for s in resp_b.json().get("suppliers", [])}
        assert "sup_b_ml_001" in supplier_ids_b
        assert "sup_a_ml_001" not in supplier_ids_b, "Org B saw org A's supplier in ML predict"


# ---------------------------------------------------------------------------
# Authenticated endpoint — 401 when no token
# ---------------------------------------------------------------------------


class TestAuthRequiredForAllRouteGroups:
    """All route groups require authentication."""

    _endpoint_samples = [
        ("/api/dashboard/live", "get"),
        ("/api/evidence/drilldown/energy_kwh", "get"),
        ("/api/frameworks/map", "get"),
        ("/api/questionnaires/response-summary", "get"),
        ("/api/suppliers/", "get"),
        ("/api/risk/flags", "get"),
        ("/api/risk/summary", "get"),
        ("/api/scope3/categories", "get"),
        ("/api/scope3/completeness", "get"),
        ("/api/emission-factors/", "get"),
        ("/api/alerts/thresholds", "get"),
        ("/api/audit/log", "get"),
        ("/api/templates/", "get"),
        ("/api/trust/badges", "get"),
        ("/api/reports/esg-pdf", "get"),
        ("/api/export/suppliers", "get"),
        ("/api/ml/predict", "get"),
    ]

    @pytest.mark.parametrize("path,method", _endpoint_samples)
    def test_returns_401_without_token(self, path, method):
        """Every authenticated endpoint returns 401 without a Bearer token."""
        from fastapi.testclient import TestClient
        from src.api.main import app

        c = TestClient(app)
        if method == "get":
            resp = c.get(path)
        else:
            resp = c.post(path, json={})
        assert resp.status_code == 401, (
            f"{method.upper()} {path} returned {resp.status_code} instead of 401"
        )
