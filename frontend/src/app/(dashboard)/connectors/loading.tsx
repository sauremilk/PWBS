import { ConnectorStatusSkeleton } from "@/components/ui/loading-states";

export default function ConnectorsLoading() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="h-8 w-36 animate-pulse rounded bg-gray-200" />
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 4 }, (_, i) => (
          <ConnectorStatusSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}