import {
  LoadingStatus,
  PanelSkeleton,
  Skeleton,
} from "@/components/loading-shell";

export default function AiSkillsLoading() {
  return (
    <div className="space-y-6" aria-label="Loading AI skills analysis" aria-busy="true">
      <LoadingStatus>Scanning job descriptions for AI skill signals</LoadingStatus>

      <div>
        <Skeleton className="mb-3 h-3 w-44" />
        <Skeleton className="h-9 w-64 max-w-full" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <PanelSkeleton tall />
        <section className="rounded-lg border border-line bg-panel p-4">
          <Skeleton className="mb-4 h-5 w-32" />
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-20 w-full" />
            ))}
          </div>
        </section>
      </div>

      <PanelSkeleton tall />
    </div>
  );
}
