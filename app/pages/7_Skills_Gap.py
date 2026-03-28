import streamlit as st
import plotly.graph_objects as go
from collections import Counter

from app.utils.supabase_client import get_client
from app.components.filters import render_role_scope

st.header("Skills Gap Analyzer")

st.markdown(
    "Enter the skills you have and discover which roles you qualify for, "
    "which skills you're missing, and what to learn next to maximise your "
    "job prospects."
)

selected_roles = render_role_scope(key="skills_gap")

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
def load_listings():
    """Load all classified listings with role, seniority, and technical skills."""
    client = get_client()
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("classified_listings")
            .select("role_category, seniority_level, technical_skills")
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
        "No classified jobs yet. Run the pipeline first:\n\n"
        "```bash\npython pipeline/run_pipeline.py\n```"
    )
    st.stop()


# ---------------------------------------------------------------------------
# Build skill universe and role-skill mappings
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def build_skill_data(_listings):
    """
    Return:
    - all_skills_sorted: list of all unique skills sorted by frequency (desc)
    - role_listings: dict mapping role -> list of skill sets (one per listing)
    - role_skill_freq: dict mapping role -> Counter of skill frequencies
    """
    skill_counter = Counter()
    role_listings = {}
    role_skill_freq = {}

    for row in _listings:
        role = row.get("role_category") or "Other"
        skills = row.get("technical_skills") or []
        skills_set = set(s.strip() for s in skills if s and s.strip())

        # Global skill frequency
        for s in skills_set:
            skill_counter[s] += 1

        # Per-role listings
        role_listings.setdefault(role, []).append(skills_set)

        # Per-role skill frequency
        if role not in role_skill_freq:
            role_skill_freq[role] = Counter()
        for s in skills_set:
            role_skill_freq[role][s] += 1

    all_skills_sorted = [s for s, _ in skill_counter.most_common()]
    return all_skills_sorted, role_listings, role_skill_freq


all_skills_sorted, role_listings, role_skill_freq = build_skill_data(listings)


# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------

st.subheader("Your Skills")

col_multi, col_free = st.columns([3, 2])

with col_multi:
    selected_skills = st.multiselect(
        "Select skills from the database",
        all_skills_sorted,
        default=[],
        help="Skills that appear in job listings we have collected.",
    )

with col_free:
    free_text = st.text_input(
        "Additional skills (comma-separated)",
        placeholder="e.g. Rust, dbt, Airflow",
        help="Add skills not in the list above.",
    )

# Merge user skills into a single normalised set
user_skills = set(s.strip() for s in selected_skills if s.strip())
if free_text:
    for s in free_text.split(","):
        s = s.strip()
        if s:
            user_skills.add(s)

if not user_skills:
    st.info("Add at least one skill above to see your skills-gap analysis.")
    st.stop()

st.markdown(
    "**Your skills:** "
    + ", ".join(f"`{s}`" for s in sorted(user_skills))
)

st.markdown("---")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def listing_match(listing_skills: set, user_skills: set) -> bool:
    """Return True if user has >= 50% of the listing's required skills."""
    if not listing_skills:
        return False
    # Case-insensitive matching
    listing_lower = {s.lower() for s in listing_skills}
    user_lower = {s.lower() for s in user_skills}
    overlap = listing_lower & user_lower
    return len(overlap) / len(listing_lower) >= 0.5


def skill_overlap_count(listing_skills: set, user_skills: set) -> int:
    """Count overlapping skills (case-insensitive)."""
    listing_lower = {s.lower() for s in listing_skills}
    user_lower = {s.lower() for s in user_skills}
    return len(listing_lower & user_lower)


# ---------------------------------------------------------------------------
# 1. Role Match Scores
# ---------------------------------------------------------------------------

st.subheader("Role Match Scores")

role_scores = {}
for role, role_skill_sets in role_listings.items():
    total = len(role_skill_sets)
    matched = sum(1 for ls in role_skill_sets if listing_match(ls, user_skills))
    role_scores[role] = {
        "match_pct": matched / total if total > 0 else 0.0,
        "matched": matched,
        "total": total,
    }

# Sort by match percentage descending
sorted_roles = sorted(role_scores.items(), key=lambda x: x[1]["match_pct"], reverse=True)

for role, info in sorted_roles:
    pct = info["match_pct"]
    label = f"**{role}** -- {info['matched']}/{info['total']} listings ({pct:.0%})"
    st.progress(pct, text=label)

st.markdown("---")


# ---------------------------------------------------------------------------
# 2. Skills Gap by Role
# ---------------------------------------------------------------------------

st.subheader("Skills Gap by Role")

role_names = [r for r, _ in sorted_roles]
selected_role = st.selectbox(
    "Select a role to analyze",
    role_names,
    help="Choose a role to see which of your skills match and which are missing.",
)

