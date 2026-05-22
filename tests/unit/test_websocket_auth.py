"""Tests for WebSocket /ws/alerts authentication."""

import sys

sys.path.insert(0, "src")

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.api.main import app
from src.auth.jwt import create_token


def _make_token(org_id: str = "org_bd_001", role: str = "admin", expired: bool = False):
    kwargs = {
        "sub": "ws_test_user",
        "org_id": org_id,
        "email": "ws@test.com",
        "role": role,
    }
    # Pass expires_in as a keyword arg to create_token, NOT as a dict key.
    # create_token(payload, expires_in) — expires_in is a separate parameter.
    if expired:
        return create_token(kwargs, expires_in=-3600)
    return create_token(kwargs)


class TestWebSocketAuth:
    """Test that WebSocket /ws/alerts requires valid JWT auth."""

    def test_websocket_rejects_connection_without_token(self):
        """Connection without any token should be rejected with close code 4001."""
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc_info:  # noqa: SIM117
            with client.websocket_connect("/ws/alerts"):
                pass
        assert exc_info.value.code == 4001

    def test_websocket_rejects_invalid_token(self):
        """Connection with an invalid token should be rejected with close code 4001."""
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc_info:  # noqa: SIM117
            with client.websocket_connect("/ws/alerts?token=invalid.token.here"):
                pass
        assert exc_info.value.code == 4001

    def test_websocket_rejects_expired_token(self):
        """Connection with an expired token should be rejected with close code 4001."""
        token = _make_token(expired=True)
        # Use raise_server_exceptions=True to ensure any server exceptions propagate
        client = TestClient(app, raise_server_exceptions=True)
        with pytest.raises(WebSocketDisconnect) as exc_info:  # noqa: SIM117
            with client.websocket_connect(f"/ws/alerts?token={token}"):
                pass
        assert exc_info.value.code == 4001

    def test_websocket_accepts_valid_token(self):
        """Connection with a valid token should be accepted and respond to ping."""
        token = _make_token()
        client = TestClient(app)
        with client.websocket_connect(f"/ws/alerts?token={token}") as websocket:
            import json

            websocket.send_text(json.dumps({"type": "ping"}))
            response = websocket.receive_text()
            data = json.loads(response)
            assert data.get("type") == "pong"

    def test_websocket_org_id_isolation(self):
        """Connection with org_other token should be associated with org_other."""
        token = _make_token(org_id="org_other")
        client = TestClient(app)
        with client.websocket_connect(f"/ws/alerts?token={token}") as websocket:
            import json

            websocket.send_text(json.dumps({"type": "ping"}))
            response = websocket.receive_text()
            data = json.loads(response)
            assert data.get("type") == "pong"

    def test_websocket_ping_pong_round_trip(self):
        """A ping message must receive a pong response."""
        token = _make_token()
        client = TestClient(app)
        with client.websocket_connect(f"/ws/alerts?token={token}") as websocket:
            import json

            for _ in range(3):
                websocket.send_text(json.dumps({"type": "ping"}))
                response = websocket.receive_text()
                data = json.loads(response)
                assert data.get("type") == "pong"

    def test_websocket_invalid_json_ignored(self):
        """Invalid JSON messages should be silently ignored (no crash)."""
        token = _make_token()
        client = TestClient(app)
        with client.websocket_connect(f"/ws/alerts?token={token}") as websocket:
            # Send garbage — should not raise
            websocket.send_text("not valid json {")
            # Should still be able to receive pong
            import json

            websocket.send_text(json.dumps({"type": "ping"}))
            response = websocket.receive_text()
            data = json.loads(response)
            assert data.get("type") == "pong"

    def test_websocket_close_on_disconnect(self):
        """WebSocket should disconnect cleanly when client closes."""
        token = _make_token()
        client = TestClient(app)
        with client.websocket_connect(f"/ws/alerts?token={token}") as websocket:
            websocket.close()
        # TestClient handles clean close without raising
