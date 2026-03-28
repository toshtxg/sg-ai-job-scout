import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from collections import Counter, defaultdict

from app.utils.supabase_client import get_client
from app.components.charts import LAYOUT_DEFAULTS, ROLE_COLORS
from pipeline.ai_skills_analyzer import AI_SKILLS_TAXONOMY, analyze_all_listings

st.header("Market Pulse")
st.caption(
    "What's the overall AI job market landscape? Where are the opportunities?"
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_market_data():
    """Load classified listings joined with raw_listings for full analysis."""
    client = get_client()
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("classified_listings")
            .select(
                "*, raw_listings!listing_id("
                "title, company, description, salary_min, salary_max, "
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


raw_data = load_market_data()

if not raw_data:
    st.info(
        "No classified jobs yet. Run the pipeline first:\n\n"
        "```bash\npython pipeline/run_pipeline.py\n```"
    )
    st.stop()

# ---------------------------------------------------------------------------
# Build flat DataFrame
# ---------------------------------------------------------------------------
rows = []
for row in raw_data:
    raw = row.get("raw_listings") or {}
    company = (raw.get("company") or "Unknown").strip()
    if not company:
        company = "Unknown"
    rows.append(
        {
            "title": raw.get("title", "Untitled"),
            "company": company,
            "description": raw.get("description", ""),
            "salary_min": (
                float(raw["salary_min"])
                if raw.get("salary_min") is not None
                else None
            ),
            "salary_max": (
                float(raw["salary_max"])
                if raw.get("salary_max") is not None
                else None
            ),
            "technical_skills": row.get("technical_skills") or [],
            "role_category": row.get("role_category", "Other"),
            "seniority_level": row.get("seniority_level", "Mid"),
            "industry": row.get("industry", "Unknown"),
            "requires_ai_ml": row.get("requires_ai_ml", False),
            "remote_hybrid_onsite": row.get("remote_hybrid_onsite", "Unknown"),
        }
    )

df = pd.DataFrame(rows)

# Compute a usable salary column (midpoint where both exist, else whichever is available)
df["salary_mid"] = df.apply(
    lambda r: (
        (r["salary_min"] + r["salary_max"]) / 2
        if pd.notna(r["salary_min"]) and pd.notna(r["salary_max"])
        else r["salary_max"] if pd.notna(r["salary_max"])
        else r["salary_min"] if pd.notna(r["salary_min"])
        else None
    ),
    axis=1,
)

df_ai = df[df["requires_ai_ml"] == True]  # noqa: E712
df_non_ai = df[df["requires_ai_ml"] == False]  # noqa: E712


# =========================================================================
# Section 1: Market Overview Metrics
# =========================================================================
st.markdown("---")

total_listings = len(df)
ai_listings = len(df_ai)
ai_penetration = ai_listings / total_listings * 100 if total_listings else 0

ai_salary_vals = df_ai["salary_mid"].dropna()
non_ai_salary_vals = df_non_ai["salary_mid"].dropna()
median_ai_salary = ai_salary_vals.median() if not ai_salary_vals.empty else None
median_non_ai_salary = (
    non_ai_salary_vals.median() if not non_ai_salary_vals.empty else None
)

if median_ai_salary is not None and median_non_ai_salary and median_non_ai_salary > 0:
    salary_premium = (
        (median_ai_salary - median_non_ai_salary) / median_non_ai_salary * 100
    )
else:
    salary_premium = None

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Listings", f"{total_listings:,}")
col2.metric("AI/ML Listings", f"{ai_listings:,}")
col3.metric("AI Penetration", f"{ai_penetration:.1f}%")

if median_ai_salary is not None and median_non_ai_salary is not None:
    col4.metric(
        "AI Salary Premium",
        f"{salary_premium:+.1f}%" if salary_premium is not None else "N/A",
        help=(
            f"Median AI salary: ${median_ai_salary:,.0f} vs "
            f"non-AI: ${median_non_ai_salary:,.0f}"
        ),
    )
else:
    col4.metric("AI Salary Premium", "N/A", help="Insufficient salary data")

# Show median salaries as a sub-row
sub1, sub2, sub3, sub4 = st.columns(4)
sub1.caption(f"AI median: ${median_ai_salary:,.0f}/mo" if median_ai_salary else "")
sub2.caption(
    f"Non-AI median: ${median_non_ai_salary:,.0f}/mo" if median_non_ai_salary else ""
)


# =========================================================================
# Section 2: Skill Demand vs Rarity Index
# =========================================================================
st.markdown("---")
st.subheader("Skill Demand vs Hiring Breadth")
st.caption(
    "Each skill plotted by how many listings mention it (demand) vs how many "
    "distinct companies hire for it (breadth). Bubble size = average salary."
)

# Compute per-skill stats
skill_stats: dict[str, dict] = {}
for _, listing in df.iterrows():
    skills = listing["technical_skills"]
    company = listing["company"]
    salary = listing["salary_mid"]
    for skill in skills:
        if skill not in skill_stats:
            skill_stats[skill] = {
                "count": 0,
                "companies": set(),
                "salaries": [],
            }
        skill_stats[skill]["count"] += 1
        skill_stats[skill]["companies"].add(company)
        if pd.notna(salary):
            skill_stats[skill]["salaries"].append(salary)

# Filter to skills appearing in >= 5 listings, keep top 40 by demand
MIN_LISTINGS = 5
filtered_skills = {
    k: v for k, v in skill_stats.items() if v["count"] >= MIN_LISTINGS
}

if filtered_skills:
    scatter_data = []
    for skill, stats in filtered_skills.items():
        n_companies = len(stats["companies"])
        avg_salary = (
            sum(stats["salaries"]) / len(stats["salaries"])
            if stats["salaries"]
            else 0
        )
        scatter_data.append(
            {
                "skill": skill,
                "demand": stats["count"],
                "companies": n_companies,
                "avg_salary": avg_salary,
            }
        )

    sdf = pd.DataFrame(scatter_data)
    # Keep only top 40 skills by demand to reduce clutter
    sdf = sdf.nlargest(40, "demand").reset_index(drop=True)

    # Classify into quadrants
    median_demand = sdf["demand"].median()
    median_companies = sdf["companies"].median()

    def classify_quadrant(row):
        high_demand = row["demand"] > median_demand
        high_breadth = row["companies"] > median_companies
        if high_demand and high_breadth:
            return "Universal (table stakes)"
        elif high_demand and not high_breadth:
            return "Concentrated (industry-specific)"
        elif not high_demand and high_breadth:
            return "Emerging (growing across companies)"
        else:
            return "Niche (specialist)"

    sdf["quadrant"] = sdf.apply(classify_quadrant, axis=1)

    quadrant_colors = {
        "Universal (table stakes)": "#0ea5e9",
        "Concentrated (industry-specific)": "#f59e0b",
        "Emerging (growing across companies)": "#14b8a6",
        "Niche (specialist)": "#8b5cf6",
    }

    # Only label the top 15 skills to avoid overlap
    top_labeled = set(sdf.nlargest(15, "demand")["skill"])

    fig = go.Figure()
    for quadrant, color in quadrant_colors.items():
        mask = sdf["quadrant"] == quadrant
        subset = sdf[mask]
        if subset.empty:
            continue
        # Scale bubble size: use salary relative to max for visual clarity
        max_salary = sdf["avg_salary"].max() if sdf["avg_salary"].max() > 0 else 1
        sizes = (
            subset["avg_salary"].apply(
                lambda s: max(10, s / max_salary * 45) if s > 0 else 10
            )
        )
        # Only show text for top skills
        labels = subset["skill"].apply(lambda s: s if s in top_labeled else "")
        fig.add_trace(
            go.Scatter(
                x=subset["companies"],
                y=subset["demand"],
                mode="markers+text",
                name=quadrant,
                marker=dict(
                    size=sizes,
                    color=color,
                    opacity=0.8,
                    line=dict(width=1, color="#fafafa"),
                ),
                text=labels,
                textposition="top center",
                textfont=dict(size=10, color="#e2e8f0"),
                hovertext=subset["skill"],
                hovertemplate=(
                    "<b>%{hovertext}</b><br>"
                    "Listings: %{y}<br>"
                    "Companies: %{x}<br>"
                    "Avg Salary: $%{customdata:,.0f}/mo"
                    "<extra></extra>"
                ),
                customdata=subset["avg_salary"],
            )
        )

    # Draw quadrant lines
    fig.add_hline(
        y=median_demand,
        line_dash="dot",
        line_color="#475569",
        opacity=0.6,
    )
    fig.add_vline(
        x=median_companies,
        line_dash="dot",
        line_color="#475569",
        opacity=0.6,
    )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Skill Demand vs Hiring Breadth",
        xaxis_title="Number of Distinct Companies",
        yaxis_title="Number of Listings",
        height=550,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
        ),
    )
    st.plotly_chart(fig, width="stretch")

    # Show a summary table below
    with st.expander("Skill quadrant details"):
        display_sdf = sdf.sort_values("demand", ascending=False).copy()
        display_sdf["avg_salary"] = display_sdf["avg_salary"].apply(
            lambda v: f"${v:,.0f}" if v > 0 else "N/A"
        )
        display_sdf = display_sdf.rename(
            columns={
                "skill": "Skill",
                "demand": "Listings",
                "companies": "Companies",
                "avg_salary": "Avg Salary",
                "quadrant": "Quadrant",
            }
        )
        st.dataframe(display_sdf, width="stretch", hide_index=True)
