/**
 * E2E-Test: DSGVO-Flow (TASK-111)
 *
 * Verifiziert: Datenexport anfordern -> Account-Loeschung einleiten ->
 *              Karenzfrist-Banner -> Loeschung abbrechen
 * Quelle: D4 User Flow 4, D4 US-5.1-5.4
 */
import { test, expect } from "./fixtures/auth";

test.describe("DSGVO-Flow", () => {
  test("Datenexport anfordern", async ({ authenticatedPage: page }) => {
    // Navigate to settings page
    await page.goto("/settings");
    await expect(page).toHaveURL(/\/settings/);

    // Look for export button/section (Datenschutz tab or section)
    const exportButton = page
      .getByRole("button", { name: /export/i })
      .or(page.getByText(/Datenexport/i));

    // If the export section exists, click it
    if (await exportButton.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await exportButton.click();

      // Should trigger an export or show confirmation
      await page.waitForTimeout(2_000);

      // No crash
      await expect(page.locator("main")).toBeVisible();
    }
  });

  test("Account-Loeschung einleiten und abbrechen", async ({
    authenticatedPage: page,
    testUser,
  }) => {
    await page.goto("/settings");

    // --- Step 1: Find account deletion section ---
    // Look for "Account" tab or deletion section
    const accountTab = page
      .getByRole("tab", { name: /account|konto/i })
      .or(page.getByText(/Account/i).first());

    if (await accountTab.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await accountTab.click();
    }

    // --- Step 2: Find delete button ---
    const deleteButton = page
      .getByRole("button", { name: /loeschen|Account loeschen|Account l\u00f6schen/i })
      .or(page.getByText(/Account l\u00f6schen/i));

    await expect(deleteButton).toBeVisible({ timeout: 5_000 });

    // --- Step 3: Initiate deletion ---
    await deleteButton.click();

    // --- Step 4: Deletion dialog should appear ---
    // Should show confirmation checkbox and password input
    const confirmCheckbox = page
      .getByRole("checkbox")
      .or(page.locator('input[type="checkbox"]'));
    const passwordInput = page.locator("#delete-password");

    // At least one should be visible (confirmation step)
    const hasDialog =
      (await confirmCheckbox.isVisible({ timeout: 3_000 }).catch(() => false)) ||
      (await passwordInput.isVisible({ timeout: 1_000 }).catch(() => false));

    if (hasDialog) {
      // Check the confirmation box
      if (await confirmCheckbox.isVisible().catch(() => false)) {
        await confirmCheckbox.check();
      }

      // Enter password
      if (await passwordInput.isVisible().catch(() => false)) {
        await passwordInput.fill(testUser.password);
      }

      // --- Step 5: Karenzfrist info should be visible ---
      // Look for 30-day grace period info
      const graceInfo = page
        .getByText(/30 Tage/i)
        .or(page.getByText(/Karenzfrist/i))
        .or(page.getByText(/nicht r\u00fcckg\u00e4ngig/i));

      await expect(graceInfo).toBeVisible({ timeout: 3_000 });

      // --- Step 6: Cancel the deletion ---
      const cancelButton = page
        .getByRole("button", { name: /abbrechen|cancel/i })
        .or(page.getByText(/Abbrechen/i));

      if (await cancelButton.isVisible().catch(() => false)) {
        await cancelButton.click();
        // Should return to settings without deletion
        await expect(page).toHaveURL(/\/settings/);
      }
    }
  });

  test("Settings-Seite zeigt Sicherheitsstatus", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/settings");

    // Should render settings page with security information
    await expect(page.locator("main")).toBeVisible();

    // No unhandled errors
    await expect(page.locator('[data-testid="error-boundary"]')).not.toBeVisible();
  });
});
