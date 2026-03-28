import streamlit as st

st.set_page_config(
    page_title="SG AI Job Market Scout",
    page_icon="\U0001f50d",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 12px 16px;
    }
    [data-testid="stMetricLabel"] { font-size: 0.85rem; }
    [data-testid="stMetricValue"] { font-size: 1.4rem; }
    .stExpander { border: 1px solid #334155; border-radius: 8px; }
</style>""",
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.markdown("## \U0001f50d SG AI Job Market Scout")
    st.caption("Understanding Singapore's AI job market through data")
    st.markdown("---")

    st.markdown("### About")
    st.markdown(
        "Built to understand Singapore's AI job market. Uses LLMs to classify "
        "unstructured job descriptions into structured, queryable data."
    )
    st.markdown("**Sources:** MyCareersFuture.gov.sg")
    st.markdown(
        "**Methodology:** GPT-4o-mini classifies each listing into role "
        "category, seniority, skills, and industry."
    )
    st.markdown(
        "**Schedule:** Pipeline runs Monday & Thursday at 2 AM UTC via "
        "GitHub Actions."
    )
    st.markdown("---")
    st.caption("Created by Tosh")

# Home page
st.markdown("# SG AI Job Market Scout")
st.markdown(
    "Explore Singapore's AI, data science, and analytics job market "
    "with structured insights derived from live job listings."
)

st.markdown("### Navigate")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.page_link("pages/1_Dashboard.py", label="\U0001f4ca Dashboard", use_container_width=True)
with col2:
    st.page_link("pages/2_Job_Explorer.py", label="\U0001f50e Job Explorer", use_container_width=True)
with col3:
    st.page_link("pages/3_Role_Taxonomy.py", label="\U0001f9e0 Role Taxonomy", use_container_width=True)
with col4:
    st.page_link("pages/4_Trends.py", label="\U0001f4c8 Trends", use_container_width=True)

st.markdown("---")
st.markdown(
    "#### How it works\n"
    "1. **Scrape** — Job listings are collected from MyCareersFuture.gov.sg\n"
    "2. **Classify** — GPT-4o-mini extracts role, seniority, skills, and industry\n"
    "3. **Aggregate** — Market snapshots capture trends over time\n"
    "4. **Explore** — This dashboard lets you filter, compare, and discover"
)