else:
    st.info("Not enough skill data to generate the demand vs breadth chart.")


# =========================================================================
# Section 3: Industry AI Adoption
# =========================================================================
st.markdown("---")
st.subheader("Industry AI Adoption")
st.caption(
    "How deeply has AI hiring penetrated each industry? "
    "Compare total listings vs AI/ML listings by industry."
)

industry_stats = []
for industry, group in df.groupby("industry"):
    total_ind = len(group)
    ai_ind = group["requires_ai_ml"].sum()
    ai_pct = ai_ind / total_ind * 100 if total_ind else 0

    # Top 5 skills
    skill_counter = Counter()
    for skills_list in group["technical_skills"]:
        for s in skills_list:
            skill_counter[s] += 1
    top5_skills = ", ".join(s for s, _ in skill_counter.most_common(5))

    salary_vals = group["salary_mid"].dropna()
    avg_salary = salary_vals.mean() if not salary_vals.empty else None

    industry_stats.append(
        {
            "industry": industry,
            "total": total_ind,
            "ai_count": int(ai_ind),
            "ai_pct": ai_pct,
            "top_skills": top5_skills,
            "avg_salary": avg_salary,
        }
    )

ind_df = pd.DataFrame(industry_stats).sort_values("total", ascending=False)
# Keep only top 15 industries to avoid oversized chart
ind_df = ind_df.head(15).sort_values("total", ascending=True)

