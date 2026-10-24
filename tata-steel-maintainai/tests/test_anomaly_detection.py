"""
Automated unit tests for Isolation Forest anomaly detection and sensor limits.
"""

import pytest
import pandas as pd
import numpy as np

from src.anomaly_detection import IndustrialAnomalyDetector, detect_sensor_evidence


def test_isolation_forest_scoring():
    """Verify Isolation Forest flags abnormal multivariate observations."""
    detector = IndustrialAnomalyDetector(contamination=0.1)

    # 50 healthy samples
    healthy_data = []
    for _ in range(50):
        healthy_data.append({
            "temperature": np.random.normal(60.0, 2.0),
            "vibration": np.random.normal(2.0, 0.2),
            "pressure": np.random.normal(4.0, 0.1),
            "rotational_speed": np.random.normal(1480, 10),
            "electrical_current": np.random.normal(110.0, 5.0),
            "operating_load": np.random.normal(80.0, 3.0),
        })
    df_healthy = pd.DataFrame(healthy_data)
    detector.fit(df_healthy)

    # Test extreme outlier
    outlier_df = pd.DataFrame([{
        "temperature": 150.0,
        "vibration": 18.0,
        "pressure": 1.0,
        "rotational_speed": 400,
        "electrical_current": 300.0,
        "operating_load": 105.0,
    }])
    flags, scores = detector.score_readings(outlier_df)
    assert flags[0] == 1, "Expected extreme multivariate reading to be flagged as an anomaly."
    assert scores[0] > 0.5, "Expected high anomaly score for extreme reading."


def test_detect_sensor_evidence_thresholds():
    """Verify physical sensor boundary excursions are detected with appropriate severity."""
    eq_type = "Blast furnace auxiliary equipment"

    # Extreme temperature reading
    sensor_row = {
        "temperature": 115.0,  # crit_max is 105°C
        "vibration": 2.0,
        "pressure": 3.5,
        "electrical_current": 100.0,
    }
    evidence = detect_sensor_evidence(sensor_row, eq_type)
    assert len(evidence) >= 1
    temp_ev = [e for e in evidence if e["sensor"] == "Temperature"][0]
    assert temp_ev["severity"] == "CRITICAL"
    assert "critical limit" in temp_ev["detail"]
