"""
WebSocket alerts endpoint — real-time push of new risk flags to connected dashboards.
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Any

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
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        if len(self._connections) >= self.MAX_CONNECTIONS:
            await websocket.close(code=1013, reason="Max connections reached")
            return
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, event: dict[str, Any]) -> None:
        payload = json.dumps(event, default=str)
        disconnected = []
        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)


_alert_bus = AlertBus()


async def push_new_flag(flag: dict[str, Any]) -> None:
    """Call this whenever a new risk flag is created."""
    event = {
        "type": "new_flag",
        "data": flag,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await _alert_bus.broadcast(event)


async def push_acknowledgement(flag_id: str, acknowledged_by: str) -> None:
    """Call this whenever a flag is acknowledged."""
    event = {
        "type": "flag_acknowledged",
        "data": {"flag_id": flag_id, "acknowledged_by": acknowledged_by},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await _alert_bus.broadcast(event)


async def ws_alerts_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint: GET /ws/alerts
    Receives real-time risk flag events.
    """
    if WebSocket is None:
        return
    await _alert_bus.connect(websocket)
    try:
        while True:
            # Keep connection alive — client can send ping/pong
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
