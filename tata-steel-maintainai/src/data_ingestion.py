"""
Data Ingestion and Validation Pipeline for TATA STEEL MAINTAINAI.
Validates schemas, data types, physical constraints, missing values,
duplicates, and foreign key references for industrial datasets.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import io

from database.db import get_connection, get_all_machines, log_audit, execute_query

# Schema Definitions
REQUIRED_COLUMNS = {
    "sensor_readings": [
        "timestamp", "machine_id", "temperature", "vibration",
        "pressure", "rotational_speed", "electrical_current",
        "operating_load", "operating_hours"
    ],
    "failure_history": [
        "machine_id", "failure_timestamp", "failure_category",
        "affected_component", "downtime_duration", "repair_expense", "root_cause"
    ],
    "maintenance_history": [
        "machine_id", "maintenance_date", "maintenance_type",
        "components_inspected_or_replaced", "maintenance_duration",
        "maintenance_cost", "technician_or_team_assignment", "work_order_status"
    ],
    "production_schedules": [
        "production_area", "start_time", "end_time", "planned_shift",
        "planned_shutdown", "shutdown_type", "production_demand_pct",
        "machine_availability_required"
    ],
}


def validate_dataset(dataset_type: str, df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate an uploaded or provided DataFrame against required schema,
    null constraints, duplicate timestamps, unknown machine IDs, and physical boundaries.
    """
    errors: List[str] = []
    warnings: List[str] = []
    stats: Dict[str, Any] = {}

    if dataset_type not in REQUIRED_COLUMNS:
        return {
            "is_valid": False,
            "errors": [f"Unsupported dataset type: '{dataset_type}'. Supported: {list(REQUIRED_COLUMNS.keys())}"],
            "warnings": [],
            "row_count": len(df),
            "stats": {},
            "clean_df": df,
        }

    req_cols = REQUIRED_COLUMNS[dataset_type]
    df_cols = list(df.columns)

    # 1. Check Missing Required Columns
    missing_cols = [c for c in req_cols if c not in df_cols]
    if missing_cols:
        errors.append(f"Missing required columns: {', '.join(missing_cols)}")
        return {
            "is_valid": False,
            "errors": errors,
            "warnings": warnings,
            "row_count": len(df),
            "stats": {},
            "clean_df": df,
        }

    # 2. Check Empty Dataset
    if df.empty:
        errors.append("Dataset is empty (0 rows).")
        return {
            "is_valid": False,
            "errors": errors,
            "warnings": warnings,
            "row_count": 0,
            "stats": {},
            "clean_df": df,
        }

    clean_df = df.copy()

    # 3. Timestamp Validation & Parsing
    ts_col = {
        "sensor_readings": "timestamp",
        "failure_history": "failure_timestamp",
        "maintenance_history": "maintenance_date",
        "production_schedules": "start_time",
    }[dataset_type]

    try:
        clean_df[ts_col] = pd.to_datetime(clean_df[ts_col])
        clean_df = clean_df.sort_values(by=ts_col)
    except Exception as e:
        errors.append(f"Invalid timestamp formatting in column '{ts_col}': {str(e)}")

    if dataset_type == "production_schedules":
        try:
            clean_df["end_time"] = pd.to_datetime(clean_df["end_time"])
            invalid_spans = clean_df[clean_df["end_time"] <= clean_df["start_time"]]
            if not invalid_spans.empty:
                errors.append(f"Found {len(invalid_spans)} schedule rows where end_time <= start_time.")
        except Exception as e:
            errors.append(f"Invalid schedule end_time formatting: {str(e)}")

    # 4. Machine ID Verification against Fleet Registry
    if "machine_id" in clean_df.columns:
        registered_machines = set(get_all_machines()["machine_id"].dropna().unique())
        unknown_machines = set(clean_df["machine_id"].dropna().unique()) - registered_machines
        if unknown_machines:
            warnings.append(f"Contains {len(unknown_machines)} machine ID(s) not in registered fleet: {sorted(list(unknown_machines))}")

    # 5. Missing Values & Nulls
    null_counts = clean_df[req_cols].isnull().sum().to_dict()
    total_nulls = sum(null_counts.values())
    stats["null_counts"] = null_counts
    if total_nulls > 0:
        warnings.append(f"Found {total_nulls} missing/null value(s) across required columns.")

    # 6. Duplicates Checking
    if dataset_type == "sensor_readings":
        dup_mask = clean_df.duplicated(subset=["machine_id", "timestamp"], keep="first")
        num_dups = int(dup_mask.sum())
        if num_dups > 0:
            warnings.append(f"Found and removed {num_dups} duplicate sensor reading(s) for same machine/timestamp.")
            clean_df = clean_df[~dup_mask]

        # 7. Physical sensor boundaries validation
        invalid_temps = clean_df[(clean_df["temperature"] < -20.0) | (clean_df["temperature"] > 250.0)]
        if not invalid_temps.empty:
            warnings.append(f"{len(invalid_temps)} temperature readings outside realistic range (-20 to 250°C).")

        invalid_vibs = clean_df[(clean_df["vibration"] < 0.0) | (clean_df["vibration"] > 50.0)]
        if not invalid_vibs.empty:
            warnings.append(f"{len(invalid_vibs)} vibration readings outside realistic range (0 to 50 mm/s).")

        invalid_loads = clean_df[(clean_df["operating_load"] < 0.0) | (clean_df["operating_load"] > 120.0)]
        if not invalid_loads.empty:
            warnings.append(f"{len(invalid_loads)} operating load readings outside realistic range (0 to 120%).")

    # Format timestamp column back to string for SQLite storage
    if ts_col in clean_df.columns:
        clean_df[ts_col] = clean_df[ts_col].dt.strftime("%Y-%m-%d %H:%M:%S")
    if dataset_type == "production_schedules" and "end_time" in clean_df.columns:
        clean_df["end_time"] = clean_df["end_time"].dt.strftime("%Y-%m-%d %H:%M:%S")

    stats["total_rows"] = len(df)
    stats["clean_rows"] = len(clean_df)
    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "row_count": len(clean_df),
        "stats": stats,
        "clean_df": clean_df,
    }


