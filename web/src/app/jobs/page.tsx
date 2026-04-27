import { compactListingsForClient, loadClassifiedListings } from "@/lib/data";
import { JobExplorer } from "@/components/job-explorer";
import { PageHeader } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function JobsPage() {
  const listings = compactListingsForClient(await loadClassifiedListings());
  return (
    <>
      <PageHeader title="Job Explorer" eyebrow="Search and export" />
      <JobExplorer listings={listings} />
    </>
  );
}
