export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type RawListing = {
  title: string | null;
  company: string | null;
  description: string | null;
  salary_min: number | string | null;
  salary_max: number | string | null;
  salary_currency?: string | null;
  source_url: string | null;
  posting_date: string | null;
  scraped_at?: string | null;
  source?: string | null;
};

export type ClassifiedListing = {
  id?: string;
  listing_id?: string;
  role_category: string | null;
  seniority_level: string | null;
  technical_skills: string[] | null;
  soft_skills?: string[] | null;
  domain_knowledge?: string[] | null;
  requires_ai_ml: boolean | null;
  remote_hybrid_onsite: string | null;
  industry: string | null;
  classified_at?: string | null;
  model_used?: string | null;
  raw: RawListing;
};

export type MarketSnapshot = {
  id?: string;
  snapshot_date: string;
  total_listings: number | null;
  listings_by_role: Record<string, number> | null;
  listings_by_seniority: Record<string, number> | null;
  top_skills: { skill: string; count: number }[] | null;
  avg_salary_by_role:
    | Record<
        string,
        { avg_min: number | null; avg_max: number | null; count?: number | null }
      >
    | null;
  new_listings_count: number | null;
  created_at?: string | null;
};

export type AiCategoryMatch = {
  category: string;
  keywords: string[];
};

export type ChartDatum = {
  name: string;
  value: number;
  secondary?: number;
  label?: string;
};

export type PostingTrendPoint = {
  date: string;
  daily: number;
  rolling_average: number;
};
