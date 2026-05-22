import { test, expect } from "./conftest";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";

test.describe("Login and Authentication", () => {
  test("should redirect authenticated user away from /login to dashboard", async ({
    authenticatedPage,
  }) => {
    const { page } = authenticatedPage;

    // Authenticated user visiting /login should be redirected to dashboard
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    const dashboardPage = new DashboardPage(page);
    await dashboardPage.expectLoaded();
    await dashboardPage.expectNoAuthError();
  });

  test("should redirect unauthenticated users to login", async ({
    browser,
  }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    const dashboardPage = new DashboardPage(page);
    await dashboardPage.goto();

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
    await context.close();
  });

  test("should show error on invalid credentials", async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    await loginPage.login("wrong@email.com", "wrongpassword");
    await loginPage.expectErrorVisible();
  });
});
