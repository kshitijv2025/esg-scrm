"""
Threshold alert configuration models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID


@dataclass
class ThresholdAlert:
    """Defines a threshold-based alert configuration.

    Attributes:
        id: Unique identifier for this alert configuration.
        organization_id: Organization this alert belongs to.
        metric_type: Type of metric to monitor (e.g., "energy_kwh", "emissions_tco2").
        threshold_value: The threshold value for triggering alerts.
        threshold_unit: Unit of the threshold value.
        comparison: Comparison operator for threshold evaluation.
        window: Time window for aggregation ("hourly", "daily", "weekly").
        action: Notification action ("email", "whatsapp", "dashboard_badge", "all").
        recipient_emails: List of email addresses for notifications.
        recipient_whatsapp: WhatsApp number for notifications.
        consecutive_periods_before_alert: Number of consecutive periods to breach before alerting.
        active: Whether this alert configuration is active.
        created_at: When this alert was created.
    """

    id: UUID
    organization_id: UUID
    metric_type: str
    threshold_value: Decimal
    threshold_unit: str
    comparison: str  # gt, lt, gte, lte, eq
    window: str  # hourly, daily, weekly
    action: str  # email, whatsapp, dashboard_badge, all
    recipient_emails: list[str] = field(default_factory=list)
    recipient_whatsapp: Optional[str] = None
    consecutive_periods_before_alert: int = 3
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate fields and set defaults."""
        valid_comparisons = {"gt", "lt", "gte", "lte", "eq"}
        if self.comparison not in valid_comparisons:
            raise ValueError(
                f"Invalid comparison operator: {self.comparison!r}. "
                f"Must be one of: {valid_comparisons}"
            )

        valid_windows = {"hourly", "daily", "weekly"}
        if self.window not in valid_windows:
            raise ValueError(f"Invalid window: {self.window!r}. Must be one of: {valid_windows}")

        valid_actions = {"email", "whatsapp", "dashboard_badge", "all"}
        if self.action not in valid_actions:
            raise ValueError(f"Invalid action: {self.action!r}. Must be one of: {valid_actions}")

        if self.consecutive_periods_before_alert < 1:
            raise ValueError(
                "consecutive_periods_before_alert must be at least 1, "
                f"got {self.consecutive_periods_before_alert}"
            )

    def should_notify(self, consecutive_breaches: int, current_value: Decimal) -> bool:
        """Determine if notification should be sent based on fatigue rules.

        Args:
            consecutive_breaches: Number of consecutive periods the threshold was breached.
            current_value: The current metric value.

        Returns:
            True if notification should be sent based on:
            - Threshold breached for N consecutive periods (default 3)
            - OR breach exceeds 2x threshold (significant event)
        """
        from src.realtime.alert_aggregator import AlertAggregator

        aggregator = AlertAggregator()
        return aggregator.should_send(
            alert_event=None,  # Not used in current implementation
            threshold_breach_count=consecutive_breaches,
            current_value=current_value,
            threshold_value=self.threshold_value,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "metric_type": self.metric_type,
            "threshold_value": str(self.threshold_value),
            "threshold_unit": self.threshold_unit,
            "comparison": self.comparison,
            "window": self.window,
            "action": self.action,
            "recipient_emails": self.recipient_emails,
            "recipient_whatsapp": self.recipient_whatsapp,
            "consecutive_periods_before_alert": self.consecutive_periods_before_alert,
            "active": self.active,
            "created_at": self.created_at.isoformat()
            if isinstance(self.created_at, datetime)
            else self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ThresholdAlert":
        """Create ThresholdAlert from dictionary representation."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()

        return cls(
            id=UUID(data["id"]),
            organization_id=UUID(data["organization_id"]),
            metric_type=data["metric_type"],
            threshold_value=Decimal(str(data["threshold_value"])),
            threshold_unit=data["threshold_unit"],
            comparison=data["comparison"],
            window=data["window"],
            action=data["action"],
            recipient_emails=data.get("recipient_emails", []),
            recipient_whatsapp=data.get("recipient_whatsapp"),
            consecutive_periods_before_alert=data.get("consecutive_periods_before_alert", 3),
            active=data.get("active", True),
            created_at=created_at,
        )
