import { test, expect } from "./conftest";
import { SupplyChainPage } from "./pages/SupplyChainPage";

test.describe("Supplier Creation", () => {
  test("should navigate to supply chain page", async ({
    authenticatedPage,
  }) => {
    const { page } = authenticatedPage;

    const supplyChainPage = new SupplyChainPage(page);
    await supplyChainPage.goto();
    await supplyChainPage.expectLoaded();
  });

  test("should create a new supplier", async ({ authenticatedPage }) => {
    const { page } = authenticatedPage;

    const supplyChainPage = new SupplyChainPage(page);
    await supplyChainPage.goto();

    const supplierName = `Test Supplier ${Date.now()}`;
    const country = "Bangladesh";

    await supplyChainPage.openAddSupplierForm();
    await supplyChainPage.fillSupplierForm(supplierName, country);
    await supplyChainPage.submitSupplier();

    // Verify supplier appears in the table
    await supplyChainPage.expectSupplierInTable(supplierName);
  });
});
