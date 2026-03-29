import streamlit as st

st.set_page_config(layout="wide")

import pandas as pd

from app.utils.supabase_client import get_client
from app.components.filters import render_job_filters, apply_filters

st.header("Job Explorer")


@st.cache_data(ttl=3600)
def load_jobs():
    client = get_client()
    all_jobs = []
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
        all_jobs.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return all_jobs


jobs = load_jobs()

if not jobs:
    st.info(
        "No job data available yet. Data is refreshed automatically on "
        "Mondays and Thursdays — check back soon!"
    )
    st.stop()

# Sidebar filters
with st.sidebar:
    filters = render_job_filters()

filtered = apply_filters(jobs, filters)

st.markdown(f"**{len(filtered)}** jobs found (of {len(jobs)} total)")

# Export filtered results
export_rows = []
for r in filtered:
    raw = r.get("raw_listings") or {}
    export_rows.append(
        {
            "Title": raw.get("title", ""),
            "Company": raw.get("company", ""),
            "Role": r.get("role_category", ""),
            "Seniority": r.get("seniority_level", ""),
            "Salary Min": raw.get("salary_min"),
            "Salary Max": raw.get("salary_max"),
            "Skills": ", ".join(r.get("technical_skills") or []),
            "Industry": r.get("industry", ""),
            "Work Mode": r.get("remote_hybrid_onsite", ""),
            "Posted Date": raw.get("posting_date", ""),
            "Source URL": raw.get("source_url", ""),
        }
    )
export_df = pd.DataFrame(export_rows)
st.download_button(
    label="Download CSV",
    data=export_df.to_csv(index=False),
    file_name="filtered_jobs.csv",
    mime="text/csv",
)

# Sort options
sort_col = st.selectbox(
    "Sort by",
    ["Posting Date (newest)", "Salary (highest)", "Role", "Company"],
)


def _sort_key(row):
    raw = row.get("raw_listings") or {}
    if sort_col == "Posting Date (newest)":
        return raw.get("posting_date") or "1900-01-01"
    elif sort_col == "Salary (highest)":
        return float(raw.get("salary_max") or 0)
    elif sort_col == "Role":
        return row.get("role_category", "")
    else:
        return raw.get("company") or ""


reverse = sort_col in ["Posting Date (newest)", "Salary (highest)"]
filtered.sort(key=_sort_key, reverse=reverse)

# Display
for row in filtered[:100]:  # Show first 100
    raw = row.get("raw_listings") or {}
    title = raw.get("title", "Untitled")
    company = raw.get("company", "Unknown")
    role = row.get("role_category", "")
    seniority = row.get("seniority_level", "")
    salary_min = raw.get("salary_min")
    salary_max = raw.get("salary_max")
    posting_date = raw.get("posting_date", "")
    source_url = raw.get("source_url", "")

    salary_str = ""
    if salary_min is not None and salary_max is not None:
        salary_str = f"${float(salary_min):,.0f} - ${float(salary_max):,.0f}/mo"
    elif salary_max is not None:
        salary_str = f"Up to ${float(salary_max):,.0f}/mo"

    work_mode = row.get("remote_hybrid_onsite", "Unknown")
    wm_icons = {"Remote": "🏠", "Hybrid": "🔄", "Onsite": "🏢"}
    wm_tag = wm_icons.get(work_mode, "")

    header = f"**{title}** — {company}"
    if salary_str:
        header += f"  |  {salary_str}"
    if wm_tag:
        header += f"  {wm_tag}"

    with st.expander(header):
        # Top row: key info + apply button
        meta_html = (
            f'<div style="display:flex;gap:16px;align-items:center;'
            f'flex-wrap:wrap;margin-bottom:8px;">'
            f'<span style="background:#0f172a;border:1px solid #334155;'
            f'border-radius:8px;padding:4px 12px;font-size:0.85rem;">'
            f'{role}</span>'
            f'<span style="background:#0f172a;border:1px solid #334155;'
            f'border-radius:8px;padding:4px 12px;font-size:0.85rem;">'
            f'{seniority}</span>'
            f'<span style="background:#0f172a;border:1px solid #334155;'
            f'border-radius:8px;padding:4px 12px;font-size:0.85rem;">'
            f'{wm_tag} {work_mode}</span>'
            f'<span style="color:#94a3b8;font-size:0.85rem;">'
            f'{row.get("industry", "")}</span>'
            f'<span style="color:#64748b;font-size:0.8rem;margin-left:auto;">'
            f'Posted {posting_date}</span>'
            f'</div>'
        )
        st.markdown(meta_html, unsafe_allow_html=True)

        if source_url:
            st.link_button("Apply →", source_url)

        # Skills tags
        tech_skills = row.get("technical_skills") or []
        if tech_skills:
            skills_html = " ".join(
                f'<span style="background:#1e293b;border:1px solid #334155;'
                f'border-radius:12px;padding:2px 10px;margin:2px;'
                f'display:inline-block;font-size:0.85rem;">{s}</span>'
                for s in tech_skills
            )
            st.markdown(skills_html, unsafe_allow_html=True)

        # Description preview
        desc = raw.get("description", "")
        if desc:
            st.markdown(
                f'<div style="color:#cbd5e1;font-size:0.9rem;line-height:1.5;'
                f'margin-top:8px;white-space:pre-wrap;">'
                f'{desc[:600]}{"..." if len(desc) > 600 else ""}</div>',
                unsafe_allow_html=True,
            )

if len(filtered) > 100:
    st.info(f"Showing first 100 of {len(filtered)} results. Use filters to narrow down.")
