import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // Exclude files that use Node's built-in test runner (node:test).
    // Those are run standalone via: npx tsx <file>
    exclude: ["src/**/__tests__/**", "node_modules/**", "e2e/**"],
  },
});
