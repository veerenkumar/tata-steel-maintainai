"""
TAB 3 — Failure Predictions and Model Inference for TATA STEEL MAINTAINAI.
Interactive failure probability forecasting, contributing feature breakdown,
model version lineage, and explanatory diagnostic evidence.
"""

import gradio as gr
import plotly.graph_objects as go
import pandas as pd
import json

from database.db import get_all_machines, fetch_df
from src.prediction_engine import predict_machine_failure


def create_probability_gauge(prob: float, risk_cat: str) -> go.Figure:
    """Create interactive failure probability gauge."""
    val_pct = prob * 100.0

    if "Critical" in risk_cat:
        bar_color = "#ef4444"
    elif "High" in risk_cat:
        bar_color = "#f97316"
    elif "Medium" in risk_cat:
        bar_color = "#f59e0b"
    else:
        bar_color = "#10b981"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val_pct,
        number=dict(suffix="%", font=dict(size=38, color="#ffffff", family="Inter")),
        title=dict(text=f"Failure Probability ({risk_cat})", font=dict(size=14, color="#94a3b8")),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor="#94a3b8", tickvals=[0, 25, 55, 80, 100]),
            bar=dict(color=bar_color, thickness=0.35),
            bgcolor="#0f172a",
            borderwidth=1,
            bordercolor="#334155",
            steps=[
                dict(range=[0, 25], color="rgba(16, 185, 129, 0.15)"),
                dict(range=[25, 55], color="rgba(245, 158, 11, 0.15)"),
                dict(range=[55, 80], color="rgba(249, 115, 22, 0.15)"),
                dict(range=[80, 100], color="rgba(239, 68, 68, 0.25)"),
            ],
            threshold=dict(
                line=dict(color="#ef4444", width=3),
                thickness=0.8,
                value=80.0
            )
        )
    ))

    fig.update_layout(
        paper_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        height=260,
        margin=dict(l=30, r=30, t=40, b=20),
    )
    return fig


def create_feature_drivers_chart(top_features_json: str) -> go.Figure:
    """Horizontal bar chart showing top contributing predictive features."""
    try:
        features = json.loads(top_features_json)
    except Exception:
        features = []

    if not features:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", height=260)
        return fig

    names = [f["feature"].replace("_", " ").title() for f in features][::-1]
    importances = [f["importance"] for f in features][::-1]
    values = [f"{f['value']}" for f in features][::-1]

    fig = go.Figure(go.Bar(
        x=importances,
        y=names,
        orientation="h",
        marker=dict(color="#38bdf8"),
        text=[f"Observed: {v}" for v in values],
        textposition="inside",
        insidetextanchor="end",
    ))

    fig.update_layout(
        title="Top Contributing Risk Drivers (Feature Importance)",
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        xaxis=dict(title="Relative Feature Importance Weight", gridcolor="#334155"),
        yaxis=dict(title="", gridcolor="#334155"),
        height=260,
        margin=dict(l=10, r=20, t=40, b=20),
    )
    return fig


def render_failure_predictions_tab():
    """Construct Gradio layout for Tab 3 - Failure Predictions."""
    all_machines = get_all_machines()
    machine_ids = all_machines["machine_id"].tolist() if not all_machines.empty else ["BF-PUMP-001"]

    with gr.Column():
        gr.Markdown("### 🔮 Supervised Equipment Failure Prediction Engine")

        with gr.Row():
            dd_pred_machine = gr.Dropdown(choices=machine_ids, value=machine_ids[0], label="Select Machinery Asset", scale=2)
            dd_horizon = gr.Dropdown(choices=[24, 48, 72, 168], value=72, label="Forecast Horizon (Hours)", scale=1)
            btn_run_pred = gr.Button("⚡ Run Inference", elem_classes=["btn-primary"], scale=1)

        with gr.Row():
            gauge_plot = gr.Plot(scale=1)
            drivers_plot = gr.Plot(scale=1)

        info_card = gr.HTML()
        explanation_box = gr.Markdown()

        gr.Markdown("#### 📈 Historical Inferences for Selected Asset")
        tbl_pred_history = gr.Dataframe(interactive=False)

        def execute_prediction(m_id, horizon):
            pred = predict_machine_failure(m_id, horizon_hours=horizon, persist=True)
            p_gauge = create_probability_gauge(pred["failure_probability"], pred["risk_category"])
            p_drivers = create_feature_drivers_chart(pred["top_contributing_features"])

            cb = pred["cost_breakdown"]
            info_html = f"""
            <div class="kpi-container" style="margin-top: 10px;">
                <div class="kpi-card" style="border-top: 3px solid #0284c7;">
                    <div class="kpi-title">Model Version</div>
                    <div class="kpi-value" style="font-size: 16px;">{pred['model_version']}</div>
                    <div class="kpi-subtext">Calibrated Random Forest</div>
                </div>
                <div class="kpi-card" style="border-top: 3px solid #f97316;">
                    <div class="kpi-title">Composite Risk</div>
                    <div class="kpi-value" style="color: #f97316;">{pred['composite_risk_score']}</div>
                    <div class="kpi-subtext">Score (0-100 Scale)</div>
                </div>
                <div class="kpi-card" style="border-top: 3px solid #ef4444;">
                    <div class="kpi-title">Expected Failure Loss</div>
                    <div class="kpi-value" style="color: #fca5a5;">${pred['expected_failure_loss']:,.0f}</div>
                    <div class="kpi-subtext">Prob × Total Breakdown Cost</div>
                </div>
                <div class="kpi-card" style="border-top: 3px solid #f59e0b;">
                    <div class="kpi-title">Single Failure Impact</div>
                    <div class="kpi-value" style="font-size: 20px;">${cb['total_failure_cost']:,.0f}</div>
                    <div class="kpi-subtext">Repair + {cb['unplanned_downtime_hours']}h Downtime</div>
                </div>
            </div>
            """

            exp_md = f"""
            > **🤖 Diagnostic Explanation & Contributing Evidence:**
            > {pred['explanation']}
            >
            > **⚠️ Operational Notice:** {pred['limitations_disclaimer']}
            """

            # Fetch history
            hist_df = fetch_df(
                "SELECT prediction_timestamp, forecast_horizon_hours, failure_probability, risk_category, composite_risk_score, expected_failure_loss, model_version FROM predictions WHERE machine_id = ? ORDER BY prediction_timestamp DESC LIMIT 8;",
                (m_id,)
            )

            return p_gauge, p_drivers, info_html, exp_md, hist_df

        btn_run_pred.click(
            fn=execute_prediction,
            inputs=[dd_pred_machine, dd_horizon],
            outputs=[gauge_plot, drivers_plot, info_card, explanation_box, tbl_pred_history]
        )

        dd_pred_machine.change(
            fn=execute_prediction,
            inputs=[dd_pred_machine, dd_horizon],
            outputs=[gauge_plot, drivers_plot, info_card, explanation_box, tbl_pred_history]
        )

    return {
        "dd_pred_machine": dd_pred_machine,
        "execute_fn": execute_prediction,
    }
