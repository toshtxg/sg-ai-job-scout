import { loadClassifiedListings } from "@/lib/data";
import { buildMarketPulseData } from "@/lib/market";
import { MarketPulse } from "@/components/market-pulse";
import { PageHeader } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function MarketPulsePage() {
  const listings = await loadClassifiedListings({ includeDescription: true });
  const data = buildMarketPulseData(listings);
  return (
    <>
      <PageHeader title="Market Pulse" eyebrow="AI exposure, skills, and industry demand" />
      <MarketPulse data={data} />
    </>
  );
}
