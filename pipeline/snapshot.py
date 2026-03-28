import json
import logging
from collections import Counter
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)


def generate_snapshot(supabase_client) -> dict:
    """Aggregate classified data into a market snapshot for today."""
    today = date.today().isoformat()

    # Fetch classified listings with related raw listing data
    all_classified = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase_client.table("classified_listings")
            .select(
                "*, raw_listings!listing_id("
                "title, salary_min, salary_max, posting_date, scraped_at"
                ")"
            )
            .range(offset, offset + page_size - 1)
            .execute()
        )
        all_classified.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size

    if not all_classified:
        logger.warning("No classified listings found — skipping snapshot")
        return {"snapshot_date": today}

    total = len(all_classified)

    # Listings by role
    role_counter = Counter(row.get("role_category", "Other") for row in all_classified)
    listings_by_role = dict(role_counter.most_common())

    # Listings by seniority
    seniority_counter = Counter(
        row.get("seniority_level", "Mid") for row in all_classified
    )
    listings_by_seniority = dict(seniority_counter.most_common())

    # Top skills
    skill_counter = Counter()
    for row in all_classified:
        for skill in row.get("technical_skills", []) or []:
            skill_counter[skill] += 1
    top_skills = [
        {"skill": skill, "count": count}
        for skill, count in skill_counter.most_common(30)
    ]

    # Average salary by role
    salary_by_role: dict[str, dict] = {}
    for row in all_classified:
        raw = row.get("raw_listings", {}) or {}
        role = row.get("role_category", "Other")
        s_min = raw.get("salary_min")
        s_max = raw.get("salary_max")
        if s_min is not None or s_max is not None:
            if role not in salary_by_role:
                salary_by_role[role] = {"mins": [], "maxs": []}
            if s_min is not None:
                salary_by_role[role]["mins"].append(float(s_min))
            if s_max is not None:
                salary_by_role[role]["maxs"].append(float(s_max))

    avg_salary_by_role = {}
    for role, data in salary_by_role.items():
        avg_salary_by_role[role] = {
            "avg_min": round(sum(data["mins"]) / len(data["mins"]), 2)
            if data["mins"]
            else None,
            "avg_max": round(sum(data["maxs"]) / len(data["maxs"]), 2)
            if data["maxs"]
            else None,
            "count": max(len(data["mins"]), len(data["maxs"])),
        }

    # New listings in last 7 days
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    new_count = sum(
        1
        for row in all_classified
        if (row.get("raw_listings", {}) or {}).get("posting_date")
        and row["raw_listings"]["posting_date"] >= cutoff
    )

    snapshot = {
        "snapshot_date": today,
        "total_listings": total,
        "listings_by_role": listings_by_role,
        "listings_by_seniority": listings_by_seniority,
        "top_skills": top_skills,
        "avg_salary_by_role": avg_salary_by_role,
        "new_listings_count": new_count,
    }

    # Upsert into market_snapshots
    try:
        supabase_client.table("market_snapshots").upsert(
            snapshot, on_conflict="snapshot_date"
        ).execute()
        logger.info(f"Snapshot saved for {today}")
    except Exception as e:
        logger.error(f"Failed to save snapshot: {e}")

    return snapshot
