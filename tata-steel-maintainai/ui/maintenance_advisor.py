"""
TAB 5 — Maintenance Recommendation Advisor for TATA STEEL MAINTAINAI.
Explainable AI recommendations, required spare parts mapping,
and authorized human approval/rejection decision workflows with audit persistence.
"""

import gradio as gr
import pandas as pd
from typing import Dict, Any

from database.db import fetch_df, log_audit
from src.recommendation_engine import (
    generate_fleet_recommendations,
    update_recommendation_decision,
)


def load_recommendations_dataframe() -> pd.DataFrame:
    """Fetch all recommendations sorted by urgency and failure likelihood."""
    df = generate_fleet_recommendations()
    display_cols = [
        "recommendation_id", "machine_id", "priority", "risk_category",
        "predicted_failure_probability", "suggested_action",
        "estimated_maintenance_cost", "potential_downtime_exposure",
        "approval_status", "suggested_maintenance_window"
    ]
    df_disp = df[display_cols].copy()
    df_disp["predicted_failure_probability"] = (df_disp["predicted_failure_probability"] * 100).round(1).astype(str) + "%"
    df_disp["estimated_maintenance_cost"] = "$" + df_disp["estimated_maintenance_cost"].round(0).astype(int).astype(str)
    df_disp["potential_downtime_exposure"] = "$" + df_disp["potential_downtime_exposure"].round(0).astype(int).astype(str)
    return df_disp


def build_recommendation_card_html(rec: Dict[str, Any]) -> str:
    """Construct formatted HTML inspection card for selected recommendation."""
    if not rec:
        return "<p>No recommendation selected.</p>"

    prio = rec["priority"]
    prio_color = "#ef4444" if prio == "Critical" else ("#f97316" if prio == "High" else "#10b981")
    stat = rec["approval_status"]
    stat_color = "#10b981" if stat == "Approved" else ("#ef4444" if stat == "Rejected" else "#f59e0b")

    return f"""
    <div class="steel-card" style="border-left: 4px solid {prio_color};">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 8px;">
            <div>
                <span style="font-size: 17px; font-weight: 700; color: #ffffff;">{rec['recommendation_id']}</span>
                <span style="font-size: 13px; color: #94a3b8; margin-left: 10px;">Asset: <b>{rec['machine_id']}</b></span>
            </div>
            <div>
                <span style="background: {prio_color}22; color: {prio_color}; border: 1px solid {prio_color}; padding: 3px 10px; border-radius: 4px; font-weight: 600; font-size: 11px;">{prio} Priority</span>
                <span style="background: {stat_color}22; color: {stat_color}; border: 1px solid {stat_color}; padding: 3px 10px; border-radius: 4px; font-weight: 600; font-size: 11px; margin-left: 6px;">Status: {stat}</span>
            </div>
        </div>

        <div style="margin-top: 12px;">
            <div style="font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600;">Suggested Maintenance & Inspection Action</div>
            <div style="font-size: 14px; color: #f8fafc; font-weight: 500; margin-top: 2px;">{rec['suggested_action']}</div>
        </div>

        <div style="margin-top: 10px;">
            <div style="font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600;">Contributing Rationale & Telemetry Evidence</div>
            <div style="font-size: 13px; color: #cbd5e1; margin-top: 2px;">{rec['reason_for_recommendation']}</div>
            <div style="font-size: 12px; color: #fca5a5; margin-top: 4px;">• <i>{rec['anomaly_evidence']}</i></div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; margin-top: 14px;">
            <div style="background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid #334155;">
                <div style="font-size: 11px; color: #94a3b8;">Est. Duration</div>
                <div style="font-size: 14px; font-weight: 600; color: #38bdf8;">{rec['estimated_maintenance_duration']} Hours</div>
            </div>
            <div style="background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid #334155;">
                <div style="font-size: 11px; color: #94a3b8;">Est. Preventive Cost</div>
                <div style="font-size: 14px; font-weight: 600; color: #10b981;">${rec['estimated_maintenance_cost']:,.0f}</div>
            </div>
            <div style="background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid #334155;">
                <div style="font-size: 11px; color: #94a3b8;">Potential Downtime Exposure</div>
                <div style="font-size: 14px; font-weight: 600; color: #ef4444;">${rec['potential_downtime_exposure']:,.0f}</div>
            </div>
            <div style="background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid #334155;">
                <div style="font-size: 11px; color: #94a3b8;">Suggested Window</div>
                <div style="font-size: 12px; font-weight: 600; color: #f59e0b;">{rec['suggested_maintenance_window']}</div>
            </div>
        </div>

        <div style="margin-top: 12px; background: #0f172a; padding: 8px 12px; border-radius: 6px; border: 1px solid #334155; font-size: 12px; color: #94a3b8;">
            <b>Recommended Spare Parts Catalog:</b> {rec.get('required_parts', 'Standard Consumables')}
        </div>
    </div>
    """


