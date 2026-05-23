"""
Alert event models for real-time monitoring.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID


@dataclass
class AlertEvent:
    """Represents a single alert event in the monitoring system.

    Attributes:
        id: Unique identifier for this alert event instance.
        alert_id: Reference to the ThresholdAlert that triggered this event.
        metric_type: Type of metric that triggered the alert (e.g., "energy_kwh", "emissions_tco2").
        triggered_at: Timestamp when the alert was triggered.
        actual_value: The actual measured value that breached the threshold.
        actual_unit: Unit of the actual value (e.g., "kWh", "tCO2e").
        threshold_value: The threshold value that was breached.
        threshold_unit: Unit of the threshold value.
        comparison: Comparison operator used ("gt", "lt", "gte", "lte", "eq").
        consecutive_breaches: How many consecutive periods this threshold was breached.
        notification_sent: Whether a notification was sent for this event.
        acknowledged: Whether this alert has been acknowledged.
        acknowledged_by: User ID who acknowledged the alert.
        acknowledged_at: Timestamp when the alert was acknowledged.
    """

    id: UUID
    alert_id: UUID
    metric_type: str
    triggered_at: datetime
    actual_value: Decimal
    actual_unit: str
    threshold_value: Decimal
    threshold_unit: str
    comparison: str  # gt, lt, gte, lte, eq
    consecutive_breaches: int = 0
    notification_sent: bool = False
    acknowledged: bool = False
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate comparison operator."""
        valid_comparisons = {"gt", "lt", "gte", "lte", "eq"}
        if self.comparison not in valid_comparisons:
            raise ValueError(
                f"Invalid comparison operator: {self.comparison!r}. "
                f"Must be one of: {valid_comparisons}"
            )

    def is_breach(self, current_value: Decimal) -> bool:
        """Check if the current value breaches the threshold based on comparison operator.

        Args:
            current_value: The current metric value to check.

        Returns:
            True if the value breaches the threshold according to the comparison operator.
        """
        if self.comparison == "gt":
            return current_value > self.threshold_value
        elif self.comparison == "lt":
            return current_value < self.threshold_value
        elif self.comparison == "gte":
            return current_value >= self.threshold_value
        elif self.comparison == "lte":
            return current_value <= self.threshold_value
        elif self.comparison == "eq":
            return current_value == self.threshold_value
        return False

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "alert_id": str(self.alert_id),
            "metric_type": self.metric_type,
            "triggered_at": self.triggered_at.isoformat(),
            "actual_value": str(self.actual_value),
            "actual_unit": self.actual_unit,
            "threshold_value": str(self.threshold_value),
            "threshold_unit": self.threshold_unit,
            "comparison": self.comparison,
            "consecutive_breaches": self.consecutive_breaches,
            "notification_sent": self.notification_sent,
            "acknowledged": self.acknowledged,
            "acknowledged_by": str(self.acknowledged_by) if self.acknowledged_by else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AlertEvent":
        """Create AlertEvent from dictionary representation."""
        return cls(
            id=UUID(data["id"]),
            alert_id=UUID(data["alert_id"]),
            metric_type=data["metric_type"],
            triggered_at=datetime.fromisoformat(data["triggered_at"]),
            actual_value=Decimal(str(data["actual_value"])),
            actual_unit=data["actual_unit"],
            threshold_value=Decimal(str(data["threshold_value"])),
            threshold_unit=data["threshold_unit"],
            comparison=data["comparison"],
            consecutive_breaches=data.get("consecutive_breaches", 0),
            notification_sent=data.get("notification_sent", False),
            acknowledged=data.get("acknowledged", False),
            acknowledged_by=UUID(data["acknowledged_by"]) if data.get("acknowledged_by") else None,
            acknowledged_at=datetime.fromisoformat(data["acknowledged_at"])
            if data.get("acknowledged_at")
            else None,
        )
