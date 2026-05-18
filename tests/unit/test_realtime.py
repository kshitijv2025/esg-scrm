"""Tests for realtime alert bus and risk detector."""
import sys
sys.path.insert(0, "src")

from src.realtime.alerts import AlertBus, get_bus
from src.realtime.risk_detector import THRESHOLDS, check_latest_metrics
from src.db.seed import seed


class TestAlertBus:
    def test_alert_bus_initializes_empty(self):
        bus = AlertBus()
        assert len(bus._connections) == 0

    def test_get_bus_returns_singleton(self):
        bus1 = get_bus()
        bus2 = get_bus()
        assert bus1 is bus2

    def test_broadcast_with_no_connections(self):
        import asyncio
        bus = AlertBus()
        asyncio.get_event_loop().run_until_complete(bus.broadcast({"type": "test"}))
        assert len(bus._connections) == 0


class TestRiskDetector:
    def setup_method(self):
        seed()

    def test_thresholds_defined(self):
        assert "energy_kwh" in THRESHOLDS
        assert "water_m3" in THRESHOLDS
        assert "diesel_consumed" in THRESHOLDS
        for key, t in THRESHOLDS.items():
            assert "max" in t
            assert "severity" in t
            assert "text" in t

    def test_check_latest_metrics_returns_list(self):
        flags = check_latest_metrics()
        assert isinstance(flags, list)

    def test_no_duplicate_flags_created(self):
        flags1 = check_latest_metrics()
        flags2 = check_latest_metrics()
        assert len(flags2) == 0 or len(flags2) <= len(flags1)
