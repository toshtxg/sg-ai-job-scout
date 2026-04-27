import { compactListingsForClient, loadClassifiedListings } from "@/lib/data";
import { LearningRoadmap } from "@/components/learning-roadmap";
import { PageHeader } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function LearningRoadmapPage() {
  const listings = compactListingsForClient(await loadClassifiedListings());
  return (
    <>
      <PageHeader title="Learning Roadmap" eyebrow="Skill sequence by role and seniority" />
      <LearningRoadmap listings={listings} />
    </>
  );
}
