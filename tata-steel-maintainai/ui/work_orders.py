"""
TAB 10 — Work Orders and Audit Trail for TATA STEEL MAINTAINAI.
Tracks formal maintenance work orders, technician completion logs,
prediction vs actual outcome audits, and complete governance logs.
"""

import gradio as gr
import pandas as pd
from datetime import datetime
from typing import Dict, Any

from database.db import fetch_df, execute_query, log_audit


def load_work_orders_table() -> pd.DataFrame:
    """Fetch active work orders."""
    df = fetch_df(
        """
        SELECT w.work_order_id, w.machine_id, w.task_priority,
               w.scheduled_start, w.scheduled_end, t.name as technician_name,
               w.allocated_parts, w.estimated_cost, w.actual_cost, w.status
        FROM maintenance_work_orders w
        LEFT JOIN technicians t ON w.assigned_technician_id = t.tech_id
        ORDER BY w.scheduled_start DESC;
        """
    )
    if df.empty:
        return pd.DataFrame()
    df["estimated_cost"] = "$" + df["estimated_cost"].round(0).astype(int).astype(str)
    return df


def load_audit_trail_table() -> pd.DataFrame:
    """Fetch recent system governance and audit logs."""
    return fetch_df(
        "SELECT event_timestamp, action_type, entity_type, entity_id, actor, details, previous_state, new_state FROM audit_logs ORDER BY event_timestamp DESC LIMIT 50;"
    )


def load_prediction_audit_table() -> pd.DataFrame:
    """
    Compare high-risk predictions against maintenance interventions and actual outcomes.
    Verifies model accuracy and preventive maintenance effectiveness.
    """
    query = """
    SELECT
        w.work_order_id,
        w.machine_id,
        p.risk_category as model_predicted_risk,
        p.failure_probability,
        w.scheduled_start as intervention_date,
        w.status as maintenance_status,
        CASE
            WHEN w.actual_failure_occurred = 1 THEN 'Actual Breakdown Occurred (True Positive)'
            WHEN w.status = 'Completed' AND w.actual_failure_occurred = 0 THEN 'Failure Successfully Prevented by PM'
            ELSE 'Scheduled / In-Progress'
        END as verified_outcome,
        w.recorded_observations
    FROM maintenance_work_orders w
    LEFT JOIN predictions p ON w.machine_id = p.machine_id
    GROUP BY w.work_order_id
    ORDER BY w.created_at DESC;
    """
    df = fetch_df(query)
    if not df.empty and "failure_probability" in df.columns:
        df["failure_probability"] = (df["failure_probability"].fillna(0.0) * 100).round(1).astype(str) + "%"
    return df


def render_work_orders_tab():
    """Construct Gradio layout for Tab 10 - Work Orders & Audit."""
    with gr.Column():
        gr.Markdown("### 🛠️ Maintenance Work Orders and Execution Management")

        with gr.Row():
            btn_refresh_wo = gr.Button("🔄 Refresh Work Orders & Audit", elem_classes=["btn-primary"], scale=1)

        tbl_work_orders = gr.Dataframe(interactive=False)

        gr.Markdown("---")
        gr.Markdown("### 📝 Work Order Completion & Feedback Logging")

        with gr.Row():
            dd_select_wo = gr.Dropdown(choices=["No Work Orders"], label="Select Work Order ID", scale=2)
            txt_actual_cost = gr.Number(label="Actual Incurred Cost ($)", value=3500.0, scale=1)
            rdo_actual_fail = gr.Radio(
                choices=[("Prevented by PM (No Breakdown)", 0), ("Actual Breakdown Occurred", 1)],
                value=0,
                label="Physical Outcome Verification",
                scale=2
            )

        txt_observations = gr.Textbox(
            label="Field Technician Observations & Replaced Part Details",
            placeholder="e.g. Bearing outer raceway showed early spalling. Replaced bearing and re-aligned shaft.",
            lines=2
        )

        btn_mark_completed = gr.Button("✅ Log Completion & Close Work Order", elem_classes=["btn-success"])
        completion_feedback = gr.Markdown()

        gr.Markdown("---")
        gr.Markdown("### 🎯 Prediction vs Actual Outcome Audit (Model Reliability Audit)")
        tbl_prediction_audit = gr.Dataframe(interactive=False)

        gr.Markdown("---")
        gr.Markdown("### 📜 System Governance & Decision Audit Trail")
        tbl_audit_trail = gr.Dataframe(interactive=False)

        def update_wo_choices():
            df = fetch_df("SELECT work_order_id FROM maintenance_work_orders WHERE status != 'Completed' ORDER BY created_at DESC;")
            choices = df["work_order_id"].tolist() if not df.empty else ["No Active Work Orders"]
            return gr.update(choices=choices, value=choices[0])

        def on_refresh():
            wo_df = load_work_orders_table()
            audit_df = load_audit_trail_table()
            pred_audit_df = load_prediction_audit_table()
            wo_choices = update_wo_choices()
            return wo_df, audit_df, pred_audit_df, wo_choices

        def on_complete_wo(wo_id, actual_cost, fail_occ, obs):
            if not wo_id or wo_id == "No Active Work Orders":
                return "⚠️ No active work order selected.", load_work_orders_table(), load_audit_trail_table(), load_prediction_audit_table(), update_wo_choices()

            execute_query(
                """
                UPDATE maintenance_work_orders SET
                    status = 'Completed',
                    actual_cost = ?,
                    actual_failure_occurred = ?,
                    recorded_observations = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE work_order_id = ?;
                """,
                (float(actual_cost), int(fail_occ), str(obs), wo_id)
            )

            outcome_str = "Breakdown Occurred" if fail_occ == 1 else "Breakdown Successfully Prevented"
            log_audit(
                action_type="WORK_ORDER_COMPLETE",
                entity_type="maintenance_work_orders",
                entity_id=wo_id,
                details=f"Closed work order. Actual Cost: ${actual_cost:,.2f}. Outcome: {outcome_str}. Obs: {obs}",
                previous_state="Scheduled",
                new_state="Completed"
            )

            msg = f"✅ Work Order **{wo_id}** marked as **Completed**. Verified Outcome: **{outcome_str}**."
            wo_df, audit_df, pred_audit_df, wo_choices = on_refresh()
            return msg, wo_df, audit_df, pred_audit_df, wo_choices

        btn_refresh_wo.click(
            fn=on_refresh,
            inputs=[],
            outputs=[tbl_work_orders, tbl_audit_trail, tbl_prediction_audit, dd_select_wo]
        )

        btn_mark_completed.click(
            fn=on_complete_wo,
            inputs=[dd_select_wo, txt_actual_cost, rdo_actual_fail, txt_observations],
            outputs=[completion_feedback, tbl_work_orders, tbl_audit_trail, tbl_prediction_audit, dd_select_wo]
        )

    return {
        "load_fn": on_refresh,
    }
