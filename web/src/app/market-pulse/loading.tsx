import {
  LoadingStatus,
  PanelSkeleton,
  Skeleton,
} from "@/components/loading-shell";

export default function MarketPulseLoading() {
  return (
    <div className="space-y-6" aria-label="Loading market pulse" aria-busy="true">
      <LoadingStatus>Comparing AI-exposed and non-AI listings</LoadingStatus>

      <div>
        <Skeleton className="mb-3 h-3 w-48" />
        <Skeleton className="h-9 w-56 max-w-full" />
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="rounded-lg border border-line bg-panel p-4">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="mt-3 h-8 w-24" />
            <Skeleton className="mt-3 h-3 w-36" />
          </div>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <PanelSkeleton tall />
        <PanelSkeleton tall />
      </div>
    </div>
  );
}
