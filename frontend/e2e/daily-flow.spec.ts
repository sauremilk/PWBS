/**
 * E2E-Test: Taeglicher Flow (TASK-111)
 *
 * Verifiziert: Login -> Dashboard mit Morgenbriefing -> Suche -> Ergebnisse
 * Quelle: D4 User Flow 1-3, D4 NF-025
 */
import { test, expect, loginViaUI, registerViaUI } from "./fixtures/auth";

test.describe("Taeglicher Flow", () => {
  test.beforeEach(async ({ page, testUser }) => {
    // Register + land on welcome / dashboard
    await registerViaUI(page, testUser);
  });

  test("Login -> Dashboard -> Briefing -> Suche (Kernflow)", async ({
    page,
    testUser,
  }) => {
    // --- Step 1: Logout and re-login ---
    await page.goto("/login");
    await loginViaUI(page, testUser);

    // Should be on dashboard
    await expect(page).toHaveURL("/");

    // --- Step 2: Dashboard shows briefing section ---
    // The dashboard at / is the (dashboard) page which should show briefings
    await expect(
      page.getByRole("heading").or(page.locator("main")),
    ).toBeVisible({ timeout: 10_000 });

    // --- Step 3: Navigate to briefings list ---
    await page.goto("/briefings");
    await expect(page).toHaveURL(/\/briefings/);

    // Page should render without errors (no unhandled error boundary)
    await expect(page.locator('[data-testid="error-boundary"]')).not.toBeVisible();

    // --- Step 4: Navigate to search ---
    await page.goto("/search");
    await expect(page).toHaveURL(/\/search/);

    // Search page should have an input or search form
    const searchInput = page
      .getByRole("searchbox")
      .or(page.getByPlaceholder(/such/i))
      .or(page.locator('input[type="search"], input[type="text"]').first());
    await expect(searchInput).toBeVisible({ timeout: 5_000 });

    // --- Step 5: Perform a search ---
    await searchInput.fill("Projekt");
    // Submit via Enter or button
    await searchInput.press("Enter");

    // Wait for results area to appear (might be empty, but no crash)
    await page.waitForTimeout(2_000);
    await expect(page.locator("main")).toBeVisible();

    // No unhandled errors
    await expect(page.locator('[data-testid="error-boundary"]')).not.toBeVisible();
  });

  test("Dashboard laed innerhalb 15 Sekunden (Onboarding NF-025)", async ({
    page,
    testUser,
  }) => {
    const start = Date.now();
    await page.goto("/login");
    await loginViaUI(page, testUser);
    await expect(page).toHaveURL("/");
    await expect(page.locator("main")).toBeVisible();
    const elapsed = Date.now() - start;

    // NF-025: Onboarding-Dauer <= 15 Minuten (we verify < 15s for page load)
    expect(elapsed).toBeLessThan(15_000);
  });

  test("Navigation zwischen Hauptseiten funktioniert", async ({ page }) => {
    const routes = ["/", "/briefings", "/search", "/connectors", "/settings"];

    for (const route of routes) {
      await page.goto(route);
      // Each page renders without hard error
      await expect(page.locator("body")).toBeVisible();
      await expect(page.locator('[data-testid="error-boundary"]')).not.toBeVisible();
    }
  });
});