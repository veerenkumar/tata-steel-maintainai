"""
Anomaly Detection Engine for TATA STEEL MAINTAINAI.
Utilizes Isolation Forest trained on healthy baseline regimes
and evaluates sensor deviations against machine-specific reference ranges.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from sklearn.ensemble import IsolationForest
import joblib

from config.settings import (
    EQUIPMENT_REFERENCE_RANGES,
    ANOMALY_CONTAMINATION,
    RANDOM_SEED,
    MODELS_DIR,
)
from database.db import get_connection, log_audit, execute_query


class IndustrialAnomalyDetector:
    """
    Unsupervised Isolation Forest detector for equipment sensor telemetry.
    Distinguishes unexplained telemetry drift from supervised failure probabilities.
    """

    def __init__(self, contamination: float = ANOMALY_CONTAMINATION):
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            random_state=RANDOM_SEED,
            n_estimators=100,
            max_samples="auto"
        )
        self.features = [
            "temperature", "vibration", "pressure",
            "rotational_speed", "electrical_current", "operating_load"
        ]
        self.is_fitted = False

    def fit(self, healthy_df: pd.DataFrame) -> "IndustrialAnomalyDetector":
        """Fit Isolation Forest on healthy operating observations."""
        if healthy_df.empty or len(healthy_df) < 30:
            return self

        X = healthy_df[self.features].dropna().values
        self.model.fit(X)
        self.is_fitted = True
        return self

    def score_readings(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute anomaly flags (-1 = anomaly, 1 = normal) and continuous scores.
        Score is inverted so higher positive value represents higher anomalousness (0.0 to 1.0).
        """
        if not self.is_fitted or df.empty:
            # Fallback heuristic if not fitted
            return np.zeros(len(df), dtype=int), np.zeros(len(df), dtype=float)

        X = df[self.features].fillna(0.0).values
        raw_preds = self.model.predict(X)  # -1 for anomaly, 1 for normal
        raw_scores = self.model.decision_function(X)  # lower = more anomalous

        # Normalize score to 0..1 range (higher = more anomalous)
        # decision_function typically ranges from -0.3 to +0.3
        norm_scores = np.clip(0.5 - (raw_scores * 1.5), 0.0, 1.0)
        anomaly_flags = (raw_preds == -1).astype(int)

        return anomaly_flags, np.round(norm_scores, 4)


def detect_sensor_evidence(
    sensor_row: Dict[str, Any],
    equipment_type: str
) -> List[Dict[str, Any]]:
    """
    Evaluate which individual sensors exceed machine-specific operational reference ranges.
    Returns list of specific abnormal observations with severity and physical deviations.
    """
    ranges = EQUIPMENT_REFERENCE_RANGES.get(equipment_type, EQUIPMENT_REFERENCE_RANGES["Industrial motors"])
    evidence = []

    # 1. Temperature check
    temp = float(sensor_row.get("temperature", 0.0))
    t_cfg = ranges["temperature"]
    if temp > t_cfg["crit_max"]:
        evidence.append({
            "sensor": "Temperature",
            "value": temp,
            "unit": "°C",
            "severity": "CRITICAL",
            "limit": t_cfg["crit_max"],
            "detail": f"Severe thermal buildup: {temp}°C exceeds critical limit of {t_cfg['crit_max']}°C.",
        })
    elif temp > t_cfg["warn_max"]:
        evidence.append({
            "sensor": "Temperature",
            "value": temp,
            "unit": "°C",
            "severity": "WARNING",
            "limit": t_cfg["warn_max"],
            "detail": f"Elevated temperature: {temp}°C exceeds warning threshold of {t_cfg['warn_max']}°C.",
        })

    # 2. Vibration check
    vib = float(sensor_row.get("vibration", 0.0))
    v_cfg = ranges["vibration"]
    if vib > v_cfg["crit_max"]:
        evidence.append({
            "sensor": "Vibration",
            "value": vib,
            "unit": "RMS mm/s",
            "severity": "CRITICAL",
            "limit": v_cfg["crit_max"],
            "detail": f"Critical mechanical vibration: {vib} mm/s breaches ISO limit ({v_cfg['crit_max']} mm/s).",
        })
    elif vib > v_cfg["warn_max"]:
        evidence.append({
            "sensor": "Vibration",
            "value": vib,
            "unit": "RMS mm/s",
            "severity": "WARNING",
            "limit": v_cfg["warn_max"],
            "detail": f"Elevated vibration: {vib} mm/s exceeds operational warning boundary ({v_cfg['warn_max']} mm/s).",
        })

    # 3. Pressure check
    press = float(sensor_row.get("pressure", 0.0))
    p_cfg = ranges["pressure"]
    p_warn_min = p_cfg.get("warn_min", p_cfg["normal_min"] * 0.7)
    p_warn_max = p_cfg.get("warn_max", p_cfg["normal_max"] * 1.3)
    p_crit_max = p_cfg.get("crit_max", p_cfg["normal_max"] * 1.6)

    if press > p_crit_max:
        evidence.append({
            "sensor": "Pressure",
            "value": press,
            "unit": "bar",
            "severity": "CRITICAL",
            "limit": p_crit_max,
            "detail": f"Hydraulic/pneumatic overpressure: {press} bar exceeds {p_crit_max} bar.",
        })
    elif press < p_warn_min and press > 0.1:
        evidence.append({
            "sensor": "Pressure",
            "value": press,
            "unit": "bar",
            "severity": "WARNING",
            "limit": p_warn_min,
            "detail": f"Sub-nominal pressure drop: {press} bar below safe minimum of {p_warn_min} bar (possible line breach/cavitation).",
        })

    # 4. Electrical Current check
    curr = float(sensor_row.get("electrical_current", 0.0))
    c_cfg = ranges["electrical_current"]
    if curr > c_cfg["crit_max"]:
        evidence.append({
            "sensor": "Electrical Current",
            "value": curr,
            "unit": "A",
            "severity": "CRITICAL",
            "limit": c_cfg["crit_max"],
            "detail": f"Motor current surge: {curr} A exceeds maximum winding rating ({c_cfg['crit_max']} A).",
        })
    elif curr > c_cfg["warn_max"]:
        evidence.append({
            "sensor": "Electrical Current",
            "value": curr,
            "unit": "A",
            "severity": "WARNING",
            "limit": c_cfg["warn_max"],
            "detail": f"Sustained electrical current overload: {curr} A exceeds normal rating ({c_cfg['warn_max']} A).",
        })

    return evidence


