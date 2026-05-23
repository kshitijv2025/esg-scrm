import { type Page, type Locator, expect } from "@playwright/test";

export class SupplyChainPage {
  readonly page: Page;
  readonly addSupplierBtn: Locator;
  readonly supplierTable: Locator;
  readonly supplierNameInput: Locator;
  readonly countryInput: Locator;
  readonly saveBtn: Locator;

  constructor(page: Page) {
    this.page = page;
    this.addSupplierBtn = page.getByRole("button", { name: /add supplier/i });
    this.supplierTable = page.locator(
      "table.suppliers, [data-testid='supplier-table']",
    );
    this.supplierNameInput = page.getByLabel(/supplier name/i);
    this.countryInput = page.getByLabel(/country/i);
    this.saveBtn = page.getByRole("button", { name: /save/i });
  }

  async goto() {
    await this.page.goto("/supply-chain");
  }

  async expectLoaded() {
    await expect(this.page).toHaveURL(/\/supply-chain/);
  }

  async openAddSupplierForm() {
    await this.addSupplierBtn.click();
  }

  async fillSupplierForm(name: string, country: string) {
    await this.supplierNameInput.fill(name);
    await this.countryInput.fill(country);
  }

  async submitSupplier() {
    await this.saveBtn.click();
  }

  async expectSupplierInTable(name: string) {
    await expect(this.supplierTable.locator("text=" + name)).toBeVisible();
  }
}
