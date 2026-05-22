"""Tests for alert deduplication — fetch_recent_matching_flag and should_suppress_flag."""

import sys

sys.path.insert(0, "src")

import pytest

from datetime import datetime, timezone, timedelta

from src.db.database import (
    fetch_recent_matching_flag,
    should_suppress_flag,
    get_connection,
    release_connection,
)
from src.db.seed import seed
from src.realtime.alerts import (
    _get_recommendation,
    _should_escalate,
)


class TestAlertDeduplication:
    """D1.6: Alert deduplication — prevent duplicate risk flags within a 24-hour window."""

    def setup_method(self):
        seed()

    def _insert_flag(
        self,
        flag_id: str,
        org_id: str,
        cluster: str,
        severity: str = "WARNING",
        acknowledged: int = 0,
    ) -> None:
        """Insert a risk flag directly for test setup."""
        conn = get_connection()
        try:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc).isoformat()
            if acknowledged:
                conn.execute(
                    """
                    INSERT INTO risk_flags
                        (id, org_id, factory_id, flag_text, cluster, severity, days_overdue, priority_score, acknowledged, acknowledged_at)
                    VALUES (?, ?, 'factory_bd_001', 'test flag', ?, ?, 0, 50.0, 1, ?)
                    """,
                    (flag_id, org_id, cluster, severity, now),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO risk_flags
                        (id, org_id, factory_id, flag_text, cluster, severity, days_overdue, priority_score, acknowledged)
                    VALUES (?, ?, 'factory_bd_001', 'test flag', ?, ?, 0, 50.0, 0)
                    """,
                    (flag_id, org_id, cluster, severity),
                )
            conn.commit()
        finally:
            release_connection(conn)

    def test_fetch_recent_matching_flag_returns_existing_flag(self):
        """Same org_id + cluster returns the flag within the lookback window."""
        self._insert_flag(
            flag_id="flag_dedup_001",
            org_id="org_bd_001",
            cluster="energy",
            severity="WARNING",
        )
        result = fetch_recent_matching_flag("org_bd_001", "energy", lookback_hours=24)
        assert result is not None
        assert result["id"] == "flag_dedup_001"
        assert result["cluster"] == "energy"
        assert result["org_id"] == "org_bd_001"

    def test_fetch_recent_matching_flag_returns_none_for_different_cluster(self):
        """Different cluster on same org returns None (no duplicate)."""
        self._insert_flag(
            flag_id="flag_dedup_002",
            org_id="org_bd_001",
            cluster="energy",
            severity="WARNING",
        )
        result = fetch_recent_matching_flag("org_bd_001", "water_m3", lookback_hours=24)
        assert result is None

    def test_fetch_recent_matching_flag_returns_none_for_different_org(self):
        """Different org_id returns None (org isolation)."""
        self._insert_flag(
            flag_id="flag_dedup_003",
            org_id="org_bd_001",
            cluster="energy",
            severity="WARNING",
        )
        result = fetch_recent_matching_flag("org_other", "energy", lookback_hours=24)
        assert result is None

    def test_fetch_recent_matching_flag_excludes_acknowledged_flags(self):
        """Acknowledged flags are not returned — allows re-alerting after acknowledgement."""
        self._insert_flag(
            flag_id="flag_dedup_004",
            org_id="org_bd_001",
            cluster="energy",
            severity="WARNING",
            acknowledged=1,
        )
        result = fetch_recent_matching_flag("org_bd_001", "energy", lookback_hours=24)
        assert result is None

    def test_should_suppress_flag_true_on_duplicate(self):
        """Duplicate condition within lookback window triggers suppression."""
        self._insert_flag(
            flag_id="flag_dedup_005",
            org_id="org_bd_001",
            cluster="energy",
            severity="WARNING",
        )
        assert should_suppress_flag("org_bd_001", "energy", lookback_hours=24) is True

    def test_should_suppress_flag_false_on_no_duplicate(self):
        """No duplicate exists — suppression should not fire."""
        self._insert_flag(
            flag_id="flag_dedup_006",
            org_id="org_bd_001",
            cluster="water_m3",
            severity="WARNING",
        )
        assert should_suppress_flag("org_bd_001", "energy", lookback_hours=24) is False

    def test_should_suppress_flag_false_after_acknowledgement(self):
        """Once acknowledged, a new flag can be created for the same condition."""
        self._insert_flag(
            flag_id="flag_dedup_007",
            org_id="org_bd_001",
            cluster="energy",
            severity="WARNING",
            acknowledged=1,
        )
        assert should_suppress_flag("org_bd_001", "energy", lookback_hours=24) is False


class TestGetRecommendation:
    """D1.3: Plain-language recommendations per cluster and severity."""

    @pytest.mark.parametrize(
        "cluster,severity,expected_contains",
        [
            ("energy_kwh", "WARNING", "Review"),
            ("energy_kwh", "CRITICAL", "suspend"),
            ("emissions_tco2", "WARNING", "Audit"),
            ("emissions_tco2", "CRITICAL", "reduction plan"),
            ("water_m3", "WARNING", "inspect"),
            ("water_m3", "CRITICAL", "conservation"),
            ("scope3_category1", "WARNING", "suppliers"),
            ("scope3_category1", "CRITICAL", "scorecard"),
            ("diesel_consumed", "WARNING", "generator"),
            ("diesel_consumed", "CRITICAL", "justified"),
            ("gender_pct", "WARNING", "diversity"),
            ("gender_pct", "CRITICAL", "equity"),
            ("safety_incidents", "WARNING", "safety audit"),
            ("safety_incidents", "CRITICAL", "regulatory"),
            ("governance_score", "WARNING", "board"),
            ("governance_score", "CRITICAL", "governance audit"),
        ],
    )
    def test_recommendation_contains_action_keywords(self, cluster, severity, expected_contains):
        """Each cluster/severity combination returns a non-empty recommendation with action words."""
        rec = _get_recommendation(cluster, severity)
        assert isinstance(rec, str)
        assert len(rec) > 10
        assert expected_contains.lower() in rec.lower()

    def test_recommendation_unknown_cluster_returns_generic(self):
        """Unknown cluster returns a generic fallback recommendation."""
        rec = _get_recommendation("unknown_metric_cluster", "WARNING")
        assert isinstance(rec, str)
        assert len(rec) > 5


class TestShouldEscalate:
    """D1.6: Flags older than 72h escalate from non-CRITICAL to CRITICAL."""

    def test_no_escalate_when_already_critical(self):
        """CRITICAL flags never escalate."""
        old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=100)).isoformat()
        escalate, severity = _should_escalate(old_timestamp, "CRITICAL")
        assert escalate is False
        assert severity == "CRITICAL"

    def test_no_escalate_when_young_warning(self):
        """WARNING flags under 72h do not escalate."""
        young_timestamp = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        escalate, severity = _should_escalate(young_timestamp, "WARNING")
        assert escalate is False
        assert severity == "WARNING"

    def test_escalate_when_old_warning(self):
        """WARNING flags over 72h escalate to CRITICAL."""
        old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=100)).isoformat()
        escalate, severity = _should_escalate(old_timestamp, "WARNING")
        assert escalate is True
        assert severity == "CRITICAL"

    def test_no_escalate_when_young_info(self):
        """INFO flags under 72h do not escalate."""
        young_timestamp = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
        escalate, severity = _should_escalate(young_timestamp, "INFO")
        assert escalate is False
        assert severity == "INFO"

    def test_escalate_when_old_info(self):
        """INFO flags over 72h escalate to CRITICAL."""
        old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=200)).isoformat()
        escalate, severity = _should_escalate(old_timestamp, "INFO")
        assert escalate is True
        assert severity == "CRITICAL"

    def test_no_escalate_invalid_timestamp(self):
        """Invalid timestamps return no escalation."""
        escalate, severity = _should_escalate("not-a-timestamp", "WARNING")
        assert escalate is False
        assert severity == "WARNING"
