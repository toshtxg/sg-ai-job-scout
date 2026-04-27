"use client";

import { useState } from "react";
import { AI_SKILLS_TAXONOMY, SKILL_TIERS } from "@/lib/constants";
import type { AiSkillsAnalysis } from "@/lib/market";
import { HorizontalBars } from "@/components/charts";
import { Badge, EmptyState, Panel, SectionTitle } from "@/components/ui";

export function AiSkillsDashboard({ analysis }: { analysis: AiSkillsAnalysis }) {
  const [selected, setSelected] = useState(
    analysis.categories[0]?.name || Object.keys(AI_SKILLS_TAXONOMY)[0],
  );
  const chartData = analysis.categories;
  const keywords = analysis.keywordCounts[selected] || [];
  const roleRows = analysis.rolesByCategory[selected] || [];

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Panel>
          <SectionTitle>AI Skill Categories In Listings</SectionTitle>
          {chartData.length ? <HorizontalBars data={chartData} /> : <EmptyState>No AI keyword matches found.</EmptyState>}
        </Panel>
        <Panel>
          <SectionTitle>Career Tiers</SectionTitle>
          <div className="space-y-3">
            {Object.entries(SKILL_TIERS).map(([tier, categories]) => (
              <div key={tier} className="rounded-lg border border-line bg-panel-strong p-3">
                <div className="mb-2 font-semibold">{tier}</div>
                <div className="flex flex-wrap gap-2">
                  {categories.map((category) => <Badge key={category}>{category}</Badge>)}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel>
        <div className="mb-4 grid gap-3 lg:grid-cols-[0.5fr_1fr]">
          <label className="block text-sm">
            <span className="text-muted">Category</span>
            <select value={selected} onChange={(event) => setSelected(event.target.value)} className="mt-1 h-10 w-full rounded-md border border-line bg-panel-strong px-3 text-foreground outline-none focus:border-accent">
              {Object.keys(AI_SKILLS_TAXONOMY).map((category) => <option key={category}>{category}</option>)}
            </select>
          </label>
          <div className="text-sm leading-6 text-muted">
            Keyword matching is run against job descriptions and extracted technical skills. Counts are approximate, but useful for spotting directional demand.
          </div>
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          <div>
            <SectionTitle>What Employers Say</SectionTitle>
            <div className="flex flex-wrap gap-2">
              {keywords.length ? keywords.map((item) => <Badge key={item.name}>{item.name}: {item.value}</Badge>) : <EmptyState>No keyword matches for this category.</EmptyState>}
            </div>
          </div>
          <div>
            <SectionTitle>Top Roles For This Category</SectionTitle>
            <div className="space-y-2">
              {roleRows.length ? roleRows.slice(0, 12).map((row) => (
                <div key={row.name} className="flex items-center justify-between rounded-md border border-line bg-panel-strong px-3 py-2 text-sm">
                  <span>{row.name}</span><span className="text-muted">{row.value}</span>
                </div>
              )) : <EmptyState>No role matches for this category.</EmptyState>}
            </div>
          </div>
        </div>
      </Panel>
    </div>
  );
}
