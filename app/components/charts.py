import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

ROLE_COLORS = [
    "#0ea5e9", "#14b8a6", "#8b5cf6", "#f59e0b", "#ef4444",
    "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
    "#d946ef", "#64748b",
]

LAYOUT_DEFAULTS = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#fafafa"),
    margin=dict(l=20, r=20, t=40, b=20),
)


def create_listings_by_role_chart(listings_by_role: dict) -> go.Figure:
    """Vertical bar chart of listings count by role category."""
    if not listings_by_role:
        return _empty_figure("No role data available")

    roles = list(listings_by_role.keys())
    counts = list(listings_by_role.values())

    fig = go.Figure(
        go.Bar(
            x=roles,
            y=counts,
            marker_color=ROLE_COLORS[: len(roles)],
            text=counts,
            textposition="outside",
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Listings by Role",
        xaxis_title="",
        yaxis_title="Count",
        xaxis_tickangle=-35,
        height=400,
    )
    return fig


def create_salary_comparison_chart(avg_salary_by_role: dict) -> go.Figure:
    """Horizontal bar chart comparing salary ranges by role."""
    if not avg_salary_by_role:
        return _empty_figure("No salary data available")

    roles = []
    avg_mins = []
    avg_maxs = []
    for role, data in sorted(
        avg_salary_by_role.items(), key=lambda x: x[1].get("avg_max") or 0
    ):
        if data.get("avg_min") is not None or data.get("avg_max") is not None:
            roles.append(role)
            avg_mins.append(data.get("avg_min") or 0)
            avg_maxs.append(data.get("avg_max") or 0)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=roles,
            x=avg_mins,
            name="Avg Min",
            orientation="h",
            marker_color="#0ea5e9",
            text=[f"${v:,.0f}" for v in avg_mins],
            textposition="inside",
        )
    )
    fig.add_trace(
        go.Bar(
            y=roles,
            x=[m - n for m, n in zip(avg_maxs, avg_mins)],
            name="Avg Max (range)",
            orientation="h",
            marker_color="#14b8a6",
            text=[f"${v:,.0f}" for v in avg_maxs],
            textposition="inside",
            base=avg_mins,
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Salary Range by Role (SGD/month)",
        barmode="overlay",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=max(300, len(roles) * 40 + 100),
    )
    return fig


def create_volume_over_time_chart(snapshots: list[dict]) -> go.Figure:
    """Line chart of total listing volume over time."""
    if not snapshots or len(snapshots) < 1:
        return _empty_figure("Need multiple pipeline runs to show trends")

    dates = [s["snapshot_date"] for s in snapshots]
    totals = [s.get("total_listings", 0) for s in snapshots]
    new_counts = [s.get("new_listings_count", 0) for s in snapshots]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=totals,
            name="Total Listings",
            mode="lines+markers",
            line=dict(color="#0ea5e9", width=3),
            marker=dict(size=8),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=new_counts,
            name="New This Week",
            mode="lines+markers",
            line=dict(color="#14b8a6", width=2, dash="dash"),
            marker=dict(size=6),
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Listing Volume Over Time",
        xaxis_title="Date",
        yaxis_title="Count",
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def create_skills_heatmap(df: pd.DataFrame) -> go.Figure:
    """Heatmap of skills vs roles."""
    if df.empty:
        return _empty_figure("No skills data available")

    fig = go.Figure(
        go.Heatmap(
            z=df.values,
            x=df.columns.tolist(),
            y=df.index.tolist(),
            colorscale=[[0, "#0e1117"], [0.5, "#0ea5e9"], [1, "#14b8a6"]],
            text=df.values,
            texttemplate="%{text}",
            hovertemplate="Role: %{y}<br>Skill: %{x}<br>Count: %{z}<extra></extra>",
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Skills by Role",
        height=max(400, len(df) * 35 + 100),
        xaxis_tickangle=-45,
    )
    return fig


def create_sunburst_chart(df: pd.DataFrame) -> go.Figure:
    """Sunburst chart of role → seniority distribution."""
    if df.empty:
        return _empty_figure("No data available")

    fig = px.sunburst(
        df,
        path=["role_category", "seniority_level"],
        values="count",
        color_discrete_sequence=ROLE_COLORS,
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Role → Seniority Distribution",
        height=500,
    )
    return fig


def create_trends_by_role_chart(snapshots: list[dict]) -> go.Figure:
    """Line chart of listing counts by role over time."""
    if not snapshots or len(snapshots) < 2:
        return _empty_figure(
            "Need at least 2 pipeline runs to show trends"
        )

    fig = go.Figure()
    # Collect all roles across snapshots
    all_roles: set[str] = set()
    for s in snapshots:
        by_role = s.get("listings_by_role") or {}
        all_roles.update(by_role.keys())

    for i, role in enumerate(sorted(all_roles)):
        dates = []
        counts = []
        for s in snapshots:
            by_role = s.get("listings_by_role") or {}
            if role in by_role:
                dates.append(s["snapshot_date"])
                counts.append(by_role[role])
        if dates:
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=counts,
                    name=role,
                    mode="lines+markers",
                    line=dict(color=ROLE_COLORS[i % len(ROLE_COLORS)]),
                )
            )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Listings by Role Over Time",
        xaxis_title="Date",
        yaxis_title="Count",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def create_industry_pie_chart(industry_counts: dict) -> go.Figure:
    """Pie chart of industry breakdown."""
    if not industry_counts:
        return _empty_figure("No industry data available")

    fig = go.Figure(
        go.Pie(
            labels=list(industry_counts.keys()),
            values=list(industry_counts.values()),
            marker=dict(colors=ROLE_COLORS),
            hole=0.4,
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Industry Breakdown",
        height=400,
    )
    return fig


def _empty_figure(message: str) -> go.Figure:
    """Return a placeholder figure with a centered message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color="#94a3b8"),
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        height=300,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
