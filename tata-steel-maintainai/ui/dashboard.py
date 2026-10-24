"""
TAB 1 — Executive Overview Dashboard for TATA STEEL MAINTAINAI.
Visualizes high-level industrial asset health, fleet risk distribution,
unplanned downtime financial exposure, and executive KPI summaries.
"""

import gradio as gr
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Tuple, Dict, Any

from database.db import fetch_df
from src.prediction_engine import generate_fleet_predictions
from src.business_impact import compute_business_impact_analysis
from src.reporting import generate_executive_pdf_report


def build_kpi_html(fleet_df: pd.DataFrame, impact: Dict[str, Any]) -> str:
    """Generate HTML snippet for modern executive KPI cards."""
    total_assets = len(fleet_df)
    crit_count = len(fleet_df[fleet_df["risk_category"] == "Critical Risk"])
    high_count = len(fleet_df[fleet_df["risk_category"] == "High Risk"])
    med_count = len(fleet_df[fleet_df["risk_category"] == "Medium Risk"])
    healthy_count = len(fleet_df[fleet_df["risk_category"] == "Low Risk"])
    anom_count = len(fleet_df[fleet_df["is_anomaly"] == "YES"])

    total_exposure = impact["modeled_scenarios"]["scenario_a_run_to_failure_cost"]
    net_savings = impact["modeled_scenarios"]["net_potential_savings"]
    roi = impact["modeled_scenarios"]["modeled_roi_pct"]

    return f"""
    <div class="kpi-container">
        <div class="kpi-card" style="border-top: 3px solid #0284c7;">
            <div class="kpi-title">Fleet Monitored</div>
            <div class="kpi-value">{total_assets}</div>
            <div class="kpi-subtext">100% telemetry online</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #10b981;">
            <div class="kpi-title">Healthy Assets</div>
            <div class="kpi-value" style="color: #10b981;">{healthy_count}</div>
            <div class="kpi-subtext">Operating within nominal specs</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #f97316;">
            <div class="kpi-title">High / Critical Risk</div>
            <div class="kpi-value" style="color: #f97316;">{crit_count + high_count}</div>
            <div class="kpi-subtext">{crit_count} Critical, {high_count} High</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #f59e0b;">
            <div class="kpi-title">Active Anomalies</div>
            <div class="kpi-value" style="color: #f59e0b;">{anom_count}</div>
            <div class="kpi-subtext">Isolation Forest sensor drift</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #ef4444;">
            <div class="kpi-title">Failure Exposure</div>
            <div class="kpi-value" style="color: #fca5a5;">${total_exposure:,.0f}</div>
            <div class="kpi-subtext">Run-to-failure risk (72h)</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #38bdf8;">
            <div class="kpi-title">Potential Net Savings</div>
            <div class="kpi-value" style="color: #38bdf8;">${net_savings:,.0f}</div>
            <div class="kpi-subtext">{roi:.1f}% Modeled PM ROI</div>
        </div>
    </div>
    """


def create_risk_distribution_donut(fleet_df: pd.DataFrame) -> go.Figure:
    """Create interactive donut chart of machine risk categories."""
    risk_counts = fleet_df["risk_category"].value_counts()
    categories = ["Low Risk", "Medium Risk", "High Risk", "Critical Risk"]
    color_map = {
        "Low Risk": "#10b981",
        "Medium Risk": "#f59e0b",
        "High Risk": "#f97316",
        "Critical Risk": "#ef4444",
    }
    
    values = [risk_counts.get(c, 0) for c in categories]
    colors = [color_map[c] for c in categories]

    fig = go.Figure(data=[go.Pie(
        labels=categories,
        values=values,
        hole=0.6,
        marker=dict(colors=colors, line=dict(color="#0f172a", width=2)),
        textinfo="label+value",
        hoverinfo="label+percent+value",
    )])

    fig.update_layout(
        title="Fleet Risk Distribution (72h Forecast Horizon)",
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=40, b=30),
        height=320,
    )
    return fig


def create_area_risk_barchart(fleet_df: pd.DataFrame) -> go.Figure:
    """Create bar chart of composite risk score by production area."""
    area_summary = fleet_df.groupby("production_area")["composite_risk_score"].mean().reset_index()
    area_summary = area_summary.sort_values(by="composite_risk_score", ascending=True)

    fig = go.Figure(go.Bar(
        x=area_summary["composite_risk_score"],
        y=area_summary["production_area"],
        orientation="h",
        marker=dict(
            color=area_summary["composite_risk_score"],
            colorscale=[[0.0, "#10b981"], [0.5, "#f59e0b"], [1.0, "#ef4444"]],
            showscale=False,
        ),
        text=[f"{v:.1f}" for v in area_summary["composite_risk_score"]],
        textposition="outside",
    ))

    fig.update_layout(
        title="Mean Operational Risk Score by Production Area",
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        xaxis=dict(title="Average Composite Risk Score (0-100)", range=[0, 100], gridcolor="#334155"),
        yaxis=dict(title="", gridcolor="#334155"),
        margin=dict(l=20, r=20, t=40, b=30),
        height=320,
    )
    return fig


