import { SearchResultListSkeleton, SkeletonLine } from "@/components/ui/loading-states";

export default function SearchLoading() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-24 animate-pulse rounded bg-surface-secondary" />
      <SkeletonLine className="h-10 w-full rounded-lg" />
      <SearchResultListSkeleton count={5} />
    </div>
  );
}