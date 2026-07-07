import type { ClassifiedListing } from "@/lib/types";

export type SalaryBin = {
  label: string;
  min: number;
  max: number;
};

export const SALARY_BINS: SalaryBin[] = [
  { label: "Under $5k", min: 0, max: 5000 },
  { label: "$5k–$7k", min: 5000, max: 7000 },
  { label: "$7k–$10k", min: 7000, max: 10000 },
  { label: "$10k–$15k", min: 10000, max: 15000 },
  { label: "$15k–$20k", min: 15000, max: 20000 },
  { label: "$20k+", min: 20000, max: Number.POSITIVE_INFINITY },
];

function toNumber(value: number | string | null | undefined) {
  if (value === null || value === undefined) return null;
  const num = typeof value === "number" ? value : Number(value);
  return Number.isFinite(num) ? num : null;
}

export function assignSalaryBin(
  salaryMin: number | string | null | undefined,
  salaryMax: number | string | null | undefined,
): string | null {
  const values = [toNumber(salaryMin), toNumber(salaryMax)].filter(
    (v): v is number => v !== null,
  );
  if (values.length === 0) return null;
  const midpoint = values.reduce((acc, v) => acc + v, 0) / values.length;
  const bin = SALARY_BINS.find((b) => midpoint >= b.min && midpoint < b.max);
  return bin ? bin.label : null;
}

export function formatSalaryRange(
  salaryMin: number | string | null | undefined,
  salaryMax: number | string | null | undefined,
): string {
  const lo = toNumber(salaryMin);
  const hi = toNumber(salaryMax);
  const fmt = (v: number) => `$${Math.round(v).toLocaleString()}`;
  if (lo !== null && hi !== null) return `${fmt(lo)}–${fmt(hi)}`;
  if (hi !== null) return `Up to ${fmt(hi)}`;
  if (lo !== null) return `From ${fmt(lo)}`;
  return "—";
}

export type SalaryPercentiles = {
  key: string;
  count: number;
  p25: number;
  p50: number;
  p75: number;
};

function salaryMidpointValue(
  salaryMin: number | string | null | undefined,
  salaryMax: number | string | null | undefined,
): number | null {
  const lo = toNumber(salaryMin);
  const hi = toNumber(salaryMax);
  if (lo !== null && hi !== null) return (lo + hi) / 2;
  return hi ?? lo;
}

/** Linear-interpolated percentile of an ascending-sorted array (0 <= p <= 1). */
export function percentile(sortedValues: number[], p: number): number {
  if (!sortedValues.length) return 0;
  if (sortedValues.length === 1) return sortedValues[0];
  const index = (sortedValues.length - 1) * p;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  if (lower === upper) return sortedValues[lower];
  const weight = index - lower;
  return sortedValues[lower] * (1 - weight) + sortedValues[upper] * weight;
}

/**
 * Compute p25 / median / p75 of the posted-salary midpoint, grouped by the
 * key returned from `getKey`. Groups with fewer than `minCount` salaried
 * listings are dropped so percentiles stay meaningful.
 */
export function salaryPercentilesByKey(
  listings: ClassifiedListing[],
  getKey: (row: ClassifiedListing) => string | null | undefined,
  minCount = 5,
): SalaryPercentiles[] {
  const groups = new Map<string, number[]>();
  for (const row of listings) {
    const midpoint = salaryMidpointValue(row.raw.salary_min, row.raw.salary_max);
    if (midpoint === null) continue;
    const key = getKey(row);
    if (!key) continue;
    const bucket = groups.get(key);
    if (bucket) bucket.push(midpoint);
    else groups.set(key, [midpoint]);
  }

  return [...groups.entries()]
    .filter(([, values]) => values.length >= minCount)
    .map(([key, values]) => {
      const sorted = [...values].sort((a, b) => a - b);
      return {
        key,
        count: sorted.length,
        p25: Math.round(percentile(sorted, 0.25)),
        p50: Math.round(percentile(sorted, 0.5)),
        p75: Math.round(percentile(sorted, 0.75)),
      };
    })
    .sort((a, b) => b.p50 - a.p50);
}