def run_fleet_anomaly_scan() -> Dict[str, Any]:
    """
    Fit anomaly detector on fleet baseline readings and update SQLite sensor_readings table.
    Returns summary of anomalies identified across fleet.
    """
    with get_connection() as conn:
        sensor_df = pd.read_sql_query("SELECT * FROM sensor_readings ORDER BY timestamp ASC;", conn)
        machines_df = pd.read_sql_query("SELECT * FROM machines;", conn)

    if sensor_df.empty:
        return {"total_scanned": 0, "anomalies_found": 0, "recent_anomalies": []}

    # Filter healthy baseline (early 50% of timeline where machines operated normally)
    mid_idx = int(len(sensor_df) * 0.5)
    healthy_baseline = sensor_df.iloc[:mid_idx]

    detector = IndustrialAnomalyDetector(contamination=ANOMALY_CONTAMINATION)
    detector.fit(healthy_baseline)

    flags, scores = detector.score_readings(sensor_df)
    sensor_df["is_anomaly"] = flags
    sensor_df["anomaly_score"] = scores

    # Batch update database with anomaly flags
    records_to_update = list(zip(flags.tolist(), scores.tolist(), sensor_df["id"].tolist()))

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            "UPDATE sensor_readings SET is_anomaly = ?, anomaly_score = ? WHERE id = ?;",
            records_to_update
        )
        conn.commit()

    # Save fitted detector
    detector_path = MODELS_DIR / "isolation_forest.joblib"
    joblib.dump(detector, detector_path)

    # Compile recent anomalies (last 48 hours of timeline)
    max_ts = pd.to_datetime(sensor_df["timestamp"].max())
    recent_cutoff = (max_ts - pd.Timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")

    recent_anom_df = sensor_df[
        (sensor_df["is_anomaly"] == 1) & (sensor_df["timestamp"] >= recent_cutoff)
    ].sort_values(by="anomaly_score", ascending=False)

    recent_anomalies = []
    machines_dict = {r["machine_id"]: r["equipment_type"] for _, r in machines_df.iterrows()}

    for _, row in recent_anom_df.head(20).iterrows():
        m_id = row["machine_id"]
        eq_type = machines_dict.get(m_id, "Industrial motors")
        ev = detect_sensor_evidence(row.to_dict(), eq_type)
        ev_summary = "; ".join([e["detail"] for e in ev]) if ev else "Statistical multi-sensor multivariate drift."
        recent_anomalies.append({
            "timestamp": row["timestamp"],
            "machine_id": m_id,
            "equipment_type": eq_type,
            "anomaly_score": round(float(row["anomaly_score"]), 3),
            "temperature": row["temperature"],
            "vibration": row["vibration"],
            "pressure": row["pressure"],
            "electrical_current": row["electrical_current"],
            "evidence": ev_summary,
        })

    log_audit(
        "ANOMALY_SCAN",
        "sensor_readings",
        "fleet",
        details=f"Scanned {len(sensor_df)} readings. Detected {int(flags.sum())} anomalous readings. Recent 48h anomalies: {len(recent_anom_df)}"
    )

    return {
        "total_scanned": len(sensor_df),
        "anomalies_found": int(flags.sum()),
        "recent_anomalies_count": len(recent_anom_df),
        "recent_anomalies": recent_anomalies,
    }
