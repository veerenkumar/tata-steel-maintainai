"""
TAB 4 — Sensor Telemetry Analytics and Anomaly Inspection for TATA STEEL MAINTAINAI.
Multi-sensor interactive time-series plots with operational reference boundaries,
anomaly scatter overlays, time-range controls, and telemetry validation.
"""

import gradio as gr
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

from database.db import get_all_machines, get_machine_by_id, fetch_df
from config.settings import EQUIPMENT_REFERENCE_RANGES
from src.data_ingestion import validate_dataset


def create_sensor_timeseries_plots(machine_id: str, days_window: int = 14):
    """
    Generate detailed interactive Plotly time series for:
    1. Temperature (°C) with normal, warn, crit limits
    2. Vibration (RMS mm/s) with ISO limits
    3. Pressure (bar) with nominal operating band
    4. Rotational Speed (RPM) and Motor Line Current (A)
    """
    m = get_machine_by_id(machine_id)
    if not m:
        return go.Figure(), go.Figure(), go.Figure(), go.Figure()

    eq_type = m["equipment_type"]
    ranges = EQUIPMENT_REFERENCE_RANGES.get(eq_type, EQUIPMENT_REFERENCE_RANGES["Industrial motors"])

    # Fetch sensor readings
    df = fetch_df(
        "SELECT * FROM sensor_readings WHERE machine_id = ? ORDER BY timestamp ASC;",
        (machine_id,)
    )
    if df.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", height=300)
        return empty_fig, empty_fig, empty_fig, empty_fig

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if days_window > 0:
        cutoff = df["timestamp"].max() - timedelta(days=days_window)
        df = df[df["timestamp"] >= cutoff]

    anom_df = df[df["is_anomaly"] == 1]

    # 1. Temperature Chart
    t_cfg = ranges["temperature"]
    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(
        x=df["timestamp"], y=df["temperature"],
        mode="lines", name="Temperature (°C)",
        line=dict(color="#38bdf8", width=2),
    ))
    # Threshold lines
    fig_temp.add_hline(y=t_cfg["normal_max"], line_dash="dash", line_color="#10b981", annotation_text=f"Normal Max ({t_cfg['normal_max']}°C)")
    fig_temp.add_hline(y=t_cfg["warn_max"], line_dash="dash", line_color="#f59e0b", annotation_text=f"Warning ({t_cfg['warn_max']}°C)")
    fig_temp.add_hline(y=t_cfg["crit_max"], line_dash="dash", line_color="#ef4444", annotation_text=f"Critical ({t_cfg['crit_max']}°C)")
    # Anomaly scatter
    if not anom_df.empty:
        fig_temp.add_trace(go.Scatter(
            x=anom_df["timestamp"], y=anom_df["temperature"],
            mode="markers", name="Telemetry Anomaly",
            marker=dict(color="#ef4444", size=7, symbol="x"),
        ))
    fig_temp.update_layout(
        title=f"Bearing / Casing Temperature Telemetry (°C) — {machine_id}",
        paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        yaxis=dict(title="Temperature (°C)", gridcolor="#334155"),
        xaxis=dict(gridcolor="#334155"),
        height=300, margin=dict(l=20, r=20, t=40, b=20),
    )

    # 2. Vibration Chart
    v_cfg = ranges["vibration"]
    fig_vib = go.Figure()
    fig_vib.add_trace(go.Scatter(
        x=df["timestamp"], y=df["vibration"],
        mode="lines", name="Vibration (RMS mm/s)",
        line=dict(color="#a855f7", width=2),
    ))
    fig_vib.add_hline(y=v_cfg["normal_max"], line_dash="dash", line_color="#10b981", annotation_text=f"ISO Good ({v_cfg['normal_max']} mm/s)")
    fig_vib.add_hline(y=v_cfg["warn_max"], line_dash="dash", line_color="#f59e0b", annotation_text=f"Alert ({v_cfg['warn_max']} mm/s)")
    fig_vib.add_hline(y=v_cfg["crit_max"], line_dash="dash", line_color="#ef4444", annotation_text=f"Danger ({v_cfg['crit_max']} mm/s)")
    if not anom_df.empty:
        fig_vib.add_trace(go.Scatter(
            x=anom_df["timestamp"], y=anom_df["vibration"],
            mode="markers", name="Anomaly",
            marker=dict(color="#ef4444", size=7, symbol="x"),
        ))
    fig_vib.update_layout(
        title=f"ISO 10816 Vibration Severity (RMS mm/s) — {machine_id}",
        paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        yaxis=dict(title="Vibration (mm/s)", gridcolor="#334155"),
        xaxis=dict(gridcolor="#334155"),
        height=300, margin=dict(l=20, r=20, t=40, b=20),
    )

    # 3. Pressure Chart
    p_cfg = ranges["pressure"]
    fig_press = go.Figure()
    fig_press.add_trace(go.Scatter(
        x=df["timestamp"], y=df["pressure"],
        mode="lines", name="Pressure (bar)",
        line=dict(color="#10b981", width=2),
    ))
    fig_press.add_hline(y=p_cfg["normal_max"], line_dash="dot", line_color="#64748b", annotation_text=f"Nominal Upper ({p_cfg['normal_max']} bar)")
    fig_press.add_hline(y=p_cfg["normal_min"], line_dash="dot", line_color="#64748b", annotation_text=f"Nominal Lower ({p_cfg['normal_min']} bar)")
    fig_press.update_layout(
        title=f"Hydraulic / Pneumatic Pressure (bar) — {machine_id}",
        paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        yaxis=dict(title="Pressure (bar)", gridcolor="#334155"),
        xaxis=dict(gridcolor="#334155"),
        height=300, margin=dict(l=20, r=20, t=40, b=20),
    )

    # 4. RPM and Electrical Current
    fig_power = go.Figure()
    fig_power.add_trace(go.Scatter(
        x=df["timestamp"], y=df["electrical_current"],
        mode="lines", name="Current (A)",
        line=dict(color="#f59e0b", width=2),
    ))
    fig_power.add_trace(go.Scatter(
        x=df["timestamp"], y=df["operating_load"],
        mode="lines", name="Load (%)",
        line=dict(color="#06b6d4", width=1.5, dash="dot"),
        yaxis="y2"
    ))
    fig_power.update_layout(
        title=f"Motor Electrical Current (A) & Operating Load (%) — {machine_id}",
        paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
        font=dict(color="#f8fafc", family="Inter"),
        yaxis=dict(title="Line Current (A)", gridcolor="#334155"),
        yaxis2=dict(title="Operating Load (%)", overlaying="y", side="right", range=[0, 120]),
        xaxis=dict(gridcolor="#334155"),
        height=300, margin=dict(l=20, r=40, t=40, b=20),
    )

    return fig_temp, fig_vib, fig_press, fig_power


