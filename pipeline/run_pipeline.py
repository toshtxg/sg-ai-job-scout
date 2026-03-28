#!/usr/bin/env python3
"""
Run the full scraping -> classification -> snapshot pipeline.
Usage: python pipeline/run_pipeline.py
"""
import logging
import os
import sys

# Add project root to path so imports work from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

from pipeline.scrapers.mycareersfuture import MyCareersFutureScraper
from pipeline.scrapers.nodeflair import NodeFlairScraper
from pipeline.scrapers.jobstreet import JobStreetScraper
from pipeline.classifier import classify_unprocessed
from pipeline.snapshot import generate_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SEARCH_TERMS = [
    "data scientist",
    "data analyst",
    "machine learning engineer",
    "AI engineer",
    "data engineer",
    "analytics",
    "MLOps",
    "NLP",
    "LLM",
]


def store_listings(listings: list[dict], client) -> int:
    """Upsert listings into raw_listings, skipping duplicates by source_url."""
    if not listings:
        return 0
    # Upsert in batches to avoid payload size limits
    batch_size = 100
    total = 0
    for i in range(0, len(listings), batch_size):
        batch = listings[i : i + batch_size]
        try:
            response = (
                client.table("raw_listings")
                .upsert(batch, on_conflict="source_url")
                .execute()
            )
            total += len(response.data)
        except Exception as e:
            logger.error(f"Failed to store batch {i // batch_size}: {e}")
    return total


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    client = create_client(url, key)
    logger.info("=" * 60)
    logger.info("SG AI Job Market Scout — Pipeline Run")
    logger.info("=" * 60)

    # --- Phase A: Scrape ---
    logger.info("--- PHASE A: Scraping ---")
    scrapers = [
        MyCareersFutureScraper(),
        NodeFlairScraper(),
        JobStreetScraper(),
    ]
    total_stored = 0
    for scraper in scrapers:
        try:
            listings = scraper.scrape_all(SEARCH_TERMS, max_pages=3)
            if listings:
                stored = store_listings(listings, client)
                total_stored += stored
                logger.info(f"[{scraper.source_name}] Stored {stored} listings")
            else:
                logger.info(f"[{scraper.source_name}] No listings found")
        except Exception as e:
            logger.error(f"[{scraper.source_name}] Scraper failed: {e}")

    logger.info(f"Total listings stored: {total_stored}")

    # --- Phase B: Classify ---
    logger.info("--- PHASE B: Classification ---")
    try:
        classified_count = classify_unprocessed(client)
        logger.info(f"Classified {classified_count} new listings")
    except Exception as e:
        logger.error(f"Classification failed: {e}")

    # --- Phase C: Snapshot ---
    logger.info("--- PHASE C: Snapshot ---")
    try:
        snapshot = generate_snapshot(client)
        logger.info(
            f"Snapshot: {snapshot.get('total_listings', 0)} total listings, "
            f"{snapshot.get('new_listings_count', 0)} new this week"
        )
    except Exception as e:
        logger.error(f"Snapshot generation failed: {e}")

    logger.info("=" * 60)
    logger.info("Pipeline complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
