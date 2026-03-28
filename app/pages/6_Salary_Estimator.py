import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from collections import Counter

from app.utils.supabase_client import get_client

st.header("Salary Estimator")

st.markdown(
    "Estimate salary ranges for AI & data roles in Singapore based on "
    "collected job posting data."
)

ROLE_CATEGORIES = [
    "Data Scientist",
    "ML Engineer",
    "Data Analyst",
    "AI Engineer",
    "Data Engineer",
    "Analytics Manager",
    "MLOps Engineer",
    "NLP Specialist",
    "Research Scientist",
    "BI Analyst",
    "AI Product Manager",
    "Other",
]

SENIORITY_LEVELS = [
    "Junior",
    "Mid",
    "Senior",
    "Lead",
    "Principal",
    "Director",
]

LAYOUT_DEFAULTS = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#fafafa"),
    margin=dict(l=20, r=20, t=40, b=20),
)

PRIMARY_COLOR = "#0ea5e9"
SECONDARY_COLOR = "#14b8a6"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def load_salary_data():
    """Load classified listings joined with raw_listings for salary info."""
    client = get_client()
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("classified_listings")
            .select(
                "*, raw_listings!listing_id("
                "title, company, salary_min, salary_max, "
                "source_url, posting_date, source"
                ")"
            )
            .range(offset, offset + page_size - 1)
            .execute()
        )
        all_rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return all_rows


raw_data = load_salary_data()

if not raw_data:
    st.info(
        "No classified jobs yet. Run the pipeline first:\n\n"
        "```bash\npython pipeline/run_pipeline.py\n```"
    )
    st.stop()


# ---------------------------------------------------------------------------
# Pre-process into a DataFrame
# ---------------------------------------------------------------------------


def flatten_rows(rows):
    """Flatten the nested Supabase join into a flat list of dicts."""
    flat = []
    for row in rows:
        raw = row.get("raw_listings") or {}
        salary_min = raw.get("salary_min")
        salary_max = raw.get("salary_max")
        # Only include rows that have at least one salary value
        if salary_min is None and salary_max is None:
            continue
        flat.append(
            {
                "role_category": row.get("role_category", "Other"),
                "seniority_level": row.get("seniority_level", "Mid"),
                "technical_skills": row.get("technical_skills") or [],
                "title": raw.get("title", ""),
                "company": raw.get("company", ""),
                "salary_min": float(salary_min) if salary_min is not None else None,
                "salary_max": float(salary_max) if salary_max is not None else None,
                "source_url": raw.get("source_url", ""),
                "posting_date": raw.get("posting_date", ""),
                "source": raw.get("source", ""),
            }
        )
    return pd.DataFrame(flat)


df_all = flatten_rows(raw_data)

if df_all.empty:
    st.info("No listings with salary data found. Salary estimates require job postings that include compensation information.")
    st.stop()


# ---------------------------------------------------------------------------
# Collect top skills across all listings for the multiselect widget
# ---------------------------------------------------------------------------

skill_counter: Counter = Counter()
for skills_list in df_all["technical_skills"]:
    for skill in skills_list:
        skill_counter[skill] += 1

top_skills_list = [s for s, _ in skill_counter.most_common(50)]


# ---------------------------------------------------------------------------
# Input widgets
# ---------------------------------------------------------------------------

st.subheader("Select Criteria")

col_role, col_seniority = st.columns(2)

with col_role:
    selected_role = st.selectbox("Role Category", ROLE_CATEGORIES)

with col_seniority:
    selected_seniority = st.selectbox("Seniority Level", SENIORITY_LEVELS)

selected_skills = st.multiselect(
    "Technical Skills (optional -- narrows results)",
    top_skills_list,
    default=[],
    help="Filter to listings that mention ALL selected skills.",
)


# ---------------------------------------------------------------------------
# Filter data
# ---------------------------------------------------------------------------

def filter_data(df, role, seniority, skills):
    """Return rows matching the given role, seniority, and skills."""
    mask = (df["role_category"] == role) & (df["seniority_level"] == seniority)
    filtered = df[mask].copy()

    if skills:
        # Keep rows where every selected skill appears in the listing's skills
        def has_all_skills(row_skills):
            return all(s in row_skills for s in skills)

        filtered = filtered[filtered["technical_skills"].apply(has_all_skills)]

    return filtered


df_filtered = filter_data(df_all, selected_role, selected_seniority, selected_skills)


# ---------------------------------------------------------------------------
# Compute statistics
# ---------------------------------------------------------------------------

def compute_salary_stats(df):
    """Return a dict of salary statistics from a DataFrame."""
    stats = {}
    for col_label, col_name in [("min", "salary_min"), ("max", "salary_max")]:
        series = df[col_name].dropna()
        if series.empty:
            stats[f"median_{col_label}"] = None
            stats[f"p25_{col_label}"] = None
            stats[f"p75_{col_label}"] = None
        else:
            stats[f"median_{col_label}"] = float(np.median(series))
            stats[f"p25_{col_label}"] = float(np.percentile(series, 25))
            stats[f"p75_{col_label}"] = float(np.percentile(series, 75))
    stats["count"] = len(df)
    return stats


# ---------------------------------------------------------------------------
# Display results
# ---------------------------------------------------------------------------

st.markdown("---")

