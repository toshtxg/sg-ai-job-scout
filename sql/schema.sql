-- SG AI Job Market Scout — Database Schema
-- Run this in the Supabase Dashboard SQL Editor

CREATE TABLE IF NOT EXISTS raw_listings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source TEXT NOT NULL,
    source_url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    description TEXT,
    salary_min NUMERIC,
    salary_max NUMERIC,
    salary_currency TEXT DEFAULT 'SGD',
    posting_date DATE,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    raw_data JSONB
);

CREATE TABLE IF NOT EXISTS classified_listings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    listing_id UUID REFERENCES raw_listings(id) ON DELETE CASCADE,
    role_category TEXT,
    seniority_level TEXT,
    technical_skills TEXT[],
    soft_skills TEXT[],
    domain_knowledge TEXT[],
    requires_ai_ml BOOLEAN,
    remote_hybrid_onsite TEXT,
    industry TEXT,
    classified_at TIMESTAMPTZ DEFAULT NOW(),
    model_used TEXT DEFAULT 'gpt-5-nano'
);

CREATE TABLE IF NOT EXISTS market_snapshots (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    snapshot_date DATE NOT NULL UNIQUE,
    total_listings INTEGER,
    listings_by_role JSONB,
    listings_by_seniority JSONB,
    top_skills JSONB,
    avg_salary_by_role JSONB,
    new_listings_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
