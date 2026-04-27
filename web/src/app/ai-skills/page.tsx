import { loadClassifiedListings } from "@/lib/data";
import { buildAiSkillsAnalysis } from "@/lib/market";
import { AiSkillsDashboard } from "@/components/ai-skills-dashboard";
import { PageHeader } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function AiSkillsPage() {
  const listings = await loadClassifiedListings({ includeDescription: true });
  const analysis = buildAiSkillsAnalysis(listings);
  return (
    <>
      <PageHeader title="AI Skills Deep Dive" eyebrow="AI taxonomy and keyword demand" />
      <AiSkillsDashboard analysis={analysis} />
    </>
  );
}
