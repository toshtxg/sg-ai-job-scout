#!/usr/bin/env python3
"""
Re-classify listings that were tagged as "Other" or invalid role categories.
Run: python -m pipeline.reclassify_others
"""
import logging
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

from pipeline.classifier import CLASSIFIER_MODEL, VALID_ROLES, _enforce_enums, classify_listing
from pipeline.skills_normalizer import normalize_skills

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    client = create_client(url, key)

    # Find all classified listings with bad role categories
    logger.info("Fetching misclassified listings...")
    all_classified = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("classified_listings")
            .select("id, listing_id, role_category")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        all_classified.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size

    # Find ones with "Other" or invalid role categories
    bad = [
        r for r in all_classified
        if r["role_category"] == "Other" or r["role_category"] not in VALID_ROLES
    ]
    logger.info(f"Found {len(bad)} listings to re-classify (Other or invalid role)")

    if not bad:
        logger.info("Nothing to re-classify")
        return

    # Fetch the raw listings for these
    bad_listing_ids = {r["listing_id"] for r in bad}
    bad_id_map = {r["listing_id"]: r["id"] for r in bad}

    raw_listings = []
    for listing_id in bad_listing_ids:
        resp = (
            client.table("raw_listings")
            .select("id, title, company, description")
            .eq("id", listing_id)
            .execute()
        )
        if resp.data:
            raw_listings.append(resp.data[0])

    logger.info(f"Fetched {len(raw_listings)} raw listings for re-classification")

    reclassified = 0
    still_other = 0
    for i, listing in enumerate(raw_listings):
        result = classify_listing(
            listing["title"],
            listing.get("company"),
            listing.get("description"),
        )
        if result is None:
            continue

        result = _enforce_enums(result)
        new_role = result.get("role_category", "Other")

        if new_role == "Other":
            still_other += 1

        classified_id = bad_id_map[listing["id"]]

        update_row = {
            "role_category": new_role,
            "seniority_level": result.get("seniority_level", "Mid"),
            "technical_skills": normalize_skills(result.get("technical_skills", [])),
            "soft_skills": normalize_skills(result.get("soft_skills", [])),
            "domain_knowledge": result.get("domain_knowledge", []),
            "requires_ai_ml": result.get("requires_ai_ml", False),
            "remote_hybrid_onsite": result.get("remote_hybrid_onsite", "Unknown"),
            "industry": result.get("industry", "Technology"),
            "model_used": CLASSIFIER_MODEL,
        }

        try:
            client.table("classified_listings").update(update_row).eq(
                "id", classified_id
            ).execute()
            reclassified += 1
        except Exception as e:
            logger.error(f"Failed to update {classified_id}: {e}")

        if (i + 1) % 50 == 0:
            logger.info(f"Progress: {i + 1}/{len(raw_listings)}")

        time.sleep(0.2)

    logger.info(f"Re-classified {reclassified} listings")
    logger.info(f"Still 'Other' after re-classification: {still_other}")
    logger.info(
        f"Successfully re-categorized: {reclassified - still_other} listings"
    )


if __name__ == "__main__":
    main()
