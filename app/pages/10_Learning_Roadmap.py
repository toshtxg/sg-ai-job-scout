import streamlit as st

st.set_page_config(layout="wide")

import plotly.graph_objects as go
from collections import Counter, defaultdict

from app.utils.supabase_client import get_client
from app.components.charts import LAYOUT_DEFAULTS
from app.components.filters import render_role_scope

st.header("Learning Roadmap")
st.caption(
    "What should you learn and in what order? "
    "See how skill requirements change with seniority, and get a personalised "
    "learning path for your target role."
)

selected_roles = render_role_scope(key="learning_roadmap")

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

SENIORITY_ORDER = ["Junior", "Mid", "Senior", "Lead", "Principal", "Director"]


@st.cache_data(ttl=3600)
def load_listings():
    """Load classified listings with role, seniority, skills, and AI flag."""
    client = get_client()
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("classified_listings")
            .select("role_category, seniority_level, technical_skills, requires_ai_ml")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        all_rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return all_rows


_all_listings = load_listings()
listings = [r for r in _all_listings if not selected_roles or r.get("role_category") in selected_roles]

if not listings:
    st.info(
        "No data available yet. Data is refreshed automatically on "
        "Mondays and Thursdays — check back soon!"
    )
    st.stop()

# ---------------------------------------------------------------------------
# Pre-compute shared data structures
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def build_roadmap_data(_listings):
    """Build data structures used across all sections."""
    # Per-seniority skill counts and totals
    seniority_skill_counts = {}
    seniority_totals = Counter()

    # Per-role+seniority skill counts
    role_seniority_skill_counts = {}
    role_seniority_totals = defaultdict(Counter)

    # Global skill counter for top-N selection
    global_skill_counter = Counter()

    # Listing-level skill sets for co-occurrence
    all_skill_sets = []

    for row in _listings:
        seniority = row.get("seniority_level") or "Mid"
        role = row.get("role_category") or "Other"
        skills = row.get("technical_skills") or []
        skills_set = set(s.strip() for s in skills if s and s.strip())

        if not skills_set:
            continue

        all_skill_sets.append(skills_set)

        # Seniority-level aggregation
        seniority_totals[seniority] += 1
        if seniority not in seniority_skill_counts:
            seniority_skill_counts[seniority] = Counter()
        for s in skills_set:
            seniority_skill_counts[seniority][s] += 1
            global_skill_counter[s] += 1

        # Role + seniority aggregation
        key = (role, seniority)
        role_seniority_totals[role][seniority] += 1
        if key not in role_seniority_skill_counts:
            role_seniority_skill_counts[key] = Counter()
        for s in skills_set:
            role_seniority_skill_counts[key][s] += 1

    return (
        seniority_skill_counts,
        dict(seniority_totals),
        role_seniority_skill_counts,
        dict(role_seniority_totals),
        global_skill_counter,
        all_skill_sets,
    )


(
    seniority_skill_counts,
    seniority_totals,
    role_seniority_skill_counts,
    role_seniority_totals,
    global_skill_counter,
    all_skill_sets,
) = build_roadmap_data(listings)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════
# Section 1: Skill Progression by Seniority
# ═══════════════════════════════════════════════════════════════════════════

st.subheader("1. Skill Progression by Seniority")
st.markdown(
    "Which skills become more or less important as you advance? "
    "Cell values show the percentage of listings at each seniority level "
    "that mention the skill."
)

# Collect top 15 skills per seniority, then take the union
active_levels = [lvl for lvl in SENIORITY_ORDER if lvl in seniority_skill_counts]

