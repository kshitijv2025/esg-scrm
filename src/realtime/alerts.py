"""
WebSocket alerts endpoint — real-time push of new risk flags to connected dashboards.
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from fastapi import WebSocket, WebSocketDisconnect
except ImportError:
    WebSocket = None
    WebSocketDisconnect = None


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


async def push_acknowledgement(flag_id: str, acknowledged_by: str, org_id: Optional[str] = None) -> None:
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
                pass
    except WebSocketDisconnect:
        _alert_bus.disconnect(websocket)


def get_bus() -> AlertBus:
    return _alert_bus