if not ind_df.empty:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=ind_df["industry"],
            x=ind_df["total"],
            name="Total Listings",
            orientation="h",
            marker_color="#0ea5e9",
            text=ind_df["total"],
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Bar(
            y=ind_df["industry"],
            x=ind_df["ai_count"],
            name="AI/ML Listings",
            orientation="h",
            marker_color="#14b8a6",
            text=ind_df["ai_count"],
            textposition="outside",
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Total vs AI/ML Listings by Industry",
        xaxis_title="Number of Listings",
        barmode="group",
        height=min(600, max(400, len(ind_df) * 40 + 80)),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
        ),
    )
    st.plotly_chart(fig, width="stretch")

    # Expandable table with full details
    with st.expander("Full industry details"):
        table_df = ind_df.sort_values("total", ascending=False).copy()
        table_df["avg_salary"] = table_df["avg_salary"].apply(
            lambda v: f"${v:,.0f}" if pd.notna(v) else "N/A"
        )
        table_df["ai_pct"] = table_df["ai_pct"].apply(lambda v: f"{v:.1f}%")
        table_df = table_df.rename(
            columns={
                "industry": "Industry",
                "total": "Total Listings",
                "ai_count": "AI/ML Listings",
                "ai_pct": "AI %",
                "top_skills": "Top 5 Skills",
                "avg_salary": "Avg Salary",
            }
        )
        st.dataframe(table_df, width="stretch", hide_index=True)


