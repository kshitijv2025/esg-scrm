import { describe, it, expect, beforeEach, vi } from "vitest";

// apiFetch and helpers are module-scoped, so we test via exported functions
// and mock global fetch + localStorage

const TOKEN_KEY = "esg_token";

// We need to reimport after clearing localStorage
describe("api/client", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  describe("token management", () => {
    it("getToken returns null when no token stored", async () => {
      const { getToken } = await import("../api/client");
      expect(getToken()).toBeNull();
    });

    it("setToken/getToken round-trip works", async () => {
      const { setToken, getToken } = await import("../api/client");
      setToken("test-jwt-123");
      expect(getToken()).toBe("test-jwt-123");
    });

    it("clearToken removes stored token", async () => {
      const { setToken, clearToken, getToken } = await import("../api/client");
      setToken("test-jwt-123");
      clearToken();
      expect(getToken()).toBeNull();
    });
  });

  describe("AuthError", () => {
    it("is an Error subclass with correct name", async () => {
      const { AuthError } = await import("../api/client");
      const err = new AuthError("Session expired");
      expect(err).toBeInstanceOf(Error);
      expect(err.name).toBe("AuthError");
      expect(err.message).toBe("Session expired");
    });
  });

  describe("ApiError", () => {
    it("stores status code", async () => {
      const { ApiError } = await import("../api/client");
      const err = new ApiError(404, "Not found");
      expect(err).toBeInstanceOf(Error);
      expect(err.name).toBe("ApiError");
      expect(err.status).toBe(404);
      expect(err.message).toBe("Not found");
    });
  });

  describe("apiFetch", () => {
    it("prepends /api to relative paths", async () => {
      const { setToken } = await import("../api/client");
      setToken("tok");

      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      });
      vi.stubGlobal("fetch", mockFetch);

      const { apiFetch } = await import("../api/client");
      await apiFetch("/dashboard/live");

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/dashboard/live",
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer tok",
          }),
        }),
      );
    });

    it("does not double-prefix /api paths", async () => {
      const { setToken } = await import("../api/client");
      setToken("tok");

      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      });
      vi.stubGlobal("fetch", mockFetch);

      const { apiFetch } = await import("../api/client");
      await apiFetch("/api/auth/me");

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/auth/me",
        expect.any(Object),
      );
    });

    it("throws ApiError on non-401 failure", async () => {
      const { setToken, ApiError } = await import("../api/client");
      setToken("tok");

      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 500,
          text: () => Promise.resolve("Internal Server Error"),
        }),
      );

      const { apiFetch } = await import("../api/client");
      await expect(apiFetch("/dashboard/live")).rejects.toThrow(ApiError);
    });

    it("dispatches auth:logout and throws AuthError on 401 when refresh fails", async () => {
      const { setToken, AuthError } = await import("../api/client");
      setToken("expired-tok");

      const dispatchSpy = vi.spyOn(window, "dispatchEvent");

      // First call: 401 response. Second call (refresh): failure.
      vi.stubGlobal(
        "fetch",
        vi
          .fn()
          .mockResolvedValueOnce({
            ok: false,
            status: 401,
            text: () => Promise.resolve("Unauthorized"),
          })
          .mockResolvedValueOnce({
            ok: false,
            status: 401,
          }),
      );

      const { apiFetch } = await import("../api/client");
      await expect(apiFetch("/dashboard/live")).rejects.toThrow(AuthError);
      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({ type: "auth:logout" }),
      );
    });
  });
});
