"use client";

import { useMemo, useState } from "react";
import { DEFAULT_ROLES, ROLE_CATEGORIES } from "@/lib/constants";
import { buildSenioritySkillMatrix, countBy, skillCounts, topCounts } from "@/lib/market";
import type { ClassifiedListing } from "@/lib/types";
import { HorizontalBars, MatrixHeatmap, VerticalBars } from "@/components/charts";
import { EmptyState, Panel, SectionTitle } from "@/components/ui";

export function RoleInsights({ listings }: { listings: ClassifiedListing[] }) {
  const [scope, setScope] = useState("Data & Analytics");
  const scoped = useMemo(() => {
    if (scope === "All Roles") return listings.filter((row) => row.role_category !== "Other");
    if (scope === "Data & Analytics") return listings.filter((row) => DEFAULT_ROLES.includes(row.role_category || ""));
    return listings.filter((row) => row.role_category === scope);
  }, [listings, scope]);
  const roleBars = topCounts(countBy(scoped, (row) => row.role_category), 12);
  const topSkillBars = skillCounts(scoped, 15);
  const matrix = buildSenioritySkillMatrix(scoped, 16);
  const topSkills = skillCounts(scoped, 12).map((item) => item.name);
  const roleMatrix = ROLE_CATEGORIES.filter((role) => role !== "Other")
    .map((role) => {
      const roleRows = scoped.filter((row) => row.role_category === role);
      return {
        role,
        total: roleRows.length,
        values: topSkills.map((skill) => ({
          skill,
          count: roleRows.filter((row) => (row.technical_skills || []).includes(skill)).length,
        })),
      };
    })
    .filter((row) => row.total > 0);

  return (
    <div className="space-y-4">
      <Panel>
        <label className="block max-w-sm text-sm">
          <span className="text-muted">Role focus</span>
          <select value={scope} onChange={(event) => setScope(event.target.value)} className="mt-1 h-10 w-full rounded-md border border-line bg-panel-strong px-3 text-foreground outline-none focus:border-accent">
            <option>Data & Analytics</option>
            <option>All Roles</option>
            {ROLE_CATEGORIES.filter((role) => role !== "Other").map((role) => <option key={role}>{role}</option>)}
          </select>
        </label>
      </Panel>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel>
          <SectionTitle>Listings By Role</SectionTitle>
          {roleBars.length ? <HorizontalBars data={roleBars} /> : <EmptyState>No role data.</EmptyState>}
        </Panel>
        <Panel>
          <SectionTitle>Top Skills</SectionTitle>
          {topSkillBars.length ? <VerticalBars data={topSkillBars.slice(0, 12)} /> : <EmptyState>No skill data.</EmptyState>}
        </Panel>
      </div>
      <Panel>
        <SectionTitle>Skill Progression By Seniority</SectionTitle>
        {matrix.length ? <MatrixHeatmap rows={matrix} /> : <EmptyState>No seniority data available.</EmptyState>}
      </Panel>
      <Panel>
        <SectionTitle>Skills By Role</SectionTitle>
        <div className="overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-1 text-sm">
            <thead>
              <tr>
                <th className="sticky left-0 bg-panel px-2 py-2 text-left text-muted">Role</th>
                {topSkills.map((skill) => <th key={skill} className="min-w-24 px-2 py-2 text-left text-muted">{skill}</th>)}
              </tr>
            </thead>
            <tbody>
              {roleMatrix.map((row) => (
                <tr key={row.role}>
                  <td className="sticky left-0 bg-panel px-2 py-2 text-foreground">{row.role}</td>
                  {row.values.map((value) => {
                    const pct = row.total ? Math.round((value.count / row.total) * 100) : 0;
                    return (
                      <td key={value.skill} className="px-1 py-1">
                        <div className="rounded-md px-2 py-2 text-xs" style={{ background: `rgba(245,158,11,${Math.max(pct, 6) / 100})` }}>{pct}%</div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
