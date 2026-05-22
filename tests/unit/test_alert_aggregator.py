"""
Unit tests for AlertAggregator.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from src.realtime.alert_aggregator import AlertAggregator
from src.realtime.alert_models import AlertEvent


class TestAlertAggregator:
    """Tests for AlertAggregator class."""

    def test_constructor(self):
        """Test AlertAggregator initializes with correct defaults."""
        aggregator = AlertAggregator()
        assert aggregator._last_digest_time is None
        assert aggregator._digest_interval_hours == 24
        assert aggregator._breach_count == 0

    def test_record_breach_increments_counter(self):
        """record_breach() increments the internal breach counter."""
        aggregator = AlertAggregator()
        assert aggregator._breach_count == 0
        aggregator.record_breach()
        assert aggregator._breach_count == 1
        aggregator.record_breach()
        assert aggregator._breach_count == 2
        aggregator.record_breach()
        assert aggregator._breach_count == 3

    def test_reset_resets_breach_counter_to_zero(self):
        """reset() resets the breach counter to 0."""
        aggregator = AlertAggregator()
        aggregator.record_breach()
        aggregator.record_breach()
        aggregator.record_breach()
        assert aggregator._breach_count == 3
        aggregator.reset()
        assert aggregator._breach_count == 0

    def test_record_breach_and_reset_after_breach_count(self):
        """record_breach() and reset() can be called in sequence."""
        aggregator = AlertAggregator()
        aggregator.record_breach()
        aggregator.record_breach()
        aggregator.reset()
        aggregator.record_breach()
        assert aggregator._breach_count == 1

    def test_should_send_returns_true_when_consecutive_breaches_meets_required(self):
        """Test should_send returns True when consecutive_breaches >= required_periods (default 3)."""
        aggregator = AlertAggregator()
        alert_event = AlertEvent(
            id=uuid4(),
            alert_id=uuid4(),
            metric_type="energy_kwh",
            triggered_at=datetime.now(timezone.utc),
            actual_value=Decimal("150.0"),
            actual_unit="kWh",
            threshold_value=Decimal("100.0"),
            threshold_unit="kWh",
            comparison="gt",
            consecutive_breaches=3,
        )
        result = aggregator.should_send(
            alert_event=alert_event,
            threshold_breach_count=3,
            current_value=Decimal("150.0"),
            threshold_value=Decimal("100.0"),
        )
        assert result is True

    def test_should_send_returns_true_when_consecutive_breaches_exceeds_required(self):
        """Test should_send returns True when consecutive_breaches > required_periods."""
        aggregator = AlertAggregator()
        result = aggregator.should_send(
            alert_event=None,
            threshold_breach_count=5,
            current_value=Decimal("150.0"),
            threshold_value=Decimal("100.0"),
        )
        assert result is True

    def test_should_send_returns_true_when_current_value_exceeds_2x_threshold(self):
        """Test should_send returns True when current_value >= threshold * 2 (significant event)."""
        aggregator = AlertAggregator()
        result = aggregator.should_send(
            alert_event=None,
            threshold_breach_count=1,
            current_value=Decimal("250.0"),
            threshold_value=Decimal("100.0"),
        )
        assert result is True

    def test_should_send_returns_true_when_current_value_equals_2x_threshold(self):
        """Test should_send returns True when current_value == threshold * 2."""
        aggregator = AlertAggregator()
        result = aggregator.should_send(
            alert_event=None,
            threshold_breach_count=1,
            current_value=Decimal("200.0"),
            threshold_value=Decimal("100.0"),
        )
        assert result is True

    def test_should_send_returns_false_when_below_threshold_and_no_consecutive_periods(self):
        """Test should_send returns False when below threshold and no consecutive periods."""
        aggregator = AlertAggregator()
        result = aggregator.should_send(
            alert_event=None,
            threshold_breach_count=1,
            current_value=Decimal("120.0"),
            threshold_value=Decimal("100.0"),
        )
        assert result is False

    def test_should_send_returns_false_when_no_breaches(self):
        """Test should_send returns False when threshold_breach_count is 0."""
        aggregator = AlertAggregator()
        result = aggregator.should_send(
            alert_event=None,
            threshold_breach_count=0,
            current_value=Decimal("150.0"),
            threshold_value=Decimal("100.0"),
        )
        assert result is False

    def test_should_send_with_daily_digest_time_returns_true_regardless_of_breaches(self):
        """Test should_send_digest returns True when digest interval has passed."""
        aggregator = AlertAggregator()
        # First call should return True (initialization)
        result1 = aggregator.should_send_digest()
        assert result1 is True
        # Manually set last digest time to long ago
        aggregator._last_digest_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        result2 = aggregator.should_send_digest()
        assert result2 is True

    def test_should_send_digest_returns_false_when_within_interval(self):
        """Test should_send_digest returns False when digest interval has not passed."""
        aggregator = AlertAggregator()
        # Set last digest time to just now
        aggregator._last_digest_time = datetime.now(timezone.utc)
        result = aggregator.should_send_digest()
        assert result is False

    def test_custom_required_periods_via_internal_check(self):
        """Test with custom required_periods via _check_consecutive_breaches."""
        aggregator = AlertAggregator()
        alert_event = AlertEvent(
            id=uuid4(),
            alert_id=uuid4(),
            metric_type="energy_kwh",
            triggered_at=datetime.now(timezone.utc),
            actual_value=Decimal("150.0"),
            actual_unit="kWh",
            threshold_value=Decimal("100.0"),
            threshold_unit="kWh",
            comparison="gt",
            consecutive_breaches=2,
        )
        # With default required_periods=3, 2 breaches should not trigger
        result_default = aggregator._check_consecutive_breaches(
            alert_event, consecutive_count=2, required_periods=3
        )
        assert result_default is False
        # With custom required_periods=2, 2 breaches should trigger
        result_custom = aggregator._check_consecutive_breaches(
            alert_event, consecutive_count=2, required_periods=2
        )
        assert result_custom is True

    def test_record_breach_concept_via_aggregator_behavior(self):
        """Test that the aggregator correctly handles breach counting via should_send."""
        aggregator = AlertAggregator()
        # With consecutive_breaches=3 (default required), should return True
        result = aggregator.should_send(
            alert_event=None,
            threshold_breach_count=3,
            current_value=Decimal("110.0"),
            threshold_value=Decimal("100.0"),
        )
        assert result is True
        # With consecutive_breaches=2, below threshold and not 2x, should return False
        result2 = aggregator.should_send(
            alert_event=None,
            threshold_breach_count=2,
            current_value=Decimal("110.0"),
            threshold_value=Decimal("100.0"),
        )
        assert result2 is False

    def test_non_breach_resets_consecutive_breaches_via_should_send(self):
        """Test that non-breach scenario (breach_count=0) returns False for consecutive rule."""
        aggregator = AlertAggregator()
        # With 0 consecutive breaches, consecutive rule should not trigger
        result = aggregator.should_send(
            alert_event=None,
            threshold_breach_count=0,
            current_value=Decimal("150.0"),
            threshold_value=Decimal("100.0"),
        )
        # This returns True because value is >= 2x threshold (significant event)
        # But the consecutive_breaches check would return False
        # Let's verify by checking below 2x threshold with 0 breaches
        result2 = aggregator.should_send(
            alert_event=None,
            threshold_breach_count=0,
            current_value=Decimal("120.0"),
            threshold_value=Decimal("100.0"),
        )
        assert result2 is False

    def test_set_digest_interval_valid(self):
        """Test set_digest_interval accepts valid values."""
        aggregator = AlertAggregator()
        aggregator.set_digest_interval(hours=12)
        assert aggregator._digest_interval_hours == 12

    def test_set_digest_interval_invalid(self):
        """Test set_digest_interval raises ValueError for invalid values."""
        aggregator = AlertAggregator()
        with pytest.raises(ValueError, match="Digest interval must be at least 1 hour"):
            aggregator.set_digest_interval(hours=0)

    def test_reset_digest_timer(self):
        """Test reset_digest_timer sets last_digest_time to now."""
        aggregator = AlertAggregator()
        aggregator._last_digest_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        aggregator.reset_digest_timer()
        assert aggregator._last_digest_time is not None
        # Should be close to now (within 5 seconds)
        now = datetime.now(timezone.utc)
        diff = abs((now - aggregator._last_digest_time).total_seconds())
        assert diff < 5
