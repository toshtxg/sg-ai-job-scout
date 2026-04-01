#!/usr/bin/env python3
"""
Run the full scraping -> classification -> snapshot pipeline.
Usage: python pipeline/run_pipeline.py
"""
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

from pipeline.scrapers.mycareersfuture import MyCareersFutureScraper
from pipeline.classifier import classify_unprocessed
from pipeline.snapshot import generate_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SEARCH_TERMS = [
    # Data Science
    "data scientist",
    "data science",
    "data analyst",
    "data engineer",
    "data architect",
    "data manager",
    # AI / ML
    "machine learning engineer",
    "AI engineer",
    "artificial intelligence",
    "deep learning",
    "computer vision",
    "MLOps",
    "NLP",
    "LLM",
    "generative AI",
    "prompt engineer",
    # Analytics / BI
    "analytics",
    "analytics engineer",
    "business intelligence",
    "BI analyst",
    "BI developer",
    "business analyst data",
    "reporting analyst",
    "insights analyst",
    # Research
    "research scientist AI",
    "applied scientist",
    "quantitative analyst",
]


def _get_existing_urls(client) -> set[str]:
    """Fetch all source_urls already in raw_listings."""
    existing = set()
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("raw_listings")
            .select("source_url")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        for row in resp.data:
            existing.add(row["source_url"])
        if len(resp.data) < page_size:
            break
        offset += page_size
    return existing


def store_listings(listings: list[dict], client) -> int:
    """Insert only truly new listings, skipping URLs already in the database."""
    if not listings:
        return 0

    existing_urls = _get_existing_urls(client)
    new_listings = [l for l in listings if l["source_url"] not in existing_urls]

    if not new_listings:
        logger.info("No new listings to store (all already in database)")
        return 0

    logger.info(
        f"Inserting {len(new_listings)} new listings "
        f"(skipped {len(listings) - len(new_listings)} existing)"
    )

    batch_size = 100
    total = 0
    for i in range(0, len(new_listings), batch_size):
        batch = new_listings[i : i + batch_size]
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
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    client = create_client(url, key)
    logger.info("=" * 60)
    logger.info("SG AI Job Market Scout — Pipeline Run")
    logger.info("=" * 60)

    # --- Phase A: Scrape ---
    logger.info("--- PHASE A: Scraping ---")
    scrapers = [
        MyCareersFutureScraper(),
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
