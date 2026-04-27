import { compactListingsForClient, loadClassifiedListings } from "@/lib/data";
import { CompanyLeaderboard } from "@/components/company-leaderboard";
import { PageHeader } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function CompaniesPage() {
  const listings = compactListingsForClient(await loadClassifiedListings());
  return (
    <>
      <PageHeader title="Company Leaderboard" eyebrow="Hiring companies and role profiles" />
      <CompanyLeaderboard listings={listings} />
    </>
  );
}