def create_cost_exposure_comparison(impact: Dict[str, Any]) -> go.Figure:
    """Bar chart comparing Run-to-Failure vs Planned Preventive Maintenance costs."""
    scenarios = impact["modeled_scenarios"]
    sc_a = scenarios["scenario_a_run_to_failure_cost"]
    sc_b = scenarios["scenario_b_preventive_cost"]
    savings = scenarios["net_potential_savings"]

    categories = ["Scenario A: Run-to-Failure Exposure", "Scenario B: Planned PM Cost", "Net Modeled Savings"]
    vals = [sc_a, sc_b, savings]
    bar_colors = ["#ef4444", "#0284c7", "#10b981"]

    fig = go.Figure(go.Bar(
        x=categories,
        y=vals,
        marker=dict(color=bar_colors),
        text=[f"${v:,.0f}" for v in vals],
        textposition="outside",
    ))

    fig.update_layout(
        title="Financial Impact: Unplanned Breakdown Exposure vs Planned Intervention",
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        yaxis=dict(title="Cost Exposure (USD)", gridcolor="#334155"),
        margin=dict(l=20, r=20, t=40, b=30),
        height=320,
    )
    return fig


def create_historical_downtime_chart() -> go.Figure:
    """Bar chart of historical failures and maintenance expenses."""
    failures_df = fetch_df("SELECT * FROM failure_events;")
    if failures_df.empty:
        # Placeholder if no failures recorded
        fig = go.Figure()
        fig.update_layout(
            title="Historical Failure Downtime by Machine",
            paper_bgcolor="#1e293b",
            plot_bgcolor="#1e293b",
            font=dict(color="#f8fafc"),
            height=320,
        )
        return fig

    fig = go.Figure(go.Bar(
        x=failures_df["machine_id"],
        y=failures_df["downtime_duration"],
        name="Downtime Duration (Hours)",
        marker=dict(color="#ea580c"),
        text=[f"{v:.1f} hrs" for v in failures_df["downtime_duration"]],
        textposition="outside",
    ))

    fig.update_layout(
        title="Recorded Historical Unplanned Breakdown Downtime (Hours)",
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        xaxis=dict(title="Machine ID", gridcolor="#334155"),
        yaxis=dict(title="Downtime Duration (Hours)", gridcolor="#334155"),
        margin=dict(l=20, r=20, t=40, b=30),
        height=320,
    )
    return fig


def render_dashboard_tab():
    """Construct Gradio layout for Tab 1 - Executive Overview."""
    with gr.Column():
        kpi_display = gr.HTML()

        with gr.Row():
            chart_risk_donut = gr.Plot()
            chart_area_bars = gr.Plot()

        with gr.Row():
            chart_cost_compare = gr.Plot()
            chart_hist_downtime = gr.Plot()

        with gr.Row():
            btn_refresh = gr.Button("🔄 Refresh Fleet Status", elem_classes=["btn-primary"])
            btn_export_pdf = gr.Button("📄 Generate Executive PDF Briefing", elem_classes=["btn-primary"])
            pdf_download = gr.File(label="Download Briefing Report", visible=False)

        def refresh_overview():
            fleet_df = generate_fleet_predictions(horizon_hours=72, persist=False)
            impact = compute_business_impact_analysis()
            kpi_html = build_kpi_html(fleet_df, impact)
            f_donut = create_risk_distribution_donut(fleet_df)
            f_bars = create_area_risk_barchart(fleet_df)
            f_cost = create_cost_exposure_comparison(impact)
            f_dt = create_historical_downtime_chart()
            return kpi_html, f_donut, f_bars, f_cost, f_dt

        def on_export_pdf():
            pdf_path = generate_executive_pdf_report(horizon_hours=72)
            return gr.update(value=pdf_path, visible=True)

        btn_refresh.click(
            fn=refresh_overview,
            inputs=[],
            outputs=[kpi_display, chart_risk_donut, chart_area_bars, chart_cost_compare, chart_hist_downtime]
        )

        btn_export_pdf.click(
            fn=on_export_pdf,
            inputs=[],
            outputs=[pdf_download]
        )

    return {
        "refresh_fn": refresh_overview,
        "kpi_display": kpi_display,
        "chart_risk_donut": chart_risk_donut,
        "chart_area_bars": chart_area_bars,
        "chart_cost_compare": chart_cost_compare,
        "chart_hist_downtime": chart_hist_downtime,
    }
