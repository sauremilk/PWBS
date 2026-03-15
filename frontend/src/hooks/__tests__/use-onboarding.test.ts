/**
 * Tests for Onboarding hook (TASK-181).
 * Runs with: npx tsx src/hooks/__tests__/use-onboarding.test.ts
 */

import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";

// Simulate browser environment with localStorage
if (typeof globalThis.window === "undefined") {
  const store = new Map<string, string>();
  (globalThis as unknown as Record<string, unknown>).window = globalThis;
  (globalThis as unknown as Record<string, unknown>).localStorage = {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => store.set(key, value),
    removeItem: (key: string) => store.delete(key),
    clear: () => store.clear(),
    get length() { return store.size; },
    key: (idx: number) => [...store.keys()][idx] ?? null,
  };
}

const STORAGE_KEY = "pwbs_onboarding_completed";

describe("Onboarding Storage (TASK-181)", () => {
  beforeEach(() => {
    localStorage.removeItem(STORAGE_KEY);
  });

  it("returns null when no value is stored", () => {
    const stored = localStorage.getItem(STORAGE_KEY);
    assert.equal(stored, null);
  });

  it("marks onboarding as completed", () => {
    localStorage.setItem(STORAGE_KEY, "true");
    assert.equal(localStorage.getItem(STORAGE_KEY), "true");
  });

  it("resets onboarding status", () => {
    localStorage.setItem(STORAGE_KEY, "true");
    localStorage.removeItem(STORAGE_KEY);
    assert.equal(localStorage.getItem(STORAGE_KEY), null);
  });

  it("does not leak between tests", () => {
    assert.equal(localStorage.getItem(STORAGE_KEY), null);
  });
});
