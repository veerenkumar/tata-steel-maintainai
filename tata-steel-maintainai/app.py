"""
TATA STEEL MAINTAINAI — Main Application
AI-Powered Predictive Maintenance and Industrial Asset Intelligence Platform.
Primary Frontend: Gradio Blocks
"""

import sys
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import gradio as gr
import logging

from config.settings import APP_TITLE, APP_SUBTITLE, PORTFOLIO_DISCLAIMER
from database.db import init_db, fetch_df
from src.synthetic_data import seed_synthetic_data_into_db
from src.train_model import load_active_model
from ui.styles import CUSTOM_CSS

from ui.dashboard import render_dashboard_tab
from ui.machine_fleet import render_machine_fleet_tab
from ui.failure_predictions import render_failure_predictions_tab
from ui.sensor_analytics import render_sensor_analytics_tab
from ui.maintenance_advisor import render_maintenance_advisor_tab
from ui.maintenance_planner import render_maintenance_planner_tab
from ui.business_impact import render_business_impact_tab
from ui.data_management import render_data_management_tab
from ui.model_lab import render_model_lab_tab
from ui.work_orders import render_work_orders_tab

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("MaintainAI")


def initialize_app_state():
    """Ensure database schema is created, initial telemetry is seeded, and active model is trained."""
    logger.info("Initializing TATA STEEL MAINTAINAI application state...")
    init_db(force_recreate=False)

    # Check if sensor telemetry exists; if not, seed synthetic data
    sensor_count_df = fetch_df("SELECT COUNT(*) as count FROM sensor_readings;")
    if sensor_count_df.empty or sensor_count_df.iloc[0]["count"] < 100:
        logger.info("Seeding initial synthetic telemetry and schedules...")
        seed_synthetic_data_into_db()

    # Ensure model is ready
    load_active_model(horizon_hours=72)
    logger.info("Application state ready.")


def build_app() -> gr.Blocks:
    """Construct full 10-tab industrial intelligence dashboard with Gradio Blocks."""
    initialize_app_state()

    theme = gr.themes.Base(
        primary_hue="sky",
        secondary_hue="slate",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("Inter"), "sans-serif"],
        font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "monospace"],
    ).set(
        body_background_fill="#0b1120",
        body_background_fill_dark="#0b1120",
        block_background_fill="#1e293b",
        block_background_fill_dark="#1e293b",
        block_border_color="#334155",
        block_border_color_dark="#334155",
        input_background_fill="#0f172a",
        input_background_fill_dark="#0f172a",
        input_border_color="#334155",
        input_border_color_dark="#334155",
    )

    with gr.Blocks(title=f"{APP_TITLE} | Asset Intelligence") as demo:
        # Header Banner
        gr.HTML(
            f"""
            <div class="steel-header">
                <h1>
                    <span>🔥</span>
                    <span>{APP_TITLE}</span>
                    <span style="font-size: 14px; font-weight: 500; background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid #38bdf8; padding: 2px 10px; border-radius: 9999px;">
                        Enterprise Predictive Maintenance
                    </span>
                </h1>
                <p class="subtitle">{APP_SUBTITLE}</p>
                <div class="disclaimer-banner">
                    <b>OPERATIONAL DISCLAIMER:</b> {PORTFOLIO_DISCLAIMER}
                </div>
            </div>
            """
        )

        with gr.Tabs(elem_classes=["tabs"]):
            with gr.Tab("📊 Executive Overview", id="tab_overview"):
                dash_components = render_dashboard_tab()

            with gr.Tab("🏭 Machine Fleet", id="tab_fleet"):
                fleet_components = render_machine_fleet_tab()

            with gr.Tab("🔮 Failure Predictions", id="tab_predictions"):
                pred_components = render_failure_predictions_tab()

            with gr.Tab("📈 Sensor Analytics", id="tab_sensors"):
                sensor_components = render_sensor_analytics_tab()

            with gr.Tab("🛡️ Maintenance Advisor", id="tab_advisor"):
                advisor_components = render_maintenance_advisor_tab()

            with gr.Tab("📅 Maintenance Planner", id="tab_planner"):
                planner_components = render_maintenance_planner_tab()

            with gr.Tab("💰 Business Impact", id="tab_impact"):
                impact_components = render_business_impact_tab()

            with gr.Tab("🗄️ Data Management", id="tab_data"):
                render_data_management_tab()

            with gr.Tab("🔬 Model Lab", id="tab_model_lab"):
                lab_components = render_model_lab_tab()

            with gr.Tab("🛠️ Work Orders & Audit", id="tab_work_orders"):
                wo_components = render_work_orders_tab()

        # Initial trigger on launch to populate overview and tables
        demo.load(
            fn=dash_components["refresh_fn"],
            inputs=[],
            outputs=[
                dash_components["kpi_display"],
                dash_components["chart_risk_donut"],
                dash_components["chart_area_bars"],
                dash_components["chart_cost_compare"],
                dash_components["chart_hist_downtime"],
            ]
        )

        demo.load(
            fn=fleet_components["load_fn"],
            inputs=[],
            outputs=[
                fleet_components["tbl_fleet"],
                fleet_components["inspector_html"],
            ]
        )

    demo.theme = theme
    demo.css = CUSTOM_CSS
    return demo


if __name__ == "__main__":
    demo = build_app()
    demo.launch(theme=demo.theme, css=demo.css, server_name="127.0.0.1", server_port=7860, share=False)
