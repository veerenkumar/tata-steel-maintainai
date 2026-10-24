"""
Inference and Failure Prediction Engine for TATA STEEL MAINTAINAI.
Executes calibrated model inference, feature contribution explanations,
risk calculation, and database persistence.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from config.settings import (
    DEFAULT_PREDICTION_HORIZON_HOURS,
    PORTFOLIO_DISCLAIMER,
)
from database.db import get_connection, log_audit, execute_query
from src.train_model import load_active_model
from src.feature_engineering import (
    extract_features_from_telemetry,
    FEATURE_COLUMNS,
)
from src.risk_scoring import compute_composite_risk
from src.anomaly_detection import detect_sensor_evidence


def predict_machine_failure(
    machine_id: str,
    horizon_hours: int = DEFAULT_PREDICTION_HORIZON_HOURS,
    persist: bool = True
) -> Dict[str, Any]:
    """
    Generate failure prediction for a specific machinery asset based on latest telemetry snapshot.
    """
    bundle = load_active_model(horizon_hours=horizon_hours)
    model = bundle["model"]
    feature_cols = bundle.get("feature_columns", FEATURE_COLUMNS)
    version_id = bundle.get("version_id", "RF-DEFAULT")

    with get_connection() as conn:
        m_df = pd.read_sql_query("SELECT * FROM machines WHERE machine_id = ?;", conn, params=(machine_id,))
        if m_df.empty:
            raise ValueError(f"Machine ID '{machine_id}' not found in registry.")
        machine_meta = m_df.iloc[0].to_dict()

        sensor_df = pd.read_sql_query(
            "SELECT * FROM sensor_readings WHERE machine_id = ? ORDER BY timestamp ASC;",
            conn,
            params=(machine_id,)
        )
        failures_df = pd.read_sql_query(
            "SELECT * FROM failure_events WHERE machine_id = ? ORDER BY failure_timestamp ASC;",
            conn,
            params=(machine_id,)
        )
        maintenance_df = pd.read_sql_query(
            "SELECT * FROM maintenance_records WHERE machine_id = ? ORDER BY maintenance_date ASC;",
            conn,
            params=(machine_id,)
        )

    if sensor_df.empty:
        raise ValueError(f"No sensor readings recorded for machine {machine_id}.")

    # Extract physics-guided features
    feat_df = extract_features_from_telemetry(
        sensor_df=sensor_df,
        machine_meta=machine_meta,
        maint_df=maintenance_df,
        fail_df=failures_df,
    )

    if feat_df.empty:
        raise ValueError(f"Unable to extract feature vector for machine {machine_id}.")

    latest_row = feat_df.iloc[-1]
    X_latest = pd.DataFrame([latest_row[feature_cols]])

    # Predict failure probability
    probs = model.predict_proba(X_latest)[0]
    fail_prob = float(probs[1]) if len(probs) > 1 else float(probs[0])

    # Anomaly status from latest sensor reading
    is_anomaly = int(latest_row.get("is_anomaly", 0))
    anomaly_score = float(latest_row.get("anomaly_score", 0.0))

    # Check physical sensor limits for critical safety alarm
    sensor_evidence = detect_sensor_evidence(latest_row.to_dict(), machine_meta["equipment_type"])
    has_crit_alarm = any(e["severity"] == "CRITICAL" for e in sensor_evidence)

    # Compute risk score and loss
    risk_info = compute_composite_risk(
        failure_prob=fail_prob,
        anomaly_score=anomaly_score,
        criticality_str=machine_meta["criticality"],
        sensor_critical_alarm=has_crit_alarm,
        machine_meta=machine_meta,
    )

    # Determine top contributing features
    feature_importances = bundle.get("feature_importances", {})
    contributing_drivers = []
    for col in feature_cols:
        val = float(latest_row[col])
        imp = feature_importances.get(col, 0.0)
        contributing_drivers.append({
            "feature": col,
            "value": round(val, 2),
            "importance": imp,
        })
    # Sort by feature importance
    contributing_drivers = sorted(contributing_drivers, key=lambda x: x["importance"], reverse=True)[:5]

    # Generate explanatory rationale
    reasons = []
    if has_crit_alarm:
        crit_details = [e["detail"] for e in sensor_evidence if e["severity"] == "CRITICAL"]
        reasons.append(f"PHYSICAL SAFETY ALARM: {'; '.join(crit_details)}")
    if fail_prob >= 0.5:
        reasons.append(
            f"Supervised ML model predicts high failure likelihood ({fail_prob*100:.1f}%) within the next {horizon_hours} hours."
        )
    if is_anomaly:
        reasons.append(f"Isolation Forest flagged multivariate telemetry anomaly (Score: {anomaly_score:.2f}).")
    if latest_row.get("vib_abnormality_ratio", 1.0) > 1.3:
        reasons.append(f"Vibration is {latest_row['vib_abnormality_ratio']:.1f}x higher than standard operational reference.")
    if latest_row.get("temp_trend_24h", 0.0) > 5.0:
        reasons.append(f"Thermal buildup detected: temperature climbed {latest_row['temp_trend_24h']:.1f}°C in past 24 hours.")
    if not reasons:
        reasons.append("Machine telemetry conforms to normal healthy operating limits.")

    explanation_str = " | ".join(reasons)

    pred_record = {
        "prediction_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "machine_id": machine_id,
        "forecast_horizon_hours": horizon_hours,
        "failure_probability": round(fail_prob, 4),
        "risk_category": risk_info["risk_category"],
        "composite_risk_score": risk_info["composite_risk_score"],
        "expected_failure_loss": risk_info["expected_failure_loss"],
        "is_anomaly": is_anomaly,
        "anomaly_score": round(anomaly_score, 4),
        "top_contributing_features": json.dumps(contributing_drivers),
        "model_version": version_id,
        "limitations_disclaimer": (
            "Predicted probability represents statistical failure likelihood based on current sensor signatures. "
            "It is not a guarantee of mechanical breakdown. Certified technician inspection is mandatory."
        ),
        "explanation": explanation_str,
        "sensor_evidence": sensor_evidence,
        "cost_breakdown": risk_info["cost_breakdown"],
    }

    if persist:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO predictions (
                    prediction_timestamp, machine_id, forecast_horizon_hours,
                    failure_probability, risk_category, composite_risk_score,
                    expected_failure_loss, is_anomaly, anomaly_score,
                    top_contributing_features, model_version, limitations_disclaimer
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    pred_record["prediction_timestamp"],
                    machine_id,
                    horizon_hours,
                    pred_record["failure_probability"],
                    pred_record["risk_category"],
                    pred_record["composite_risk_score"],
                    pred_record["expected_failure_loss"],
                    pred_record["is_anomaly"],
                    pred_record["anomaly_score"],
                    pred_record["top_contributing_features"],
                    version_id,
                    pred_record["limitations_disclaimer"],
                )
            )
            conn.commit()

    return pred_record


def generate_fleet_predictions(
    horizon_hours: int = DEFAULT_PREDICTION_HORIZON_HOURS,
    persist: bool = True
) -> pd.DataFrame:
    """
    Generate inference predictions for all registered machines across the fleet.
    Returns DataFrame ranked by composite risk score.
    """
    with get_connection() as conn:
        machines_df = pd.read_sql_query("SELECT * FROM machines ORDER BY machine_id ASC;", conn)

    results = []
    for _, m_row in machines_df.iterrows():
        m_id = m_row["machine_id"]
        try:
            pred = predict_machine_failure(m_id, horizon_hours=horizon_hours, persist=persist)
            results.append({
                "machine_id": m_id,
                "equipment_type": m_row["equipment_type"],
                "production_area": m_row["production_area"],
                "criticality": m_row["criticality"],
                "operating_status": m_row["operating_status"],
                "failure_probability": pred["failure_probability"],
                "risk_category": pred["risk_category"],
                "composite_risk_score": pred["composite_risk_score"],
                "expected_failure_loss": pred["expected_failure_loss"],
                "is_anomaly": "YES" if pred["is_anomaly"] else "NO",
                "explanation": pred["explanation"],
                "last_maintenance_date": m_row["last_maintenance_date"],
            })
        except Exception as e:
            results.append({
                "machine_id": m_id,
                "equipment_type": m_row["equipment_type"],
                "production_area": m_row["production_area"],
                "criticality": m_row["criticality"],
                "operating_status": m_row["operating_status"],
                "failure_probability": 0.05,
                "risk_category": "Low Risk",
                "composite_risk_score": 15.0,
                "expected_failure_loss": 1500.0,
                "is_anomaly": "NO",
                "explanation": f"Evaluation error: {str(e)}",
                "last_maintenance_date": m_row["last_maintenance_date"],
            })

    fleet_preds_df = pd.DataFrame(results)
    fleet_preds_df = fleet_preds_df.sort_values(by="composite_risk_score", ascending=False).reset_index(drop=True)

    log_audit(
        "PREDICTION_RUN",
        "predictions",
        "fleet",
        details=f"Ran {horizon_hours}h failure prediction for {len(fleet_preds_df)} machines."
    )

    return fleet_preds_df
