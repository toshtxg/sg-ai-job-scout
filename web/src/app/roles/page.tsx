import { compactListingsForClient, loadClassifiedListings } from "@/lib/data";
import { RoleInsights } from "@/components/role-insights";
import { PageHeader } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function RolesPage() {
  const listings = compactListingsForClient(await loadClassifiedListings());
  return (
    <>
      <PageHeader title="Role Taxonomy & Skills" eyebrow="Role demand and skill mix" />
      <RoleInsights listings={listings} />
    </>
  );
}