if selected_role:
    freq = role_skill_freq.get(selected_role, Counter())
    total_listings_for_role = len(role_listings.get(selected_role, []))

    # Determine which skills the user has / is missing (case-insensitive)
    user_lower_map = {s.lower(): s for s in user_skills}

    skills_have = []
    skills_missing = []
    for skill, count in freq.most_common():
        if skill.lower() in user_lower_map:
            skills_have.append((skill, count))
        else:
            skills_missing.append((skill, count))

    col_have, col_miss = st.columns(2)

    with col_have:
        st.markdown(f"#### Skills You Have ({len(skills_have)})")
        if skills_have:
            for skill, count in skills_have:
                pct_of_role = count / total_listings_for_role if total_listings_for_role else 0
                st.markdown(
                    f'<span style="background:#065f46;border:1px solid #10b981;'
                    f'border-radius:12px;padding:4px 12px;margin:2px;'
                    f'display:inline-block;font-size:0.85rem;">'
                    f"{skill} ({count} listings, {pct_of_role:.0%})</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("None of your skills match this role's requirements.")

    with col_miss:
        st.markdown(f"#### Skills You're Missing ({len(skills_missing)})")
        if skills_missing:
            for skill, count in skills_missing[:20]:
                pct_of_role = count / total_listings_for_role if total_listings_for_role else 0
                st.markdown(
                    f'<span style="background:#7f1d1d;border:1px solid #ef4444;'
                    f'border-radius:12px;padding:4px 12px;margin:2px;'
                    f'display:inline-block;font-size:0.85rem;">'
                    f"{skill} ({count} listings, {pct_of_role:.0%})</span>",
                    unsafe_allow_html=True,
                )
            if len(skills_missing) > 20:
                st.caption(f"...and {len(skills_missing) - 20} more.")
        else:
            st.caption("You have all the skills commonly listed for this role!")

    # Visual gap chart
    st.markdown("")
    st.markdown("##### Skills Coverage")

    # Top 15 skills for this role, ordered by frequency
    top_role_skills = freq.most_common(15)
    if top_role_skills:
        skill_names = [s for s, _ in top_role_skills]
        skill_counts = [c for _, c in top_role_skills]
        user_has = [
            1 if s.lower() in user_lower_map else 0 for s in skill_names
        ]

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=skill_counts,
                y=skill_names,
                orientation="h",
                marker_color=[
                    SECONDARY_COLOR if h else "#ef4444" for h in user_has
                ],
                text=[
                    f"{'HAVE' if h else 'MISSING'} ({c} listings)"
                    for h, c in zip(user_has, skill_counts)
                ],
                textposition="auto",
                textfont=dict(size=11),
            )
        )

        fig.update_layout(
            **LAYOUT_DEFAULTS,
            title=f"Top Skills for {selected_role} (green = you have, red = missing)",
            xaxis_title="Number of listings requiring this skill",
            yaxis=dict(autorange="reversed"),
            height=max(350, len(skill_names) * 32),
            showlegend=False,
        )

        st.plotly_chart(fig, width="stretch")


st.markdown("---")


# ---------------------------------------------------------------------------
# 3. Personalized Recommendations -- Top 5 skills to learn next
# ---------------------------------------------------------------------------

st.subheader("Top Skills to Learn Next")
st.markdown(
    "These are the skills that would unlock the most **additional** job matches "
    "if you learned them. Each listing requires you to have at least 50% of its "
    "skills to count as a match."
)

# Identify all listings where user currently does NOT match but is close
# For each candidate skill, simulate adding it and count new matches gained.

# Collect all skills that appear in listings but the user doesn't have
user_lower = {s.lower() for s in user_skills}
candidate_skills = set()
for role_skill_sets in role_listings.values():
    for ls in role_skill_sets:
        for s in ls:
            if s.lower() not in user_lower:
                candidate_skills.add(s)

# For performance, limit candidates to those appearing in at least 3 listings
global_skill_counter = Counter()
for role_skill_sets in role_listings.values():
    for ls in role_skill_sets:
        for s in ls:
            global_skill_counter[s] += 1

candidate_skills = {
    s for s in candidate_skills if global_skill_counter[s] >= 3
}

# Pre-compute current matches per listing (flat list across all roles)
all_listing_skills = []
for role_skill_sets in role_listings.values():
    for ls in role_skill_sets:
        all_listing_skills.append(ls)

current_matches = set()
for idx, ls in enumerate(all_listing_skills):
    if listing_match(ls, user_skills):
        current_matches.add(idx)

# Calculate gain for each candidate skill
skill_gain = {}
for candidate in candidate_skills:
    augmented = user_skills | {candidate}
    new_matches = 0
    for idx, ls in enumerate(all_listing_skills):
        if idx in current_matches:
            continue
        if listing_match(ls, augmented):
            new_matches += 1
    if new_matches > 0:
        skill_gain[candidate] = new_matches

# Sort by gain descending
top_recommendations = sorted(skill_gain.items(), key=lambda x: x[1], reverse=True)[:5]

if not top_recommendations:
    st.info(
        "No additional skills would significantly increase your job matches. "
        "You may already be well-covered, or try adding more of your current "
        "skills above for a more accurate analysis."
    )
else:
    # Display as a horizontal bar chart
    rec_skills = [s for s, _ in top_recommendations]
    rec_gains = [g for _, g in top_recommendations]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=rec_gains,
            y=rec_skills,
            orientation="h",
            marker_color=PRIMARY_COLOR,
            text=[f"+{g} jobs" for g in rec_gains],
            textposition="outside",
            textfont=dict(size=12),
        )
    )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Top 5 Skills to Learn (by additional job matches unlocked)",
        xaxis_title="Additional listings you'd qualify for",
        yaxis=dict(autorange="reversed"),
        height=300,
        showlegend=False,
    )

    st.plotly_chart(fig, width="stretch")

    # Also show as a table for clarity
    for rank, (skill, gain) in enumerate(top_recommendations, 1):
        appearances = global_skill_counter[skill]
        st.markdown(
            f"**{rank}. {skill}** -- +{gain} new job matches "
            f"(appears in {appearances} total listings)"
        )


# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption(
    "**Note:** Match percentages are based on technical skills extracted from "
    "job postings and may not capture all requirements (e.g. soft skills, "
    "years of experience, domain knowledge). Use this analysis as a guide, "
    "not an absolute measure of qualification."
)
