import {
  AI_INVOLVEMENT_LEVELS,
  AI_SKILLS_TAXONOMY,
  DEFAULT_ROLES,
  SENIORITY_LEVELS,
} from "@/lib/constants";
import type {
  AiCategoryMatch,
  ChartDatum,
  ClassifiedListing,
  PostingTrendPoint,
} from "@/lib/types";

export function toNumber(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatSalary(min: number | string | null, max: number | string | null) {
  const salaryMin = toNumber(min);
  const salaryMax = toNumber(max);
  if (salaryMin !== null && salaryMax !== null) {
    return `SGD ${salaryMin.toLocaleString()}-${salaryMax.toLocaleString()}/mo`;
  }
  if (salaryMax !== null) return `Up to SGD ${salaryMax.toLocaleString()}/mo`;
  if (salaryMin !== null) return `From SGD ${salaryMin.toLocaleString()}/mo`;
  return "Salary not posted";
}

export function compactSalary(min: number | string | null, max: number | string | null) {
  const salaryMin = toNumber(min);
  const salaryMax = toNumber(max);
  if (salaryMin !== null && salaryMax !== null) {
    return `$${salaryMin.toLocaleString()}-${salaryMax.toLocaleString()}`;
  }
  if (salaryMax !== null) return `Up to $${salaryMax.toLocaleString()}`;
  return "-";
}

export function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function formatDate(value: string | null | undefined) {
  const parsed = parseDate(value);
  if (!parsed) return "-";
  return new Intl.DateTimeFormat("en-SG", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}

export function formatAge(value: string | null | undefined) {
  const parsed = parseDate(value);
  if (!parsed) return "unknown";
  const deltaMs = Math.max(Date.now() - parsed.getTime(), 0);
  const days = Math.floor(deltaMs / 86_400_000);
  if (days > 0) return `${days}d ago`;
  const hours = Math.floor(deltaMs / 3_600_000);
  if (hours > 0) return `${hours}h ago`;
  return `${Math.floor(deltaMs / 60_000)}m ago`;
}

export function isDataRole(role: string | null | undefined) {
  return DEFAULT_ROLES.includes(role || "");
}

export function isRecentListing(row: ClassifiedListing, days = 7) {
  const posted = parseDate(row.raw.posting_date);
  if (!posted) return false;
  const cutoff = Date.now() - days * 86_400_000;
  return posted.getTime() >= cutoff;
}

export function countBy<T>(items: T[], getKey: (item: T) => string | null | undefined) {
  const counts = new Map<string, number>();
  for (const item of items) {
    const key = getKey(item) || "Unknown";
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  return counts;
}

export function topCounts(counts: Map<string, number>, limit = 20): ChartDatum[] {
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([name, value]) => ({ name, value }));
}

export function skillCounts(listings: ClassifiedListing[], limit = 30) {
  const counts = new Map<string, number>();
  for (const row of listings) {
    for (const skill of row.technical_skills || []) {
      if (!skill) continue;
      counts.set(skill, (counts.get(skill) || 0) + 1);
    }
  }
  return topCounts(counts, limit);
}

export function uniqueSkills(listings: ClassifiedListing[]) {
  return skillCounts(listings, 500).map((item) => item.name);
}

export function salaryMidpoint(row: ClassifiedListing) {
  const min = toNumber(row.raw.salary_min);
  const max = toNumber(row.raw.salary_max);
  if (min !== null && max !== null) return (min + max) / 2;
  return max ?? min;
}

export function average(values: number[]) {
  if (!values.length) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function analyzeAiCategories(row: ClassifiedListing): AiCategoryMatch[] {
  const text = `${row.raw.description || ""} ${(row.technical_skills || []).join(" ")}`.toLowerCase();
  const matches: AiCategoryMatch[] = [];
  for (const [category, keywords] of Object.entries(AI_SKILLS_TAXONOMY)) {
    const found = keywords.filter((keyword) => text.includes(keyword.toLowerCase()));
    if (found.length) matches.push({ category, keywords: found });
  }
  return matches;
}

export function classifyAiInvolvement(matches: AiCategoryMatch[]) {
  const matchedCategories = new Set(matches.map((match) => match.category));
  return Object.entries(AI_INVOLVEMENT_LEVELS)
    .filter(([, categories]) => categories.some((category) => matchedCategories.has(category)))
    .map(([label]) => label);
}

export function roleScopeFilter(rows: ClassifiedListing[], scope: string) {
  if (scope === "All Roles") return rows.filter((row) => row.role_category !== "Other");
  if (scope === "Data & Analytics") {
    return rows.filter((row) => DEFAULT_ROLES.includes(row.role_category || ""));
  }
  return rows.filter((row) => row.role_category !== "Other");
}

export function buildSenioritySkillMatrix(listings: ClassifiedListing[], topN = 18) {
  const activeLevels = SENIORITY_LEVELS.filter((level) =>
    listings.some((row) => row.seniority_level === level),
  );
  const globalCounts = new Map<string, number>();
  const totals = new Map<string, number>();
  const byLevel = new Map<string, Map<string, number>>();

  for (const row of listings) {
    const level = row.seniority_level || "Mid";
    const skills = new Set((row.technical_skills || []).filter(Boolean));
    if (!skills.size) continue;
    totals.set(level, (totals.get(level) || 0) + 1);
    if (!byLevel.has(level)) byLevel.set(level, new Map());
    const levelCounts = byLevel.get(level)!;
    for (const skill of skills) {
      globalCounts.set(skill, (globalCounts.get(skill) || 0) + 1);
      levelCounts.set(skill, (levelCounts.get(skill) || 0) + 1);
    }
  }

  const skills = [...globalCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .map(([skill]) => skill);

  return skills.map((skill) => ({
    skill,
    values: activeLevels.map((level) => {
      const total = totals.get(level) || 1;
      const count = byLevel.get(level)?.get(skill) || 0;
      return { level, value: Math.round((count / total) * 100) };
    }),
  }));
}

export type AiSkillsAnalysis = {
  categories: ChartDatum[];
  keywordCounts: Record<string, ChartDatum[]>;
  rolesByCategory: Record<string, ChartDatum[]>;
};

export function buildAiSkillsAnalysis(listings: ClassifiedListing[]): AiSkillsAnalysis {
  const categoryCounts = new Map<string, number>();
  const keywordCounts = new Map<string, Map<string, number>>();
  const rolesByCategory = new Map<string, Map<string, number>>();

  for (const listing of listings) {
    const matches = analyzeAiCategories(listing);
    for (const match of matches) {
      categoryCounts.set(match.category, (categoryCounts.get(match.category) || 0) + 1);

      if (!keywordCounts.has(match.category)) keywordCounts.set(match.category, new Map());
      const categoryKeywords = keywordCounts.get(match.category)!;
      for (const keyword of match.keywords) {
        categoryKeywords.set(keyword, (categoryKeywords.get(keyword) || 0) + 1);
      }

      if (!rolesByCategory.has(match.category)) rolesByCategory.set(match.category, new Map());
      const role = listing.role_category || "Unknown";
      const roleCounts = rolesByCategory.get(match.category)!;
      roleCounts.set(role, (roleCounts.get(role) || 0) + 1);
    }
  }

  return {
    categories: topCounts(categoryCounts),
    keywordCounts: Object.fromEntries(
      [...keywordCounts.entries()].map(([category, counts]) => [
        category,
        topCounts(counts, 20),
      ]),
    ),
    rolesByCategory: Object.fromEntries(
      [...rolesByCategory.entries()].map(([category, counts]) => [
        category,
        topCounts(counts, 20).filter((row) => row.name !== "Other"),
      ]),
    ),
  };
}

export type MarketPulseData = {
  dataRowsCount: number;
  aiRowsCount: number;
  aiSalary: number;
  nonAiSalary: number;
  premium: number;
  topSkills: ChartDatum[];
  industries: ChartDatum[];
};

export function buildMarketPulseData(listings: ClassifiedListing[]): MarketPulseData {
  const dataRows = listings.filter((row) => row.role_category !== "Other");
  const aiRows = dataRows.filter(
    (row) => row.requires_ai_ml || analyzeAiCategories(row).length > 0,
  );
  const aiRowIds = new Set(aiRows.map((row) => row.id || row.raw.source_url));
  const nonAiRows = dataRows.filter((row) => !aiRowIds.has(row.id || row.raw.source_url));
  const aiSalary = average(aiRows.map(salaryMidpoint).filter((value): value is number => value !== null));
  const nonAiSalary = average(
    nonAiRows.map(salaryMidpoint).filter((value): value is number => value !== null),
  );
  const premium = nonAiSalary ? Math.round(((aiSalary - nonAiSalary) / nonAiSalary) * 100) : 0;
  const industryCounts = new Map<string, number>();

  for (const row of aiRows) {
    const industry = row.industry || "Unknown";
    industryCounts.set(industry, (industryCounts.get(industry) || 0) + 1);
  }

  return {
    dataRowsCount: dataRows.length,
    aiRowsCount: aiRows.length,
    aiSalary,
    nonAiSalary,
    premium,
    topSkills: skillCounts(dataRows, 12),
    industries: topCounts(industryCounts, 12),
  };
}

export function buildPostingTrend(
  listings: ClassifiedListing[],
  days = 30,
): PostingTrendPoint[] {
  const datedRows = listings
    .map((row) => parseDate(row.raw.posting_date))
    .filter((value): value is Date => value !== null)
    .sort((a, b) => a.getTime() - b.getTime());

  if (!datedRows.length) return [];

  const lastDate = datedRows[datedRows.length - 1];
  const end = new Date(
    Date.UTC(lastDate.getUTCFullYear(), lastDate.getUTCMonth(), lastDate.getUTCDate()),
  );
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - (days - 1));

  const dailyCounts = new Map<string, number>();
  for (const posted of datedRows) {
    const key = posted.toISOString().slice(0, 10);
    dailyCounts.set(key, (dailyCounts.get(key) || 0) + 1);
  }

  const points: PostingTrendPoint[] = [];
  const rollingWindow: number[] = [];
  for (let cursor = new Date(start); cursor <= end; cursor.setUTCDate(cursor.getUTCDate() + 1)) {
    const key = cursor.toISOString().slice(0, 10);
    const daily = dailyCounts.get(key) || 0;
    rollingWindow.push(daily);
    if (rollingWindow.length > 7) rollingWindow.shift();
    const rollingAverage =
      rollingWindow.reduce((sum, value) => sum + value, 0) / rollingWindow.length;
    points.push({
      date: key,
      daily,
      rolling_average: Number(rollingAverage.toFixed(1)),
    });
  }

  return points;
}