def ingest_dataset_file(
    dataset_type: str,
    file_content_or_path: Any,
    mode: str = "append",
    actor: str = "Operator"
) -> Dict[str, Any]:
    """
    Ingest CSV file or DataFrame into SQLite database with full validation and audit logging.
    mode: 'append' or 'replace'
    """
    try:
        if isinstance(file_content_or_path, (str, bytes)):
            if isinstance(file_content_or_path, str) and file_content_or_path.endswith(".csv"):
                df = pd.read_csv(file_content_or_path)
            elif isinstance(file_content_or_path, bytes):
                df = pd.read_csv(io.BytesIO(file_content_or_path))
            else:
                df = pd.read_csv(io.StringIO(file_content_or_path))
        elif isinstance(file_content_or_path, pd.DataFrame):
            df = file_content_or_path
        elif hasattr(file_content_or_path, "name") and file_content_or_path.name.endswith(".csv"):
            df = pd.read_csv(file_content_or_path.name)
        else:
            return {"success": False, "message": "Unsupported file input format."}
    except Exception as e:
        return {"success": False, "message": f"Failed to read CSV input: {str(e)}"}

    validation = validate_dataset(dataset_type, df)
    if not validation["is_valid"]:
        return {
            "success": False,
            "message": f"Validation failed with {len(validation['errors'])} error(s).",
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "stats": validation["stats"],
        }

    clean_df = validation["clean_df"]
    table_name = {
        "sensor_readings": "sensor_readings",
        "failure_history": "failure_events",
        "maintenance_history": "maintenance_records",
        "production_schedules": "production_schedules",
    }[dataset_type]

    with get_connection() as conn:
        if mode == "replace":
            conn.execute(f"DELETE FROM {table_name};")
        clean_df.to_sql(table_name, conn, if_exists="append", index=False)
        conn.commit()

    log_audit(
        action_type="DATA_INGESTION",
        entity_type=table_name,
        actor=actor,
        details=f"Ingested {len(clean_df)} records (Mode: {mode}). Warnings: {len(validation['warnings'])}"
    )

    return {
        "success": True,
        "message": f"Successfully ingested {len(clean_df)} records into '{table_name}'.",
        "errors": [],
        "warnings": validation["warnings"],
        "row_count": len(clean_df),
        "stats": validation["stats"],
    }
