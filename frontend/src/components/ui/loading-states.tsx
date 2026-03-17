"use client";

import { Loader2 } from "lucide-react";

export function Spinner({ className = "" }: { className?: string }) {
  return <Loader2 className={`animate-spin text-text-tertiary ${className}`} />;
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center py-12">
      <Spinner className="h-8 w-8" />
    </div>
  );
}

export function SkeletonLine({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-border ${className}`} />;
}

export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-border bg-surface p-4 space-y-3">
      <SkeletonLine className="h-4 w-2/3" />
      <SkeletonLine className="h-3 w-full" />
      <SkeletonLine className="h-3 w-4/5" />
    </div>
  );
}

export function SkeletonList({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }, (_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

/** Skeleton for the dashboard briefing card. */
export function BriefingCardSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-surface p-6 space-y-3">
      <div className="flex items-center gap-3">
        <SkeletonLine className="h-10 w-10 rounded-xl" />
        <div className="flex-1 space-y-1.5">
          <SkeletonLine className="h-3 w-24" />
          <SkeletonLine className="h-3 w-12" />
        </div>
      </div>
      <SkeletonLine className="h-5 w-3/4" />
    </div>
  );
}

/** Skeleton for a single search result row. */
export function SearchResultSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
      <div className="flex items-center gap-2">
        <SkeletonLine className="h-4 w-4 rounded" />
        <SkeletonLine className="h-4 w-1/3" />
        <div className="ml-auto">
          <SkeletonLine className="h-3 w-16" />
        </div>
      </div>
      <SkeletonLine className="h-3 w-full" />
      <SkeletonLine className="h-3 w-5/6" />
    </div>
  );
}

/** Skeleton list for search results. */
export function SearchResultListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }, (_, i) => (
        <SearchResultSkeleton key={i} />
      ))}
    </div>
  );
}

/** Skeleton for the connector status widget. */
export function ConnectorStatusSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-surface p-5 space-y-3">
      <div className="flex items-center justify-between">
        <SkeletonLine className="h-4 w-24" />
        <SkeletonLine className="h-3 w-16" />
      </div>
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <SkeletonLine className="h-2 w-2 rounded-full" />
            <SkeletonLine className="h-3 w-20" />
          </div>
          <SkeletonLine className="h-5 w-12 rounded-full" />
        </div>
      ))}
    </div>
  );
}

/** Skeleton for a generic dashboard widget. */
export function DashboardWidgetSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-surface p-6 space-y-4">
      <SkeletonLine className="h-5 w-1/3" />
      <SkeletonLine className="h-20 w-full rounded-xl" />
      <div className="flex gap-3">
        <SkeletonLine className="h-3 w-1/4" />
        <SkeletonLine className="h-3 w-1/4" />
      </div>
    </div>
  );
}
