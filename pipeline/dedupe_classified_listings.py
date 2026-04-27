#!/usr/bin/env python3
"""
Remove duplicate classified_listings rows, keeping the newest row per listing_id.

Examples:
  python -m pipeline.dedupe_classified_listings
  python -m pipeline.dedupe_classified_listings --apply
"""
import argparse
import logging
import os
import sys
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove duplicate classified_listings rows."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete duplicate rows. Without this flag, the script only reports.",
    )
    return parser.parse_args()


def _sort_key(row: dict) -> tuple:
    return (row.get("classified_at") or "", row["id"])


def main() -> None:
    args = parse_args()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    client = create_client(url, key)

    rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("classified_listings")
            .select("id, listing_id, classified_at")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size

    by_listing_id: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        by_listing_id[row["listing_id"]].append(row)

    duplicate_groups = [
        sorted(group, key=_sort_key, reverse=True)
        for group in by_listing_id.values()
        if len(group) > 1
    ]
    delete_ids = [row["id"] for group in duplicate_groups for row in group[1:]]

    logger.info("classified_listings rows: %s", len(rows))
    logger.info("duplicate listing_ids: %s", len(duplicate_groups))
    logger.info("rows to delete: %s", len(delete_ids))

    if not delete_ids:
        logger.info("No duplicate rows found")
        return

    if not args.apply:
        logger.info("Dry run only. Re-run with --apply to delete duplicates.")
        return

    batch_size = 100
    deleted = 0
    for i in range(0, len(delete_ids), batch_size):
        batch = delete_ids[i : i + batch_size]
        client.table("classified_listings").delete().in_("id", batch).execute()
        deleted += len(batch)

    logger.info("Deleted %s duplicate rows", deleted)


if __name__ == "__main__":
    main()