if active_levels:
    union_skills = set()
    for lvl in active_levels:
        top15 = [s for s, _ in seniority_skill_counts[lvl].most_common(15)]
        union_skills.update(top15)

    # Sort skills by overall frequency descending for a stable row order
    sorted_skills = sorted(
        union_skills, key=lambda s: global_skill_counter.get(s, 0), reverse=True
    )

    # Build percentage matrix: rows = skills, columns = seniority levels
    z_values = []
    text_values = []
    for skill in sorted_skills:
        row_z = []
        row_t = []
        for lvl in active_levels:
            total = seniority_totals.get(lvl, 0)
            count = seniority_skill_counts.get(lvl, Counter()).get(skill, 0)
            pct = (count / total * 100) if total > 0 else 0
            row_z.append(round(pct, 1))
            row_t.append(f"{pct:.0f}%")
        z_values.append(row_z)
        text_values.append(row_t)

    fig = go.Figure(
        go.Heatmap(
            z=z_values,
            x=active_levels,
            y=sorted_skills,
            colorscale=[[0, "#0e1117"], [0.5, "#0ea5e9"], [1, "#14b8a6"]],
            text=text_values,
            texttemplate="%{text}",
            hovertemplate=(
                "Skill: %{y}<br>Seniority: %{x}<br>"
                "Frequency: %{text}<extra></extra>"
            ),
            colorbar=dict(title="% of listings"),
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Skill Frequency (%) by Seniority Level",
        height=max(500, len(sorted_skills) * 28 + 100),
        xaxis=dict(side="top"),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, width="stretch")
else:
    st.info("No seniority data available.")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════
# Section 2: Role-Based Learning Paths
# ═══════════════════════════════════════════════════════════════════════════

st.subheader("2. Role-Based Learning Paths")
st.markdown(
    "Select your target role and seniority to see which skills are "
    "foundational, which differentiate you, and which are specialist niches."
)

all_roles = sorted(set(row.get("role_category", "Other") for row in listings))

col_role, col_current, col_target = st.columns(3)

with col_role:
    target_role = st.selectbox("Target role", all_roles)

available_seniorities = [
    lvl for lvl in SENIORITY_ORDER
    if role_seniority_totals.get(target_role, {}).get(lvl, 0) > 0
]

with col_current:
    current_seniority = st.selectbox(
        "Current seniority",
        available_seniorities if available_seniorities else SENIORITY_ORDER,
        index=0,
    )

with col_target:
    # Default target to one level above current if possible
    target_options = available_seniorities if available_seniorities else SENIORITY_ORDER
    default_idx = 0
    if current_seniority in SENIORITY_ORDER:
        current_idx = SENIORITY_ORDER.index(current_seniority)
        for i, opt in enumerate(target_options):
            if opt in SENIORITY_ORDER and SENIORITY_ORDER.index(opt) > current_idx:
                default_idx = i
                break
    target_seniority = st.selectbox(
        "Target seniority",
        target_options,
        index=min(default_idx, len(target_options) - 1),
    )

key = (target_role, target_seniority)
skill_counts = role_seniority_skill_counts.get(key, Counter())
total_at_target = role_seniority_totals.get(target_role, {}).get(target_seniority, 0)

if skill_counts and total_at_target > 0:
    foundation = []
    differentiator = []
    specialist = []

    for skill, count in skill_counts.most_common():
        pct = count / total_at_target * 100
        if pct > 50:
            foundation.append((skill, pct, count))
        elif pct >= 20:
            differentiator.append((skill, pct, count))
        elif pct >= 5:
            specialist.append((skill, pct, count))

    col_f, col_d, col_s = st.columns(3)

    def _render_skill_tier(column, title, color, emoji_label, skills_list):
        with column:
            st.markdown(f"#### {title}")
            st.caption(emoji_label)
            if skills_list:
                names = [s for s, _, _ in skills_list]
                pcts = [p for _, p, _ in skills_list]

                fig = go.Figure(
                    go.Bar(
                        x=pcts[::-1],
                        y=names[::-1],
                        orientation="h",
                        marker_color=color,
                        text=[f"{p:.0f}%" for p in pcts[::-1]],
                        textposition="outside",
                    )
                )
                tier_layout = {
                    k: v for k, v in LAYOUT_DEFAULTS.items() if k != "margin"
                }
                fig.update_layout(
                    **tier_layout,
                    margin=dict(l=10, r=40, t=10, b=10),
                    height=max(200, len(names) * 28),
                    xaxis_title="% of listings",
                    showlegend=False,
                )
                st.plotly_chart(fig, width="stretch")
            else:
                st.caption("No skills in this tier for the selected combination.")

    _render_skill_tier(
        col_f, "Foundation", "#14b8a6",
        f"Appear in >50% of {target_role} {target_seniority} listings",
        foundation,
    )
    _render_skill_tier(
        col_d, "Differentiator", "#f59e0b",
        "Appear in 20-50% -- valuable but not universal",
        differentiator,
    )
    _render_skill_tier(
        col_s, "Specialist", "#8b5cf6",
        "Appear in 5-20% -- niche but can set you apart",
        specialist,
    )

    st.markdown(
        f"Based on **{total_at_target}** listings for "
        f"**{target_role}** at **{target_seniority}** level."
    )
else:
    st.info(
        f"No data for {target_role} at {target_seniority} level. "
        "Try a different combination."
    )


# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption(
    "**Note:** This roadmap is derived from patterns in Singapore job listings "
    "and reflects employer demand, not an exhaustive curriculum. Skill frequency "
    "percentages are based on the subset of listings that mention each seniority "
    "level or role category."
)
