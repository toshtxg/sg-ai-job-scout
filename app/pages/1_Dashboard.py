import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st

from app.utils.supabase_client import get_client
from app.components.charts import (
    create_listings_by_role_chart,
    create_salary_comparison_chart,
    create_volume_over_time_chart,
)
from app.components.metrics import render_metric_row

st.header("Dashboard")


@st.cache_data(ttl=3600)
def load_dashboard_data():
    client = get_client()
    latest_snapshot = (
        client.table("market_snapshots")
        .select("*")
        .order("snapshot_date", desc=True)
        .limit(1)
        .execute()
    )
    all_snapshots = (
        client.table("market_snapshots")
        .select("*")
        .order("snapshot_date")
        .execute()
    )
    return latest_snapshot.data, all_snapshots.data


snapshot_data, all_snapshots = load_dashboard_data()

if not snapshot_data:
    st.info(
        "No data yet. Run the pipeline first:\n\n"
        "```bash\npython pipeline/run_pipeline.py\n```"
    )
    st.stop()

latest = snapshot_data[0]

# Extract top role and top skill
listings_by_role = latest.get("listings_by_role") or {}
top_role = max(listings_by_role, key=listings_by_role.get) if listings_by_role else "N/A"

top_skills = latest.get("top_skills") or []
top_skill = top_skills[0]["skill"] if top_skills else "N/A"

# Metrics row
render_metric_row(
    total=latest.get("total_listings", 0),
    new_this_week=latest.get("new_listings_count", 0),
    top_role=top_role,
    top_skill=top_skill,
)

st.markdown("")

# Charts
col1, col2 = st.columns(2)
with col1:
    fig = create_listings_by_role_chart(listings_by_role)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    avg_salary = latest.get("avg_salary_by_role") or {}
    fig = create_salary_comparison_chart(avg_salary)
    st.plotly_chart(fig, use_container_width=True)

# Volume over time — full width
fig = create_volume_over_time_chart(all_snapshots)
st.plotly_chart(fig, use_container_width=True)

# Top skills detail
if top_skills:
    st.markdown("### Top Technical Skills")
    cols = st.columns(5)
    for i, s in enumerate(top_skills[:15]):
        with cols[i % 5]:
            st.metric(s["skill"], s["count"])

# Last updated
created_at = latest.get("created_at", "")
if created_at:
    st.caption(f"Last updated: {created_at[:19].replace('T', ' ')} UTC")
