import json
import logging
from collections import Counter
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

# Snapshot columns added by sql/migrations/2026-07-05-listing-lifecycle.sql.
# Stripped from the upsert payload on the fallback path when the migration is
# not yet applied.
NEW_SNAPSHOT_KEYS = ("salary_percentiles_by_role", "active_listings_count")
_warned_snapshot_upsert = False


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Linear-interpolation percentile of a pre-sorted, non-empty list."""
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * pct
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = rank - lower
    return sorted_values[lower] + (
        sorted_values[upper] - sorted_values[lower]
    ) * fraction


def _fetch_classified(supabase_client, embed_columns: str) -> list[dict]:
    """Fetch all classified listings with embedded raw listing columns."""
    all_classified = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase_client.table("classified_listings")
            .select(f"*, raw_listings!listing_id({embed_columns})")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        all_classified.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return all_classified


def generate_snapshot(supabase_client) -> dict:
    """Aggregate classified data into a market snapshot for today."""
    global _warned_snapshot_upsert
    today = date.today().isoformat()

    # Fetch classified listings with related raw listing data. expiry_date is
    # a lifecycle column — if its migration has not been run yet, retry the
    # select without it.
    try:
        all_classified = _fetch_classified(
            supabase_client,
            "title, salary_min, salary_max, posting_date, scraped_at, expiry_date",
        )
    except Exception as e:
        logger.warning(
            "Snapshot select with expiry_date failed. Run "
            "sql/migrations/2026-07-05-listing-lifecycle.sql in Supabase. "
            "Retrying without lifecycle columns: %s",
            e,
        )
        all_classified = _fetch_classified(
            supabase_client,
            "title, salary_min, salary_max, posting_date, scraped_at",
        )

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

    # Salary percentiles by role — p25/p50/p75 of the listing salary midpoint
    midpoints_by_role: dict[str, list[float]] = {}
    for row in all_classified:
        raw = row.get("raw_listings", {}) or {}
        role = row.get("role_category", "Other")
        s_min = raw.get("salary_min")
        s_max = raw.get("salary_max")
        values = [float(v) for v in (s_min, s_max) if v is not None]
        if not values:
            continue
        midpoints_by_role.setdefault(role, []).append(sum(values) / len(values))

    salary_percentiles_by_role = {}
    for role, midpoints in midpoints_by_role.items():
        midpoints.sort()
        salary_percentiles_by_role[role] = {
            "p25": round(_percentile(midpoints, 0.25), 2),
            "p50": round(_percentile(midpoints, 0.50), 2),
            "p75": round(_percentile(midpoints, 0.75), 2),
            "count": len(midpoints),
        }

    # New listings in last 7 days
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    new_count = sum(
        1
        for row in all_classified
        if (row.get("raw_listings", {}) or {}).get("posting_date")
        and row["raw_listings"]["posting_date"] >= cutoff
    )

    # Active listings — raw listing expiry_date is today or later
    active_count = sum(
        1
        for row in all_classified
        if (row.get("raw_listings", {}) or {}).get("expiry_date")
        and row["raw_listings"]["expiry_date"] >= today
    )

    snapshot = {
        "snapshot_date": today,
        "total_listings": total,
        "listings_by_role": listings_by_role,
        "listings_by_seniority": listings_by_seniority,
        "top_skills": top_skills,
        "avg_salary_by_role": avg_salary_by_role,
        "new_listings_count": new_count,
        "salary_percentiles_by_role": salary_percentiles_by_role,
        "active_listings_count": active_count,
    }

    # Upsert into market_snapshots. If the new snapshot columns are missing
    # (migration not yet run), warn once and retry without them.
    try:
        supabase_client.table("market_snapshots").upsert(
            snapshot, on_conflict="snapshot_date"
        ).execute()
        logger.info(f"Snapshot saved for {today}")
    except Exception as e:
        if not _warned_snapshot_upsert:
            logger.warning(
                "market_snapshots upsert failed (likely missing new columns). "
                "Run sql/migrations/2026-07-05-listing-lifecycle.sql in "
                "Supabase, then retry. Falling back without new keys for now: %s",
                e,
            )
            _warned_snapshot_upsert = True
        else:
            logger.error(f"Failed to save snapshot: {e}")
        slim = {k: v for k, v in snapshot.items() if k not in NEW_SNAPSHOT_KEYS}
        try:
            supabase_client.table("market_snapshots").upsert(
                slim, on_conflict="snapshot_date"
            ).execute()
            logger.info(f"Snapshot saved for {today} (without new columns)")
        except Exception as retry_error:
            logger.error(f"Failed to save snapshot: {retry_error}")

    return snapshot
