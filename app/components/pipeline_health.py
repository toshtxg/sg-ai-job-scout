import streamlit as st
from datetime import datetime, timedelta, timezone


@st.cache_data(ttl=300)
def _fetch_health_stats(_client):
    """Fetch pipeline health stats from Supabase (cached 5 min)."""
    # Total raw listings
    raw_resp = (
        _client.table("raw_listings")
        .select("*", count="exact")
        .limit(0)
        .execute()
    )
    total_raw = raw_resp.count or 0

    # Total classified listings
    cls_resp = (
        _client.table("classified_listings")
        .select("*", count="exact")
        .limit(0)
        .execute()
    )
    total_classified = cls_resp.count or 0

    # Latest scraped_at
    scraped_resp = (
        _client.table("raw_listings")
        .select("scraped_at")
        .order("scraped_at", desc=True)
        .limit(1)
        .execute()
    )
    last_scraped = None
    if scraped_resp.data:
        last_scraped = scraped_resp.data[0]["scraped_at"]

    # Latest snapshot date
    snap_resp = (
        _client.table("market_snapshots")
        .select("snapshot_date")
        .order("snapshot_date", desc=True)
        .limit(1)
        .execute()
    )
    latest_snapshot = None
    if snap_resp.data:
        latest_snapshot = snap_resp.data[0]["snapshot_date"]

    return {
        "total_raw": total_raw,
        "total_classified": total_classified,
        "last_scraped": last_scraped,
        "latest_snapshot": latest_snapshot,
    }


def render_pipeline_health(client):
    """Render pipeline health metrics in the sidebar."""
    stats = _fetch_health_stats(client)

    total_raw = stats["total_raw"]
    total_classified = stats["total_classified"]
    last_scraped = stats["last_scraped"]
    latest_snapshot = stats["latest_snapshot"]

    # Data freshness
    if last_scraped:
        scraped_dt = datetime.fromisoformat(last_scraped)
        if scraped_dt.tzinfo is None:
            scraped_dt = scraped_dt.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - scraped_dt
        days_ago = age.days

        if days_ago < 4:
            freshness = ":green[Fresh]"
        elif days_ago <= 7:
            freshness = ":orange[Stale]"
        else:
            freshness = ":red[Outdated]"

        st.caption(f"Last run: {scraped_dt:%Y-%m-%d %H:%M} UTC")
        st.caption(f"Freshness: {freshness} ({days_ago}d ago)")
    else:
        st.caption("Last run: unknown")

    # Counts
    st.caption(f"Raw listings: **{total_raw:,}**")
    st.caption(f"Classified: **{total_classified:,}**")

    # Coverage
    if total_raw > 0:
        coverage = total_classified / total_raw * 100
        st.caption(f"Coverage: **{coverage:.1f}%**")
    else:
        st.caption("Coverage: N/A")

    # Latest snapshot
    if latest_snapshot:
        st.caption(f"Latest snapshot: {latest_snapshot}")
    else:
        st.caption("Latest snapshot: none")
