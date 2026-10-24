"""
Explainable Maintenance Recommendation Agent for TATA STEEL MAINTAINAI.
Synthesizes ML failure predictions, physical sensor boundary excursions,
machine criticality, and maintenance history to formulate actionable recommendations.
Includes human approval, deferral, and rejection workflows with full audit persistence.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
import pandas as pd

from config.settings import (
    EQUIPMENT_REFERENCE_RANGES,
    SPARE_PARTS_CATALOG,
    PORTFOLIO_DISCLAIMER,
)
from database.db import get_connection, log_audit, execute_query, fetch_df
from src.prediction_engine import predict_machine_failure


def map_equipment_to_spare_parts(equipment_type: str) -> List[str]:
    """Identify recommended spare parts for this equipment category from catalog."""
    matching_parts = [
        f"{p['name']} ({p['part_id']})"
        for p in SPARE_PARTS_CATALOG
        if p["equipment_type"] == equipment_type
    ]
    return matching_parts if matching_parts else ["General Inspection Gasket & O-Ring Fastener Kit"]


def generate_recommendation_for_machine(
    machine_id: str,
    horizon_hours: int = 72,
    persist: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Evaluate machine risk and physical telemetry to generate a targeted maintenance recommendation.
    If machine is healthy with low risk and no sensor excursions, routine inspection is recommended.
    """
    pred = predict_machine_failure(machine_id, horizon_hours=horizon_hours, persist=False)
    fail_prob = pred["failure_probability"]
    risk_cat = pred["risk_category"]
    evidence_list = pred["sensor_evidence"]
    breakdown = pred["cost_breakdown"]

    with get_connection() as conn:
        m_df = pd.read_sql_query("SELECT * FROM machines WHERE machine_id = ?;", conn, params=(machine_id,))
        machine_meta = m_df.iloc[0].to_dict()

    eq_type = machine_meta["equipment_type"]
    crit_str = machine_meta["criticality"]
    maint_duration = float(machine_meta["expected_maintenance_duration_hours"])
    maint_cost = round(float(machine_meta["estimated_repair_cost"]) * 0.35, 2)  # PM costs ~35% of emergency repair
    potential_downtime_exposure = breakdown["unplanned_downtime_cost"]

    # Deduce appropriate action and reason based on evidence
    suggested_actions = []
    reasons = []

    vib_evidence = [e for e in evidence_list if e["sensor"] == "Vibration"]
    temp_evidence = [e for e in evidence_list if e["sensor"] == "Temperature"]
    press_evidence = [e for e in evidence_list if e["sensor"] == "Pressure"]
    curr_evidence = [e for e in evidence_list if e["sensor"] == "Electrical Current"]

    if vib_evidence:
        reasons.append(f"Vibration anomaly detected ({vib_evidence[0]['detail']}).")
        if "motor" in eq_type.lower() or "pump" in eq_type.lower():
            suggested_actions.append("Perform dynamic vibration FFT analysis; inspect drive-end bearings, foundation anchor bolts, and flexible coupling alignment.")
        elif "conveyor" in eq_type.lower():
            suggested_actions.append("Inspect conveyor drive pulley bearing blocks, take-up counterweight tensioning, and idler roller alignment.")
        elif "fan" in eq_type.lower() or "blower" in eq_type.lower():
            suggested_actions.append("Conduct dynamic balancing of impeller fan assembly; check casing wear plates and shaft runout.")
        elif "rolling" in eq_type.lower():
            suggested_actions.append("Inspect roll chock four-row cylindrical roller bearings and spindle universal joint clearances.")
        else:
            suggested_actions.append("Inspect mechanical bearings, shaft alignment, and structural mounting bolts.")

    if temp_evidence:
        reasons.append(f"Thermal excursion detected ({temp_evidence[0]['detail']}).")
        suggested_actions.append("Inspect forced-oil cooling circuit, heat exchanger tube cleanliness, lubrication viscosity, and RTD probe seating.")

    if press_evidence:
        reasons.append(f"Hydraulic/pneumatic pressure deviation detected ({press_evidence[0]['detail']}).")
        suggested_actions.append("Inspect proportional servo valves, hydraulic cylinder piston seals, accumulator pre-charge pressure, and line filter differential.")

    if curr_evidence:
        reasons.append(f"Motor current overload/fluctuations detected ({curr_evidence[0]['detail']}).")
        suggested_actions.append("Test stator insulation resistance (Megger test), verify 3-phase current balance, and inspect variable frequency drive (VFD) output.")

    # High predicted risk without specific sensor threshold breach (subtle multivariate deterioration)
    if not suggested_actions and fail_prob >= 0.40:
        reasons.append(f"Multivariate ML model flagged high failure likelihood ({fail_prob*100:.1f}%) within {horizon_hours}h.")
        suggested_actions.append("Schedule comprehensive non-destructive predictive inspection (ultrasonic acoustic lubrication test, thermography, and mechanical backlash audit).")

    # If asset is completely healthy
    if not suggested_actions:
        if fail_prob < 0.25 and risk_cat == "Low Risk":
            # Routine periodic check
            reasons.append("Telemetry operates within nominal baseline reference parameters.")
            suggested_actions.append("Maintain routine visual inspection and scheduled periodic lubrication interval.")
            priority = "Routine"
        else:
            reasons.append("Moderate statistical risk indicator.")
            suggested_actions.append("Conduct scheduled shift walkdown inspection and sensor recalibration.")
            priority = "Medium"
    else:
        if "Critical" in risk_cat or fail_prob >= 0.70 or any(e["severity"] == "CRITICAL" for e in evidence_list):
            priority = "Critical"
        elif "High" in risk_cat or fail_prob >= 0.45:
            priority = "High"
        else:
            priority = "Medium"

    reason_str = " ".join(reasons)
    action_str = " ".join(suggested_actions)
    matched_parts = map_equipment_to_spare_parts(eq_type)
    parts_str = ", ".join(matched_parts)

    rec_id = f"REC-{machine_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    suggested_window = "Next Available Planned Shutdown Window (Within 48h)" if priority in ["Critical", "High"] else "Next Regular Scheduled Maintenance Shift"

    recommendation = {
        "recommendation_id": rec_id,
        "machine_id": machine_id,
        "risk_category": risk_cat,
        "predicted_failure_probability": round(fail_prob, 4),
        "anomaly_evidence": "; ".join([e["detail"] for e in evidence_list]) if evidence_list else "None (Nominal Range)",
        "reason_for_recommendation": reason_str,
        "suggested_action": action_str,
        "priority": priority,
        "estimated_maintenance_duration": maint_duration,
        "estimated_maintenance_cost": maint_cost,
        "potential_downtime_exposure": potential_downtime_exposure,
        "suggested_maintenance_window": suggested_window,
        "required_parts": parts_str,
        "approval_status": "Pending",
        "approval_notes": "",
        "approved_by": "",
        "decision_timestamp": "",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    if persist:
        with get_connection() as conn:
            cursor = conn.cursor()
            # Do not create duplicate pending recommendations for same machine
            cursor.execute(
                "SELECT recommendation_id FROM maintenance_recommendations WHERE machine_id = ? AND approval_status = 'Pending';",
                (machine_id,)
            )
            existing = cursor.fetchone()
            if existing:
                # Update existing pending recommendation
                rec_id = existing[0]
                recommendation["recommendation_id"] = rec_id
                cursor.execute(
                    """
                    UPDATE maintenance_recommendations SET
                        risk_category = ?, predicted_failure_probability = ?,
                        anomaly_evidence = ?, reason_for_recommendation = ?,
                        suggested_action = ?, priority = ?,
                        estimated_maintenance_duration = ?, estimated_maintenance_cost = ?,
                        potential_downtime_exposure = ?, suggested_maintenance_window = ?,
                        required_parts = ?
                    WHERE recommendation_id = ?;
                    """,
                    (
                        recommendation["risk_category"],
                        recommendation["predicted_failure_probability"],
                        recommendation["anomaly_evidence"],
                        recommendation["reason_for_recommendation"],
                        recommendation["suggested_action"],
                        recommendation["priority"],
                        recommendation["estimated_maintenance_duration"],
                        recommendation["estimated_maintenance_cost"],
                        recommendation["potential_downtime_exposure"],
                        recommendation["suggested_maintenance_window"],
                        recommendation["required_parts"],
                        rec_id,
                    )
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO maintenance_recommendations (
                        recommendation_id, machine_id, risk_category,
                        predicted_failure_probability, anomaly_evidence,
                        reason_for_recommendation, suggested_action, priority,
                        estimated_maintenance_duration, estimated_maintenance_cost,
                        potential_downtime_exposure, suggested_maintenance_window,
                        required_parts, approval_status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        recommendation["recommendation_id"],
                        recommendation["machine_id"],
                        recommendation["risk_category"],
                        recommendation["predicted_failure_probability"],
                        recommendation["anomaly_evidence"],
                        recommendation["reason_for_recommendation"],
                        recommendation["suggested_action"],
                        recommendation["priority"],
                        recommendation["estimated_maintenance_duration"],
                        recommendation["estimated_maintenance_cost"],
                        recommendation["potential_downtime_exposure"],
                        recommendation["suggested_maintenance_window"],
                        recommendation["required_parts"],
                        "Pending",
                        recommendation["created_at"],
                    )
                )
            conn.commit()

    return recommendation


def generate_fleet_recommendations() -> pd.DataFrame:
    """Evaluate all machinery assets across the fleet and return recommendations table."""
    with get_connection() as conn:
        machines_df = pd.read_sql_query("SELECT machine_id FROM machines ORDER BY machine_id ASC;", conn)

    for _, row in machines_df.iterrows():
        generate_recommendation_for_machine(row["machine_id"], persist=True)

    with get_connection() as conn:
        recs_df = pd.read_sql_query(
            """
            SELECT r.*, m.production_area, m.equipment_type, m.criticality
            FROM maintenance_recommendations r
            JOIN machines m ON r.machine_id = m.machine_id
            ORDER BY
                CASE r.priority
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    ELSE 4
                END,
                r.predicted_failure_probability DESC;
            """,
            conn
        )

    log_audit("RECOMMENDATION_RUN", "maintenance_recommendations", "fleet", details=f"Generated {len(recs_df)} fleet recommendations.")
    return recs_df


def update_recommendation_decision(
    recommendation_id: str,
    decision: str,  # 'Approved', 'Rejected', 'Deferred'
    notes: str = "",
    decided_by: str = "Maintenance Manager"
) -> Dict[str, Any]:
    """
    Apply authorized human decision on a recommendation.
    Decision values: 'Approved', 'Rejected', 'Deferred'.
    """
    if decision not in ["Approved", "Rejected", "Deferred"]:
        return {"success": False, "message": f"Invalid decision: {decision}. Must be Approved, Rejected, or Deferred."}

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM maintenance_recommendations WHERE recommendation_id = ?;",
            (recommendation_id,)
        )
        row = cursor.fetchone()
        if not row:
            return {"success": False, "message": f"Recommendation ID '{recommendation_id}' not found."}

        prev_status = row["approval_status"]
        cursor.execute(
            """
            UPDATE maintenance_recommendations SET
                approval_status = ?,
                approval_notes = ?,
                approved_by = ?,
                decision_timestamp = ?
            WHERE recommendation_id = ?;
            """,
            (decision, notes, decided_by, now_str, recommendation_id)
        )
        conn.commit()

    log_audit(
        action_type="APPROVAL_DECISION",
        entity_type="maintenance_recommendations",
        entity_id=recommendation_id,
        actor=decided_by,
        details=f"Decision '{decision}'. Notes: {notes}",
        previous_state=prev_status,
        new_state=decision,
    )

    return {
        "success": True,
        "message": f"Recommendation {recommendation_id} successfully marked as '{decision}'.",
        "recommendation_id": recommendation_id,
        "status": decision,
    }
