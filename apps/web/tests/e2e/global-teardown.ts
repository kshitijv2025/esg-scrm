import { chromium } from "@playwright/test";

/**
 * Global teardown — runs once after all E2E tests finish.
 *
 * Responsibilities:
 * 1. Clean up any browser state from global-setup
 * 2. Remove the temp token file written by global-setup
 */
export default async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext();

  // Clean up temp token file
  try {
    const fs = await import("fs");
    const os = await import("os");
    const path = await import("path");
    const tokenPath = path.join(os.tmpdir(), "esg-e2e-token.txt");
    fs.unlinkSync(tokenPath);
  } catch {
    // Token file may not exist — that's fine
  }

  await browser.close();
};
