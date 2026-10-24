"""
Database connection and operations module for TATA STEEL MAINTAINAI.
SQLite backend with parameterized queries and transaction management.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from datetime import datetime

from config.settings import (
    DB_PATH,
    BASE_DIR,
    INITIAL_MACHINE_FLEET,
    TECHNICIAN_ROSTER,
    SPARE_PARTS_CATALOG,
)

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    """Establish connection to SQLite database with foreign keys enabled."""
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(force_recreate: bool = False) -> None:
    """Initialize database tables using schema.sql and seed reference data."""
    schema_path = BASE_DIR / "database" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_connection() as conn:
        if force_recreate:
            cursor = conn.cursor()
            # Drop tables in reverse dependency order
            tables = [
                "audit_logs", "model_versions", "maintenance_work_orders",
                "maintenance_recommendations", "predictions", "spare_parts",
                "technicians", "production_schedules", "maintenance_records",
                "failure_events", "sensor_readings", "machines"
            ]
            for t in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {t};")
            conn.commit()

        conn.executescript(schema_sql)
        conn.commit()

    seed_reference_data()


def seed_reference_data() -> None:
    """Populate initial machines, technicians, and spare parts if empty."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Check machines
        cursor.execute("SELECT COUNT(*) FROM machines;")
        count = cursor.fetchone()[0]
        if count == 0:
            for m in INITIAL_MACHINE_FLEET:
                cursor.execute(
                    """
                    INSERT INTO machines (
                        machine_id, equipment_type, production_area, criticality,
                        commissioning_date, operating_status, operating_hours,
                        last_maintenance_date, maintenance_interval_days,
                        estimated_repair_cost, downtime_cost_per_hour,
                        expected_maintenance_duration_hours, description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        m["machine_id"], m["equipment_type"], m["production_area"], m["criticality"],
                        m["commissioning_date"], m["operating_status"], m["operating_hours"],
                        m["last_maintenance_date"], m["maintenance_interval_days"],
                        m["estimated_repair_cost"], m["downtime_cost_per_hour"],
                        m["expected_maintenance_duration_hours"], m.get("description", "")
                    )
                )

        # Check technicians
        cursor.execute("SELECT COUNT(*) FROM technicians;")
        if cursor.fetchone()[0] == 0:
            for t in TECHNICIAN_ROSTER:
                cursor.execute(
                    """
                    INSERT INTO technicians (
                        tech_id, name, specialization, skill_level, shift, hourly_rate, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (t["tech_id"], t["name"], t["specialization"], t["skill_level"], t["shift"], t["hourly_rate"], "Available")
                )

        # Check spare parts
        cursor.execute("SELECT COUNT(*) FROM spare_parts;")
        if cursor.fetchone()[0] == 0:
            for p in SPARE_PARTS_CATALOG:
                cursor.execute(
                    """
                    INSERT INTO spare_parts (
                        part_id, name, equipment_type, unit_cost, stock_quantity, reorder_lead_days
                    ) VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (p["part_id"], p["name"], p["equipment_type"], p["unit_cost"], p["stock_quantity"], p["reorder_lead_days"])
                )

        conn.commit()


def execute_query(query: str, params: Tuple = ()) -> int:
    """Execute a parameterized DML query (INSERT, UPDATE, DELETE) and commit."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount


def fetch_df(query: str, params: Tuple = ()) -> pd.DataFrame:
    """Execute a parameterized query and return results as a Pandas DataFrame."""
    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
        return df


def log_audit(
    action_type: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    actor: str = "MaintainAI Agent",
    details: str = "",
    previous_state: Optional[str] = None,
    new_state: Optional[str] = None,
) -> None:
    """Record an audit trail event."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO audit_logs (
                event_timestamp, action_type, entity_type, entity_id, actor,
                details, previous_state, new_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                action_type, entity_type, entity_id, actor,
                details, previous_state, new_state
            )
        )
        conn.commit()


def get_all_machines() -> pd.DataFrame:
    """Return all machines as DataFrame."""
    return fetch_df("SELECT * FROM machines ORDER BY machine_id ASC;")


def get_machine_by_id(machine_id: str) -> Optional[Dict[str, Any]]:
    """Return machine dictionary or None."""
    df = fetch_df("SELECT * FROM machines WHERE machine_id = ?;", (machine_id,))
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def update_machine_status(machine_id: str, new_status: str) -> None:
    """Update operating status of a machine."""
    old_machine = get_machine_by_id(machine_id)
    prev = old_machine["operating_status"] if old_machine else "Unknown"
    execute_query(
        "UPDATE machines SET operating_status = ?, updated_at = CURRENT_TIMESTAMP WHERE machine_id = ?;",
        (new_status, machine_id)
    )
    log_audit("MACHINE_STATUS_UPDATE", "machines", machine_id, details=f"Status changed from {prev} to {new_status}", previous_state=prev, new_state=new_status)
