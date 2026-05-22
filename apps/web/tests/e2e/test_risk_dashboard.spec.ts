import { test, expect } from "./conftest";
import { DashboardPage } from "./pages/DashboardPage";

test.describe("Risk Dashboard", () => {
  test("should display risk summary after login", async ({
    authenticatedPage,
  }) => {
    const { page } = authenticatedPage;

    const dashboardPage = new DashboardPage(page);
    await dashboardPage.goto();
    await dashboardPage.expectLoaded();
    await dashboardPage.expectNoAuthError();

    // Risk summary section should be visible
    await dashboardPage.expectRiskSummaryVisible();
  });

  test("should display scope3 emissions data", async ({
    authenticatedPage,
  }) => {
    const { page } = authenticatedPage;

    const dashboardPage = new DashboardPage(page);
    await dashboardPage.goto();
    await dashboardPage.expectScope3Visible();
  });

  test("should show no auth errors on page load", async ({
    authenticatedPage,
  }) => {
    const { page } = authenticatedPage;

    const dashboardPage = new DashboardPage(page);
    await dashboardPage.goto();
    await dashboardPage.expectNoAuthError();
  });
});
