import { useEffect, useRef, useCallback } from "react";
import { getToken } from "../api/client";

/**
 * WebSocket hook for real-time risk flag alerts.
 * Connects to /ws/alerts, handles ping/pong, auto-reconnect with backoff.
 *
 * @param {Function} onEvent - callback receiving parsed WS messages
 * @param {boolean} enabled - whether to connect (only when authenticated)
 */
export function useWebSocket(onEvent, enabled = true) {
  const wsRef = useRef(null);
  const retryRef = useRef(0);
  const timerRef = useRef(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (!enabled || wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/alerts`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      retryRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "pong") return;
        onEventRef.current?.(data);
      } catch {
        // ignore non-JSON messages
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
      if (!enabled) return;
      const delay = Math.min(1000 * Math.pow(2, retryRef.current), 30000);
      retryRef.current += 1;
      timerRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      // onclose will fire after this, handling reconnect
    };
  }, [enabled]);

  useEffect(() => {
    if (!enabled) {
      wsRef.current?.close();
      wsRef.current = null;
      return;
    }

    connect();

    // Send ping every 30 seconds to keep connection alive
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "ping" }));
      }
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      clearTimeout(timerRef.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [enabled, connect]);

  return wsRef;
}
