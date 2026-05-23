"""
WebSocket alerts endpoint — real-time push of new risk flags to connected dashboards.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from fastapi import WebSocket, WebSocketDisconnect
except ImportError:
    WebSocket = None
    WebSocketDisconnect = None

# ---------------------------------------------------------------------------
# Alert recommendation and escalation helpers
# ---------------------------------------------------------------------------

_RECOMMENDATION_MAP = {
    ("energy_kwh", "WARNING"): "Review energy consumption patterns for efficiency gains.",
    ("energy_kwh", "CRITICAL"): "Suspend non-essential energy use pending investigation.",
    ("emissions_tco2", "WARNING"): "Audit emissions data for accuracy and completeness.",
    ("emissions_tco2", "CRITICAL"): "Develop a carbon reduction plan immediately.",
    ("water_m3", "WARNING"): "Inspect water usage and repair leaks.",
    ("water_m3", "CRITICAL"): "Implement water conservation measures.",
    ("scope3_category1", "WARNING"): "Engage suppliers on sustainability practices.",
    ("scope3_category1", "CRITICAL"): "Update supplier scorecard with updated criteria.",
    ("diesel_consumed", "WARNING"): "Justify diesel generator usage and explore alternatives.",
    (
        "diesel_consumed",
        "CRITICAL",
    ): "Ensure diesel generator use is fully documented and justified.",
    ("gender_pct", "WARNING"): "Review diversity hiring practices.",
    ("gender_pct", "CRITICAL"): "Address equity gaps in workforce representation.",
    ("safety_incidents", "WARNING"): "Conduct immediate safety audit.",
    ("safety_incidents", "CRITICAL"): "Report to regulatory bodies as required.",
    ("governance_score", "WARNING"): "Present findings to board for review.",
    ("governance_score", "CRITICAL"): "Commission an independent governance audit.",
}


def _get_recommendation(cluster: str, severity: str) -> str:
    """Return an action recommendation for a given cluster/severity combination."""
    key = (cluster.lower(), severity.upper())
    return _RECOMMENDATION_MAP.get(key, "Review and take appropriate action.")


def _should_escalate(timestamp: str, severity: str) -> tuple[bool, str]:
    """Determine if a flag should escalate based on age and severity."""
    try:
        from datetime import datetime as dt

        try:
            from datetime import UTC
        except ImportError:
            from datetime import timezone

            UTC = timezone.utc
        flag_time = dt.fromisoformat(timestamp)
        if flag_time.tzinfo is None:
            flag_time = flag_time.replace(tzinfo=UTC)
        age_hours = (dt.now(UTC) - flag_time).total_seconds() / 3600
        if severity.upper() == "CRITICAL":
            return False, severity
        if age_hours >= 72:
            return True, "CRITICAL"
        return False, severity
    except Exception:
        logging.getLogger("alerts").debug(
            "alerts.escalate.parse_error", timestamp=timestamp, severity=severity
        )
        return False, severity


class AlertBus:
    """
    In-process broadcast bus for real-time alerts.
    In production, replace with Redis pub/sub or a message queue.
    """

    MAX_CONNECTIONS = 100

    def __init__(self):
        self._connections: dict[Any, str] = {}  # websocket -> org_id

    async def connect(self, websocket: WebSocket, org_id: str) -> None:
        await websocket.accept()
        if len(self._connections) >= self.MAX_CONNECTIONS:
            await websocket.close(code=1013, reason="Max connections reached")
            return
        self._connections[websocket] = org_id

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            del self._connections[websocket]

    async def broadcast(self, event: dict[str, Any], org_id: Optional[str] = None) -> None:
        payload = json.dumps(event, default=str)
        disconnected = []
        for ws, ws_org in list(self._connections.items()):
            if org_id and ws_org != org_id:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                logging.getLogger("alerts").debug("alerts.broadcast.send_error", org_id=org_id)
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)


_alert_bus = AlertBus()


async def push_new_flag(flag: dict[str, Any], org_id: Optional[str] = None) -> None:
    """Call this whenever a new risk flag is created."""
    event = {
        "type": "new_flag",
        "data": flag,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await _alert_bus.broadcast(event, org_id=org_id)


async def push_acknowledgement(
    flag_id: str, acknowledged_by: str, org_id: Optional[str] = None
) -> None:
    """Call this whenever a flag is acknowledged."""
    event = {
        "type": "flag_acknowledged",
        "data": {"flag_id": flag_id, "acknowledged_by": acknowledged_by},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await _alert_bus.broadcast(event, org_id=org_id)


async def ws_alerts_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint: GET /ws/alerts
    Receives real-time risk flag events. Requires JWT auth via query param or header.
    """
    if WebSocket is None:
        return

    # Authenticate: accept token as query param (?token=...) or header
    from src.auth.jwt import decode_token

    token = websocket.query_params.get("token")
    if not token:
        auth_header = websocket.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    user = decode_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    org_id = user.get("org_id", "")
    await _alert_bus.connect(websocket, org_id=org_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                logging.getLogger("alerts.websocket").debug(
                    "websocket.ignored.non_json", data=data[:100]
                )
    except WebSocketDisconnect:
        _alert_bus.disconnect(websocket)


def get_bus() -> AlertBus:
    return _alert_bus
