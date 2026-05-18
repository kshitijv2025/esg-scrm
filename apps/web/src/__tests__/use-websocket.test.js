import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useWebSocket } from "../hooks/useWebSocket";

const ORIGINAL_WS = globalThis.WebSocket;

function createMockWS() {
  const instances = [];
  const ctor = vi.fn(function (url) {
    this.url = url;
    this.readyState = 0;
    this.onopen = null;
    this.onmessage = null;
    this.onclose = null;
    this.onerror = null;
    this.send = vi.fn();
    this.close = vi.fn();
    instances.push(this);
  });
  ctor.CONNECTING = 0;
  ctor.OPEN = 1;
  ctor.CLOSING = 2;
  ctor.CLOSED = 3;
  return { ctor, instances };
}

describe("useWebSocket", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    globalThis.WebSocket = ORIGINAL_WS;
  });

  it("does not connect when enabled is false", () => {
    const { ctor } = createMockWS();
    globalThis.WebSocket = ctor;

    renderHook(() => useWebSocket(vi.fn(), false));

    expect(ctor).not.toHaveBeenCalled();
  });

  it("returns a ref object", () => {
    const { ctor } = createMockWS();
    globalThis.WebSocket = ctor;

    const { result } = renderHook(() => useWebSocket(vi.fn(), true));

    expect(result.current).toBeDefined();
    expect(result.current).toHaveProperty("current");
  });

  it("attempts WebSocket connection when enabled", async () => {
    const { ctor, instances } = createMockWS();
    globalThis.WebSocket = ctor;

    renderHook(() => useWebSocket(vi.fn(), true));

    await waitFor(() => {
      expect(instances.length).toBeGreaterThan(0);
    });

    expect(instances[0].url).toMatch(/ws.*:\/\/.*\/ws\/alerts/);
  });
});
