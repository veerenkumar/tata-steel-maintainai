"""
Feature Engineering Engine for Industrial Predictive Maintenance.
Extracts rolling sensor statistics, deterioration trends, historical maintenance intervals,
and strictly enforces temporal isolation to prevent future data leakage.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from config.settings import (
    EQUIPMENT_REFERENCE_RANGES,
    DEFAULT_PREDICTION_HORIZON_HOURS,
    DEFAULT_ROLLING_WINDOW_HOURS,
)
from src.preprocessing import clean_sensor_readings


FEATURE_COLUMNS = [
    "temp_mean_24h",
    "temp_max_24h",
    "temp_std_24h",
    "temp_trend_24h",
    "vib_mean_24h",
    "vib_max_24h",
    "vib_std_24h",
    "vib_trend_24h",
    "vib_abnormality_ratio",
    "pressure_deviation",
    "pressure_std_24h",
    "rpm_variability",
    "current_mean_24h",
    "current_load_ratio",
    "operating_load_mean",
    "operating_hours",
    "days_since_last_maint",
    "operating_hours_since_maint",
    "historical_failures_count",
    "criticality_tier",
    "recent_deterioration_score",
]


def extract_features_from_telemetry(
    sensor_df: pd.DataFrame,
    machine_meta: Dict[str, Any],
    maint_df: Optional[pd.DataFrame] = None,
    fail_df: Optional[pd.DataFrame] = None,
    rolling_hours: int = DEFAULT_ROLLING_WINDOW_HOURS,
) -> pd.DataFrame:
    """
    Extract physics-guided feature vectors for a specific machine.
    Strictly uses ONLY observations at or before the timestamp of each row.
    """
    if sensor_df.empty:
        return pd.DataFrame()

    df = clean_sensor_readings(sensor_df)
    eq_type = machine_meta.get("equipment_type", "Industrial motors")
    ranges = EQUIPMENT_REFERENCE_RANGES.get(eq_type, EQUIPMENT_REFERENCE_RANGES["Industrial motors"])

    crit_str = str(machine_meta.get("criticality", "Tier 2 - High"))
    if "Tier 1" in crit_str:
        crit_tier = 1
    elif "Tier 2" in crit_str:
        crit_tier = 2
    elif "Tier 3" in crit_str:
        crit_tier = 3
    else:
        crit_tier = 4

    t_norm_max = ranges["temperature"]["normal_max"]
    v_norm_max = ranges["vibration"]["normal_max"]
    p_norm_med = (ranges["pressure"]["normal_min"] + ranges["pressure"]["normal_max"]) / 2.0

    # Sort strictly by timestamp
    df = df.sort_values("timestamp").reset_index(drop=True)
    df.set_index("timestamp", inplace=True)

    # Rolling calculations using time window
    window_str = f"{rolling_hours}h"

    # Temperature features
    t_roll = df["temperature"].rolling(window_str, min_periods=1)
    df["temp_mean_24h"] = t_roll.mean()
    df["temp_max_24h"] = t_roll.max()
    df["temp_std_24h"] = t_roll.std().fillna(0.0)
    # Trend: difference from start of window (approx rolling_hours steps back)
    df["temp_trend_24h"] = df["temperature"] - df["temperature"].shift(rolling_hours).fillna(df["temperature"].iloc[0])

    # Vibration features
    v_roll = df["vibration"].rolling(window_str, min_periods=1)
    df["vib_mean_24h"] = v_roll.mean()
    df["vib_max_24h"] = v_roll.max()
    df["vib_std_24h"] = v_roll.std().fillna(0.0)
    df["vib_trend_24h"] = df["vibration"] - df["vibration"].shift(rolling_hours).fillna(df["vibration"].iloc[0])
    df["vib_abnormality_ratio"] = df["vibration"] / max(0.1, v_norm_max)

    # Pressure features
    p_roll = df["pressure"].rolling(window_str, min_periods=1)
    df["pressure_deviation"] = df["pressure"] - p_norm_med
    df["pressure_std_24h"] = p_roll.std().fillna(0.0)

    # RPM variability
    s_roll = df["rotational_speed"].rolling(window_str, min_periods=1)
    s_mean = s_roll.mean()
    s_std = s_roll.std().fillna(0.0)
    df["rpm_variability"] = s_std / (s_mean + 1e-4)

    # Current & load features
    c_roll = df["electrical_current"].rolling(window_str, min_periods=1)
    l_roll = df["operating_load"].rolling(window_str, min_periods=1)
    df["current_mean_24h"] = c_roll.mean()
    df["operating_load_mean"] = l_roll.mean()
    df["current_load_ratio"] = df["electrical_current"] / (df["operating_load"] + 1e-3)

    # Criticality tier
    df["criticality_tier"] = crit_tier

    # Deterioration composite score
    v_excess = (df["vib_mean_24h"] - v_norm_max).clip(lower=0.0) / max(0.1, v_norm_max)
    t_excess = (df["temp_mean_24h"] - t_norm_max).clip(lower=0.0) / max(0.1, t_norm_max)
    df["recent_deterioration_score"] = (v_excess * 60.0 + t_excess * 40.0).clip(upper=100.0)

    # Maintenance and failure history integration (strictly causal!)
    df.reset_index(inplace=True)

    # Parse maintenance events strictly before each row's timestamp
    last_maint_date_str = machine_meta.get("last_maintenance_date", "2026-06-01")
    base_last_maint = pd.to_datetime(last_maint_date_str)

    maint_dates = []
    if maint_df is not None and not maint_df.empty:
        m_maint = maint_df[maint_df["machine_id"] == machine_meta["machine_id"]].copy()
        if not m_maint.empty:
            maint_dates = sorted(pd.to_datetime(m_maint["maintenance_date"]).tolist())

    fail_dates = []
    if fail_df is not None and not fail_df.empty:
        m_fail = fail_df[fail_df["machine_id"] == machine_meta["machine_id"]].copy()
        if not m_fail.empty:
            fail_dates = sorted(pd.to_datetime(m_fail["failure_timestamp"]).tolist())

    days_since_maint = []
    hours_since_maint = []
    prior_failures = []

    for _, row in df.iterrows():
        current_ts = row["timestamp"]

        # Find most recent maintenance event <= current_ts
        relevant_maints = [d for d in maint_dates if d <= current_ts]
        effective_last_maint = relevant_maints[-1] if relevant_maints else base_last_maint
        diff_days = max(0.0, (current_ts - effective_last_maint).total_seconds() / 86400.0)
        days_since_maint.append(round(diff_days, 2))
        hours_since_maint.append(round(diff_days * 24.0, 1))

        # Count failures strictly < current_ts
        relevant_fails = [d for d in fail_dates if d < current_ts]
        prior_failures.append(len(relevant_fails))

    df["days_since_last_maint"] = days_since_maint
    df["operating_hours_since_maint"] = hours_since_maint
    df["historical_failures_count"] = prior_failures

    return df


def build_supervised_dataset(
    sensors_df: pd.DataFrame,
    machines_df: pd.DataFrame,
    failures_df: Optional[pd.DataFrame] = None,
    maintenance_df: Optional[pd.DataFrame] = None,
    forecast_horizon_hours: int = DEFAULT_PREDICTION_HORIZON_HOURS,
    sample_stride: int = 1,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Construct a labeled dataset for training failure prediction models.
    Target label Y = 1 if machine experienced a breakdown or critical threshold breach
    within the next `forecast_horizon_hours`, strictly using only features computed from t <= T.
    """
    all_feature_dfs = []
    all_labels = []

    machines_map = {row["machine_id"]: row.to_dict() for _, row in machines_df.iterrows()}

    for machine_id, m_meta in machines_map.items():
        m_sensors = sensors_df[sensors_df["machine_id"] == machine_id].copy()
        if m_sensors.empty:
            continue

        feat_df = extract_features_from_telemetry(
            sensor_df=m_sensors,
            machine_meta=m_meta,
            maint_df=maintenance_df,
            fail_df=failures_df,
            rolling_hours=DEFAULT_ROLLING_WINDOW_HOURS,
        )

        if feat_df.empty:
            continue

        # Stride sampling to reduce autocorrelation and size
        if sample_stride > 1:
            feat_df = feat_df.iloc[::sample_stride].reset_index(drop=True)

        eq_type = m_meta.get("equipment_type", "Industrial motors")
        ranges = EQUIPMENT_REFERENCE_RANGES.get(eq_type, EQUIPMENT_REFERENCE_RANGES["Industrial motors"])
        crit_v_max = ranges["vibration"]["crit_max"]
        crit_t_max = ranges["temperature"]["crit_max"]

        # Determine target failure labels within future horizon window
        # Get machine historical failures
        m_failures = []
        if failures_df is not None and not failures_df.empty:
            mf = failures_df[failures_df["machine_id"] == machine_id]
            if not mf.empty:
                m_failures = sorted(pd.to_datetime(mf["failure_timestamp"]).tolist())

        y_labels = []
        timestamps = feat_df["timestamp"].tolist()
        vibrations = feat_df["vibration"].tolist()
        temperatures = feat_df["temperature"].tolist()

        horizon_delta = timedelta(hours=forecast_horizon_hours)

        for i, ts in enumerate(timestamps):
            horizon_end = ts + horizon_delta

            # 1. Did recorded breakdown occur in (ts, ts + horizon]?
            failed_in_horizon = any(ts < f_ts <= horizon_end for f_ts in m_failures)

            # 2. Or did vibration/temp breach critical failure threshold in future horizon?
            if not failed_in_horizon:
                # Look ahead in sensor data for critical trip
                future_crit = False
                for j in range(i + 1, min(len(timestamps), i + forecast_horizon_hours + 1)):
                    if timestamps[j] > horizon_end:
                        break
                    if vibrations[j] >= crit_v_max or temperatures[j] >= crit_t_max:
                        future_crit = True
                        break
                failed_in_horizon = future_crit

            y_labels.append(1 if failed_in_horizon else 0)

        feat_df["label_failure_within_horizon"] = y_labels
        all_feature_dfs.append(feat_df)

    if not all_feature_dfs:
        return pd.DataFrame(), pd.Series(dtype=int)

    combined_df = pd.concat(all_feature_dfs, ignore_index=True)
    X = combined_df[FEATURE_COLUMNS].copy()
    y = combined_df["label_failure_within_horizon"].astype(int)

    return combined_df, y
