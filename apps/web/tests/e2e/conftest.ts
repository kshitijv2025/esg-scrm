import { test as base, type BrowserContext } from "@playwright/test";

/**
 * E2E test configuration.
 *
 * Authentication strategy: call the real backend login endpoint to get a JWT,
 * then inject it into the browser's localStorage. This avoids managing
 * JWT secrets in test code and exercises the full auth pipeline.
 *
 * Test credentials match the seeded test user in src/db/seed.py.
 */

// Seeded test user from src/db/seed.py
// Override with E2E_TEST_EMAIL / E2E_TEST_PASSWORD env vars in CI
const API_BASE = process.env.E2E_API_URL || "http://localhost:8000";
const TEST_EMAIL = process.env.E2E_TEST_EMAIL || "admin@textilebd.com";
const TEST_PASSWORD = process.env.E2E_TEST_PASSWORD || "admin123";

export interface AuthenticatedPage {
  token: string;
  page: import("@playwright/test").Page;
}

export interface E2EFixtures {
  authenticatedPage: AuthenticatedPage;
  apiBase: string;
}

async function getAuthToken(context: BrowserContext): Promise<string> {
  // Request a token from the real backend login endpoint
  const response = await context.request.post(`${API_BASE}/api/auth/login`, {
    data: {
      email: TEST_EMAIL,
      password: TEST_PASSWORD,
    },
  });

  if (!response.ok()) {
    throw new Error(
      `E2E auth login failed (${response.status()}): ${await response.text()}. ` +
        `Is the backend running on ${API_BASE}? ` +
        `Seed data must include a user with email=${TEST_EMAIL} and password=${TEST_PASSWORD}`,
    );
  }

  const body = await response.json();
  // The login endpoint returns { token: "..." } or sets a cookie
  // Check for token in body first, then fall back to cookie
  if (body.token) return body.token;

  // If the API uses httpOnly cookies instead, the cookie is already
  // set on the response - we just need to use this context for API calls.
  // For browser-based testing with localStorage, we need the raw token.
  // If the backend returns 200 without a body token, the JWT secret may
  // not match between test and backend — surface an actionable error.
  throw new Error(
    `E2E auth: /api/auth/login returned 200 but no token in body. ` +
      `Backend may be using httpOnly cookies; E2E tests need JWT in localStorage. ` +
      `Response: ${await response.text()}`,
  );
}

export const test = base.extend<E2EFixtures>({
  async authenticatedPage({ browser }, use) {
    const context = await browser.newContext();
    let token: string;

    try {
      token = await getAuthToken(context);
    } catch (err) {
      await context.close();
      throw err;
    }

    // Inject the JWT into localStorage so the frontend app can read it
    // like it does during normal login (see src/api/client.js)
    await context.addInitScript((t) => {
      localStorage.setItem("esg_token", t);
    }, token);

    const page = await context.newPage();
    await use({ token, page });
    await context.close();
  },

  apiBase: API_BASE,
});

export { expect } from "@playwright/test";
