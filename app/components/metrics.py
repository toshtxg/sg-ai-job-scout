import streamlit as st


def render_metric_row(
    total: int, new_this_week: int, top_role: str, top_skill: str
):
    """Render a row of 4 metric cards."""
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Listings", f"{total:,}")
    col2.metric("New This Week", f"{new_this_week:,}")
    col3.metric("Most In-Demand Role", top_role)
    col4.metric("Top Skill", top_skill)
