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
        "**Methodology:** GPT-5.4-mini classifies each listing into role "
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
col1, col2, col3 = st.columns(3)
with col1:
    st.page_link("pages/1_Dashboard.py", label="\U0001f4ca Dashboard", width="stretch")
    st.page_link("pages/3_Role_Taxonomy.py", label="\U0001f9e0 Roles & Skills", width="stretch")
    st.page_link("pages/10_Learning_Roadmap.py", label="\U0001f5fa Learning Roadmap", width="stretch")
with col2:
    st.page_link("pages/2_Job_Explorer.py", label="\U0001f50e Job Explorer", width="stretch")
    st.page_link("pages/5_Company_Leaderboard.py", label="\U0001f3c6 Company Leaderboard", width="stretch")
    st.page_link("pages/8_AI_Skills_Deep_Dive.py", label="\U0001f916 AI Skills Deep Dive", width="stretch")
with col3:
    st.page_link("pages/6_Jobs_For_You.py", label="\U0001f3af Jobs for You", width="stretch")
    st.page_link("pages/11_Market_Pulse.py", label="\U0001f4a1 Market Pulse", width="stretch")
