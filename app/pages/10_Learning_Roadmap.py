import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from collections import Counter, defaultdict

from app.utils.supabase_client import get_client
from app.components.charts import LAYOUT_DEFAULTS, ROLE_COLORS
from pipeline.ai_skills_analyzer import AI_SKILLS_TAXONOMY, SKILL_TIERS

st.header("Learning Roadmap")
st.caption(
    "What should you learn and in what order to maximize your career in AI/data? "
    "Explore skill progressions by seniority, co-occurrence networks, role-based "
    "learning paths, and the AI skills ladder."
)

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


listings = load_listings()

if not listings:
    st.info(
        "No classified data yet. Run the pipeline first:\n\n"
        "```bash\npython pipeline/run_pipeline.py\n```"
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
# Section 2: Skill Co-occurrence Network
# ═══════════════════════════════════════════════════════════════════════════

st.subheader("2. Skill Co-occurrence Network")
st.markdown(
    "Select a skill you already know. We show which other skills employers "
    "commonly pair it with, creating a natural learning path."
)

top50_skills = [s for s, _ in global_skill_counter.most_common(50)]

if top50_skills:
    selected_skill = st.selectbox(
        "Select a starting skill",
        top50_skills,
        help="Pick a skill you already know to discover what to learn next.",
    )

    if selected_skill:
        # First-degree co-occurrences
        co_counter = Counter()
        listings_with_skill = 0
        for skill_set in all_skill_sets:
            if selected_skill in skill_set:
                listings_with_skill += 1
                for s in skill_set:
                    if s != selected_skill:
                        co_counter[s] += 1

        if co_counter and listings_with_skill > 0:
            top15_co = co_counter.most_common(15)
            co_skills = [s for s, _ in top15_co]
            co_pcts = [c / listings_with_skill * 100 for _, c in top15_co]

            st.markdown(
                f"**If you know {selected_skill}**, employers also look for "
                f"these skills (based on {listings_with_skill:,} listings):"
            )

            fig = go.Figure(
                go.Bar(
                    x=co_pcts[::-1],
                    y=co_skills[::-1],
                    orientation="h",
                    marker_color="#0ea5e9",
                    text=[f"{p:.0f}%" for p in co_pcts[::-1]],
                    textposition="outside",
                )
            )
            fig.update_layout(
                **LAYOUT_DEFAULTS,
                title=f"Top Skills Co-occurring with {selected_skill}",
                xaxis_title="% of listings that also require this skill",
                height=max(350, len(co_skills) * 30),
                showlegend=False,
            )
            st.plotly_chart(fig, width="stretch")

            # Second-degree connections
            bridge_skill = co_skills[0]  # #1 co-occurring skill
            already_shown = set(co_skills) | {selected_skill}

            co2_counter = Counter()
            listings_with_bridge = 0
            for skill_set in all_skill_sets:
                if bridge_skill in skill_set:
                    listings_with_bridge += 1
                    for s in skill_set:
                        if s not in already_shown:
                            co2_counter[s] += 1

            if co2_counter and listings_with_bridge > 0:
                st.markdown(
                    f"**Second-degree connections** via **{bridge_skill}** "
                    f"(top co-occurrence of {selected_skill}):"
                )
                top10_co2 = co2_counter.most_common(10)
                co2_skills = [s for s, _ in top10_co2]
                co2_pcts = [c / listings_with_bridge * 100 for _, c in top10_co2]

                fig2 = go.Figure(
                    go.Bar(
                        x=co2_pcts[::-1],
                        y=co2_skills[::-1],
                        orientation="h",
                        marker_color="#14b8a6",
                        text=[f"{p:.0f}%" for p in co2_pcts[::-1]],
                        textposition="outside",
                    )
                )
                fig2.update_layout(
                    **LAYOUT_DEFAULTS,
                    title=f"Second-Degree Skills (via {bridge_skill})",
                    xaxis_title="% of listings that also require this skill",
                    height=max(300, len(co2_skills) * 30),
                    showlegend=False,
                )
                st.plotly_chart(fig2, width="stretch")

                st.markdown(
                    f"**Suggested learning path:** {selected_skill} "
                    f"-> {bridge_skill} -> {co2_skills[0]}"
                )
        else:
            st.info(f"No co-occurring skills found for {selected_skill}.")
else:
    st.info("Not enough skill data to build co-occurrence analysis.")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════
# Section 3: Role-Based Learning Paths
# ═══════════════════════════════════════════════════════════════════════════

st.subheader("3. Role-Based Learning Paths")
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
                fig.update_layout(
                    **LAYOUT_DEFAULTS,
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

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════
# Section 4: AI Skills Ladder
# ═══════════════════════════════════════════════════════════════════════════

st.subheader("4. AI Skills Ladder")
st.markdown(
    "A tiered progression through AI skills, from foundational literacy to "
    "specialist capabilities. Each tier shows current market demand based on "
    "actual job listings."
)

# Compute AI category demand from listings (keyword matching)
@st.cache_data(ttl=3600)
def compute_ai_demand(_listings):
    """Count how many listings mention each AI skill category."""
    category_counts = Counter()
    total = 0
    for row in _listings:
        skills = row.get("technical_skills") or []
        combined = " ".join(s.lower() for s in skills)
        if not combined:
            continue
        total += 1
        for category, keywords in AI_SKILLS_TAXONOMY.items():
            for kw in keywords:
                if kw in combined:
                    category_counts[category] += 1
                    break  # Count each category once per listing
    return category_counts, total


ai_category_counts, ai_total = compute_ai_demand(listings)

TIER_COLORS = {
    "Tier 1: Foundational": "#0ea5e9",
    "Tier 2: Professional": "#14b8a6",
    "Tier 3: Specialist": "#8b5cf6",
}

TIER_RECOMMENDATIONS = {
    "Tier 1: Foundational": "Start here -- build AI literacy and learn to use AI tools effectively in your daily work.",
    "Tier 2: Professional": "Build this -- develop the technical depth that makes you a competitive AI/data professional.",
    "Tier 3: Specialist": "Specialize in this -- pick one or two areas to become the go-to expert in your organization.",
}

for tier_name, tier_categories in SKILL_TIERS.items():
    color = TIER_COLORS.get(tier_name, "#64748b")
    rec = TIER_RECOMMENDATIONS.get(tier_name, "")

    with st.expander(f"**{tier_name}**", expanded=True):
        st.markdown(f"*{rec}*")

        if ai_total > 0:
            cat_names = []
            cat_counts = []
            cat_pcts = []
            for cat in tier_categories:
                count = ai_category_counts.get(cat, 0)
                pct = count / ai_total * 100
                cat_names.append(cat)
                cat_counts.append(count)
                cat_pcts.append(pct)

            fig = go.Figure(
                go.Bar(
                    x=cat_counts,
                    y=cat_names,
                    orientation="h",
                    marker_color=color,
                    text=[f"{c:,} ({p:.1f}%)" for c, p in zip(cat_counts, cat_pcts)],
                    textposition="outside",
                )
            )
            fig.update_layout(
                **LAYOUT_DEFAULTS,
                margin=dict(l=20, r=80, t=10, b=20),
                height=max(180, len(cat_names) * 45),
                xaxis_title="Number of listings mentioning this category",
                showlegend=False,
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.caption("No skill data available to compute demand.")

# Summary recommendation
st.markdown("### Recommended Progression")
st.markdown(
    "1. **Start here** -- Master AI tools and prompt engineering "
    "(Tier 1). These are rapidly becoming table stakes.\n"
    "2. **Build this** -- Develop core ML/DL skills, learn to work with LLMs, "
    "and understand MLOps (Tier 2). This is where career value compounds.\n"
    "3. **Specialize in this** -- Choose a Tier 3 niche (Agents, Safety, "
    "Computer Vision, or Governance) based on your interests and role trajectory."
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
