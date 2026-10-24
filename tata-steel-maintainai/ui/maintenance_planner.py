"""
TAB 6 — Maintenance Planning and Resource Scheduling for TATA STEEL MAINTAINAI.
Proposes feasible maintenance windows synchronized with plant shutdown schedules,
assigns qualified technical specialists, checks spare parts inventory, and manages conflicts.
"""

import gradio as gr
import pandas as pd
from typing import Dict, Any

from src.maintenance_scheduler import optimize_maintenance_schedule
from database.db import fetch_df


def load_schedule_table() -> pd.DataFrame:
    """Run optimizer and return calendar DataFrame."""
    res = optimize_maintenance_schedule(horizon_days=14, auto_create_work_orders=False)
    calendar = res.get("calendar", [])
    if not calendar:
        return pd.DataFrame()

    df = pd.DataFrame(calendar)
    display_cols = [
        "schedule_id", "machine_id", "priority", "production_area",
        "scheduled_start", "duration_hours", "is_shutdown_window",
        "assigned_technician", "allocated_part", "estimated_cost"
    ]
    df_disp = df[display_cols].copy()
    df_disp["estimated_cost"] = "$" + df_disp["estimated_cost"].round(0).astype(int).astype(str)
    return df_disp


def build_conflicts_html(res: Dict[str, Any]) -> str:
    """Format conflicts and infeasible tasks as alert banners."""
    conflicts = res.get("conflicts", [])
    infeasible = res.get("infeasible_tasks", [])

    if not conflicts and not infeasible:
        return """
        <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; padding: 12px 16px; border-radius: 6px; color: #6ee7b7; font-size: 13px;">
            ✅ <b>All Proposed Tasks Feasible:</b> Zero technician scheduling overlaps or spare-parts stockouts detected across the 14-day planning horizon.
        </div>
        """

    html = "<div style='display: flex; flex-direction: column; gap: 8px;'>"
    for c in conflicts:
        html += f"""
        <div style="background: rgba(245, 158, 11, 0.15); border: 1px solid #f59e0b; padding: 10px 14px; border-radius: 6px; color: #fde68a; font-size: 12.5px;">
            ⚠️ <b>{c.get('type', 'Resource Warning')}:</b> Asset <b>{c.get('machine_id')}</b> — {c.get('details')}
        </div>
        """

    for inf in infeasible:
        html += f"""
        <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; padding: 10px 14px; border-radius: 6px; color: #fca5a5; font-size: 12.5px;">
            🚫 <b>Infeasible Task:</b> Asset <b>{inf.get('machine_id')}</b> — {inf.get('reason')} (<i>{inf.get('resolution')}</i>)
        </div>
        """
    html += "</div>"
    return html


def render_maintenance_planner_tab():
    """Construct Gradio layout for Tab 6 - Maintenance Planner."""
    with gr.Column():
        gr.Markdown("### 📅 Constraint-Based Preventive Maintenance Scheduler")

        with gr.Row():
            btn_run_optimizer = gr.Button("⚡ Run Scheduling Optimizer", elem_classes=["btn-primary"], scale=2)
            btn_authorize_all = gr.Button("📋 Finalize & Generate Formal Work Orders", elem_classes=["btn-success"], scale=2)

        conflicts_display = gr.HTML()

        gr.Markdown("#### 🗓️ Optimized Maintenance Calendar (Next 14 Days)")
        tbl_schedule = gr.Dataframe(interactive=False)

        gr.Markdown("---")
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### 👥 Available Engineering Technicians Roster")
                tbl_techs = gr.Dataframe(interactive=False)
            with gr.Column(scale=1):
                gr.Markdown("#### 📦 Critical Maintenance Spare Parts Inventory")
                tbl_parts = gr.Dataframe(interactive=False)

        action_feedback = gr.Markdown()

        def on_optimize():
            res = optimize_maintenance_schedule(horizon_days=14, auto_create_work_orders=False)
            df_cal = load_schedule_table()
            conf_html = build_conflicts_html(res)
            techs_df = fetch_df("SELECT tech_id, name, specialization, skill_level, shift, hourly_rate FROM technicians;")
            parts_df = fetch_df("SELECT part_id, name, equipment_type, unit_cost, stock_quantity, reorder_lead_days FROM spare_parts;")
            return df_cal, conf_html, techs_df, parts_df

        def on_authorize():
            res = optimize_maintenance_schedule(horizon_days=14, auto_create_work_orders=True)
            df_cal = load_schedule_table()
            conf_html = build_conflicts_html(res)
            msg = f"✅ Successfully finalized and created **{res['total_scheduled']} official work orders** in SQLite database (persisted to Work Orders & Audit tab)."
            return msg, df_cal, conf_html

        btn_run_optimizer.click(
            fn=on_optimize,
            inputs=[],
            outputs=[tbl_schedule, conflicts_display, tbl_techs, tbl_parts]
        )

        btn_authorize_all.click(
            fn=on_authorize,
            inputs=[],
            outputs=[action_feedback, tbl_schedule, conflicts_display]
        )

    return {
        "tbl_schedule": tbl_schedule,
        "load_fn": on_optimize,
    }
