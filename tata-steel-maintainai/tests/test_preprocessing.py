"""
Automated unit tests for data preprocessing and temporal isolation.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.preprocessing import clean_sensor_readings, filter_observations_strictly_before, UNIT_SPECIFICATIONS


def test_unit_specifications_documented():
    """Verify all physical sensors have documented engineering units and standards."""
    required = ["temperature", "vibration", "pressure", "rotational_speed", "electrical_current", "operating_load"]
    for s in required:
        assert s in UNIT_SPECIFICATIONS
        assert "unit" in UNIT_SPECIFICATIONS[s]
        assert "standard" in UNIT_SPECIFICATIONS[s]


def test_clean_sensor_readings_imputation_and_clipping():
    """Verify missing values are imputed, duplicates dropped, and outliers clipped."""
    raw_data = {
        "timestamp": ["2026-10-01 10:00:00", "2026-10-01 10:00:00", "2026-10-01 11:00:00", "2026-10-01 12:00:00"],
        "machine_id": ["BF-PUMP-001", "BF-PUMP-001", "BF-PUMP-001", "BF-PUMP-001"],
        "temperature": [65.0, 65.0, np.nan, 320.0],  # duplicate row, null, and extreme outlier
        "vibration": [2.5, 2.5, 3.0, -5.0],          # negative outlier
        "pressure": [4.0, 4.0, 4.1, 4.2],
        "rotational_speed": [1480, 1480, 1485, 1490],
        "electrical_current": [110.0, 110.0, 112.0, 115.0],
        "operating_load": [80.0, 80.0, 82.0, 150.0], # load > 110%
        "operating_hours": [1000.0, 1000.0, 1001.0, 1002.0],
    }
    df = pd.DataFrame(raw_data)
    cleaned = clean_sensor_readings(df)

    # Duplicate dropped: 4 rows -> 3 unique
    assert len(cleaned) == 3
    # Missing temp was imputed
    assert cleaned["temperature"].isnull().sum() == 0
    # 320°C clipped to <= 250°C
    assert cleaned["temperature"].max() <= 250.0
    # Negative vibration clipped to >= 0.01 mm/s
    assert cleaned["vibration"].min() >= 0.01
    # 150% load clipped to <= 110%
    assert cleaned["operating_load"].max() <= 110.0


def test_temporal_isolation_filtering():
    """Verify observations strictly after cutoff_time are excluded without leakage."""
    timestamps = [
        "2026-10-01 08:00:00",
        "2026-10-01 10:00:00",
        "2026-10-01 12:00:00",
        "2026-10-01 14:00:00",
        "2026-10-01 16:00:00",
    ]
    df = pd.DataFrame({"timestamp": timestamps, "val": [1, 2, 3, 4, 5]})
    cutoff = pd.Timestamp("2026-10-01 12:00:00")

    filtered = filter_observations_strictly_before(df, cutoff_time=cutoff)
    assert len(filtered) == 3
    assert filtered["val"].tolist() == [1, 2, 3]
    assert (pd.to_datetime(filtered["timestamp"]) <= cutoff).all()
