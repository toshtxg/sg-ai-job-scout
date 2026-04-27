-- Deduplicate classified_listings and enforce one row per raw listing.
-- Run this in the Supabase SQL Editor.

BEGIN;

-- Remove any impossible rows before tightening constraints.
DELETE FROM classified_listings
WHERE listing_id IS NULL;

-- Keep the newest classification per listing_id.
WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY listing_id
            ORDER BY classified_at DESC NULLS LAST, id DESC
        ) AS row_num
    FROM classified_listings
)
DELETE FROM classified_listings AS target
USING ranked
WHERE target.id = ranked.id
  AND ranked.row_num > 1;

ALTER TABLE classified_listings
    ALTER COLUMN listing_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'classified_listings_listing_id_key'
          AND conrelid = 'classified_listings'::regclass
    ) THEN
        ALTER TABLE classified_listings
            ADD CONSTRAINT classified_listings_listing_id_key UNIQUE (listing_id);
    END IF;
END $$;

COMMIT;
