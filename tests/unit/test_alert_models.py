"""
Unit tests for AlertEvent model.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from src.realtime.alert_models import AlertEvent


class TestAlertEvent:
    """Tests for AlertEvent dataclass."""

    def test_create_with_all_fields(self):
        """Test AlertEvent creation with all fields specified."""
        now = datetime.now(timezone.utc)
        alert_id = uuid4()
        event_id = uuid4()
        ack_by = uuid4()
        ack_at = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)

        event = AlertEvent(
            id=event_id,
            alert_id=alert_id,
            metric_type="emissions_tco2",
            triggered_at=now,
            actual_value=Decimal("150.5"),
            actual_unit="tCO2e",
            threshold_value=Decimal("100.0"),
            threshold_unit="tCO2e",
            comparison="gt",
            consecutive_breaches=3,
            notification_sent=True,
            acknowledged=True,
            acknowledged_by=ack_by,
            acknowledged_at=ack_at,
        )

        assert event.id == event_id
        assert event.alert_id == alert_id
        assert event.metric_type == "emissions_tco2"
        assert event.triggered_at == now
        assert event.actual_value == Decimal("150.5")
        assert event.actual_unit == "tCO2e"
        assert event.threshold_value == Decimal("100.0")
        assert event.threshold_unit == "tCO2e"
        assert event.comparison == "gt"
        assert event.consecutive_breaches == 3
        assert event.notification_sent is True
        assert event.acknowledged is True
        assert event.acknowledged_by == ack_by
        assert event.acknowledged_at == ack_at

    def test_create_with_minimal_fields(self):
        """Test AlertEvent creation with only required fields."""
        now = datetime.now(timezone.utc)
        event_id = uuid4()
        alert_id = uuid4()

        event = AlertEvent(
            id=event_id,
            alert_id=alert_id,
            metric_type="energy_kwh",
            triggered_at=now,
            actual_value=Decimal("100.0"),
            actual_unit="kWh",
            threshold_value=Decimal("80.0"),
            threshold_unit="kWh",
            comparison="gt",
        )

        assert event.id == event_id
        assert event.alert_id == alert_id
        assert event.metric_type == "energy_kwh"
        assert event.triggered_at == now
        assert event.actual_value == Decimal("100.0")
        assert event.actual_unit == "kWh"
        assert event.threshold_value == Decimal("80.0")
        assert event.threshold_unit == "kWh"
        assert event.comparison == "gt"
        assert event.consecutive_breaches == 0  # default
        assert event.notification_sent is False  # default
        assert event.acknowledged is False  # default
        assert event.acknowledged_by is None  # default
        assert event.acknowledged_at is None  # default

    def test_consecutive_breaches_field_increments(self):
        """Test consecutive_breaches field can be incremented."""
        event = AlertEvent(
            id=uuid4(),
            alert_id=uuid4(),
            metric_type="water_gallons",
            triggered_at=datetime.now(timezone.utc),
            actual_value=Decimal("5000.0"),
            actual_unit="gallons",
            threshold_value=Decimal("3000.0"),
            threshold_unit="gallons",
            comparison="gt",
            consecutive_breaches=0,
        )
        assert event.consecutive_breaches == 0

        # Simulate incrementing
        event.consecutive_breaches += 1
        assert event.consecutive_breaches == 1

        event.consecutive_breaches += 1
        assert event.consecutive_breaches == 2

        event.consecutive_breaches += 1
        assert event.consecutive_breaches == 3

    def test_invalid_comparison_operator_raises(self):
        """Test that invalid comparison operator raises ValueError."""
        with pytest.raises(ValueError, match="Invalid comparison operator"):
            AlertEvent(
                id=uuid4(),
                alert_id=uuid4(),
                metric_type="energy_kwh",
                triggered_at=datetime.now(timezone.utc),
                actual_value=Decimal("100.0"),
                actual_unit="kWh",
                threshold_value=Decimal("80.0"),
                threshold_unit="kWh",
                comparison="invalid",
            )

    def test_is_breach_gt(self):
        """Test is_breach with 'gt' comparison."""
        event = AlertEvent(
            id=uuid4(),
            alert_id=uuid4(),
            metric_type="energy_kwh",
            triggered_at=datetime.now(timezone.utc),
            actual_value=Decimal("100.0"),
            actual_unit="kWh",
            threshold_value=Decimal("80.0"),
            threshold_unit="kWh",
            comparison="gt",
        )
        assert event.is_breach(Decimal("90.0")) is True
        assert event.is_breach(Decimal("80.0")) is False
        assert event.is_breach(Decimal("70.0")) is False

    def test_is_breach_lt(self):
        """Test is_breach with 'lt' comparison."""
        event = AlertEvent(
            id=uuid4(),
            alert_id=uuid4(),
            metric_type="temperature_c",
            triggered_at=datetime.now(timezone.utc),
            actual_value=Decimal("18.0"),
            actual_unit="celsius",
            threshold_value=Decimal("25.0"),
            threshold_unit="celsius",
            comparison="lt",
        )
        assert event.is_breach(Decimal("20.0")) is True
        assert event.is_breach(Decimal("25.0")) is False
        assert event.is_breach(Decimal("30.0")) is False

    def test_is_breach_gte(self):
        """Test is_breach with 'gte' comparison."""
        event = AlertEvent(
            id=uuid4(),
            alert_id=uuid4(),
            metric_type="energy_kwh",
            triggered_at=datetime.now(timezone.utc),
            actual_value=Decimal("100.0"),
            actual_unit="kWh",
            threshold_value=Decimal("80.0"),
            threshold_unit="kWh",
            comparison="gte",
        )
        assert event.is_breach(Decimal("90.0")) is True
        assert event.is_breach(Decimal("80.0")) is True
        assert event.is_breach(Decimal("70.0")) is False

    def test_is_breach_lte(self):
        """Test is_breach with 'lte' comparison."""
        event = AlertEvent(
            id=uuid4(),
            alert_id=uuid4(),
            metric_type="temperature_c",
            triggered_at=datetime.now(timezone.utc),
            actual_value=Decimal("18.0"),
            actual_unit="celsius",
            threshold_value=Decimal("25.0"),
            threshold_unit="celsius",
            comparison="lte",
        )
        assert event.is_breach(Decimal("20.0")) is True
        assert event.is_breach(Decimal("25.0")) is True
        assert event.is_breach(Decimal("30.0")) is False

    def test_is_breach_eq(self):
        """Test is_breach with 'eq' comparison."""
        event = AlertEvent(
            id=uuid4(),
            alert_id=uuid4(),
            metric_type="ph_level",
            triggered_at=datetime.now(timezone.utc),
            actual_value=Decimal("7.0"),
            actual_unit="ph",
            threshold_value=Decimal("7.0"),
            threshold_unit="ph",
            comparison="eq",
        )
        assert event.is_breach(Decimal("7.0")) is True
        assert event.is_breach(Decimal("6.9")) is False
        assert event.is_breach(Decimal("7.1")) is False

    def test_to_dict(self):
        """Test to_dict returns correct dictionary."""
        now = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        event_id = uuid4()
        alert_id = uuid4()

        event = AlertEvent(
            id=event_id,
            alert_id=alert_id,
            metric_type="emissions_tco2",
            triggered_at=now,
            actual_value=Decimal("150.5"),
            actual_unit="tCO2e",
            threshold_value=Decimal("100.0"),
            threshold_unit="tCO2e",
            comparison="gt",
            consecutive_breaches=3,
            notification_sent=True,
            acknowledged=False,
        )

        result = event.to_dict()

        assert result["id"] == str(event_id)
        assert result["alert_id"] == str(alert_id)
        assert result["metric_type"] == "emissions_tco2"
        assert result["triggered_at"] == now.isoformat()
        assert result["actual_value"] == "150.5"
        assert result["actual_unit"] == "tCO2e"
        assert result["threshold_value"] == "100.0"
        assert result["threshold_unit"] == "tCO2e"
        assert result["comparison"] == "gt"
        assert result["consecutive_breaches"] == 3
        assert result["notification_sent"] is True
        assert result["acknowledged"] is False
        assert result["acknowledged_by"] is None
        assert result["acknowledged_at"] is None

    def test_from_dict(self):
        """Test from_dict creates AlertEvent correctly."""
        now = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        event_id = uuid4()
        alert_id = uuid4()

        data = {
            "id": str(event_id),
            "alert_id": str(alert_id),
            "metric_type": "emissions_tco2",
            "triggered_at": now.isoformat(),
            "actual_value": "150.5",
            "actual_unit": "tCO2e",
            "threshold_value": "100.0",
            "threshold_unit": "tCO2e",
            "comparison": "gt",
            "consecutive_breaches": 3,
            "notification_sent": True,
            "acknowledged": False,
        }

        event = AlertEvent.from_dict(data)

        assert event.id == event_id
        assert event.alert_id == alert_id
        assert event.metric_type == "emissions_tco2"
        assert event.actual_value == Decimal("150.5")
        assert event.threshold_value == Decimal("100.0")
        assert event.comparison == "gt"
        assert event.consecutive_breaches == 3
        assert event.notification_sent is True
