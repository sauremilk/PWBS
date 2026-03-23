import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E configuration for PWBS.
 *
 * Expects the full stack (backend + frontend) to be running,
 * either locally or via Docker Compose.
 *
 * Usage:
 *   npm run e2e          # headless
 *   npm run e2e:ui       # interactive UI
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? "html" : "list",
  timeout: 30_000,

  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  /* Start frontend dev server automatically when not in CI */
  ...(process.env.CI
    ? {}
    : {
        webServer: [
          {
            command: "npm run dev",
            url: "http://localhost:3000",
            reuseExistingServer: true,
            timeout: 60_000,
          },
        ],
      }),
});
