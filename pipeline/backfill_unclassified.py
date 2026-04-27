#!/usr/bin/env python3
"""
Backfill unclassified raw listings into classified_listings.

Examples:
  python -m pipeline.backfill_unclassified --limit 100
  python -m pipeline.backfill_unclassified --limit 250 --batch-size 10 --refresh-snapshot
"""
import argparse
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

from pipeline.classifier import classify_unprocessed
from pipeline.snapshot import generate_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill unclassified job listings into classified_listings."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of unclassified listings to process in this run.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Number of listings to classify per OpenAI request.",
    )
    parser.add_argument(
        "--refresh-snapshot",
        action="store_true",
        help="Rebuild today's market snapshot after classification completes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    client = create_client(url, key)
    logger.info("Starting manual backfill")
    classified_count = classify_unprocessed(
        client,
        limit=args.limit,
        batch_size=args.batch_size,
    )
    logger.info(f"Backfill classified {classified_count} listings")

    if args.refresh_snapshot:
        snapshot = generate_snapshot(client)
        logger.info(
            "Snapshot refreshed: %s total listings, %s new this week",
            snapshot.get("total_listings", 0),
            snapshot.get("new_listings_count", 0),
        )


if __name__ == "__main__":
    main()
