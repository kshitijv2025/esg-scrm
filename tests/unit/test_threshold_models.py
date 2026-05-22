"""
Unit tests for ThresholdAlert model.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from src.realtime.threshold_models import ThresholdAlert


class TestThresholdAlert:
    """Tests for ThresholdAlert dataclass."""

    def test_create_with_all_fields(self):
        """Test ThresholdAlert creation with all fields specified."""
        now = datetime.now(timezone.utc)
        alert_id = uuid4()
        org_id = uuid4()

        alert = ThresholdAlert(
            id=alert_id,
            organization_id=org_id,
            metric_type="emissions_tco2",
            threshold_value=Decimal("1000.0"),
            threshold_unit="tCO2e",
            comparison="gt",
            window="daily",
            action="email",
            recipient_emails=["test@example.com", "admin@example.com"],
            recipient_whatsapp="+1234567890",
            consecutive_periods_before_alert=5,
            active=True,
            created_at=now,
        )

        assert alert.id == alert_id
        assert alert.organization_id == org_id
        assert alert.metric_type == "emissions_tco2"
        assert alert.threshold_value == Decimal("1000.0")
        assert alert.threshold_unit == "tCO2e"
        assert alert.comparison == "gt"
        assert alert.window == "daily"
        assert alert.action == "email"
        assert alert.recipient_emails == ["test@example.com", "admin@example.com"]
        assert alert.recipient_whatsapp == "+1234567890"
        assert alert.consecutive_periods_before_alert == 5
        assert alert.active is True
        assert alert.created_at == now

    def test_create_with_minimal_fields(self):
        """Test ThresholdAlert creation with only required fields."""
        alert_id = uuid4()
        org_id = uuid4()

        alert = ThresholdAlert(
            id=alert_id,
            organization_id=org_id,
            metric_type="energy_kwh",
            threshold_value=Decimal("500.0"),
            threshold_unit="kWh",
            comparison="gt",
            window="hourly",
            action="all",
        )

        assert alert.id == alert_id
        assert alert.organization_id == org_id
        assert alert.metric_type == "energy_kwh"
        assert alert.threshold_value == Decimal("500.0")
        assert alert.threshold_unit == "kWh"
        assert alert.comparison == "gt"
        assert alert.window == "hourly"
        assert alert.action == "all"
        assert alert.recipient_emails == []  # default
        assert alert.recipient_whatsapp is None  # default
        assert alert.consecutive_periods_before_alert == 3  # default
        assert alert.active is True  # default

    def test_consecutive_periods_default_value_is_3(self):
        """Test consecutive_periods_before_alert defaults to 3."""
        alert = ThresholdAlert(
            id=uuid4(),
            organization_id=uuid4(),
            metric_type="water_gallons",
            threshold_value=Decimal("10000.0"),
            threshold_unit="gallons",
            comparison="gt",
            window="weekly",
            action="dashboard_badge",
        )
        assert alert.consecutive_periods_before_alert == 3

    def test_custom_consecutive_periods_before_alert(self):
        """Test with custom consecutive_periods_before_alert value."""
        alert = ThresholdAlert(
            id=uuid4(),
            organization_id=uuid4(),
            metric_type="waste_kg",
            threshold_value=Decimal("500.0"),
            threshold_unit="kg",
            comparison="gt",
            window="daily",
            action="email",
            consecutive_periods_before_alert=7,
        )
        assert alert.consecutive_periods_before_alert == 7

    def test_invalid_comparison_operator_raises(self):
        """Test that invalid comparison operator raises ValueError."""
        with pytest.raises(ValueError, match="Invalid comparison operator"):
            ThresholdAlert(
                id=uuid4(),
                organization_id=uuid4(),
                metric_type="energy_kwh",
                threshold_value=Decimal("500.0"),
                threshold_unit="kWh",
                comparison="invalid",
                window="daily",
                action="email",
            )

    def test_invalid_window_raises(self):
        """Test that invalid window raises ValueError."""
        with pytest.raises(ValueError, match="Invalid window"):
            ThresholdAlert(
                id=uuid4(),
                organization_id=uuid4(),
                metric_type="energy_kwh",
                threshold_value=Decimal("500.0"),
                threshold_unit="kWh",
                comparison="gt",
                window="monthly",  # invalid
                action="email",
            )

    def test_invalid_action_raises(self):
        """Test that invalid action raises ValueError."""
        with pytest.raises(ValueError, match="Invalid action"):
            ThresholdAlert(
                id=uuid4(),
                organization_id=uuid4(),
                metric_type="energy_kwh",
                threshold_value=Decimal("500.0"),
                threshold_unit="kWh",
                comparison="gt",
                window="daily",
                action="sms",  # invalid
            )

    def test_consecutive_periods_less_than_1_raises(self):
        """Test that consecutive_periods_before_alert < 1 raises ValueError."""
        with pytest.raises(ValueError, match="consecutive_periods_before_alert must be at least 1"):
            ThresholdAlert(
                id=uuid4(),
                organization_id=uuid4(),
                metric_type="energy_kwh",
                threshold_value=Decimal("500.0"),
                threshold_unit="kWh",
                comparison="gt",
                window="daily",
                action="email",
                consecutive_periods_before_alert=0,
            )

    def test_should_notify_with_consecutive_breaches(self):
        """Test should_notify returns True when consecutive breaches meet threshold."""
        alert = ThresholdAlert(
            id=uuid4(),
            organization_id=uuid4(),
            metric_type="energy_kwh",
            threshold_value=Decimal("100.0"),
            threshold_unit="kWh",
            comparison="gt",
            window="daily",
            action="email",
            consecutive_periods_before_alert=3,
        )
        # 3 consecutive breaches (default required), below 2x threshold
        result = alert.should_notify(consecutive_breaches=3, current_value=Decimal("120.0"))
        assert result is True

    def test_should_notify_with_2x_threshold_breach(self):
        """Test should_notify returns True when value >= 2x threshold."""
        alert = ThresholdAlert(
            id=uuid4(),
            organization_id=uuid4(),
            metric_type="emissions_tco2",
            threshold_value=Decimal("100.0"),
            threshold_unit="tCO2e",
            comparison="gt",
            window="daily",
            action="email",
            consecutive_periods_before_alert=3,
        )
        # Value is exactly 2x threshold
        result = alert.should_notify(consecutive_breaches=1, current_value=Decimal("200.0"))
        assert result is True

    def test_should_notify_returns_false_when_below_threshold(self):
        """Test should_notify returns False when below threshold and not 2x."""
        alert = ThresholdAlert(
            id=uuid4(),
            organization_id=uuid4(),
            metric_type="energy_kwh",
            threshold_value=Decimal("100.0"),
            threshold_unit="kWh",
            comparison="gt",
            window="daily",
            action="email",
            consecutive_periods_before_alert=3,
        )
        # Only 1 breach, value is 1.5x threshold (not significant enough alone)
        result = alert.should_notify(consecutive_breaches=1, current_value=Decimal("150.0"))
        assert result is False

    def test_to_dict(self):
        """Test to_dict returns correct dictionary."""
        now = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        alert_id = uuid4()
        org_id = uuid4()

        alert = ThresholdAlert(
            id=alert_id,
            organization_id=org_id,
            metric_type="emissions_tco2",
            threshold_value=Decimal("1000.0"),
            threshold_unit="tCO2e",
            comparison="gt",
            window="daily",
            action="email",
            recipient_emails=["test@example.com"],
            consecutive_periods_before_alert=5,
            active=True,
            created_at=now,
        )

        result = alert.to_dict()

        assert result["id"] == str(alert_id)
        assert result["organization_id"] == str(org_id)
        assert result["metric_type"] == "emissions_tco2"
        assert result["threshold_value"] == "1000.0"
        assert result["threshold_unit"] == "tCO2e"
        assert result["comparison"] == "gt"
        assert result["window"] == "daily"
        assert result["action"] == "email"
        assert result["recipient_emails"] == ["test@example.com"]
        assert result["consecutive_periods_before_alert"] == 5
        assert result["active"] is True
        assert result["created_at"] == now.isoformat()

    def test_from_dict(self):
        """Test from_dict creates ThresholdAlert correctly."""
        now = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        alert_id = uuid4()
        org_id = uuid4()

        data = {
            "id": str(alert_id),
            "organization_id": str(org_id),
            "metric_type": "emissions_tco2",
            "threshold_value": "1000.0",
            "threshold_unit": "tCO2e",
            "comparison": "gt",
            "window": "daily",
            "action": "email",
            "recipient_emails": ["test@example.com"],
            "consecutive_periods_before_alert": 5,
            "active": True,
            "created_at": now.isoformat(),
        }

        alert = ThresholdAlert.from_dict(data)

        assert alert.id == alert_id
        assert alert.organization_id == org_id
        assert alert.metric_type == "emissions_tco2"
        assert alert.threshold_value == Decimal("1000.0")
        assert alert.threshold_unit == "tCO2e"
        assert alert.comparison == "gt"
        assert alert.window == "daily"
        assert alert.action == "email"
        assert alert.recipient_emails == ["test@example.com"]
        assert alert.consecutive_periods_before_alert == 5
        assert alert.active is True
        assert alert.created_at == now

    def test_from_dict_with_defaults(self):
        """Test from_dict uses defaults for missing optional fields."""
        alert_id = uuid4()
        org_id = uuid4()

        data = {
            "id": str(alert_id),
            "organization_id": str(org_id),
            "metric_type": "energy_kwh",
            "threshold_value": "500.0",
            "threshold_unit": "kWh",
            "comparison": "gt",
            "window": "hourly",
            "action": "all",
        }

        alert = ThresholdAlert.from_dict(data)

        assert alert.recipient_emails == []
        assert alert.recipient_whatsapp is None
        assert alert.consecutive_periods_before_alert == 3  # default
        assert alert.active is True  # default
        assert alert.created_at is not None  # defaults to utcnow
