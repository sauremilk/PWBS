import {
  BriefingCardSkeleton,
  ConnectorStatusSkeleton,
} from "@/components/ui/loading-states";

export default function DashboardLoading() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 animate-pulse rounded bg-surface-secondary" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <BriefingCardSkeleton />
        </div>
        <div className="space-y-4">
          <ConnectorStatusSkeleton />
        </div>
      </div>
    </div>
  );
}