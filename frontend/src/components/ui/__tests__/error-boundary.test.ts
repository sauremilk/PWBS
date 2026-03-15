/**
 * Structural tests for Error Boundary and Skeleton components (TASK-197).
 * Runs with: npx tsx src/components/ui/__tests__/error-boundary.test.ts
 *
 * Visual verification: In the browser, temporarily add `throw new Error("test")`
 * inside the BriefingCard render function in (dashboard)/page.tsx.
 * The ErrorBoundary should show the error UI with a retry button
 * instead of a whitescreen.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { ErrorBoundary } from "../error-boundary";
import {
  BriefingCardSkeleton,
  SearchResultListSkeleton,
  ConnectorStatusSkeleton,
  DashboardWidgetSkeleton,
  SkeletonCard,
  SkeletonLine,
  SkeletonList,
} from "../loading-states";

describe("ErrorBoundary (TASK-197)", () => {
  it("is a class component with getDerivedStateFromError", () => {
    assert.strictEqual(typeof ErrorBoundary, "function");
    assert.strictEqual(
      typeof ErrorBoundary.getDerivedStateFromError,
      "function",
    );
  });

  it("getDerivedStateFromError returns error state", () => {
    const err = new Error("test error");
    const state = ErrorBoundary.getDerivedStateFromError(err);
    assert.strictEqual(state.hasError, true);
    assert.strictEqual(state.error, err);
  });

  it("is instantiable as a class component", () => {
    // Verify it's a class (not just a function) with Component methods
    assert.ok(ErrorBoundary.prototype.render, "should have render method");
    assert.ok(
      ErrorBoundary.prototype.constructor === ErrorBoundary,
      "constructor should be ErrorBoundary",
    );
  });

  it("prototype has render method", () => {
    assert.strictEqual(typeof ErrorBoundary.prototype.render, "function");
  });
});

describe("Skeleton components (TASK-197)", () => {
  it("BriefingCardSkeleton is exported", () => {
    assert.strictEqual(typeof BriefingCardSkeleton, "function");
  });

  it("SearchResultListSkeleton is exported", () => {
    assert.strictEqual(typeof SearchResultListSkeleton, "function");
  });

  it("ConnectorStatusSkeleton is exported", () => {
    assert.strictEqual(typeof ConnectorStatusSkeleton, "function");
  });

  it("DashboardWidgetSkeleton is exported", () => {
    assert.strictEqual(typeof DashboardWidgetSkeleton, "function");
  });

  it("base skeleton primitives are exported", () => {
    assert.strictEqual(typeof SkeletonCard, "function");
    assert.strictEqual(typeof SkeletonLine, "function");
    assert.strictEqual(typeof SkeletonList, "function");
  });
});
