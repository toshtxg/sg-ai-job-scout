import { compactListingsForClient, loadClassifiedListings } from "@/lib/data";
import { salaryPercentilesByKey, type SalaryPercentiles } from "@/lib/salary";
import { RoleInsights } from "@/components/role-insights";
import { DataCaveat } from "@/components/data-caveat";
import { EmptyState, PageHeader, Panel, SectionTitle } from "@/components/ui";

export const revalidate = 900;

function PercentileTable({
  rows,
  keyLabel,
}: {
  rows: SalaryPercentiles[];
  keyLabel: string;
}) {
  const fmt = (value: number) => `$${value.toLocaleString()}`;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="text-left text-xs uppercase text-muted">
          <tr>
            <th className="py-2 pr-4">{keyLabel}</th>
            <th className="py-2 pr-4">Listings</th>
            <th className="py-2 pr-4">p25</th>
            <th className="py-2 pr-4">Median</th>
            <th className="py-2 pr-4">p75</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row) => (
            <tr key={row.key}>
              <td className="py-2 pr-4 font-medium text-foreground">{row.key}</td>
              <td className="py-2 pr-4 text-muted">{row.count}</td>
              <td className="py-2 pr-4 text-muted">{fmt(row.p25)}</td>
              <td className="py-2 pr-4 text-foreground">{fmt(row.p50)}</td>
              <td className="py-2 pr-4 text-muted">{fmt(row.p75)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default async function RolesPage() {
  const listings = await loadClassifiedListings();
  const dataRows = listings.filter((row) => row.role_category !== "Other");
  const byRole = salaryPercentilesByKey(dataRows, (row) => row.role_category);
  const bySeniority = salaryPercentilesByKey(dataRows, (row) => row.seniority_level);
  const clientListings = compactListingsForClient(listings);

  return (
    <>
      <PageHeader title="Role Taxonomy & Skills" eyebrow="Role demand and skill mix" />
      <DataCaveat />
      <RoleInsights listings={clientListings} />
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <Panel>
          <SectionTitle>Salary Percentiles By Role</SectionTitle>
          {byRole.length ? (
            <PercentileTable rows={byRole} keyLabel="Role" />
          ) : (
            <EmptyState>Not enough salary-posted listings yet.</EmptyState>
          )}
        </Panel>
        <Panel>
          <SectionTitle>Salary Percentiles By Seniority</SectionTitle>
          {bySeniority.length ? (
            <PercentileTable rows={bySeniority} keyLabel="Seniority" />
          ) : (
            <EmptyState>Not enough salary-posted listings yet.</EmptyState>
          )}
        </Panel>
      </div>
      <p className="mt-3 text-xs text-muted">
        Percentiles (p25 / median / p75) of the posted monthly salary midpoint,
        SGD. Computed only from listings that publish a salary range; groups
        with fewer than 5 salaried listings are omitted. These are percentiles,
        not averages.
      </p>
    </>
  );
}
