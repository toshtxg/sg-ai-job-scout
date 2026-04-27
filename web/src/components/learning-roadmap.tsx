"use client";

import { useMemo, useState } from "react";
import { DEFAULT_ROLES, ROLE_CATEGORIES } from "@/lib/constants";
import { buildSenioritySkillMatrix, skillCounts } from "@/lib/market";
import type { ClassifiedListing } from "@/lib/types";
import { MatrixHeatmap } from "@/components/charts";
import { Badge, EmptyState, Panel, SectionTitle } from "@/components/ui";

export function LearningRoadmap({ listings }: { listings: ClassifiedListing[] }) {
  const [role, setRole] = useState(DEFAULT_ROLES[0]);
  const roleRows = useMemo(
    () => listings.filter((row) => row.role_category === role),
    [listings, role],
  );
  const matrix = buildSenioritySkillMatrix(roleRows.length ? roleRows : listings.filter((row) => DEFAULT_ROLES.includes(row.role_category || "")), 18);
  const topSkills = skillCounts(roleRows, 24).map((item) => item.name);
  const foundation = topSkills.slice(0, 6);
  const differentiators = topSkills.slice(6, 14);
  const specialist = topSkills.slice(14, 22);

  return (
    <div className="space-y-4">
      <Panel>
        <label className="block max-w-sm text-sm">
          <span className="text-muted">Target role</span>
          <select value={role} onChange={(event) => setRole(event.target.value)} className="mt-1 h-10 w-full rounded-md border border-line bg-panel-strong px-3 text-foreground outline-none focus:border-accent">
            {ROLE_CATEGORIES.filter((item) => item !== "Other").map((item) => <option key={item}>{item}</option>)}
          </select>
        </label>
      </Panel>
      <Panel>
        <SectionTitle>Skill Progression By Seniority</SectionTitle>
        {matrix.length ? <MatrixHeatmap rows={matrix} /> : <EmptyState>No seniority data for this role.</EmptyState>}
      </Panel>
      <div className="grid gap-4 xl:grid-cols-3">
        <SkillBucket title="Foundation" items={foundation} note="Common across role listings; learn these first." />
        <SkillBucket title="Differentiators" items={differentiators} note="Useful skills that start separating stronger candidates." />
        <SkillBucket title="Specialist" items={specialist} note="Narrower capabilities for senior or specialized tracks." />
      </div>
    </div>
  );
}

function SkillBucket({ title, items, note }: { title: string; items: string[]; note: string }) {
  return (
    <Panel>
      <SectionTitle>{title}</SectionTitle>
      <p className="mb-3 text-sm text-muted">{note}</p>
      <div className="flex flex-wrap gap-2">
        {items.length ? items.map((item) => <Badge key={item}>{item}</Badge>) : <EmptyState>No skills available.</EmptyState>}
      </div>
    </Panel>
  );
}
