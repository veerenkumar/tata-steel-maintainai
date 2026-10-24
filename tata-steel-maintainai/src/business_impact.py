"""
Business Impact and Cost Optimization Engine for TATA STEEL MAINTAINAI.
Quantifies downtime exposure, scenario comparisons (Run-to-Failure vs Preventive Intervention),
potential financial savings, equipment availability, and sensitivity analysis.
All financial outputs are labeled as modeled estimates based on explicit operational parameters.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from database.db import get_connection, fetch_df
from src.prediction_engine import generate_fleet_predictions
from src.recommendation_engine import generate_fleet_recommendations


def compute_business_impact_analysis(
    intervention_efficacy_pct: float = 90.0,
    downtime_cost_multiplier: float = 1.0,
    pm_cost_multiplier: float = 1.0
) -> Dict[str, Any]:
    """
    Perform financial scenario analysis comparing:
    Scenario A (Run-to-Failure baseline): No intervention; absorb expected breakdown losses.
    Scenario B (Preventive Maintenance): Execute planned maintenance in scheduled windows.
    """
    with get_connection() as conn:
        machines_df = pd.read_sql_query("SELECT * FROM machines;", conn)
        failures_df = pd.read_sql_query("SELECT * FROM failure_events;", conn)
        maint_df = pd.read_sql_query("SELECT * FROM maintenance_records;", conn)

    # 1. Historical Actuals
    hist_failures_count = len(failures_df)
    hist_downtime_hours = float(failures_df["downtime_duration"].sum()) if not failures_df.empty else 0.0
    hist_repair_expenses = float(failures_df["repair_expense"].sum()) if not failures_df.empty else 0.0
    hist_pm_expenses = float(maint_df["maintenance_cost"].sum()) if not maint_df.empty else 0.0
    total_hist_maintenance_cost = hist_repair_expenses + hist_pm_expenses

    # Historical fleet availability
    total_fleet_op_hours = float(machines_df["operating_hours"].sum())
    total_recorded_hours = total_fleet_op_hours + hist_downtime_hours
    historical_availability_pct = round(
        (total_fleet_op_hours / max(1.0, total_recorded_hours)) * 100.0, 2
    )

    # 2. Predictive Scenario Calculations for Current Fleet
    fleet_preds = generate_fleet_predictions(horizon_hours=72, persist=False)
    recs_df = generate_fleet_recommendations()

    # Machine metadata lookup
    meta_map = {r["machine_id"]: r for _, r in machines_df.iterrows()}

    scenario_a_total_exposure = 0.0
    scenario_b_total_cost = 0.0
    machine_breakdowns = []

    efficacy_rate = max(0.01, min(0.99, intervention_efficacy_pct / 100.0))

    for _, pred_row in fleet_preds.iterrows():
        m_id = pred_row["machine_id"]
        m_meta = meta_map.get(m_id, {})
        fail_prob = float(pred_row["failure_probability"])

        repair_cost = float(m_meta.get("estimated_repair_cost", 25000.0))
        downtime_rate = float(m_meta.get("downtime_cost_per_hour", 12000.0)) * downtime_cost_multiplier
        unplanned_dt_hrs = float(m_meta.get("expected_maintenance_duration_hours", 6.0)) * 2.0
        scrap_cost = (repair_cost + (unplanned_dt_hrs * downtime_rate)) * 0.15

        single_failure_total_loss = repair_cost + (unplanned_dt_hrs * downtime_rate) + scrap_cost
        # Scenario A Expected Failure Loss
        scenario_a_loss = fail_prob * single_failure_total_loss
        scenario_a_total_exposure += scenario_a_loss

        # Scenario B Planned PM Cost
        pm_hrs = float(m_meta.get("expected_maintenance_duration_hours", 6.0))
        # If scheduled in shutdown window, production downtime loss = $0. If active shift, slight derating
        planned_pm_parts_labor = (repair_cost * 0.35) * pm_cost_multiplier
        planned_pm_downtime_loss = (pm_hrs * downtime_rate * 0.20)  # Planned window minimizes disruption by ~80%
        planned_pm_total = planned_pm_parts_labor + planned_pm_downtime_loss

        # Residual risk after maintenance
        residual_failure_risk = scenario_a_loss * (1.0 - efficacy_rate)

        # Only intervene if asset has meaningful failure risk (fail_prob > 0.15)
        if fail_prob > 0.15:
            scenario_b_cost = planned_pm_total + residual_failure_risk
            net_machine_savings = scenario_a_loss - scenario_b_cost
            action_recommended = "Execute Preventive Intervention"
        else:
            scenario_b_cost = scenario_a_loss
            net_machine_savings = 0.0
            action_recommended = "Continue Monitored Run (Low Risk)"

        scenario_b_total_cost += scenario_b_cost

        machine_breakdowns.append({
            "machine_id": m_id,
            "equipment_type": pred_row["equipment_type"],
            "failure_probability": round(fail_prob, 4),
            "risk_category": pred_row["risk_category"],
            "scenario_a_exposure": round(scenario_a_loss, 2),
            "scenario_b_cost": round(scenario_b_cost, 2),
            "net_potential_savings": round(net_machine_savings, 2),
            "recommended_strategy": action_recommended,
        })

    net_potential_savings = max(0.0, scenario_a_total_exposure - scenario_b_total_cost)
    roi_pct = round((net_potential_savings / max(1.0, scenario_b_total_cost)) * 100.0, 1)

    # Modeled improved availability
    avoided_downtime_hours = (hist_downtime_hours * 0.45) * efficacy_rate
    projected_availability_pct = round(
        (total_fleet_op_hours / max(1.0, total_recorded_hours - avoided_downtime_hours)) * 100.0, 2
    )

    return {
        "status": "VALID",
        "historical_metrics": {
            "unplanned_failures_count": hist_failures_count,
            "total_unplanned_downtime_hours": hist_downtime_hours,
            "total_repair_expenses": hist_repair_expenses,
            "total_preventive_expenses": hist_pm_expenses,
            "total_maintenance_expenditure": total_hist_maintenance_cost,
            "historical_fleet_availability_pct": historical_availability_pct,
        },
        "modeled_scenarios": {
            "scenario_a_run_to_failure_cost": round(scenario_a_total_exposure, 2),
            "scenario_b_preventive_cost": round(scenario_b_total_cost, 2),
            "net_potential_savings": round(net_potential_savings, 2),
            "modeled_roi_pct": roi_pct,
            "projected_availability_pct": projected_availability_pct,
            "intervention_efficacy_pct": intervention_efficacy_pct,
            "downtime_cost_multiplier": downtime_cost_multiplier,
            "pm_cost_multiplier": pm_cost_multiplier,
        },
        "machine_breakdowns": machine_breakdowns,
        "disclaimer": (
            "NOTICE: All scenario calculations are modeled financial projections based on statistical failure "
            "propensities, assumed labor rates, and user sensitivity multipliers. They represent estimated potential "
            "risk mitigation, not verified financial savings achieved."
        ),
    }