if df_filtered.empty:
    st.info(
        f"No listings with salary data found for **{selected_role}** at "
        f"**{selected_seniority}** level"
        + (f" with skills {', '.join(selected_skills)}" if selected_skills else "")
        + ". Try broadening your criteria."
    )
else:
    stats = compute_salary_stats(df_filtered)

    st.subheader("Estimated Salary Range")

    mc1, mc2, mc3 = st.columns(3)

    # Format helper
    def fmt_salary(val):
        return f"${val:,.0f}" if val is not None else "N/A"

    with mc1:
        low = stats["p25_min"]
        st.metric(
            "25th Percentile (Low End)",
            fmt_salary(low),
            help="25th percentile of minimum salaries in matching listings",
        )

    with mc2:
        mid_min = stats["median_min"]
        mid_max = stats["median_max"]
        if mid_min is not None and mid_max is not None:
            range_str = f"{fmt_salary(mid_min)} - {fmt_salary(mid_max)}"
        elif mid_max is not None:
            range_str = f"Up to {fmt_salary(mid_max)}"
        elif mid_min is not None:
            range_str = f"From {fmt_salary(mid_min)}"
        else:
            range_str = "N/A"
        st.metric(
            "Median Range",
            range_str,
            help="Median of min and max salaries across matching listings",
        )

    with mc3:
        high = stats["p75_max"]
        st.metric(
            "75th Percentile (High End)",
            fmt_salary(high),
            help="75th percentile of maximum salaries in matching listings",
        )

    st.caption(f"Based on **{stats['count']}** matching listing(s) with salary data (SGD/month)")

    # ------------------------------------------------------------------
    # Box / range chart: selected role vs other roles at same seniority
    # ------------------------------------------------------------------

    st.subheader("Comparison Across Roles")

    df_same_seniority = df_all[df_all["seniority_level"] == selected_seniority].copy()

    # Build salary ranges per role (using salary_max for comparison)
    role_groups = df_same_seniority.groupby("role_category")["salary_max"].apply(list)

    # Only keep roles with at least 3 data points for a meaningful box
    role_groups = role_groups[role_groups.apply(lambda x: len([v for v in x if v is not None]) >= 3)]

    if role_groups.empty:
        st.info("Not enough data across roles to show a comparison chart.")
    else:
        fig = go.Figure()

        for role_name in sorted(role_groups.index):
            values = [v for v in role_groups[role_name] if v is not None]
            is_selected = role_name == selected_role
            fig.add_trace(
                go.Box(
                    y=values,
                    name=role_name,
                    marker_color=PRIMARY_COLOR if is_selected else SECONDARY_COLOR,
                    opacity=1.0 if is_selected else 0.5,
                    boxmean=True,
                )
            )

        fig.update_layout(
            **LAYOUT_DEFAULTS,
            title=f"Max Salary Distribution by Role ({selected_seniority} level, SGD/month)",
            yaxis_title="SGD / month",
            showlegend=False,
            height=450,
            xaxis_tickangle=-35,
        )

        st.plotly_chart(fig, width="stretch")

    # ------------------------------------------------------------------
    # Table of comparable listings
    # ------------------------------------------------------------------

    st.subheader("Comparable Listings")

    display_df = df_filtered[
        ["title", "company", "salary_min", "salary_max", "posting_date", "source"]
    ].copy()
    display_df.columns = ["Title", "Company", "Salary Min", "Salary Max", "Posted", "Source"]

    # Format salary columns
    for col in ["Salary Min", "Salary Max"]:
        display_df[col] = display_df[col].apply(
            lambda v: f"${v:,.0f}" if pd.notna(v) else "-"
        )

    display_df = display_df.sort_values("Posted", ascending=False).reset_index(drop=True)

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
    )

    if len(display_df) > 50:
        st.caption(f"Showing all {len(display_df)} matching listings.")


# ---------------------------------------------------------------------------
# Similar roles suggestion (shown even when primary filter has results)
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("Similar Roles for Reference")

# Pick roles that share the same seniority level and have salary data
similar_roles = [r for r in ROLE_CATEGORIES if r != selected_role]
similar_stats = []

for role in similar_roles:
    df_sim = filter_data(df_all, role, selected_seniority, [])
    if df_sim.empty:
        continue
    s = compute_salary_stats(df_sim)
    if s["median_max"] is not None:
        similar_stats.append(
            {
                "Role": role,
                "Seniority": selected_seniority,
                "Listings": s["count"],
                "Median Min": fmt_salary(s["median_min"]),
                "Median Max": fmt_salary(s["median_max"]),
                "P25 Min": fmt_salary(s["p25_min"]),
                "P75 Max": fmt_salary(s["p75_max"]),
            }
        )

if similar_stats:
    st.dataframe(
        pd.DataFrame(similar_stats),
        width="stretch",
        hide_index=True,
    )
else:
    st.info(f"No other roles found at the {selected_seniority} level with salary data.")


# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption(
    "**Disclaimer:** These salary estimates are approximate and derived from "
    "publicly available job postings collected by the SG AI Job Scout pipeline. "
    "Actual compensation may vary based on company, benefits, equity, bonuses, "
    "and individual negotiation. Salary figures are in SGD per month unless "
    "otherwise noted. This tool is for informational purposes only and should "
    "not be used as the sole basis for compensation decisions."
)