def render_maintenance_advisor_tab():
    """Construct Gradio layout for Tab 5 - Maintenance Advisor."""
    recs_df = generate_fleet_recommendations()
    rec_ids = recs_df["recommendation_id"].tolist() if not recs_df.empty else ["No Recommendations"]

    with gr.Column():
        gr.Markdown("### 🛡️ AI Maintenance Advisor & Action Review")

        with gr.Row():
            btn_refresh_recs = gr.Button("🔄 Refresh Fleet Recommendations", elem_classes=["btn-primary"], scale=1)

        tbl_recommendations = gr.Dataframe(interactive=False)

        gr.Markdown("---")
        gr.Markdown("### ✍️ Human Authorization & Decision Workflow")

        with gr.Row():
            dd_select_rec = gr.Dropdown(choices=rec_ids, value=rec_ids[0], label="Select Recommendation ID", scale=2)
            txt_reviewer = gr.Textbox(label="Authorized Reviewer Name / Title", value="Maintenance Superintendent", scale=2)

        rec_card_display = gr.HTML()

        txt_decision_notes = gr.Textbox(
            label="Decision Justification & Safety Interlock Comments",
            placeholder="Document shift notes, safety clearance, or reason for deferral...",
            lines=2
        )

        with gr.Row():
            btn_approve = gr.Button("✅ Approve Work Order", elem_classes=["btn-success"])
            btn_defer = gr.Button("⏳ Defer to Next Window", elem_classes=["btn-primary"])
            btn_reject = gr.Button("❌ Reject Recommendation", elem_classes=["btn-danger"])

        feedback_md = gr.Markdown()

        def update_selected_card(rec_id):
            df = fetch_df("SELECT * FROM maintenance_recommendations WHERE recommendation_id = ?;", (rec_id,))
            if df.empty:
                return "<p>Recommendation not found.</p>"
            return build_recommendation_card_html(df.iloc[0].to_dict())

        def handle_decision(rec_id, decision, notes, reviewer):
            res = update_recommendation_decision(rec_id, decision, notes=notes, decided_by=reviewer)
            card_html = update_selected_card(rec_id)
            updated_table = load_recommendations_dataframe()
            msg = f"**Result:** {res['message']}"
            return msg, card_html, updated_table

        btn_refresh_recs.click(
            fn=lambda: (load_recommendations_dataframe(), gr.update(choices=generate_fleet_recommendations()["recommendation_id"].tolist())),
            inputs=[],
            outputs=[tbl_recommendations, dd_select_rec]
        )

        dd_select_rec.change(
            fn=update_selected_card,
            inputs=[dd_select_rec],
            outputs=[rec_card_display]
        )

        btn_approve.click(
            fn=lambda r_id, n, rev: handle_decision(r_id, "Approved", n, rev),
            inputs=[dd_select_rec, txt_decision_notes, txt_reviewer],
            outputs=[feedback_md, rec_card_display, tbl_recommendations]
        )

        btn_defer.click(
            fn=lambda r_id, n, rev: handle_decision(r_id, "Deferred", n, rev),
            inputs=[dd_select_rec, txt_decision_notes, txt_reviewer],
            outputs=[feedback_md, rec_card_display, tbl_recommendations]
        )

        btn_reject.click(
            fn=lambda r_id, n, rev: handle_decision(r_id, "Rejected", n, rev),
            inputs=[dd_select_rec, txt_decision_notes, txt_reviewer],
            outputs=[feedback_md, rec_card_display, tbl_recommendations]
        )

    return {
        "tbl_recommendations": tbl_recommendations,
        "load_fn": lambda: load_recommendations_dataframe(),
    }
