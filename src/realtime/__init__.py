"""
Real-time monitoring and alerting for ESG metrics.

Modules:
    alerts: WebSocket-based real-time alert broadcasting.
    alert_aggregator: Alert fatigue prevention logic.
    alert_models: AlertEvent dataclass.
    threshold_models: ThresholdAlert dataclass.
    risk_detector: Risk detection logic.
"""

from src.realtime.alert_aggregator import AlertAggregator
from src.realtime.alert_models import AlertEvent
from src.realtime.threshold_models import ThresholdAlert

__all__ = [
    "AlertAggregator",
    "AlertEvent",
    "ThresholdAlert",
]
