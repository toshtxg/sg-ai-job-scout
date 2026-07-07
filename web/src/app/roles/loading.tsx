import {
  LoadingStatus,
  PanelSkeleton,
  Skeleton,
} from "@/components/loading-shell";

export default function RolesLoading() {
  return (
    <div className="space-y-6" aria-label="Loading role insights" aria-busy="true">
      <LoadingStatus>Mapping roles, skills, and seniority ladders</LoadingStatus>

      <div>
        <Skeleton className="mb-3 h-3 w-40" />
        <Skeleton className="h-9 w-72 max-w-full" />
      </div>

      <section className="rounded-lg border border-line bg-panel p-4">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="mt-1 h-10 w-full max-w-sm" />
      </section>

      <div className="grid gap-4 xl:grid-cols-2">
        <PanelSkeleton tall />
        <PanelSkeleton tall />
      </div>

      <PanelSkeleton tall />

      <div className="grid gap-4 xl:grid-cols-2">
        <PanelSkeleton />
        <PanelSkeleton />
      </div>
    </div>
  );
}
