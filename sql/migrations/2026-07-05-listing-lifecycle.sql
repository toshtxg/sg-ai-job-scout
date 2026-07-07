-- Listing lifecycle fields and richer snapshot columns.
-- Migrations are NOT applied automatically: run this manually in the
-- Supabase Dashboard SQL Editor before (or soon after) deploying the
-- matching pipeline changes. Until it is run, the pipeline logs a warning
-- and falls back to writing without these columns.

BEGIN;

-- raw_listings: listing lifecycle tracking
ALTER TABLE raw_listings
    ADD COLUMN IF NOT EXISTS expiry_date DATE,
    ADD COLUMN IF NOT EXISTS original_posting_date DATE,
    ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ DEFAULT NOW();

-- market_snapshots: richer aggregates
ALTER TABLE market_snapshots
    ADD COLUMN IF NOT EXISTS salary_percentiles_by_role JSONB,
    ADD COLUMN IF NOT EXISTS active_listings_count INTEGER;

COMMIT;
