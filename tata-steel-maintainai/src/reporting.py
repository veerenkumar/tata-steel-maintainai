"""
Reporting and Export Engine for TATA STEEL MAINTAINAI.
Generates CSV datasets and professionally styled industrial PDF reports
with executive KPIs, high-risk asset audits, recommendations, and scenario modeling.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from config.settings import EXPORTS_DIR, APP_TITLE, APP_SUBTITLE, PORTFOLIO_DISCLAIMER
from database.db import get_connection, log_audit
from src.prediction_engine import generate_fleet_predictions
from src.recommendation_engine import generate_fleet_recommendations
from src.business_impact import compute_business_impact_analysis


def export_dataframe_to_csv(df: pd.DataFrame, report_name: str) -> str:
    """Export any DataFrame to timestamped CSV file in exports/ folder."""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{report_name}_{ts_str}.csv"
    filepath = EXPORTS_DIR / filename
    df.to_csv(filepath, index=False)
    log_audit("REPORT_EXPORT_CSV", "exports", filename, details=f"Exported {len(df)} rows to {filename}")
    return str(filepath)


def generate_executive_pdf_report(horizon_hours: int = 72) -> str:
    """
    Generate a complete, executive-ready PDF report using ReportLab.
    Includes fleet health overview, high-risk assets, scheduled maintenance, and cost projections.
    """
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"MaintainAI_Executive_Report_{ts_str}.pdf"
    pdf_path = EXPORTS_DIR / pdf_filename

    # Fetch fresh operational data
    fleet_df = generate_fleet_predictions(horizon_hours=horizon_hours, persist=False)
    recs_df = generate_fleet_recommendations()
    impact = compute_business_impact_analysis()

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom palette: Slate Navy (#0f172a), Steel Blue (#0284c7), Molten Amber (#ea580c), Dark Text (#1e293b)
    c_primary = colors.HexColor("#0f172a")
    c_accent = colors.HexColor("#0284c7")
    c_warn = colors.HexColor("#ea580c")
    c_crit = colors.HexColor("#ef4444")
    c_light_bg = colors.HexColor("#f8fafc")
    c_border = colors.HexColor("#cbd5e1")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=c_primary,
        alignment=0,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=c_accent,
        alignment=0,
    )
    disclaimer_style = ParagraphStyle(
        "DocDisclaimer",
        parent=styles["Italic"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#64748b"),
    )
    section_h1 = ParagraphStyle(
        "SectionH1",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=c_primary,
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )
    tbl_hdr_style = ParagraphStyle(
        "TblHdr",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )
    tbl_cell_style = ParagraphStyle(
        "TblCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1e293b"),
    )

    story = []

    # 1. Header
    story.append(Paragraph(APP_TITLE, title_style))
    story.append(Paragraph(f"{APP_SUBTITLE} | Executive Maintenance Intelligence Briefing", subtitle_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | <b>Forecast Horizon:</b> {horizon_hours} Hours | <b>Status:</b> Active",
        body_style
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>LEGAL NOTICE:</b> {PORTFOLIO_DISCLAIMER}", disclaimer_style))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceBefore=2, spaceAfter=8))

    # 2. Executive Fleet Health KPIs
    story.append(Paragraph("1. EXECUTIVE FLEET HEALTH SUMMARY", section_h1))
    
    total_machines = len(fleet_df)
    crit_count = len(fleet_df[fleet_df["risk_category"] == "Critical Risk"])
    high_count = len(fleet_df[fleet_df["risk_category"] == "High Risk"])
    med_count = len(fleet_df[fleet_df["risk_category"] == "Medium Risk"])
    low_count = len(fleet_df[fleet_df["risk_category"] == "Low Risk"])
    anom_count = len(fleet_df[fleet_df["is_anomaly"] == "YES"])

    total_exposure = impact["modeled_scenarios"]["scenario_a_run_to_failure_cost"]
    net_savings = impact["modeled_scenarios"]["net_potential_savings"]
    roi = impact["modeled_scenarios"]["modeled_roi_pct"]

    kpi_data = [
        [
            Paragraph("<b>Monitored Assets</b>", tbl_cell_style),
            Paragraph("<b>Critical / High Risk</b>", tbl_cell_style),
            Paragraph("<b>Active Anomalies</b>", tbl_cell_style),
            Paragraph("<b>Total Failure Exposure</b>", tbl_cell_style),
            Paragraph("<b>Est. Net Savings</b>", tbl_cell_style),
            Paragraph("<b>Modeled ROI</b>", tbl_cell_style),
        ],
        [
            Paragraph(f"<font size=11><b>{total_machines}</b></font>", tbl_cell_style),
            Paragraph(f"<font size=11 color='red'><b>{crit_count + high_count}</b></font> ({crit_count} Crit, {high_count} High)", tbl_cell_style),
            Paragraph(f"<font size=11 color='orange'><b>{anom_count}</b></font>", tbl_cell_style),
            Paragraph(f"<font size=11><b>${total_exposure:,.0f}</b></font>", tbl_cell_style),
            Paragraph(f"<font size=11 color='green'><b>${net_savings:,.0f}</b></font>", tbl_cell_style),
            Paragraph(f"<font size=11 color='green'><b>{roi:.1f}%</b></font>", tbl_cell_style),
        ]
    ]
    t_kpi = Table(kpi_data, colWidths=[90, 95, 80, 95, 95, 85])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_light_bg),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 10))

    # 3. High-Risk Machinery Table
    story.append(Paragraph("2. HIGH-PRIORITY MACHINERY ASSET AUDIT", section_h1))
    top_risk = fleet_df.head(6)
    
    asset_headers = [
        Paragraph("<b>Machine ID</b>", tbl_hdr_style),
        Paragraph("<b>Equipment Type</b>", tbl_hdr_style),
        Paragraph("<b>Production Area</b>", tbl_hdr_style),
        Paragraph("<b>Failure Prob</b>", tbl_hdr_style),
        Paragraph("<b>Risk Score</b>", tbl_hdr_style),
        Paragraph("<b>Category</b>", tbl_hdr_style),
        Paragraph("<b>Expected Loss</b>", tbl_hdr_style),
    ]
    asset_rows = [asset_headers]
    for _, r in top_risk.iterrows():
        p_val = float(r['failure_probability'])
        cat = r['risk_category']
        cat_color = "red" if "Critical" in cat or "High" in cat else ("orange" if "Medium" in cat else "green")
        asset_rows.append([
            Paragraph(f"<b>{r['machine_id']}</b>", tbl_cell_style),
            Paragraph(r['equipment_type'][:22], tbl_cell_style),
            Paragraph(r['production_area'][:22], tbl_cell_style),
            Paragraph(f"{p_val*100:.1f}%", tbl_cell_style),
            Paragraph(f"{r['composite_risk_score']:.1f}", tbl_cell_style),
            Paragraph(f"<font color='{cat_color}'><b>{cat}</b></font>", tbl_cell_style),
            Paragraph(f"${r['expected_failure_loss']:,.0f}", tbl_cell_style),
        ])

    t_assets = Table(asset_rows, colWidths=[75, 105, 110, 60, 55, 65, 70])
    t_assets.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_assets)
    story.append(Spacer(1, 10))

    # 4. Recommended Actions
    story.append(Paragraph("3. PRIORITIZED PREVENTIVE MAINTENANCE RECOMMENDATIONS", section_h1))
    pending_recs = recs_df.head(4)
    rec_headers = [
        Paragraph("<b>Priority</b>", tbl_hdr_style),
        Paragraph("<b>Machine ID</b>", tbl_hdr_style),
        Paragraph("<b>Action Summary & Rationale</b>", tbl_hdr_style),
        Paragraph("<b>Target Window</b>", tbl_hdr_style),
        Paragraph("<b>Est. Cost</b>", tbl_hdr_style),
        Paragraph("<b>Status</b>", tbl_hdr_style),
    ]
    rec_rows = [rec_headers]
    for _, r in pending_recs.iterrows():
        prio_color = "red" if r['priority'] in ['Critical', 'High'] else "orange"
        rec_rows.append([
            Paragraph(f"<font color='{prio_color}'><b>{r['priority']}</b></font>", tbl_cell_style),
            Paragraph(f"<b>{r['machine_id']}</b>", tbl_cell_style),
            Paragraph(f"<b>Action:</b> {r['suggested_action'][:80]}...<br/><b>Reason:</b> {r['reason_for_recommendation'][:80]}", tbl_cell_style),
            Paragraph(r['suggested_maintenance_window'][:30], tbl_cell_style),
            Paragraph(f"${r['estimated_maintenance_cost']:,.0f}", tbl_cell_style),
            Paragraph(r['approval_status'], tbl_cell_style),
        ])

    t_recs = Table(rec_rows, colWidths=[55, 75, 185, 105, 60, 60])
    t_recs.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_accent),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_recs)
    story.append(Spacer(1, 10))

    # 5. Financial Cost Optimization & ROI
    story.append(Paragraph("4. BUSINESS IMPACT & FINANCIAL SCENARIO COMPARISON", section_h1))
    scenarios = impact["modeled_scenarios"]
    fin_data = [
        [
            Paragraph("<b>Scenario Metric</b>", tbl_hdr_style),
            Paragraph("<b>Scenario A (Run-to-Failure)</b>", tbl_hdr_style),
            Paragraph("<b>Scenario B (Planned PM)</b>", tbl_hdr_style),
            Paragraph("<b>Net Variance / Savings</b>", tbl_hdr_style),
        ],
        [
            Paragraph("Total Financial Exposure", tbl_cell_style),
            Paragraph(f"${scenarios['scenario_a_run_to_failure_cost']:,.2f}", tbl_cell_style),
            Paragraph(f"${scenarios['scenario_b_preventive_cost']:,.2f}", tbl_cell_style),
            Paragraph(f"<font color='green'><b>${scenarios['net_potential_savings']:,.2f}</b></font>", tbl_cell_style),
        ],
        [
            Paragraph("Fleet Availability Projection", tbl_cell_style),
            Paragraph(f"{impact['historical_metrics']['historical_fleet_availability_pct']:.2f}%", tbl_cell_style),
            Paragraph(f"{scenarios['projected_availability_pct']:.2f}%", tbl_cell_style),
            Paragraph(f"<font color='green'><b>+{scenarios['projected_availability_pct'] - impact['historical_metrics']['historical_fleet_availability_pct']:.2f}%</b></font>", tbl_cell_style),
        ],
        [
            Paragraph("Intervention Effectiveness Assumption", tbl_cell_style),
            Paragraph("0.0% (No Intervention)", tbl_cell_style),
            Paragraph(f"{scenarios['intervention_efficacy_pct']:.0f}% Risk Mitigation", tbl_cell_style),
            Paragraph("Target Parameter", tbl_cell_style),
        ],
    ]
    t_fin = Table(fin_data, colWidths=[160, 130, 130, 120])
    t_fin.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_fin)
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "<b>Summary Conclusion:</b> By shifting from reactive breakdown remediation to condition-based proactive maintenance "
        "synchronized with planned plant shutdowns, the operation preserves high capital equipment uptime while reducing "
        "emergency repair premiums and catastrophic molten steel production outages.",
        body_style
    ))

    # Build PDF
    doc.build(story)
    log_audit("REPORT_EXPORT_PDF", "exports", pdf_filename, details=f"Generated executive PDF report: {pdf_filename}")
    return str(pdf_path)
