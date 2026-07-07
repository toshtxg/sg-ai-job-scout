import { loadClassifiedListings } from "@/lib/data";
import { buildMarketPulseData } from "@/lib/market";
import { DataCaveat } from "@/components/data-caveat";
import { MarketPulse } from "@/components/market-pulse";
import { PageHeader } from "@/components/ui";

export const revalidate = 900;

export default async function MarketPulsePage() {
  const listings = await loadClassifiedListings({ includeDescription: true });
  const data = buildMarketPulseData(listings);
  return (
    <>
      <PageHeader title="Market Pulse" eyebrow="AI premium and industry adoption" />
      <DataCaveat />
      <MarketPulse data={data} />
    </>
  );
}