# =========================================================================
# Section 4: Seniority Distribution for AI Roles
# =========================================================================
st.markdown("---")
st.subheader("Seniority Distribution: AI vs Non-AI Roles")
st.caption(
    "How does the seniority mix differ between roles that require AI/ML "
    "and those that don't?"
)

SENIORITY_ORDER = ["Junior", "Mid", "Senior", "Lead", "Principal", "Director"]

ai_seniority = df_ai["seniority_level"].value_counts()
non_ai_seniority = df_non_ai["seniority_level"].value_counts()

# Ensure consistent ordering
all_seniority_levels = [
    s for s in SENIORITY_ORDER
    if s in ai_seniority.index or s in non_ai_seniority.index
]

ai_counts = [ai_seniority.get(s, 0) for s in all_seniority_levels]
non_ai_counts = [non_ai_seniority.get(s, 0) for s in all_seniority_levels]

col_left, col_right = st.columns(2)

with col_left:
    fig_ai_sen = go.Figure(
        go.Bar(
            x=all_seniority_levels,
            y=ai_counts,
            marker_color="#14b8a6",
            text=ai_counts,
            textposition="outside",
        )
    )
    fig_ai_sen.update_layout(
        **LAYOUT_DEFAULTS,
        title="AI/ML Roles",
        xaxis_title="Seniority",
        yaxis_title="Count",
        height=350,
    )
    st.plotly_chart(fig_ai_sen, width="stretch")

with col_right:
    fig_non_sen = go.Figure(
        go.Bar(
            x=all_seniority_levels,
            y=non_ai_counts,
            marker_color="#0ea5e9",
            text=non_ai_counts,
            textposition="outside",
        )
    )
    fig_non_sen.update_layout(
        **LAYOUT_DEFAULTS,
        title="Non-AI/ML Roles",
        xaxis_title="Seniority",
        yaxis_title="Count",
        height=350,
    )
    st.plotly_chart(fig_non_sen, width="stretch")

# Generate insight about skew
if ai_counts and non_ai_counts and sum(ai_counts) > 0 and sum(non_ai_counts) > 0:
    # Compute weighted average seniority index for AI vs non-AI
    seniority_index = {s: i for i, s in enumerate(all_seniority_levels)}
    ai_total = sum(ai_counts)
    non_ai_total = sum(non_ai_counts)
    ai_weighted = sum(
        seniority_index[s] * c for s, c in zip(all_seniority_levels, ai_counts)
    ) / ai_total
    non_ai_weighted = sum(
        seniority_index[s] * c for s, c in zip(all_seniority_levels, non_ai_counts)
    ) / non_ai_total

    if ai_weighted > non_ai_weighted + 0.3:
        skew = "senior"
    elif ai_weighted < non_ai_weighted - 0.3:
        skew = "junior"
    else:
        skew = "similarly distributed"

    if skew in ("senior", "junior"):
        st.info(
            f"AI roles skew more **{skew}** compared to non-AI roles "
            f"(avg seniority index: AI={ai_weighted:.2f}, non-AI={non_ai_weighted:.2f})."
        )
    else:
        st.info(
            f"AI and non-AI roles have a **{skew}** seniority mix "
            f"(avg seniority index: AI={ai_weighted:.2f}, non-AI={non_ai_weighted:.2f})."
        )


