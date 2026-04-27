function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-panel-strong ${className}`} />;
}

function SkeletonPanel({ tall = false }: { tall?: boolean }) {
  return (
    <section className="rounded-lg border border-line bg-panel p-4">
      <SkeletonBlock className="mb-4 h-5 w-44" />
      <SkeletonBlock className={tall ? "h-72 w-full" : "h-40 w-full"} />
    </section>
  );
}

export default function Loading() {
  return (
    <div className="space-y-6" aria-label="Loading page">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <SkeletonBlock className="mb-3 h-3 w-32" />
          <SkeletonBlock className="h-9 w-80 max-w-full" />
        </div>
        <SkeletonBlock className="h-10 w-44" />
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="rounded-lg border border-line bg-panel p-4">
            <SkeletonBlock className="h-4 w-28" />
            <SkeletonBlock className="mt-3 h-8 w-24" />
            <SkeletonBlock className="mt-3 h-3 w-36" />
          </div>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <SkeletonPanel tall />
        <SkeletonPanel tall />
      </div>

      <SkeletonPanel />
    </div>
  );
}
