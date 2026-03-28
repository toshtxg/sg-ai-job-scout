import streamlit as st
from datetime import date, timedelta

ROLE_CATEGORIES = [
    "Data Scientist", "ML Engineer", "Data Analyst", "AI Engineer",
    "Data Engineer", "Analytics Manager", "MLOps Engineer", "NLP Specialist",
    "Research Scientist", "BI Analyst", "AI Product Manager", "Other",
]

SENIORITY_LEVELS = ["Junior", "Mid", "Senior", "Lead", "Principal", "Director"]


def render_job_filters() -> dict:
    """Render sidebar filters and return selected filter values."""
    st.markdown("### Filters")

    filters = {}
    filters["role_category"] = st.multiselect("Role Category", ROLE_CATEGORIES)
    filters["seniority"] = st.multiselect("Seniority Level", SENIORITY_LEVELS)
    filters["salary_range"] = st.slider(
        "Salary Range (SGD/month)", 0, 30_000, (0, 30_000), step=500
    )
    filters["skills_search"] = st.text_input(
        "Skills Search", placeholder="e.g. Python, TensorFlow"
    )
    filters["source"] = st.multiselect(
        "Source", ["mycareersfuture"]
    )
    filters["requires_ai_ml"] = st.checkbox("Requires AI/ML only", value=False)

    return filters


def apply_filters(data: list[dict], filters: dict) -> list[dict]:
    """Apply filter dict to a list of classified listing rows."""
    filtered = data

    if filters.get("role_category"):
        filtered = [
            r for r in filtered if r.get("role_category") in filters["role_category"]
        ]

    if filters.get("seniority"):
        filtered = [
            r
            for r in filtered
            if r.get("seniority_level") in filters["seniority"]
        ]

    sal_min, sal_max = filters.get("salary_range", (0, 30_000))
    if sal_min > 0 or sal_max < 30_000:
        def _in_salary_range(row):
            raw = row.get("raw_listings") or {}
            s_min = raw.get("salary_min")
            s_max = raw.get("salary_max")
            if s_min is None and s_max is None:
                return True  # Include jobs without salary info
            if s_max is not None and float(s_max) < sal_min:
                return False
            if s_min is not None and float(s_min) > sal_max:
                return False
            return True

        filtered = [r for r in filtered if _in_salary_range(r)]

    skills_search = filters.get("skills_search", "").strip()
    if skills_search:
        search_terms = [s.strip().lower() for s in skills_search.split(",")]
        filtered = [
            r
            for r in filtered
            if any(
                term in skill.lower()
                for term in search_terms
                for skill in (r.get("technical_skills") or [])
            )
        ]

    if filters.get("source"):
        filtered = [
            r
            for r in filtered
            if (r.get("raw_listings") or {}).get("source") in filters["source"]
        ]

    if filters.get("requires_ai_ml"):
        filtered = [r for r in filtered if r.get("requires_ai_ml")]

    return filtered
