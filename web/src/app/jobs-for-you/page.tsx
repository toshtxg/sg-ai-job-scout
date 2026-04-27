import { compactListingsForClient, loadClassifiedListings } from "@/lib/data";
import { JobsForYou } from "@/components/jobs-for-you";
import { PageHeader } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function JobsForYouPage() {
  const listings = compactListingsForClient(await loadClassifiedListings());
  return (
    <>
      <PageHeader title="Jobs For You" eyebrow="Skill match ranking" />
      <JobsForYou listings={listings} />
    </>
  );
}
