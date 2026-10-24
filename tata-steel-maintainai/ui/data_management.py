"""
TAB 8 — Data Management and Telemetry Ingestion for TATA STEEL MAINTAINAI.
Validates uploaded CSV schemas, detects missing values and duplicates,
provides synthetic data generation, and handles database reset/export actions.
"""

import gradio as gr
import pandas as pd
from typing import Dict, Any

from src.data_ingestion import ingest_dataset_file, validate_dataset
from src.synthetic_data import seed_synthetic_data_into_db
from database.db import init_db, fetch_df
from src.reporting import export_dataframe_to_csv


def render_data_management_tab():
    """Construct Gradio layout for Tab 8 - Data Management."""
    with gr.Column():
        gr.Markdown("### 🗄️ Industrial Telemetry & Dataset Ingestion Pipeline")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### 📤 Upload Industrial CSV Dataset")
                dd_dataset_type = gr.Dropdown(
                    choices=[
                        ("Sensor Telemetry Readings", "sensor_readings"),
                        ("Historical Failure Records", "failure_history"),
                        ("Maintenance History Records", "maintenance_history"),
                        ("Production & Shutdown Schedules", "production_schedules"),
                    ],
                    value="sensor_readings",
                    label="Dataset Type"
                )
                rdo_mode = gr.Radio(
                    choices=[("Append to existing records", "append"), ("Replace / overwrite existing records", "replace")],
                    value="append",
                    label="Ingestion Mode"
                )
                file_upload = gr.File(label="Select CSV File", file_types=[".csv"])
                btn_ingest = gr.Button("Ingest & Validate into Database", elem_classes=["btn-primary"])

            with gr.Column(scale=1):
                gr.Markdown("#### 🔍 Real-Time Validation Report")
                validation_box = gr.Markdown("Upload a CSV file and click Ingest to validate schema, timestamps, and physical limits.")

        gr.Markdown("---")
        gr.Markdown("### ⚙️ Synthetic Data Generator & System Maintenance")

        with gr.Row():
            btn_gen_synthetic = gr.Button("🔄 Generate Fresh Synthetic Industrial Dataset", elem_classes=["btn-primary"], scale=2)
            btn_reset_db = gr.Button("⚠️ Reset Database to Clean Seed State", elem_classes=["btn-danger"], scale=1)

        sys_action_feedback = gr.Markdown()

        gr.Markdown("---")
        gr.Markdown("### 📥 Export Processed Operational Records")
        with gr.Row():
            btn_export_sensors = gr.Button("Export Sensor Telemetry (CSV)")
            btn_export_failures = gr.Button("Export Failure History (CSV)")
            btn_export_maintenance = gr.Button("Export Maintenance Records (CSV)")
            btn_export_schedules = gr.Button("Export Production Schedules (CSV)")

        file_export_download = gr.File(label="Download Exported CSV", visible=False)

        def on_ingest(file_obj, d_type, mode):
            if not file_obj:
                return "⚠️ Please upload a CSV file before running ingestion."

            res = ingest_dataset_file(dataset_type=d_type, file_content_or_path=file_obj.name, mode=mode, actor="Superintendent")
            if not res["success"]:
                errs = "<br/>".join([f"• {e}" for e in res.get("errors", [])])
                warns = "<br/>".join([f"• {w}" for w in res.get("warnings", [])])
                return f"""
                ### ❌ Ingestion Rejected: Schema / Validation Failure
                {res['message']}

                **Errors:**
                {errs}

                **Warnings:**
                {warns}
                """
            else:
                warns = "<br/>".join([f"• {w}" for w in res.get("warnings", [])]) if res.get("warnings") else "None (Clean schema)"
                return f"""
                ### ✅ Ingestion Completed Successfully
                - **Ingested Rows:** {res['row_count']}
                - **Target Table:** `{d_type}` (Mode: `{mode}`)

                **Data Quality Warnings:**
                {warns}
                """

        def on_gen_synthetic():
            counts = seed_synthetic_data_into_db()
            return f"""
            ✅ **Synthetic Generation Complete:**
            - **Sensor Telemetry:** {counts['sensor_readings']} records
            - **Failure Events:** {counts['failure_history']} events
            - **Maintenance Logs:** {counts['maintenance_history']} records
            - **Production Schedules:** {counts['production_schedules']} shifts
            All datasets saved to `data/sample/` and seeded into active SQLite database.
            """

        def on_reset():
            init_db(force_recreate=True)
            seed_synthetic_data_into_db()
            return "✅ **System Reset Complete:** Database recreated from `schema.sql`, default fleet registered, and initial telemetry seeded."

        def export_table(tbl, filename):
            df = fetch_df(f"SELECT * FROM {tbl};")
            path = export_dataframe_to_csv(df, filename)
            return gr.update(value=path, visible=True)

        btn_ingest.click(
            fn=on_ingest,
            inputs=[file_upload, dd_dataset_type, rdo_mode],
            outputs=[validation_box]
        )

        btn_gen_synthetic.click(
            fn=on_gen_synthetic,
            inputs=[],
            outputs=[sys_action_feedback]
        )

        btn_reset_db.click(
            fn=on_reset,
            inputs=[],
            outputs=[sys_action_feedback]
        )

        btn_export_sensors.click(
            fn=lambda: export_table("sensor_readings", "sensor_readings_export"),
            inputs=[],
            outputs=[file_export_download]
        )

        btn_export_failures.click(
            fn=lambda: export_table("failure_events", "failure_events_export"),
            inputs=[],
            outputs=[file_export_download]
        )

        btn_export_maintenance.click(
            fn=lambda: export_table("maintenance_records", "maintenance_records_export"),
            inputs=[],
            outputs=[file_export_download]
        )

        btn_export_schedules.click(
            fn=lambda: export_table("production_schedules", "production_schedules_export"),
            inputs=[],
            outputs=[file_export_download]
        )

    return {}
