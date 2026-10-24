"""
TAB 7 — Business Impact and Financial Optimization for TATA STEEL MAINTAINAI.
Quantifies downtime exposure, scenario comparisons (Run-to-Failure vs Preventive Intervention),
potential financial savings, equipment availability, and interactive sensitivity controls.
"""

import gradio as gr
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any

from src.business_impact import compute_business_impact_analysis
from src.reporting import export_dataframe_to_csv


def build_scenario_kpis_html(impact: Dict[str, Any]) -> str:
    """Format business impact scenario KPI cards."""
    sc = impact["modeled_scenarios"]
    hist = impact["historical_metrics"]

    return f"""
    <div class="kpi-container">
        <div class="kpi-card" style="border-top: 3px solid #ef4444;">
            <div class="kpi-title">Scenario A (Run-to-Failure)</div>
            <div class="kpi-value" style="color: #fca5a5;">${sc['scenario_a_run_to_failure_cost']:,.0f}</div>
            <div class="kpi-subtext">Sum of Expected Failure Losses</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #0284c7;">
            <div class="kpi-title">Scenario B (Planned PM)</div>
            <div class="kpi-value" style="color: #38bdf8;">${sc['scenario_b_preventive_cost']:,.0f}</div>
            <div class="kpi-subtext">PM Parts, Labor & Residual Risk</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #10b981;">
            <div class="kpi-title">Net Potential Savings</div>
            <div class="kpi-value" style="color: #10b981;">${sc['net_potential_savings']:,.0f}</div>
            <div class="kpi-subtext">Modeled Risk Mitigation Delta</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #f59e0b;">
            <div class="kpi-title">Modeled PM ROI</div>
            <div class="kpi-value" style="color: #fde68a;">{sc['modeled_roi_pct']:.1f}%</div>
            <div class="kpi-subtext">Net Savings / Intervention Cost</div>
        </div>
        <div class="kpi-card" style="border-top: 3px solid #8b5cf6;">
            <div class="kpi-title">Projected Availability</div>
            <div class="kpi-value" style="color: #c4b5fd;">{sc['projected_availability_pct']:.2f}%</div>
            <div class="kpi-subtext">Baseline: {hist['historical_fleet_availability_pct']:.2f}%</div>
        </div>
    </div>
    """


def create_scenario_breakdown_chart(machine_breakdowns: list) -> go.Figure:
    """Create grouped bar chart comparing Scenario A vs Scenario B cost per machine."""
    df = pd.DataFrame(machine_breakdowns)
    if df.empty:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", height=320)
        return fig

    # Top 8 machines by exposure
    df = df.sort_values(by="scenario_a_exposure", ascending=False).head(8)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["machine_id"],
        y=df["scenario_a_exposure"],
        name="Scenario A: Run-to-Failure Exposure",
        marker=dict(color="#ef4444"),
    ))
    fig.add_trace(go.Bar(
        x=df["machine_id"],
        y=df["scenario_b_cost"],
        name="Scenario B: Planned PM Cost",
        marker=dict(color="#0284c7"),
    ))

    fig.update_layout(
        title="Asset-Level Scenario Cost Comparison (Top Exposure Machinery)",
        barmode="group",
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        yaxis=dict(title="Modeled Cost Exposure ($)", gridcolor="#334155"),
        xaxis=dict(title="Machine ID", gridcolor="#334155"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        height=340,
        margin=dict(l=20, r=20, t=40, b=40),
    )
    return fig


def render_business_impact_tab():
    """Construct Gradio layout for Tab 7 - Business Impact."""
    with gr.Column():
        gr.Markdown("### 💰 Business Impact and Maintenance Cost Optimization")

        kpi_display = gr.HTML()

        gr.Markdown("---")
        gr.Markdown("#### 🎛️ Sensitivity Parameters & Operational Assumptions")
        with gr.Row():
            sld_efficacy = gr.Slider(
                minimum=70.0, maximum=99.0, value=90.0, step=1.0,
                label="Intervention Efficacy (%)",
                info="Percentage of failure risk eliminated by planned maintenance"
            )
            sld_dt_multiplier = gr.Slider(
                minimum=0.5, maximum=2.5, value=1.0, step=0.1,
                label="Downtime Cost Multiplier",
                info="Stress test higher or lower market steel production margins"
            )
            sld_pm_multiplier = gr.Slider(
                minimum=0.8, maximum=1.5, value=1.0, step=0.05,
                label="Maintenance Labor/Parts Cost Multiplier",
                info="Factor in overtime or emergency spare part logistics fees"
            )

        plot_comparison = gr.Plot()

        gr.Markdown("#### 📋 Machine-by-Machine Financial Breakdown")
        tbl_machines = gr.Dataframe(interactive=False)

        with gr.Row():
            btn_export_impact = gr.Button("📥 Download Scenario Report (CSV)", elem_classes=["btn-primary"], scale=1)
            file_download = gr.File(label="Download CSV", visible=False)

        disclaimer_box = gr.Markdown()

        def recalculate(efficacy, dt_mult, pm_mult):
            impact = compute_business_impact_analysis(
                intervention_efficacy_pct=float(efficacy),
                downtime_cost_multiplier=float(dt_mult),
                pm_cost_multiplier=float(pm_mult)
            )
            kpis_html = build_scenario_kpis_html(impact)
            chart = create_scenario_breakdown_chart(impact["machine_breakdowns"])
            df_table = pd.DataFrame(impact["machine_breakdowns"])

            disclaimer_text = f"""
            > **⚠️ Operational Disclaimer & Modeling Assumptions:**
            > {impact['disclaimer']}
            """
            return kpis_html, chart, df_table, disclaimer_text

        def on_export(efficacy, dt_mult, pm_mult):
            impact = compute_business_impact_analysis(
                intervention_efficacy_pct=float(efficacy),
                downtime_cost_multiplier=float(dt_mult),
                pm_cost_multiplier=float(pm_mult)
            )
            df = pd.DataFrame(impact["machine_breakdowns"])
            path = export_dataframe_to_csv(df, "business_impact_scenario_report")
            return gr.update(value=path, visible=True)

        for sld in [sld_efficacy, sld_dt_multiplier, sld_pm_multiplier]:
            sld.change(
                fn=recalculate,
                inputs=[sld_efficacy, sld_dt_multiplier, sld_pm_multiplier],
                outputs=[kpi_display, plot_comparison, tbl_machines, disclaimer_box]
            )

        btn_export_impact.click(
            fn=on_export,
            inputs=[sld_efficacy, sld_dt_multiplier, sld_pm_multiplier],
            outputs=[file_download]
        )

    return {
        "load_fn": lambda: recalculate(90.0, 1.0, 1.0),
    }
