"""
Automated unit tests for feature extraction and temporal leakage prevention.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.feature_engineering import extract_features_from_telemetry, FEATURE_COLUMNS
from config.settings import INITIAL_MACHINE_FLEET


def test_feature_extraction_columns():
    """Verify all defined feature columns are extracted and populated."""
    machine_meta = INITIAL_MACHINE_FLEET[0]
    base_time = datetime(2026, 10, 1, 0, 0, 0)
    rows = []
    for h in range(30):
        rows.append({
            "timestamp": (base_time + timedelta(hours=h)).strftime("%Y-%m-%d %H:%M:%S"),
            "machine_id": machine_meta["machine_id"],
            "temperature": 60.0 + h * 0.1,
            "vibration": 2.0 + h * 0.05,
            "pressure": 3.8,
            "rotational_speed": 1480,
            "electrical_current": 105.0,
            "operating_load": 75.0,
            "operating_hours": 1000.0 + h,
            "is_anomaly": 0,
            "anomaly_score": 0.0,
        })
    df_sensors = pd.DataFrame(rows)

    feat_df = extract_features_from_telemetry(df_sensors, machine_meta)
    for col in FEATURE_COLUMNS:
        assert col in feat_df.columns, f"Missing feature column: {col}"
    assert len(feat_df) == 30
    assert not feat_df[FEATURE_COLUMNS].isnull().any().any()


def test_temporal_leakage_prevention():
    """
    CRITICAL UNIT TEST:
    Verify that appending future telemetry data (after time T) has ZERO effect
    on the feature values calculated at time T.
    """
    machine_meta = INITIAL_MACHINE_FLEET[0]
    base_time = datetime(2026, 10, 1, 0, 0, 0)

    # Initial batch of 24 hours
    batch_1 = []
    for h in range(24):
        batch_1.append({
            "timestamp": (base_time + timedelta(hours=h)).strftime("%Y-%m-%d %H:%M:%S"),
            "machine_id": machine_meta["machine_id"],
            "temperature": 65.0,
            "vibration": 2.2,
            "pressure": 4.0,
            "rotational_speed": 1485,
            "electrical_current": 110.0,
            "operating_load": 80.0,
            "operating_hours": 1000.0 + h,
            "is_anomaly": 0,
            "anomaly_score": 0.0,
        })
    df_batch_1 = pd.DataFrame(batch_1)
    feat_1 = extract_features_from_telemetry(df_batch_1, machine_meta)
    features_at_t23_batch_1 = feat_1.iloc[23][FEATURE_COLUMNS].to_dict()

    # Append 12 future hours with catastrophic spike (T+24 to T+35)
    batch_2 = list(batch_1)
    for h in range(24, 36):
        batch_2.append({
            "timestamp": (base_time + timedelta(hours=h)).strftime("%Y-%m-%d %H:%M:%S"),
            "machine_id": machine_meta["machine_id"],
            "temperature": 180.0,  # catastrophic future spike
            "vibration": 15.0,     # catastrophic future spike
            "pressure": 1.0,
            "rotational_speed": 500,
            "electrical_current": 250.0,
            "operating_load": 100.0,
            "operating_hours": 1000.0 + h,
            "is_anomaly": 1,
            "anomaly_score": 0.95,
        })
    df_batch_2 = pd.DataFrame(batch_2)
    feat_2 = extract_features_from_telemetry(df_batch_2, machine_meta)
    features_at_t23_batch_2 = feat_2.iloc[23][FEATURE_COLUMNS].to_dict()

    # The features at T=23 must be EXACTLY IDENTICAL despite future spike
    for col in FEATURE_COLUMNS:
        val_1 = features_at_t23_batch_1[col]
        val_2 = features_at_t23_batch_2[col]
        assert pytest.approx(val_1, rel=1e-5) == val_2, (
            f"Temporal Leakage Detected in '{col}'! Value at T=23 changed from {val_1} to {val_2} after future data was introduced."
        )
