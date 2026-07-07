import { loadClassifiedListings } from "@/lib/data";
import { buildAiSkillsAnalysis } from "@/lib/market";
import { AiSkillsDashboard } from "@/components/ai-skills-dashboard";
import { DataCaveat } from "@/components/data-caveat";
import { PageHeader } from "@/components/ui";

export const revalidate = 900;

export default async function AiSkillsPage() {
  const listings = await loadClassifiedListings({ includeDescription: true });
  const analysis = buildAiSkillsAnalysis(listings);
  return (
    <>
      <PageHeader title="AI Skills Deep Dive" eyebrow="AI taxonomy and keyword demand" />
      <DataCaveat />
      <AiSkillsDashboard analysis={analysis} />
    </>
  );
}
