"""
TAB 2 — Machine Fleet Registry and Asset Inspector for TATA STEEL MAINTAINAI.
Searchable, filterable machinery table with drill-down asset inspection,
telemetry baselines, maintenance history, and operating status management.
"""

import gradio as gr
import pandas as pd
from typing import Dict, Any, List

from database.db import get_all_machines, get_machine_by_id, update_machine_status, fetch_df
from src.prediction_engine import generate_fleet_predictions
from config.settings import PRODUCTION_AREAS, EQUIPMENT_REFERENCE_RANGES


def load_fleet_data(
    search_query: str = "",
    area_filter: str = "All",
    criticality_filter: str = "All",
    risk_filter: str = "All"
) -> pd.DataFrame:
    """Filter fleet machines based on user criteria."""
    fleet_preds = generate_fleet_predictions(horizon_hours=72, persist=False)

    df = fleet_preds.copy()
    if search_query:
        q = search_query.lower()
        mask = (
            df["machine_id"].str.lower().str.contains(q) |
            df["equipment_type"].str.lower().str.contains(q)
        )
        df = df[mask]

    if area_filter != "All":
        df = df[df["production_area"] == area_filter]

    if criticality_filter != "All":
        df = df[df["criticality"] == criticality_filter]

    if risk_filter != "All":
        df = df[df["risk_category"] == risk_filter]

    # Format probability as percent string
    df_display = df[[
        "machine_id", "equipment_type", "production_area", "criticality",
        "operating_status", "failure_probability", "is_anomaly",
        "composite_risk_score", "risk_category", "last_maintenance_date"
    ]].copy()

    df_display["failure_probability"] = (df_display["failure_probability"] * 100).round(1).astype(str) + "%"
    return df_display


def get_asset_inspector_html(machine_id: str) -> str:
    """Build detailed HTML asset overview card."""
    m = get_machine_by_id(machine_id)
    if not m:
        return "<p>No machine selected.</p>"

    eq_type = m["equipment_type"]
    ranges = EQUIPMENT_REFERENCE_RANGES.get(eq_type, {})

    return f"""
    <div class="steel-card">
        <div class="steel-card-title">
            <span>⚙️ <b>{m['machine_id']}</b> — {m['equipment_type']}</span>
        </div>
        <p style="color: #94a3b8; font-size: 13px; margin-top: -6px;">{m.get('description', '')}</p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 12px;">
            <div style="background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid #334155;">
                <div style="font-size: 11px; color: #94a3b8;">Production Area</div>
                <div style="font-size: 13px; font-weight: 600; color: #f8fafc;">{m['production_area']}</div>
            </div>
            <div style="background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid #334155;">
                <div style="font-size: 11px; color: #94a3b8;">Criticality Level</div>
                <div style="font-size: 13px; font-weight: 600; color: #f97316;">{m['criticality']}</div>
            </div>
            <div style="background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid #334155;">
                <div style="font-size: 11px; color: #94a3b8;">Cumulative Runtime</div>
                <div style="font-size: 13px; font-weight: 600; color: #38bdf8;">{m['operating_hours']:,.1f} Hours</div>
            </div>
            <div style="background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid #334155;">
                <div style="font-size: 11px; color: #94a3b8;">Downtime Cost Rate</div>
                <div style="font-size: 13px; font-weight: 600; color: #fca5a5;">${m['downtime_cost_per_hour']:,.0f} / hr</div>
            </div>
            <div style="background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid #334155;">
                <div style="font-size: 11px; color: #94a3b8;">Est. Repair Expense</div>
                <div style="font-size: 13px; font-weight: 600; color: #fca5a5;">${m['estimated_repair_cost']:,.0f}</div>
            </div>
            <div style="background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid #334155;">
                <div style="font-size: 11px; color: #94a3b8;">Last Maintenance</div>
                <div style="font-size: 13px; font-weight: 600; color: #10b981;">{m['last_maintenance_date']}</div>
            </div>
        </div>
    </div>
    """


