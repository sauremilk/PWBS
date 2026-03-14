"use client";

import { Loader2 } from "lucide-react";

export function Spinner({ className = "" }: { className?: string }) {
  return <Loader2 className={`animate-spin text-gray-400 ${className}`} />;
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center py-12">
      <Spinner className="h-8 w-8" />
    </div>
  );
}

export function SkeletonLine({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-pulse rounded bg-gray-200 ${className}`} />
  );
}

export function SkeletonCard() {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
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
