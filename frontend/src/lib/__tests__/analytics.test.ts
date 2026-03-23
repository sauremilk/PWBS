/**
 * Tests for Plausible Analytics utility (TASK-179).
 * Runs with: npx tsx src/lib/__tests__/analytics.test.ts
 */

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";

// Simulate browser environment
if (typeof globalThis.window === "undefined") {
  (globalThis as Record<string, unknown>).window = globalThis;
}

import {
  trackEvent,
  trackSignup,
  trackFirstConnector,
  trackFirstBriefing,
  trackSearch,
  trackReferral,
} from "../analytics.js";

describe("Plausible Analytics (TASK-179)", () => {
  const calls: unknown[][] = [];
  const spy = (...args: unknown[]) => calls.push(args);

  beforeEach(() => {
    calls.length = 0;
    (window as unknown as Record<string, unknown>).plausible = spy;
  });

  afterEach(() => {
    delete (window as unknown as Record<string, unknown>).plausible;
  });

  describe("trackEvent", () => {
    it("calls window.plausible with event name", () => {
      trackEvent("signup");
      assert.equal(calls.length, 1);
      assert.deepEqual(calls[0], ["signup", undefined]);
    });

    it("passes props when provided", () => {
      trackEvent("first_connector", { connector_type: "notion" });
      assert.equal(calls.length, 1);
      assert.deepEqual(calls[0], [
        "first_connector",
        { props: { connector_type: "notion" } },
      ]);
    });

    it("is no-op when window.plausible is not defined", () => {
      delete (window as unknown as Record<string, unknown>).plausible;
      assert.doesNotThrow(() => trackEvent("signup"));
      assert.equal(calls.length, 0);
    });
  });

  describe("shorthand functions", () => {
    it("trackSignup sends signup event", () => {
      trackSignup();
      assert.deepEqual(calls[0], ["signup", undefined]);
    });

    it("trackFirstConnector sends connector_type prop", () => {
      trackFirstConnector("gmail");
      assert.deepEqual(calls[0], [
        "first_connector",
        { props: { connector_type: "gmail" } },
      ]);
    });

    it("trackFirstBriefing sends briefing_type prop", () => {
      trackFirstBriefing("morning");
      assert.deepEqual(calls[0], [
        "first_briefing",
        { props: { briefing_type: "morning" } },
      ]);
    });

    it("trackSearch sends mode prop", () => {
      trackSearch("hybrid");
      assert.deepEqual(calls[0], [
        "search",
        { props: { mode: "hybrid" } },
      ]);
    });

    it("trackReferral sends referral event", () => {
      trackReferral();
      assert.deepEqual(calls[0], ["referral", undefined]);
    });
  });

  describe("DSGVO compliance", () => {
    it("does not send any PII in events", () => {
      trackSignup();
      trackFirstConnector("notion");
      trackFirstBriefing("weekly");
      trackSearch("hybrid");
      trackReferral();

      for (const call of calls) {
        const options = call[1] as
          | { props?: Record<string, string> }
          | undefined;
        if (options?.props) {
          for (const val of Object.values(options.props)) {
            assert.ok(!val.includes("@"), "No email addresses in events");
            assert.ok(
              !/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i.test(val),
              "No UUIDs in events",
            );
          }
        }
      }
    });

    it("gracefully degrades when script is blocked", () => {
      delete (window as unknown as Record<string, unknown>).plausible;
      assert.doesNotThrow(() => {
        trackSignup();
        trackFirstConnector("gmail");
        trackFirstBriefing("morning");
        trackSearch("hybrid");
        trackReferral();
      });
    });
  });
});
