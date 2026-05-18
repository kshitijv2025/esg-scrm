import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { AuthProvider, useAuth } from "../contexts/AuthContext";

function wrapper({ children }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe("AuthContext", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("starts with no user when no token stored", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    // Wait for loading to finish
    await vi.waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.user).toBeNull();
  });

  it("login sets user and stores token on success", async () => {
    const mockUser = {
      id: "usr_123",
      email: "test@example.com",
      full_name: "Test User",
      role: "admin",
    };

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ user: mockUser, token: "jwt-token-123" }),
      }),
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await vi.waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await act(async () => {
      await result.current.login("test@example.com", "password123");
    });

    expect(result.current.user).toEqual(mockUser);
    expect(localStorage.getItem("esg_token")).toBe("jwt-token-123");
  });

  it("login throws on invalid credentials", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: "Invalid email or password" }),
      }),
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await vi.waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await act(async () => {
      await expect(
        result.current.login("bad@example.com", "wrong"),
      ).rejects.toThrow("Invalid email or password");
    });
  });

  it("logout clears user and token", async () => {
    localStorage.setItem("esg_token", "some-token");

    // Mock /auth/me for initial load
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            user: { id: "1", email: "a@b.com", full_name: "A", role: "admin" },
          }),
      }),
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await vi.waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    act(() => {
      result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(localStorage.getItem("esg_token")).toBeNull();
  });

  it("register sets user and token on success", async () => {
    const mockUser = {
      id: "usr_new",
      email: "new@example.com",
      full_name: "New User",
      role: "admin",
    };

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            user: mockUser,
            token: "jwt-new-123",
            org: { id: "org_1", name: "Test Org" },
          }),
      }),
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await vi.waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await act(async () => {
      await result.current.register(
        "new@example.com",
        "pass123",
        "New User",
        "Test Org",
      );
    });

    expect(result.current.user).toEqual(mockUser);
    expect(localStorage.getItem("esg_token")).toBe("jwt-new-123");
  });

  it("useAuth throws when used outside AuthProvider", () => {
    expect(() => {
      renderHook(() => useAuth());
    }).toThrow("useAuth must be used within AuthProvider");
  });
});
