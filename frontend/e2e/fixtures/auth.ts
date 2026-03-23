import { test as base, type Page } from "@playwright/test";

/** Credentials for E2E test user. */
export interface TestUser {
  email: string;
  password: string;
  displayName: string;
}

/** Generate unique E2E user credentials. */
function generateTestUser(): TestUser {
  const id = `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  return {
    email: `${id}@pwbs-test.local`,
    password: "E2eTest!Secure#2026",
    displayName: "E2E Tester",
  };
}

/**
 * Register a new user via the UI and return credentials.
 * Leaves the browser on the welcome/dashboard page.
 */
async function registerViaUI(page: Page, user: TestUser): Promise<void> {
  await page.goto("/register");
  await page.locator("#display-name").fill(user.displayName);
  await page.locator("#reg-email").fill(user.email);
  await page.locator("#reg-password").fill(user.password);
  await page.getByRole("button", { name: /Registrieren/i }).click();
  // Wait for welcome dialog or dashboard redirect
  await page.waitForURL(/\/(register|$)/, { timeout: 10_000 });
}

/**
 * Login an existing user via the UI.
 * Leaves the browser on the dashboard.
 */
async function loginViaUI(page: Page, user: TestUser): Promise<void> {
  await page.goto("/login");
  await page.locator("#email").fill(user.email);
  await page.locator("#password").fill(user.password);
  await page.getByRole("button", { name: /Anmelden/i }).click();
  // Wait for redirect to dashboard
  await page.waitForURL("/", { timeout: 10_000 });
}

/** Extended test fixtures with auth helpers. */
export const test = base.extend<{
  testUser: TestUser;
  authenticatedPage: Page;
}>({
  testUser: async ({}, use) => {
    await use(generateTestUser());
  },

  authenticatedPage: async ({ page, testUser }, use) => {
    await registerViaUI(page, testUser);
    // If still on welcome page, navigate to dashboard
    if (page.url().includes("/register")) {
      await page.goto("/");
    }
    await use(page);
  },
});

export { registerViaUI, loginViaUI };
export { expect } from "@playwright/test";
