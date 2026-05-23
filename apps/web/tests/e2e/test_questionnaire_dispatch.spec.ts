import { test, expect } from "./conftest";
import { QuestionnaireDispatchPage } from "./pages/QuestionnaireDispatchPage";
import { SupplyChainPage } from "./pages/SupplyChainPage";

test.describe("Questionnaire Dispatch", () => {
  test("should navigate to supplier engagement page", async ({
    authenticatedPage,
  }) => {
    const { page } = authenticatedPage;

    const dispatchPage = new QuestionnaireDispatchPage(page);
    await dispatchPage.goto();
    await dispatchPage.expectLoaded();
  });

  test("should dispatch a questionnaire to a supplier", async ({
    authenticatedPage,
  }) => {
    const { page } = authenticatedPage;

    // First create a supplier to dispatch to
    const supplyChainPage = new SupplyChainPage(page);
    await supplyChainPage.goto();
    const supplierName = `Q-Supplier-${Date.now()}`;
    await supplyChainPage.openAddSupplierForm();
    await supplyChainPage.fillSupplierForm(supplierName, "Vietnam");
    await supplyChainPage.submitSupplier();

    // Now dispatch questionnaire
    const dispatchPage = new QuestionnaireDispatchPage(page);
    await dispatchPage.goto();
    await dispatchPage.selectQuestionnaire(0);
    await dispatchPage.selectSupplier(supplierName);
    await dispatchPage.dispatch();

    // Should show success
    await dispatchPage.expectDispatchSuccess();
  });
});
