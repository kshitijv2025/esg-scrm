"""Tests for database layer — connection manager, query helpers, seed."""
import sys

sys.path.insert(0, "src")

from src.db.database import (
    fetch_all_scope3,
    fetch_coverage_stats,
    fetch_metrics,
    fetch_risk_flags,
    fetch_supplier,
    fetch_suppliers,
    get_connection,
)
from src.db.seed import seed


class TestDatabaseManager:
    def setup_method(self):
        seed()

    def test_get_connection_returns_row_factory(self):
        conn = get_connection()
        row = conn.execute("SELECT 1 as val").fetchone()
        assert row["val"] == 1
        conn.close()

    def test_fetch_metrics_returns_list(self):
        metrics = fetch_metrics()
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        assert "cluster" in metrics[0]
        assert "value" in metrics[0]

    def test_fetch_suppliers_returns_list(self):
        suppliers = fetch_suppliers()
        assert isinstance(suppliers, list)
        assert len(suppliers) >= 7

    def test_fetch_supplier_by_id(self):
        supplier = fetch_supplier("sup_001")
        assert supplier is not None
        assert supplier["name"] == "Gujarat Cotton Traders"

    def test_fetch_supplier_nonexistent(self):
        supplier = fetch_supplier("sup_999")
        assert supplier is None

    def test_fetch_risk_flags_returns_list(self):
        flags = fetch_risk_flags()
        assert isinstance(flags, list)
        assert len(flags) >= 5

    def test_fetch_coverage_stats(self):
        stats = fetch_coverage_stats()
        assert "coverage_pct" in stats
        assert "responding_suppliers" in stats
        assert "total_suppliers" in stats
        assert stats["total_suppliers"] >= 7

    def test_fetch_all_scope3(self):
        scope3 = fetch_all_scope3()
        assert isinstance(scope3, list)
        assert len(scope3) >= 6

    def test_metrics_have_evidence_chain(self):
        conn = get_connection()
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM evidence_chain"
        ).fetchone()["cnt"]
        conn.close()
        assert count > 0

    def test_organizations_table_exists(self):
        conn = get_connection()
        orgs = conn.execute("SELECT COUNT(*) as cnt FROM organizations").fetchone()
        conn.close()
        assert orgs["cnt"] >= 1

    def test_users_table_exists(self):
        conn = get_connection()
        users = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
        conn.close()
        assert users["cnt"] >= 1
