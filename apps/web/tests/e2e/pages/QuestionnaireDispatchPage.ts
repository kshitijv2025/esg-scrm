import { type Page, type Locator, expect } from "@playwright/test";

export class QuestionnaireDispatchPage {
  readonly page: Page;
  readonly questionnaireCards: Locator;
  readonly supplierSelect: Locator;
  readonly sendBtn: Locator;
  readonly successToast: Locator;

  constructor(page: Page) {
    this.page = page;
    this.questionnaireCards = page.locator(
      "[data-testid='questionnaire-card'], .questionnaire-card",
    );
    this.supplierSelect = page.locator(
      "select, [data-testid='supplier-select']",
    );
    this.sendBtn = page.getByRole("button", { name: /send|dispatch/i });
    this.successToast = page.locator(
      "[data-testid='toast-success'], .toast-success",
    );
  }

  async goto() {
    await this.page.goto("/supplier-engagement");
  }

  async expectLoaded() {
    await expect(this.page).toHaveURL(/\/supplier-engagement/);
  }

  async selectQuestionnaire(index: number) {
    await this.questionnaireCards.nth(index).click();
  }

  async selectSupplier(supplierName: string) {
    await this.supplierSelect.selectOption({ label: supplierName });
  }

  async dispatch() {
    await this.sendBtn.click();
  }

  async expectDispatchSuccess() {
    await expect(this.successToast.first()).toBeVisible({ timeout: 5000 });
  }
}
