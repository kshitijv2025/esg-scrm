import { type Page, type Locator, expect } from "@playwright/test";

export class DashboardPage {
  readonly page: Page;
  readonly riskSummaryCard: Locator;
  readonly scope3Card: Locator;
  readonly alertBadge: Locator;
  readonly navLinks: Locator;

  constructor(page: Page) {
    this.page = page;
    this.riskSummaryCard = page.locator(
      "[data-testid='risk-summary'], .risk-summary",
    );
    this.scope3Card = page.locator(
      "[data-testid='scope3-summary'], .scope3-summary",
    );
    this.alertBadge = page.locator("[data-testid='alert-badge'], .alert-badge");
    this.navLinks = page.locator("nav a, aside a");
  }

  async goto() {
    await this.page.goto("/dashboard");
  }

  async expectLoaded() {
    await expect(this.page).toHaveURL(/\/dashboard/);
  }

  async expectRiskSummaryVisible() {
    await expect(this.riskSummaryCard.first()).toBeVisible();
  }

  async expectScope3Visible() {
    await expect(this.scope3Card.first()).toBeVisible();
  }

  async expectNoAuthError() {
    // No redirect back to login
    await expect(this.page).not.toHaveURL(/\/login/);
  }
}
