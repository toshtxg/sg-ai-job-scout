import streamlit as st
import pandas as pd
import numpy as np
from collections import Counter

import plotly.graph_objects as go

from app.utils.supabase_client import get_client
from app.components.charts import LAYOUT_DEFAULTS, ROLE_COLORS

st.header("Skills Salary Premium")
st.markdown("Which specific skills are associated with higher salaries?")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def load_salary_skills_data():
    """Load classified listings joined with raw_listings for salary + skills."""
    client = get_client()
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("classified_listings")
            .select(
                "*, raw_listings!listing_id("
                "title, company, salary_min, salary_max, posting_date"
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


raw_data = load_salary_skills_data()

if not raw_data:
    st.info(
        "No classified jobs yet. Run the pipeline first:\n\n"
        "```bash\npython pipeline/run_pipeline.py\n```"
    )
    st.stop()


# ---------------------------------------------------------------------------
# Pre-process into a DataFrame (salary rows only)
# ---------------------------------------------------------------------------

rows = []
for row in raw_data:
    raw = row.get("raw_listings") or {}
    salary_max = raw.get("salary_max")
    if salary_max is None:
        continue
    rows.append(
        {
            "role_category": row.get("role_category", "Other"),
            "seniority_level": row.get("seniority_level", "Mid"),
            "technical_skills": row.get("technical_skills") or [],
            "title": raw.get("title", ""),
            "company": raw.get("company", ""),
            "salary_min": float(raw["salary_min"]) if raw.get("salary_min") is not None else None,
            "salary_max": float(salary_max),
            "posting_date": raw.get("posting_date", ""),
        }
    )

df = pd.DataFrame(rows)

if df.empty:
    st.info("No listings with salary data found. This page requires job postings that include compensation information.")
    st.stop()


# ---------------------------------------------------------------------------
# Section 1: Skill Salary Premium Table
# ---------------------------------------------------------------------------

st.subheader("Skill Salary Premium Table")

# Count skill occurrences across salary-bearing listings
skill_counter: Counter = Counter()
for skills_list in df["technical_skills"]:
    for skill in skills_list:
        skill_counter[skill] += 1

# Overall baseline: median salary_max across ALL salary-bearing listings
baseline_median = float(np.median(df["salary_max"]))

MIN_LISTINGS = 5

premium_rows = []
for skill, count in skill_counter.items():
    if count < MIN_LISTINGS:
        continue

    # Listings WITH this skill
    mask_with = df["technical_skills"].apply(lambda s: skill in s)
    median_with = float(np.median(df.loc[mask_with, "salary_max"]))

    # Listings WITHOUT this skill
    median_without = float(np.median(df.loc[~mask_with, "salary_max"]))

    if median_without == 0:
        continue

    premium_pct = (median_with - median_without) / median_without * 100

    premium_rows.append(
        {
            "Skill": skill,
            "Median Salary (SGD/mo)": median_with,
            "Listings Count": count,
            "Salary Premium (%)": round(premium_pct, 1),
        }
    )

premium_df = pd.DataFrame(premium_rows).sort_values(
    "Salary Premium (%)", ascending=False
).reset_index(drop=True)

if premium_df.empty:
    st.info("Not enough skills with sufficient listing counts to compute premiums.")
else:
    # Style the premium column: green positive, red negative
    def _color_premium(val):
        if val > 0:
            return "color: #22c55e"
        elif val < 0:
            return "color: #ef4444"
        return ""

    styled = (
        premium_df.style
        .format(
            {
                "Median Salary (SGD/mo)": "${:,.0f}",
                "Salary Premium (%)": "{:+.1f}%",
                "Listings Count": "{:,}",
            }
        )
        .map(_color_premium, subset=["Salary Premium (%)"])
    )

    st.dataframe(
        styled,
        width="stretch",
        hide_index=True,
        height=min(len(premium_df) * 35 + 40, 600),
    )

    st.caption(
        f"Baseline median salary (all listings): **${baseline_median:,.0f}/mo**. "
        f"Only skills appearing in {MIN_LISTINGS}+ listings are shown."
    )


# ---------------------------------------------------------------------------
# Section 2: Top 20 Salary Premium Skills (Bar Chart)
# ---------------------------------------------------------------------------

st.subheader("Top 20 Salary Premium Skills")

if not premium_df.empty:
    top20 = premium_df.head(20).copy()

    fig_premium = go.Figure(
        go.Bar(
            x=top20["Salary Premium (%)"],
            y=top20["Skill"],
            orientation="h",
            marker=dict(
                color=top20["Salary Premium (%)"],
                colorscale=[[0, "#065f46"], [0.5, "#10b981"], [1, "#34d399"]],
                showscale=False,
            ),
            text=top20["Salary Premium (%)"].apply(lambda v: f"{v:+.1f}%"),
            textposition="outside",
        )
    )
    fig_premium.update_layout(
        **LAYOUT_DEFAULTS,
        title="Top 20 Skills by Salary Premium (%)",
        xaxis_title="Salary Premium (%)",
        height=max(400, len(top20) * 30),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig_premium, width="stretch")
else:
    st.info("Not enough data to display premium chart.")


# ---------------------------------------------------------------------------
# Section 3: Skills by Salary Tier
# ---------------------------------------------------------------------------

st.subheader("Skills by Salary Tier")
st.markdown(
    "Which skills dominate at each salary level? "
    "This helps distinguish entry-level from premium skills."
)

SALARY_TIERS = [
    ("< $4K", 0, 4000),
    ("$4K - $6K", 4000, 6000),
    ("$6K - $8K", 6000, 8000),
    ("$8K - $10K", 8000, 10000),
    ("$10K - $15K", 10000, 15000),
    ("$15K+", 15000, float("inf")),
]

tier_cols = st.columns(3)

for idx, (tier_label, low, high) in enumerate(SALARY_TIERS):
    tier_mask = (df["salary_max"] >= low) & (df["salary_max"] < high)
    tier_df = df[tier_mask]

    col = tier_cols[idx % 3]
    with col:
        with st.expander(f"{tier_label} ({len(tier_df)} listings)", expanded=idx < 3):
            if tier_df.empty:
                st.caption("No listings in this tier.")
            else:
                tier_skill_counter: Counter = Counter()
                for skills_list in tier_df["technical_skills"]:
                    for skill in skills_list:
                        tier_skill_counter[skill] += 1

                top10 = tier_skill_counter.most_common(10)
                if top10:
                    tier_skill_df = pd.DataFrame(top10, columns=["Skill", "Count"])
                    st.dataframe(
                        tier_skill_df,
                        width="stretch",
                        hide_index=True,
                        height=min(len(tier_skill_df) * 35 + 40, 400),
                    )
                else:
                    st.caption("No skills data in this tier.")


# ---------------------------------------------------------------------------
# Section 4: Role x Skill Salary Matrix
# ---------------------------------------------------------------------------

st.subheader("Role x Skill Salary Matrix")
st.markdown(
    "Select a role category to see which skills are associated with "
    "the highest median salaries within that role."
)

role_categories = sorted(df["role_category"].unique().tolist())
selected_role = st.selectbox("Select Role Category", role_categories, index=0)

if selected_role:
    role_df = df[df["role_category"] == selected_role]

    if len(role_df) < 3:
        st.info(f"Not enough salary data for **{selected_role}** (need at least 3 listings).")
    else:
        # Count skills within this role
        role_skill_counter: Counter = Counter()
        for skills_list in role_df["technical_skills"]:
            for skill in skills_list:
                role_skill_counter[skill] += 1

        # Take top 15 skills by frequency (must appear in >= 3 listings for this role)
        top_role_skills = [
            s for s, c in role_skill_counter.most_common(30) if c >= 3
        ][:15]

        if not top_role_skills:
            st.info(f"Not enough skill data for **{selected_role}** to compute per-skill salaries.")
        else:
            skill_medians = []
            for skill in top_role_skills:
                mask = role_df["technical_skills"].apply(lambda s: skill in s)
                vals = role_df.loc[mask, "salary_max"].dropna()
                if not vals.empty:
                    skill_medians.append(
                        {
                            "Skill": skill,
                            "Median Salary": float(np.median(vals)),
                            "Listings": len(vals),
                        }
                    )

            if skill_medians:
                skill_medians_df = pd.DataFrame(skill_medians).sort_values(
                    "Median Salary", ascending=True
                )

                fig_role = go.Figure(
                    go.Bar(
                        x=skill_medians_df["Median Salary"],
                        y=skill_medians_df["Skill"],
                        orientation="h",
                        marker_color=ROLE_COLORS[
                            role_categories.index(selected_role) % len(ROLE_COLORS)
                        ],
                        text=skill_medians_df["Median Salary"].apply(
                            lambda v: f"${v:,.0f}"
                        ),
                        textposition="outside",
                        hovertemplate=(
                            "Skill: %{y}<br>"
                            "Median Salary: $%{x:,.0f}/mo<br>"
                            "<extra></extra>"
                        ),
                    )
                )
                fig_role.update_layout(
                    **LAYOUT_DEFAULTS,
                    title=f"Median Salary by Skill — {selected_role} (SGD/mo)",
                    xaxis_title="Median Salary (SGD/mo)",
                    height=max(400, len(skill_medians_df) * 30),
                    yaxis=dict(autorange="reversed"),
                )
                st.plotly_chart(fig_role, width="stretch")
            else:
                st.info(f"No skill-salary data available for **{selected_role}**.")


# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption(
    "**Note:** Salary premiums are computed by comparing median maximum salaries "
    "of listings that mention a skill vs. those that do not. Correlation does not "
    "imply causation — skills associated with higher salaries may reflect seniority "
    "or domain complexity rather than the skill itself."
)
