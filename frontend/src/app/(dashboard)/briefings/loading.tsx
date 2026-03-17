import { BriefingCardSkeleton } from "@/components/ui/loading-states";

export default function BriefingsLoading() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="h-8 w-32 animate-pulse rounded bg-surface-secondary" />
        <div className="h-9 w-40 animate-pulse rounded bg-surface-secondary" />
      </div>
      <div className="space-y-3">
        {Array.from({ length: 5 }, (_, i) => (
          <BriefingCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}