# =========================================================================
# Section 5: Work Mode Analysis
# =========================================================================
st.markdown("---")
st.subheader("Work Mode: AI vs Non-AI Roles")
st.caption("Remote, Hybrid, or Onsite -- how do AI roles compare?")

WORK_MODES = ["Remote", "Hybrid", "Onsite", "Unknown"]

ai_work = df_ai["remote_hybrid_onsite"].value_counts()
non_ai_work = df_non_ai["remote_hybrid_onsite"].value_counts()

# Filter out "Unknown" for cleaner charts if other modes exist
ai_work_filtered = {m: ai_work.get(m, 0) for m in WORK_MODES}
non_ai_work_filtered = {m: non_ai_work.get(m, 0) for m in WORK_MODES}

DONUT_COLORS = ["#14b8a6", "#0ea5e9", "#f59e0b", "#64748b"]

col_ai, col_non_ai = st.columns(2)

with col_ai:
    ai_labels = list(ai_work_filtered.keys())
    ai_values = list(ai_work_filtered.values())
    fig_ai_work = go.Figure(
        go.Pie(
            labels=ai_labels,
            values=ai_values,
            hole=0.5,
            marker=dict(colors=DONUT_COLORS),
            textinfo="label+percent",
            textfont=dict(size=12),
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        )
    )
    fig_ai_work.update_layout(
        **LAYOUT_DEFAULTS,
        title="AI/ML Roles",
        height=380,
        showlegend=False,
    )
    st.plotly_chart(fig_ai_work, width="stretch")

with col_non_ai:
    non_ai_labels = list(non_ai_work_filtered.keys())
    non_ai_values = list(non_ai_work_filtered.values())
    fig_non_work = go.Figure(
        go.Pie(
            labels=non_ai_labels,
            values=non_ai_values,
            hole=0.5,
            marker=dict(colors=DONUT_COLORS),
            textinfo="label+percent",
            textfont=dict(size=12),
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        )
    )
    fig_non_work.update_layout(
        **LAYOUT_DEFAULTS,
        title="Non-AI/ML Roles",
        height=380,
        showlegend=False,
    )
    st.plotly_chart(fig_non_work, width="stretch")

# Work mode comparison insight
ai_remote_pct = (
    ai_work_filtered.get("Remote", 0) / len(df_ai) * 100 if len(df_ai) > 0 else 0
)
non_ai_remote_pct = (
    non_ai_work_filtered.get("Remote", 0) / len(df_non_ai) * 100
    if len(df_non_ai) > 0
    else 0
)
ai_hybrid_pct = (
    ai_work_filtered.get("Hybrid", 0) / len(df_ai) * 100 if len(df_ai) > 0 else 0
)
non_ai_hybrid_pct = (
    non_ai_work_filtered.get("Hybrid", 0) / len(df_non_ai) * 100
    if len(df_non_ai) > 0
    else 0
)

insights = []
if ai_remote_pct > non_ai_remote_pct + 3:
    insights.append(
        f"AI roles offer more remote opportunities ({ai_remote_pct:.0f}% vs "
        f"{non_ai_remote_pct:.0f}% for non-AI)."
    )
elif non_ai_remote_pct > ai_remote_pct + 3:
    insights.append(
        f"Non-AI roles have more remote options ({non_ai_remote_pct:.0f}% vs "
        f"{ai_remote_pct:.0f}% for AI roles)."
    )

if ai_hybrid_pct > non_ai_hybrid_pct + 3:
    insights.append(
        f"AI roles lean more hybrid ({ai_hybrid_pct:.0f}% vs "
        f"{non_ai_hybrid_pct:.0f}% for non-AI)."
    )

if insights:
    for insight in insights:
        st.info(insight)