def render_machine_fleet_tab():
    """Construct Gradio layout for Tab 2 - Machine Fleet."""
    all_machines = get_all_machines()
    machine_ids = all_machines["machine_id"].tolist() if not all_machines.empty else ["BF-PUMP-001"]

    with gr.Column():
        gr.Markdown("### 🏭 Equipment Fleet Directory & Health Matrix")

        # Filters
        with gr.Row():
            txt_search = gr.Textbox(label="Search Machine ID / Type", placeholder="e.g. MOTOR, BF-PUMP...", scale=2)
            dd_area = gr.Dropdown(choices=["All"] + PRODUCTION_AREAS, value="All", label="Filter Area", scale=2)
            dd_crit = gr.Dropdown(
                choices=["All", "Tier 1 - Critical", "Tier 2 - High", "Tier 3 - Medium"],
                value="All", label="Criticality", scale=1
            )
            dd_risk = gr.Dropdown(
                choices=["All", "Critical Risk", "High Risk", "Medium Risk", "Low Risk"],
                value="All", label="Risk Category", scale=1
            )

        tbl_fleet = gr.Dataframe(
            headers=[
                "Machine ID", "Equipment Type", "Production Area", "Criticality",
                "Operating Status", "Failure Prob", "Anomaly", "Risk Score",
                "Risk Category", "Last Maintenance"
            ],
            interactive=False,
            elem_classes=["fleet-table"],
        )

        gr.Markdown("---")
        gr.Markdown("### 🔍 Asset Inspector Drill-Down")

        with gr.Row():
            dd_inspector_machine = gr.Dropdown(choices=machine_ids, value=machine_ids[0], label="Select Machinery Asset", scale=2)
            dd_status_update = gr.Dropdown(
                choices=["Running", "Degraded", "Under Maintenance", "Standby"],
                value="Running",
                label="Update Operating Status",
                scale=1
            )
            btn_save_status = gr.Button("Save Status", elem_classes=["btn-primary"], scale=1)

        inspector_html = gr.HTML()
        status_feedback = gr.Markdown()

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### 📋 Recent Maintenance Records")
                tbl_maint_hist = gr.Dataframe(interactive=False)
            with gr.Column(scale=1):
                gr.Markdown("#### ⚡ Recent Sensor Readings Snapshot")
                tbl_sensor_snap = gr.Dataframe(interactive=False)

        def update_inspector(m_id):
            m = get_machine_by_id(m_id)
            current_status = m["operating_status"] if m else "Running"
            card_html = get_asset_inspector_html(m_id)

            maint_df = fetch_df(
                "SELECT maintenance_date, maintenance_type, maintenance_duration, maintenance_cost, technician_or_team_assignment, work_order_status FROM maintenance_records WHERE machine_id = ? ORDER BY maintenance_date DESC LIMIT 5;",
                (m_id,)
            )

            sensor_df = fetch_df(
                "SELECT timestamp, temperature, vibration, pressure, rotational_speed, electrical_current, operating_load, is_anomaly FROM sensor_readings WHERE machine_id = ? ORDER BY timestamp DESC LIMIT 6;",
                (m_id,)
            )

            return card_html, current_status, maint_df, sensor_df

        def on_filter_change(query, area, crit, risk):
            return load_fleet_data(query, area, crit, risk)

        def on_status_save(m_id, new_stat):
            update_machine_status(m_id, new_stat)
            msg = f"✅ Updated operating status of **{m_id}** to **{new_stat}** (persisted in SQLite & audit log)."
            card_html = get_asset_inspector_html(m_id)
            # reload fleet table
            refreshed_df = load_fleet_data()
            return msg, card_html, refreshed_df

        # Event triggers
        for c in [txt_search, dd_area, dd_crit, dd_risk]:
            c.change(
                fn=on_filter_change,
                inputs=[txt_search, dd_area, dd_crit, dd_risk],
                outputs=[tbl_fleet]
            )

        dd_inspector_machine.change(
            fn=update_inspector,
            inputs=[dd_inspector_machine],
            outputs=[inspector_html, dd_status_update, tbl_maint_hist, tbl_sensor_snap]
        )

        btn_save_status.click(
            fn=on_status_save,
            inputs=[dd_inspector_machine, dd_status_update],
            outputs=[status_feedback, inspector_html, tbl_fleet]
        )

    return {
        "tbl_fleet": tbl_fleet,
        "dd_inspector_machine": dd_inspector_machine,
        "inspector_html": inspector_html,
        "load_fn": lambda: (load_fleet_data(), update_inspector(machine_ids[0])),
    }
