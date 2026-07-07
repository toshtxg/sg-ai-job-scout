import { TrendingDown, TrendingUp } from "lucide-react";
import { loadSnapshots } from "@/lib/data";
import {
  buildRoleMixSeries,
  buildSalaryTrendByRole,
  buildSkillMomentum,
  buildSnapshotTotalsSeries,
  formatDate,
  type SkillMomentum,
} from "@/lib/market";
import {
  NewListingsLine,
  RoleMixArea,
  SnapshotTotalsArea,
} from "@/components/charts";
import { DataCaveat } from "@/components/data-caveat";
import { SalaryTrendExplorer } from "@/components/salary-trend";
import {
  EmptyState,
  MetricCard,
  PageHeader,
  Panel,
  SectionTitle,
} from "@/components/ui";

export const revalidate = 900;

function MomentumList({
  items,
  direction,
}: {
  items: SkillMomentum[];
  direction: "rising" | "declining";
}) {
  const rising = direction === "rising";
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div
          key={item.skill}
          className="flex items-center justify-between gap-3 rounded-md border border-line bg-panel-strong px-3 py-2 text-sm"
        >
          <span className="min-w-0 flex-1 truncate text-foreground">{item.skill}</span>
          <span className="text-xs text-muted">
            {item.previous} → {item.current}
          </span>
          <span
            className={`inline-flex items-center gap-1 rounded-md border border-line px-2 py-1 text-xs ${
              rising ? "text-accent" : "text-[#fb7185]"
            }`}
          >
            {rising ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
            {item.delta > 0 ? `+${item.delta}` : item.delta}
          </span>
        </div>
      ))}
    </div>
  );
}

export default async function TrendsPage() {
  const snapshots = await loadSnapshots();
  const totals = buildSnapshotTotalsSeries(snapshots);
  const roleMix = buildRoleMixSeries(snapshots);
  const momentum = buildSkillMomentum(snapshots);
  const salaryTrend = buildSalaryTrendByRole(snapshots);

  const latest = snapshots.at(-1);
  const earliest = snapshots[0];
  const shortHistory = snapshots.length > 0 && snapshots.length < 5;

  if (!snapshots.length) {
    return (
      <>
        <PageHeader title="Market Trends" eyebrow="Snapshot history over time" />
        <DataCaveat />
        <EmptyState>
          No market snapshots recorded yet. The pipeline writes one snapshot per
          day — trends will appear here once history accumulates.
        </EmptyState>
      </>
    );
  }

  return (
    <>
      <PageHeader title="Market Trends" eyebrow="Snapshot history over time" />

      <DataCaveat />

      {shortHistory && (
        <div className="mb-6 rounded-lg border border-line bg-panel p-4 text-sm text-muted">
          Only {snapshots.length} snapshot{snapshots.length === 1 ? "" : "s"}{" "}
          recorded so far — the pipeline adds one per day, so these trends will
          get more meaningful as history accumulates.
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Snapshots recorded"
          value={snapshots.length.toLocaleString()}
          detail={`${formatDate(earliest?.snapshot_date)} – ${formatDate(latest?.snapshot_date)}`}
        />
        <MetricCard
          label="Tracked listings"
          value={(latest?.total_listings ?? 0).toLocaleString()}
          detail="Latest snapshot"
        />
        <MetricCard
          label="New listings"
          value={(latest?.new_listings_count ?? 0).toLocaleString()}
          detail="Posted in the last 7 days"
        />
        <MetricCard
          label="Top skill now"
          value={latest?.top_skills?.[0]?.skill || "N/A"}
          detail={
            latest?.top_skills?.[0]
              ? `${latest.top_skills[0].count} mentions`
              : "No skill data in snapshot"
          }
        />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <Panel>
          <SectionTitle>Tracked Listings Over Time</SectionTitle>
          {totals.length >= 2 ? (
            <SnapshotTotalsArea data={totals} />
          ) : (
            <EmptyState>
              Need at least two snapshots to draw a trend line.
            </EmptyState>
          )}
        </Panel>
        <Panel>
          <SectionTitle>New Listings Per Week</SectionTitle>
          {totals.length >= 2 ? (
            <NewListingsLine data={totals} />
          ) : (
            <EmptyState>
              Need at least two snapshots to draw a trend line.
            </EmptyState>
          )}
        </Panel>
      </div>

      <div className="mt-6">
        <Panel>
          <SectionTitle>Role Mix Evolution</SectionTitle>
          {roleMix.data.length >= 2 && roleMix.roles.length ? (
            <>
              <RoleMixArea data={roleMix.data} roles={roleMix.roles} />
              <p className="mt-2 text-xs text-muted">
                Share of listings per role category across snapshots. Top roles
                from the latest snapshot are shown individually; everything else
                is grouped into &ldquo;Other roles&rdquo;.
              </p>
            </>
          ) : (
            <EmptyState>Not enough role history to chart the mix yet.</EmptyState>
          )}
        </Panel>
      </div>

      <div className="mt-6">
        <Panel>
          <SectionTitle>Skill Momentum</SectionTitle>
          {momentum.rising.length || momentum.declining.length ? (
            <>
              <p className="mb-4 text-sm text-muted">
                Skill mention counts in the latest snapshot (
                {formatDate(momentum.latestDate)}) vs{" "}
                {momentum.baselineIsEarliest
                  ? "the earliest available snapshot"
                  : `~${momentum.windowDays} days earlier`}{" "}
                ({formatDate(momentum.baselineDate)}). Snapshots track the top 30
                skills, so a skill dropping off the leaderboard counts as zero.
              </p>
              <div className="grid gap-4 xl:grid-cols-2">
                <div>
                  <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
                    <TrendingUp size={16} className="text-accent" /> Rising
                  </div>
                  {momentum.rising.length ? (
                    <MomentumList items={momentum.rising} direction="rising" />
                  ) : (
                    <EmptyState>No skills gained mentions in this window.</EmptyState>
                  )}
                </div>
                <div>
                  <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
                    <TrendingDown size={16} className="text-[#fb7185]" /> Declining
                  </div>
                  {momentum.declining.length ? (
                    <MomentumList items={momentum.declining} direction="declining" />
                  ) : (
                    <EmptyState>No skills lost mentions in this window.</EmptyState>
                  )}
                </div>
              </div>
            </>
          ) : (
            <EmptyState>
              Skill momentum needs at least two snapshots with skill data.
            </EmptyState>
          )}
        </Panel>
      </div>

      <div className="mt-6">
        <Panel>
          <SectionTitle>Salary Trend By Role</SectionTitle>
          <SalaryTrendExplorer trend={salaryTrend} />
        </Panel>
      </div>
    </>
  );
}
