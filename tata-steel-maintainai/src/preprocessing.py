"""
Preprocessing module for industrial telemetry and maintenance logs.
Ensures data hygiene, chronological ordering, missing value imputation,
and documents measurement unit assumptions.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any, List

from config.settings import EQUIPMENT_REFERENCE_RANGES, INITIAL_MACHINE_FLEET

# Documented Physical Measurement Assumptions
UNIT_SPECIFICATIONS = {
    "temperature": {"unit": "°C", "standard": "Industrial PT100 RTD sensor reading"},
    "vibration": {"unit": "RMS mm/s", "standard": "ISO 10816 Industrial Machinery Vibration Severity Standards"},
    "pressure": {"unit": "bar", "standard": "Gauge pressure relative to atmospheric ambient"},
    "rotational_speed": {"unit": "RPM", "standard": "Shaft tachometer revolutions per minute"},
    "electrical_current": {"unit": "Amperes (A)", "standard": "3-phase RMS motor line current"},
    "operating_load": {"unit": "%", "standard": "Percentage of rated full continuous output capacity"},
    "operating_hours": {"unit": "Hours (h)", "standard": "Cumulative operating runtime hours"},
}


def clean_sensor_readings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean, type-cast, sort, and handle missing values in raw sensor observations.
    Applies forward-fill within machine groups and bounded outlier clipping.
    """
    if df.empty:
        return df

    cleaned = df.copy()

    # Ensure timestamp is datetime and sort chronologically
    cleaned["timestamp"] = pd.to_datetime(cleaned["timestamp"])
    cleaned = cleaned.sort_values(by=["machine_id", "timestamp"]).reset_index(drop=True)

    # Deduplicate machine + timestamp
    cleaned = cleaned.drop_duplicates(subset=["machine_id", "timestamp"], keep="first")

    numeric_cols = [
        "temperature", "vibration", "pressure", "rotational_speed",
        "electrical_current", "operating_load", "operating_hours"
    ]

    for col in numeric_cols:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
            # Forward-fill within machine group, then backward-fill, then global fallback
            cleaned[col] = cleaned.groupby("machine_id")[col].ffill().bfill()
            if cleaned[col].isnull().any():
                cleaned[col] = cleaned[col].fillna(0.0)

    # Physical boundary clipping
    if "temperature" in cleaned.columns:
        cleaned["temperature"] = cleaned["temperature"].clip(lower=-20.0, upper=250.0)
    if "vibration" in cleaned.columns:
        cleaned["vibration"] = cleaned["vibration"].clip(lower=0.01, upper=50.0)
    if "operating_load" in cleaned.columns:
        cleaned["operating_load"] = cleaned["operating_load"].clip(lower=0.0, upper=110.0)

    return cleaned


def filter_observations_strictly_before(
    df: pd.DataFrame,
    cutoff_time: pd.Timestamp,
    timestamp_col: str = "timestamp"
) -> pd.DataFrame:
    """
    STRICT TEMPORAL ISOLATION:
    Filters observations to only those strictly prior or equal to cutoff_time.
    Guarantees no future leakage from beyond the prediction horizon.
    """
    if df.empty or cutoff_time is None:
        return df

    df_copy = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_copy[timestamp_col]):
        df_copy[timestamp_col] = pd.to_datetime(df_copy[timestamp_col])

    return df_copy[df_copy[timestamp_col] <= cutoff_time].copy()
