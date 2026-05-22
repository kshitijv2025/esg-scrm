"""
Alert aggregator with fatigue prevention for ESG monitoring.

Only sends alerts when:
1. Threshold breached for N consecutive periods (not one-off spike)
2. OR breach exceeds 2x threshold (significant event)
3. Or daily digest time (batch alerts)
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import structlog

from src.realtime.alert_models import AlertEvent

logger = structlog.get_logger(__name__)


class AlertAggregator:
    """Alert fatigue prevention for ESG monitoring.

    Implements rules to prevent alert fatigue:
    - Only alerts when threshold breached for N consecutive periods
    - OR when breach exceeds 2x threshold (significant event)
    - Daily digest mode for batch alerts
    """

    def __init__(self) -> None:
        """Initialize the alert aggregator."""
        self._last_digest_time: Optional[datetime] = None
        self._digest_interval_hours: int = 24
        self._breach_count: int = 0

    def record_breach(self) -> None:
        """Increment the internal breach counter."""
        self._breach_count += 1

    def reset(self) -> None:
        """Reset the breach counter to 0."""
        self._breach_count = 0

    def should_send(
        self,
        alert_event: Optional[AlertEvent],
        threshold_breach_count: int,
        current_value: Decimal,
        threshold_value: Decimal,
    ) -> bool:
        """Determine if alert should be sent based on fatigue rules.

        An alert is sent if ANY of these conditions are met:
        1. Consecutive breaches >= required_periods (default 3) - not a one-off spike
        2. Current value >= threshold_value * 2 - significant event
        3. Daily digest time

        Args:
            alert_event: The alert event (currently unused but available for future logic).
            threshold_breach_count: How many consecutive periods the threshold was breached.
            current_value: The actual current metric value.
            threshold_value: The threshold value being compared against.

        Returns:
            True if the alert should be sent, False to suppress.
        """
        # Check consecutive breaches rule
        if self._check_consecutive_breaches(
            alert_event, threshold_breach_count, required_periods=3
        ):
            logger.debug(
                "alert.suppress",
                reason="consecutive_breaches",
                breach_count=threshold_breach_count,
                current_value=str(current_value),
                threshold_value=str(threshold_value),
            )
            return True

        # Check magnitude breach rule (2x threshold = significant event)
        if self._check_magnitude_breach(current_value, threshold_value, multiplier=2.0):
            logger.debug(
                "alert.suppress",
                reason="magnitude_breach",
                current_value=str(current_value),
                threshold_value=str(threshold_value),
                ratio=float(current_value / threshold_value) if threshold_value != 0 else None,
            )
            return True

        # Suppress alert
        logger.debug(
            "alert.send_suppressed",
            reason="alert_fatigue",
            breach_count=threshold_breach_count,
            current_value=str(current_value),
            threshold_value=str(threshold_value),
        )
        return False

    def _check_consecutive_breaches(
        self,
        alert_event: Optional[AlertEvent],
        consecutive_count: int,
        required_periods: int = 3,
    ) -> bool:
        """Check if threshold breached for N consecutive periods.

        Args:
            alert_event: The alert event (available for future detailed checks).
            consecutive_count: Number of consecutive periods breached.
            required_periods: Number of periods required before alerting.

        Returns:
            True if consecutive breaches meet or exceed required periods.
        """
        if consecutive_count <= 0:
            return False
        return consecutive_count >= required_periods

    def _check_magnitude_breach(
        self,
        current_value: Decimal,
        threshold_value: Decimal,
        multiplier: float = 2.0,
    ) -> bool:
        """Check if breach exceeds 2x threshold (significant event).

        A 2x breach indicates a significant event that warrants immediate
        notification regardless of consecutive breach count.

        Args:
            current_value: The actual current metric value.
            threshold_value: The threshold value being compared against.
            multiplier: The multiplier for significant event detection (default 2.0).

        Returns:
            True if current_value >= threshold_value * multiplier.
        """
        if threshold_value <= 0:
            return False
        return current_value >= threshold_value * Decimal(str(multiplier))

    def should_send_digest(self) -> bool:
        """Check if it's time for a daily digest.

        Returns:
            True if the digest interval has passed since last digest.
        """
        now = datetime.now(timezone.utc)
        if self._last_digest_time is None:
            self._last_digest_time = now
            return True

        hours_since_digest = (now - self._last_digest_time).total_seconds() / 3600
        if hours_since_digest >= self._digest_interval_hours:
            self._last_digest_time = now
            logger.info(
                "alert.digest", digest_event="triggered", hours_since_last=hours_since_digest
            )
            return True

        return False

    def set_digest_interval(self, hours: int) -> None:
        """Set the digest interval in hours.

        Args:
            hours: Number of hours between digest notifications.
        """
        if hours < 1:
            raise ValueError(f"Digest interval must be at least 1 hour, got {hours}")
        self._digest_interval_hours = hours

    def reset_digest_timer(self) -> None:
        """Reset the digest timer to now."""
        self._last_digest_time = datetime.now(timezone.utc)
