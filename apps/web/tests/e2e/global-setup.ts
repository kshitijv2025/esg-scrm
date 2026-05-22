import { chromium } from "@playwright/test";

/**
 * Global setup — runs once before all E2E tests.
 *
 * Responsibilities:
 * 1. Verify the backend is reachable and seeded
 * 2. Install a pre-generated auth token into a shared "auth storage"
 *   so individual tests can restore it without re-logging in each time.
 *
 * The backend must already be running at E2E_API_URL before E2E tests start.
 * For local dev: `cd apps/web && npm run dev` (frontend) and
 * `cd src && uvicorn api.main:app --reload` (backend) in parallel.
 *
 * For CI: a separate job starts both servers before the E2E job runs.
 */
export default async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();

  const apiBase = process.env.E2E_API_URL || "http://localhost:8000";

  // Verify backend is reachable
  try {
    const resp = await context.request.get(`${apiBase}/api/dashboard/live`);
    // 401 means backend is up (auth required), 200 means health OK
    if (resp.status() === 0) {
      // ECONNREFUSED — backend not running
      throw new Error(
        `Cannot reach backend at ${apiBase}. ` +
          `Start the backend with: cd src && uvicorn api.main:app --reload ` +
          `and the frontend with: cd apps/web && npm run dev`,
      );
    }
  } catch (err) {
    if (err instanceof Error && err.message.includes("ECONNREFUSED")) {
      throw new Error(
        `Cannot reach backend at ${apiBase}. ` +
          `Start the backend with: cd src && uvicorn api.main:app --reload ` +
          `and the frontend with: cd apps/web && npm run dev`,
      );
    }
    throw err;
  }

  // Obtain a valid JWT for the seeded admin user
  const loginResp = await context.request.post(`${apiBase}/api/auth/login`, {
    data: { email: "admin@textilebd.com", password: "admin123" },
  });

  if (!loginResp.ok()) {
    const status = loginResp.status();
    const body = await loginResp.text();
    throw new Error(
      `E2E global setup: /api/auth/login failed (${status}). ` +
        `Body: ${body}. ` +
        `Verify the backend is running and the database is seeded.`,
    );
  }

  const { token } = await loginResp.json();
  if (!token) {
    throw new Error(
      `E2E global setup: /api/auth/login returned 200 but no token. ` +
        `Response: ${await loginResp.text()}`,
    );
  }

  // Persist token for use in browser contexts
  await context.storageState({
    storageState: {
      cookies: [],
      // playwright doesn't expose localStorage via storageState directly,
      // so we store in a file and inject via addInitScript in conftest.
      origins: [],
    },
  });

  // Write token to a temp file so conftest can read it
  const fs = await import("fs");
  const os = await import("os");
  const path = await import("path");
  const tokenPath = path.join(os.tmpdir(), "esg-e2e-token.txt");
  fs.writeFileSync(tokenPath, token, "utf-8");

  await browser.close();
};
