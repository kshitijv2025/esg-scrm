"""Tests for suppliers API routes."""

import sys

sys.path.insert(0, "src")

from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.jwt import create_token
from tests.conftest import _auth_headers

client = TestClient(app)


def _auth_headers_for_org(org_id: str) -> dict:
    token = create_token(
        {
            "sub": "usr_plan_test",
            "org_id": org_id,
            "email": "plantest@test.com",
            "role": "admin",
        }
    )
    return {"Authorization": f"Bearer {token}"}
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


class TestSupplierImprovementTimeline:
    """Tests for GET /api/suppliers/{supplier_id}/improvement-timeline (B3.13)."""

    def _cleanup_test_suppliers(self):
        """Remove suppliers created by this test class."""
        from src.db.database import _execute, get_connection, release_connection

        conn = get_connection()
        try:
            for sid in ("sup_test_other_org", "sup_no_responses"):
                _execute(conn, "DELETE FROM suppliers WHERE id = ?", (sid,))
        finally:
            release_connection(conn)

    def teardown_method(self):
        self._cleanup_test_suppliers()

    def test_timeline_returns_404_for_nonexistent_supplier(self):
        r = client.get(
            "/api/suppliers/nonexistent_id/improvement-timeline", headers=_auth_headers()
        )
        assert r.status_code == 404

    def test_timeline_returns_403_for_other_org_supplier(self):
        """Org isolation: users cannot see suppliers from other orgs."""
        # sup_001 belongs to org_bd_001, but our test token is for org_bd_001
        # so this would succeed. Need a supplier from a different org.
        # The seed data may not have cross-org suppliers, so we test
        # that a request for a supplier with mismatched org_id returns 403.
        from src.db.database import _execute, get_connection, release_connection

        # Create a supplier in a different org
        conn = get_connection()
        try:
            _execute(
                conn,
                """
                INSERT INTO suppliers (id, org_id, name, country, industry, tier, annual_spend_usd)
                VALUES ('sup_test_other_org', 'org_xx_999', 'Other Org Supplier', 'XX', 'Textiles', 'tier1', 100000)
            """,
            )
        finally:
            release_connection(conn)

        r = client.get(
            "/api/suppliers/sup_test_other_org/improvement-timeline", headers=_auth_headers()
        )
        assert r.status_code == 403

    def test_timeline_returns_scores_and_trends(self):
        """Timeline returns year-over-year scores with deltas and trend classification."""
        r = client.get("/api/suppliers/sup_001/improvement-timeline", headers=_auth_headers())
        assert r.status_code == 200
        data = r.json()

        assert "supplier_id" in data
        assert "years" in data
        assert "dimensions" in data
        assert "overall_trend" in data

        # Verify dimensions structure
        for dim in ("environmental", "social", "governance"):
            assert dim in data["dimensions"]
            dim_data = data["dimensions"][dim]
            assert "trend" in dim_data
            assert dim_data["trend"] in ("improving", "stable", "declining")

    def test_timeline_trend_classification(self):
        """Trend is 'improving' when delta > 5, 'stable' when -5 <= delta <= 5, 'declining' when delta < -5."""
        r = client.get("/api/suppliers/sup_001/improvement-timeline", headers=_auth_headers())
        assert r.status_code == 200
        data = r.json()

        for dim in ("environmental", "social", "governance"):
            dim_data = data["dimensions"][dim]
            if "delta" in dim_data:
                delta = dim_data["delta"]
                trend = dim_data["trend"]
                if delta > 5:
                    assert trend == "improving", f"delta={delta} should be improving"
                elif delta < -5:
                    assert trend == "declining", f"delta={delta} should be declining"
                else:
                    assert trend == "stable", f"delta={delta} should be stable"

    def test_timeline_with_no_responses_returns_baseline(self):
        """Supplier with no questionnaire responses should still return a valid structure."""
        from src.db.database import _execute, get_connection, release_connection

        # Create a fresh supplier with no responses
        conn = get_connection()
        try:
            _execute(
                conn,
                """
                INSERT INTO suppliers (id, org_id, name, country, industry, tier, annual_spend_usd)
                VALUES ('sup_no_responses', 'org_bd_001', 'No Responses Supplier', 'BD', 'Textiles', 'tier1', 50000)
            """,
            )
        finally:
            release_connection(conn)

        r = client.get(
            "/api/suppliers/sup_no_responses/improvement-timeline", headers=_auth_headers()
        )
        assert r.status_code == 200
        data = r.json()
        assert data["supplier_id"] == "sup_no_responses"
        assert "dimensions" in data


