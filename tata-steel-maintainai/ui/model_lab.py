"""
TAB 9 — Model Lab and Machine Learning Diagnostics for TATA STEEL MAINTAINAI.
Model version lineage, comparative benchmarks (Random Forest vs Gradient Boosting),
interactive Precision-Recall curves, Confusion Matrices, and controlled retraining.
"""

import gradio as gr
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any

from database.db import fetch_df
from src.train_model import load_active_model, train_failure_prediction_models


def create_confusion_matrix_heatmap(cm: list) -> go.Figure:
    """Plotly heatmap for 2x2 confusion matrix."""
    if not cm or len(cm) != 2:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", height=280)
        return fig

    z_vals = [[cm[1][1], cm[1][0]], [cm[0][1], cm[0][0]]]  # TP, FN / FP, TN
    x_labels = ["Predicted Failure (1)", "Predicted Healthy (0)"]
    y_labels = ["Actual Failure (1)", "Actual Healthy (0)"]

    annotations = []
    for i, row in enumerate(z_vals):
        for j, val in enumerate(row):
            annotations.append(dict(
                x=x_labels[j], y=y_labels[i], text=str(val),
                font=dict(color="#ffffff", size=18, family="Inter"),
                showarrow=False
            ))

    fig = go.Figure(data=go.Heatmap(
        z=z_vals, x=x_labels, y=y_labels,
        colorscale=[[0, "#0f172a"], [0.5, "#0284c7"], [1, "#10b981"]],
        showscale=False,
    ))

    fig.update_layout(
        title="Test Split Confusion Matrix (Strict Chronological)",
        paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        annotations=annotations,
        height=280, margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def create_pr_curve_chart(pr_data: dict) -> go.Figure:
    """Plotly Precision-Recall curve."""
    fig = go.Figure()
    if pr_data and "precision" in pr_data and "recall" in pr_data:
        fig.add_trace(go.Scatter(
            x=pr_data["recall"], y=pr_data["precision"],
            mode="lines", name="PR Curve",
            line=dict(color="#38bdf8", width=3),
            fill="tozeroy", fillcolor="rgba(56, 189, 248, 0.15)",
        ))

    fig.update_layout(
        title="Precision-Recall Curve (Imbalanced Failure Labels)",
        paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        xaxis=dict(title="Recall (Sensitivity)", range=[0, 1.05], gridcolor="#334155"),
        yaxis=dict(title="Precision", range=[0, 1.05], gridcolor="#334155"),
        height=280, margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def create_feature_importance_plot(feat_map: dict) -> go.Figure:
    """Horizontal bar chart for Random Forest feature importances."""
    if not feat_map:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", height=280)
        return fig

    # Top 8 features
    items = list(feat_map.items())[:8][::-1]
    features = [k.replace("_", " ").title() for k, _ in items]
    weights = [v for _, v in items]

    fig = go.Figure(go.Bar(
        x=weights, y=features,
        orientation="h",
        marker=dict(color="#f59e0b"),
        text=[f"{w:.3f}" for w in weights],
        textposition="outside",
    ))

    fig.update_layout(
        title="Global MDI Feature Importances",
        paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        xaxis=dict(title="Importance Weight", gridcolor="#334155"),
        yaxis=dict(gridcolor="#334155"),
        height=280, margin=dict(l=10, r=30, t=40, b=20),
    )
    return fig


def create_calibration_curve_plot(calib_data: dict) -> go.Figure:
    """Reliability calibration diagram."""
    fig = go.Figure()
    # 45 degree perfect line
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode="lines", name="Perfect Calibration",
        line=dict(color="#64748b", dash="dash"),
    ))

    if calib_data and "prob_pred" in calib_data and len(calib_data["prob_pred"]) > 0:
        fig.add_trace(go.Scatter(
            x=calib_data["prob_pred"], y=calib_data["prob_true"],
            mode="lines+markers", name="Random Forest",
            line=dict(color="#10b981", width=2),
            marker=dict(size=6, color="#10b981"),
        ))

    fig.update_layout(
        title="Probability Calibration (Reliability Diagram)",
        paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        xaxis=dict(title="Mean Predicted Probability", range=[0, 1.05], gridcolor="#334155"),
        yaxis=dict(title="Fraction of Positives", range=[0, 1.05], gridcolor="#334155"),
        height=280, margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def render_model_lab_tab():
    """Construct Gradio layout for Tab 9 - Model Lab."""
    with gr.Column():
        gr.Markdown("### 🔬 Machine Learning Evaluation & Retraining Lab")

        active_model_card = gr.HTML()

        with gr.Row():
            plot_cm = gr.Plot()
            plot_pr = gr.Plot()

        with gr.Row():
            plot_imp = gr.Plot()
            plot_calib = gr.Plot()

        gr.Markdown("#### ⚖️ Model Comparison Benchmark")
        tbl_comparison = gr.Dataframe(interactive=False)

        gr.Markdown("---")
        gr.Markdown("### 🔄 Controlled Model Retraining")
        with gr.Row():
            dd_retrain_horizon = gr.Dropdown(choices=[24, 48, 72, 168], value=72, label="Forecast Horizon (Hours)", scale=1)
            txt_model_tag = gr.Textbox(label="Optional Model Version Tag", placeholder="e.g. RF-TUNED-EXP1", scale=2)
            btn_retrain = gr.Button("🚀 Train & Calibrate Models", elem_classes=["btn-primary"], scale=1)

        retrain_status = gr.Markdown()

        gr.Markdown("#### 📜 Registered Model Versions (SQLite Lineage)")
        tbl_versions = gr.Dataframe(interactive=False)

        def load_diagnostics():
            bundle = load_active_model(horizon_hours=72)
            ev = bundle.get("evaluation", {})
            cm = ev.get("confusion_matrix", [[0, 0], [0, 0]])
            pr_data = ev.get("pr_curve", {})
            calib_data = ev.get("calibration", {})
            feat_map = bundle.get("feature_importances", {})

            f_cm = create_confusion_matrix_heatmap(cm)
            f_pr = create_pr_curve_chart(pr_data)
            f_imp = create_feature_importance_plot(feat_map)
            f_cal = create_calibration_curve_plot(calib_data)

            # Active Model HTML
            card_html = f"""
            <div class="kpi-container">
                <div class="kpi-card" style="border-top: 3px solid #0284c7;">
                    <div class="kpi-title">Active Version</div>
                    <div class="kpi-value" style="font-size: 16px;">{bundle.get('version_id')}</div>
                    <div class="kpi-subtext">Calibrated Random Forest</div>
                </div>
                <div class="kpi-card" style="border-top: 3px solid #10b981;">
                    <div class="kpi-title">Recall (Sensitivity)</div>
                    <div class="kpi-value" style="color: #10b981;">{ev.get('recall', 0.0)*100:.1f}%</div>
                    <div class="kpi-subtext">Catches imminent breakdowns</div>
                </div>
                <div class="kpi-card" style="border-top: 3px solid #38bdf8;">
                    <div class="kpi-title">F1-Score</div>
                    <div class="kpi-value" style="color: #38bdf8;">{ev.get('f1_score', 0.0):.3f}</div>
                    <div class="kpi-subtext">Harmonic Mean</div>
                </div>
                <div class="kpi-card" style="border-top: 3px solid #f59e0b;">
                    <div class="kpi-title">PR-AUC Score</div>
                    <div class="kpi-value" style="color: #fde68a;">{ev.get('pr_auc', 0.0):.3f}</div>
                    <div class="kpi-subtext">Average Precision Metric</div>
                </div>
                <div class="kpi-card" style="border-top: 3px solid #8b5cf6;">
                    <div class="kpi-title">ROC-AUC Score</div>
                    <div class="kpi-value" style="color: #c4b5fd;">{ev.get('roc_auc', 0.0):.3f}</div>
                    <div class="kpi-subtext">Discriminative Capability</div>
                </div>
                <div class="kpi-card" style="border-top: 3px solid #ec4899;">
                    <div class="kpi-title">Brier Score</div>
                    <div class="kpi-value" style="color: #fbcfe8;">{ev.get('brier_score', 0.0):.4f}</div>
                    <div class="kpi-subtext">Probability Calibration Error</div>
                </div>
            </div>
            """

            # Comparison table
            comp_rows = []
            models_comp = bundle.get("models_comparison", {})
            for m_name, m_ev in models_comp.items():
                if isinstance(m_ev, dict) and "precision" in m_ev:
                    comp_rows.append({
                        "Algorithm": m_name,
                        "Precision": m_ev.get("precision", 0.0),
                        "Recall": m_ev.get("recall", 0.0),
                        "F1-Score": m_ev.get("f1_score", 0.0),
                        "PR-AUC": m_ev.get("pr_auc", 0.0),
                        "ROC-AUC": m_ev.get("roc_auc", 0.0),
                        "Brier Score": m_ev.get("brier_score", 0.0),
                        "Status": "Evaluated on Test Split"
                    })
                elif isinstance(m_ev, dict):
                    comp_rows.append({
                        "Algorithm": m_name,
                        "Precision": 0.0,
                        "Recall": 0.0,
                        "F1-Score": 0.0,
                        "PR-AUC": 0.0,
                        "ROC-AUC": 0.0,
                        "Brier Score": 0.0,
                        "Status": m_ev.get("message", "Optional Benchmark")
                    })
            df_comp = pd.DataFrame(comp_rows)

            # Versions table
            df_versions = fetch_df(
                "SELECT version_id, algorithm, horizon_hours, precision_score, recall_score, f1_score, pr_auc_score, roc_auc_score, trained_at, is_active FROM model_versions ORDER BY trained_at DESC LIMIT 10;"
            )

            return card_html, f_cm, f_pr, f_imp, f_cal, df_comp, df_versions

        def on_train(horizon, tag):
            try:
                bundle = train_failure_prediction_models(
                    horizon_hours=int(horizon),
                    model_version_tag=tag.strip() if tag else None
                )
                msg = f"✅ Successfully trained and calibrated model version **{bundle['version_id']}** (Recall: {bundle['evaluation']['recall']*100:.1f}%, F1: {bundle['evaluation']['f1_score']:.3f})."
                card, cm, pr, imp, cal, comp, vers = load_diagnostics()
                return msg, card, cm, pr, imp, cal, comp, vers
            except Exception as e:
                empty = load_diagnostics()
                return f"❌ Training Failed: {str(e)}", empty[0], empty[1], empty[2], empty[3], empty[4], empty[5], empty[6]

        btn_retrain.click(
            fn=on_train,
            inputs=[dd_retrain_horizon, txt_model_tag],
            outputs=[retrain_status, active_model_card, plot_cm, plot_pr, plot_imp, plot_calib, tbl_comparison, tbl_versions]
        )

    return {
        "load_fn": load_diagnostics,
    }
