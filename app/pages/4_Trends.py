import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from collections import Counter

from app.utils.supabase_client import get_client
from app.components.charts import (
    create_trends_by_role_chart,
    create_industry_pie_chart,
    create_volume_over_time_chart,
)

st.header("Trends & Insights")


@st.cache_data(ttl=3600)
def load_trends_data():
    client = get_client()
    snapshots = (
        client.table("market_snapshots").select("*").order("snapshot_date").execute()
    )
    classified = (
        client.table("classified_listings")
        .select("industry, role_category, requires_ai_ml")
        .execute()
    )
    return snapshots.data, classified.data


snapshots, classified = load_trends_data()

if not snapshots:
    st.info(
        "No snapshots yet. Run the pipeline first:\n\n"
        "```bash\npython pipeline/run_pipeline.py\n```"
    )
    st.stop()

# --- Listing Volume Over Time ---
st.subheader("Listing Volume Over Time")
fig = create_volume_over_time_chart(snapshots)
st.plotly_chart(fig, use_container_width=True)

# --- Listings by Role Over Time ---
st.subheader("Listings by Role Over Time")
if len(snapshots) >= 2:
    fig = create_trends_by_role_chart(snapshots)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(
        "Trends by role will appear after multiple pipeline runs. "
        "The pipeline runs automatically on Monday and Thursday."
    )

# --- Salary Trends ---
st.subheader("Salary Trends")
if len(snapshots) >= 2:
    import plotly.graph_objects as go

    all_roles: set[str] = set()
    for s in snapshots:
        salary_data = s.get("avg_salary_by_role") or {}
        all_roles.update(salary_data.keys())

    role_filter = st.multiselect(
        "Filter roles", sorted(all_roles), default=list(all_roles)[:5]
    )

    fig = go.Figure()
    colors = [
        "#0ea5e9", "#14b8a6", "#8b5cf6", "#f59e0b", "#ef4444",
        "#ec4899", "#06b6d4", "#84cc16",
    ]
    for i, role in enumerate(role_filter):
        dates = []
        maxs = []
        for s in snapshots:
            salary_data = s.get("avg_salary_by_role") or {}
            if role in salary_data:
                dates.append(s["snapshot_date"])
                maxs.append(salary_data[role].get("avg_max") or 0)
        if dates:
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=maxs,
                    name=role,
                    mode="lines+markers",
                    line=dict(color=colors[i % len(colors)]),
                )
            )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#fafafa"),
        title="Average Max Salary Over Time (SGD/month)",
        xaxis_title="Date",
        yaxis_title="SGD/month",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Salary trends will appear after multiple pipeline runs.")

# --- Industry Breakdown ---
st.subheader("Industry Breakdown of AI Hiring")
if classified:
    industry_counter = Counter(
        row.get("industry", "Unknown") for row in classified
    )
    fig = create_industry_pie_chart(dict(industry_counter.most_common(12)))
    st.plotly_chart(fig, use_container_width=True)

# --- Auto-generated Insights ---
st.subheader("Key Insights")

if len(snapshots) >= 2:
    latest = snapshots[-1]
    prev = snapshots[-2]

    insights = []

    # Total growth
    curr_total = latest.get("total_listings", 0)
    prev_total = prev.get("total_listings", 0)
    if prev_total > 0:
        growth = ((curr_total - prev_total) / prev_total) * 100
        direction = "increased" if growth > 0 else "decreased"
        insights.append(
            f"Total listings have **{direction} by {abs(growth):.1f}%** "
            f"since the previous snapshot ({prev_total:,} -> {curr_total:,})."
        )

    # Fastest growing role
    curr_roles = latest.get("listings_by_role") or {}
    prev_roles = prev.get("listings_by_role") or {}
    role_growth = {}
    for role, count in curr_roles.items():
        prev_count = prev_roles.get(role, 0)
        if prev_count > 0:
            role_growth[role] = ((count - prev_count) / prev_count) * 100

    if role_growth:
        fastest = max(role_growth, key=role_growth.get)
        insights.append(
            f"**{fastest}** is the fastest growing role category "
            f"(+{role_growth[fastest]:.0f}%)."
        )

    # Top skill
    top_skills = latest.get("top_skills") or []
    if top_skills:
        insights.append(
            f"**{top_skills[0]['skill']}** remains the most in-demand skill "
            f"with {top_skills[0]['count']} listings."
        )

    # AI/ML percentage
    if classified:
        ai_ml_count = sum(1 for r in classified if r.get("requires_ai_ml"))
        ai_pct = (ai_ml_count / len(classified)) * 100
        insights.append(
            f"**{ai_pct:.0f}%** of data/analytics jobs explicitly require "
            f"AI or ML skills."
        )

    if insights:
        for insight in insights:
            st.markdown(f"- {insight}")
    else:
        st.info("Not enough data to generate insights yet.")

elif len(snapshots) == 1:
    latest = snapshots[0]
    st.markdown(
        f"- **{latest.get('total_listings', 0):,}** total listings tracked\n"
        f"- **{latest.get('new_listings_count', 0):,}** new this week\n"
        f"- More insights will be available after additional pipeline runs"
    )