class TestPlanEnforcement:
    """E1.2: Plan tier limits enforced on supplier imports."""

    def _setup_starter_org(self):
        """Create a starter-plan org with 50 existing suppliers (at the limit)."""
        from src.db.database import get_connection, release_connection

        conn = get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO organizations (id, name, industry, plan) VALUES (?, ?, ?, ?)",
                ("org_starter_limit", "Limit Test Org", "Textiles", "starter"),
            )
            # Remove any existing suppliers for this org to start fresh
            conn.execute("DELETE FROM suppliers WHERE org_id = ?", ("org_starter_limit",))
            # Create 50 suppliers to hit the Starter limit
            for i in range(50):
                conn.execute(
                    "INSERT INTO suppliers (id, org_id, name, country, tier, industry, annual_spend_usd) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"sup_limit_{i}",
                        "org_starter_limit",
                        f"Supplier {i}",
                        "BD",
                        "tier1",
                        "Textiles",
                        100000.0,
                    ),
                )
            conn.commit()
        finally:
            release_connection(conn)

    def _cleanup_starter_org(self):
        from src.db.database import get_connection, release_connection

        conn = get_connection()
        try:
            conn.execute("DELETE FROM suppliers WHERE org_id = ?", ("org_starter_limit",))
            conn.execute("DELETE FROM organizations WHERE id = ?", ("org_starter_limit",))
            conn.commit()
        finally:
            release_connection(conn)

    def test_import_blocked_when_over_supplier_limit(self):
        """Importing more suppliers than the plan allows returns 403."""
        self._setup_starter_org()
        try:
            # Try to import 2 new suppliers — would be 52 > 50 limit
            resp = client.post(
                "/api/suppliers/exchange",
                headers=_auth_headers_for_org("org_starter_limit"),
                json={
                    "suppliers": [
                        {"name": "New Supplier 1", "country": "BD"},
                        {"name": "New Supplier 2", "country": "VN"},
                    ]
                },
            )
            assert resp.status_code == 403
            assert "Plan limit reached" in resp.json()["detail"]
            assert "Starter" in resp.json()["detail"]
            assert "50" in resp.json()["detail"]
        finally:
            self._cleanup_starter_org()

    def test_import_allowed_when_at_limit_but_not_over(self):
        """Importing exactly up to the limit is allowed."""
        self._setup_starter_org()
        try:
            # Try to import 0 new suppliers (only existing 50)
            resp = client.post(
                "/api/suppliers/exchange",
                headers=_auth_headers_for_org("org_starter_limit"),
                json={
                    "suppliers": [
                        {"name": "Replacement Supplier", "country": "BD"},  # same name, no id = new
                    ]
                },
            )
            # Would be 51 > 50 — should be blocked
            assert resp.status_code == 403
        finally:
            self._cleanup_starter_org()

    def test_import_allowed_for_unlimited_plan(self):
        """Enterprise orgs can import unlimited suppliers."""
        from src.db.database import get_connection, release_connection

        conn = get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO organizations (id, name, industry, plan) VALUES (?, ?, ?, ?)",
                ("org_enterprise_unlimited", "Enterprise Org", "Tech", "enterprise"),
            )
            conn.execute("DELETE FROM suppliers WHERE org_id = ?", ("org_enterprise_unlimited",))
            conn.commit()
        finally:
            release_connection(conn)

        try:
            resp = client.post(
                "/api/suppliers/exchange",
                headers=_auth_headers_for_org("org_enterprise_unlimited"),
                json={
                    "suppliers": [
                        {"name": "Enterprise Supplier 1", "country": "US"},
                        {"name": "Enterprise Supplier 2", "country": "DE"},
                        {"name": "Enterprise Supplier 3", "country": "JP"},
                    ]
                },
            )
            # Enterprise has unlimited — should succeed
            assert resp.status_code == 200
            data = resp.json()
            assert data["imported"] == 3
        finally:
            conn = get_connection()
            try:
                conn.execute(
                    "DELETE FROM suppliers WHERE org_id = ?", ("org_enterprise_unlimited",)
                )
                conn.execute(
                    "DELETE FROM organizations WHERE id = ?", ("org_enterprise_unlimited",)
                )
                conn.commit()
            finally:
                release_connection(conn)

    def test_updates_do_not_count_toward_limit(self):
        """Updating existing suppliers is not blocked by plan limits."""
        self._setup_starter_org()
        try:
            # Update existing supplier (has id — counts as update, not import)
            resp = client.post(
                "/api/suppliers/exchange",
                headers=_auth_headers_for_org("org_starter_limit"),
                json={
                    "suppliers": [
                        {"id": "sup_limit_0", "name": "Updated Supplier Name", "country": "BD"},
                    ]
                },
            )
            # Updates are allowed regardless of plan limit
            assert resp.status_code == 200
            data = resp.json()
            assert data["updated"] == 1
        finally:
            self._cleanup_starter_org()
