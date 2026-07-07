"use client";

import { useState } from "react";
import type { SalaryTrendByRole } from "@/lib/market";
import { SalaryTrendLine } from "@/components/charts";
import { EmptyState } from "@/components/ui";

export function SalaryTrendExplorer({ trend }: { trend: SalaryTrendByRole }) {
  const [role, setRole] = useState(trend.roles[0] || "");
  const points = trend.byRole[role] || [];

  if (!trend.roles.length) {
    return <EmptyState>No salary history recorded in snapshots yet.</EmptyState>;
  }

  return (
    <div className="space-y-3">
      <label className="block max-w-sm text-sm">
        <span className="text-muted">Role</span>
        <select
          value={role}
          onChange={(event) => setRole(event.target.value)}
          className="mt-1 h-10 w-full rounded-md border border-line bg-panel-strong px-3 text-foreground outline-none focus:border-accent"
        >
          {trend.roles.map((option) => (
            <option key={option}>{option}</option>
          ))}
        </select>
      </label>
      {points.length ? (
        <>
          <SalaryTrendLine data={points} />
          <p className="text-xs text-muted">
            Average posted salary midpoint per snapshot for {role}. Averages only —
            based on listings that publish a salary range.
          </p>
        </>
      ) : (
        <EmptyState>No salary history for this role yet.</EmptyState>
      )}
    </div>
  );
}
