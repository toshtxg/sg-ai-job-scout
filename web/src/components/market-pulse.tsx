"use client";

import type { MarketPulseData } from "@/lib/market";
import { HorizontalBars, VerticalBars } from "@/components/charts";
import { MetricCard, Panel, SectionTitle } from "@/components/ui";

export function MarketPulse({ data }: { data: MarketPulseData }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="AI-exposed listings" value={data.aiRowsCount.toLocaleString()} detail={`${Math.round((data.aiRowsCount / Math.max(data.dataRowsCount, 1)) * 100)}% of data roles`} />
        <MetricCard label="AI salary midpoint" value={data.aiSalary ? `$${Math.round(data.aiSalary).toLocaleString()}` : "N/A"} detail="Average posted midpoint" />
        <MetricCard label="Non-AI midpoint" value={data.nonAiSalary ? `$${Math.round(data.nonAiSalary).toLocaleString()}` : "N/A"} detail="Average posted midpoint" />
        <MetricCard label="AI premium" value={`${data.premium}%`} detail="Directional, salary-posted jobs only" />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel>
          <SectionTitle>Most In-Demand Skills</SectionTitle>
          <VerticalBars data={data.topSkills} />
        </Panel>
        <Panel>
          <SectionTitle>Industry AI Adoption</SectionTitle>
          <HorizontalBars data={data.industries} />
        </Panel>
      </div>
    </div>
  );
}