def render_sensor_analytics_tab():
    """Construct Gradio layout for Tab 4 - Sensor Analytics."""
    all_machines = get_all_machines()
    machine_ids = all_machines["machine_id"].tolist() if not all_machines.empty else ["BF-PUMP-001"]

    with gr.Column():
        gr.Markdown("### 📊 Continuous Sensor Telemetry & Anomaly Analysis")

        with gr.Row():
            dd_sensor_machine = gr.Dropdown(choices=machine_ids, value=machine_ids[0], label="Select Machinery Asset", scale=2)
            dd_time_window = gr.Dropdown(choices=[("Last 7 Days", 7), ("Last 14 Days", 14), ("Last 30 Days", 30), ("Full Telemetry History", 0)], value=14, label="Time Range Filter", scale=1)
            btn_refresh_sensors = gr.Button("🔄 Refresh Charts", elem_classes=["btn-primary"], scale=1)

        with gr.Row():
            plot_temp = gr.Plot()
            plot_vib = gr.Plot()

        with gr.Row():
            plot_press = gr.Plot()
            plot_power = gr.Plot()

        gr.Markdown("---")
        gr.Markdown("#### 📥 Instant Sensor Telemetry Validation (CSV Upload)")
        with gr.Row():
            file_sensor_upload = gr.File(label="Upload Sensor Telemetry CSV", file_types=[".csv"])
            btn_validate_sensor = gr.Button("Validate Schema & Quality", scale=1)

        out_validation_report = gr.Markdown()

        def update_charts(m_id, days):
            return create_sensor_timeseries_plots(m_id, int(days))

        def on_validate(file_obj):
            if not file_obj:
                return "⚠️ Please upload a CSV file to validate."
            try:
                df = pd.read_csv(file_obj.name)
                res = validate_dataset("sensor_readings", df)
                status_icon = "✅ VALID" if res["is_valid"] else "❌ INVALID"
                err_str = "<br/>".join([f"• {e}" for e in res["errors"]]) if res["errors"] else "None"
                warn_str = "<br/>".join([f"• {w}" for w in res["warnings"]]) if res["warnings"] else "None"

                return f"""
                ### Validation Summary: {status_icon}
                - **Total Rows Evaluated:** {res['row_count']}
                - **Schema Errors:** {len(res['errors'])}
                - **Data Quality Warnings:** {len(res['warnings'])}

                **Errors:**
                {err_str}

                **Warnings:**
                {warn_str}
                """
            except Exception as e:
                return f"❌ Failed to parse uploaded file: {str(e)}"

        btn_refresh_sensors.click(
            fn=update_charts,
            inputs=[dd_sensor_machine, dd_time_window],
            outputs=[plot_temp, plot_vib, plot_press, plot_power]
        )

        dd_sensor_machine.change(
            fn=update_charts,
            inputs=[dd_sensor_machine, dd_time_window],
            outputs=[plot_temp, plot_vib, plot_press, plot_power]
        )

        dd_time_window.change(
            fn=update_charts,
            inputs=[dd_sensor_machine, dd_time_window],
            outputs=[plot_temp, plot_vib, plot_press, plot_power]
        )

        btn_validate_sensor.click(
            fn=on_validate,
            inputs=[file_sensor_upload],
            outputs=[out_validation_report]
        )

    return {
        "dd_sensor_machine": dd_sensor_machine,
        "update_fn": update_charts,
    }
