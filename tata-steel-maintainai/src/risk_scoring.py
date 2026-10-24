"""
Machine Health and Risk Engine for TATA STEEL MAINTAINAI.
Calculates Expected Financial Failure Loss and transparent Composite Risk Scores.
Safety alarms and physical interlocks always take precedence over statistical model outputs.
"""

from typing import Dict, Any, Tuple, Optional
from config.settings import RISK_THRESHOLDS, EQUIPMENT_REFERENCE_RANGES


def calculate_expected_failure_cost(
    machine_meta: Dict[str, Any],
    scrap_exposure_pct: float = 0.15
) -> Dict[str, float]:
    """
    Calculate total estimated financial loss if an unexpected failure occurs:
    Total Cost = Repair Cost + (Expected Downtime Duration * Downtime Cost / Hour) + Scrap/Rework Loss
    """
    repair_cost = float(machine_meta.get("estimated_repair_cost", 25000.0))
    downtime_hours = float(machine_meta.get("expected_maintenance_duration_hours", 6.0))
    # Unplanned breakdown typically takes 2.0x longer to diagnose and repair than planned PM
    unplanned_downtime_hours = downtime_hours * 2.0
    downtime_rate = float(machine_meta.get("downtime_cost_per_hour", 15000.0))

    unplanned_downtime_cost = unplanned_downtime_hours * downtime_rate
    # Scrap and molten steel ladle freeze / line purge exposure
    scrap_exposure_cost = (repair_cost + unplanned_downtime_cost) * scrap_exposure_pct

    total_failure_cost = repair_cost + unplanned_downtime_cost + scrap_exposure_cost

    return {
        "repair_cost": round(repair_cost, 2),
        "unplanned_downtime_hours": round(unplanned_downtime_hours, 1),
        "unplanned_downtime_cost": round(unplanned_downtime_cost, 2),
        "scrap_exposure_cost": round(scrap_exposure_cost, 2),
        "total_failure_cost": round(total_failure_cost, 2),
    }


def compute_composite_risk(
    failure_prob: float,
    anomaly_score: float,
    criticality_str: str,
    sensor_critical_alarm: bool = False,
    machine_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compute transparent composite risk score (0-100) and Expected Failure Loss:
    Expected Failure Loss = Failure Probability * Total Failure Cost.
    Safety Alarms always take precedence over statistical model outputs.
    """
    failure_prob = float(max(0.0, min(1.0, failure_prob)))
    anomaly_score = float(max(0.0, min(1.0, anomaly_score)))

    # Criticality Component (25 points max)
    if "Tier 1" in criticality_str:
        crit_points = 25.0
    elif "Tier 2" in criticality_str:
        crit_points = 18.0
    elif "Tier 3" in criticality_str:
        crit_points = 11.0
    else:
        crit_points = 5.0

    # Probability Component (50 points max)
    prob_points = failure_prob * 50.0

    # Anomaly Component (25 points max)
    anom_points = anomaly_score * 25.0

    # Composite Score
    score = prob_points + anom_points + crit_points
    score = round(max(0.0, min(100.0, score)), 1)

    # Determine Risk Category
    if sensor_critical_alarm or failure_prob >= 0.80 or score >= 85.0:
        category = "Critical Risk"
        color = RISK_THRESHOLDS["critical"]["color"]
    elif failure_prob >= 0.55 or score >= 65.0:
        category = "High Risk"
        color = RISK_THRESHOLDS["high"]["color"]
    elif failure_prob >= 0.25 or score >= 35.0:
        category = "Medium Risk"
        color = RISK_THRESHOLDS["medium"]["color"]
    else:
        category = "Low Risk"
        color = RISK_THRESHOLDS["low"]["color"]

    # Calculate financial exposure
    meta = machine_meta or {}
    cost_breakdown = calculate_expected_failure_cost(meta)
    expected_failure_loss = round(failure_prob * cost_breakdown["total_failure_cost"], 2)

    return {
        "failure_probability": round(failure_prob, 4),
        "anomaly_score": round(anomaly_score, 4),
        "composite_risk_score": score,
        "risk_category": category,
        "risk_color": color,
        "expected_failure_loss": expected_failure_loss,
        "cost_breakdown": cost_breakdown,
        "sensor_alarm_override": sensor_critical_alarm,
    }
