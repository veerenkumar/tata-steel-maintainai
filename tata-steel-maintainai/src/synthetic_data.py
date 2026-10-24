"""
Synthetic Data Generation Engine for TATA STEEL MAINTAINAI.
Generates temporally and physically consistent industrial sensor telemetry,
maintenance history, equipment failures, and production schedules.
All generated records are explicitly labeled as synthetic demonstrations.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
from typing import Dict, List, Tuple
from pathlib import Path

from config.settings import (
    INITIAL_MACHINE_FLEET,
    EQUIPMENT_REFERENCE_RANGES,
    PRODUCTION_AREAS,
    SAMPLE_DATA_DIR,
    RANDOM_SEED,
)
from database.db import get_connection, log_audit


def generate_all_synthetic_data(
    days: int = 45,
    freq_hours: int = 1,
    seed: int = RANDOM_SEED,
    export_csv: bool = True
) -> Dict[str, pd.DataFrame]:
    """
    Generate comprehensive synthetic datasets for all machines:
    1. Sensor readings (hourly time series with physical degradation dynamics)
    2. Failure history (causally linked to prior extreme sensor spikes)
    3. Maintenance history (records of past PMs and corrective interventions)
    4. Production schedules (planned shifts and shutdown windows)
    """
    np.random.seed(seed)
    random.seed(seed)

    end_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=days)
    timestamps = pd.date_range(start=start_time, end=end_time, freq=f"{freq_hours}h")

    # 1. Generate Sensor Telemetry
    sensor_rows = []
    failure_rows = []
    maintenance_rows = []

    # Choose specific machines to simulate active degradation towards end of window
    degrading_machines = {
        "RM-MOTOR-002": {"start_day": 32, "defect": "bearing_wear", "severity": 0.85},
        "BOF-ID-FAN-001": {"start_day": 35, "defect": "impeller_unbalance", "severity": 0.80},
        "HYD-PRESS-001": {"start_day": 38, "defect": "seal_degradation", "severity": 0.75},
        "BF-PUMP-001": {"start_day": 40, "defect": "cavitation", "severity": 0.65},
    }

    # Machines that had a past historical failure and repair
    past_failure_machines = {
        "RM-STAND-001": {"day": 15, "category": "Mechanical Chock Seizure", "component": "Work Roll Chock Bearing", "downtime": 12.5, "cost": 54000.0, "root_cause": "Lubrication starvation leading to bearing overheating"},
        "CONV-BELT-003": {"day": 22, "category": "Belt Splice Failure", "component": "Drive Pulley EP800 Belt Splice", "downtime": 8.0, "cost": 16500.0, "root_cause": "Impact tear from sharp sinter lump"},
        "LADLE-CRANE-001": {"day": 8, "category": "Electrical Motor Drive Trip", "component": "Hoist Motor Inverter", "downtime": 6.5, "cost": 22000.0, "root_cause": "Phase current harmonic spike and thermal overload trip"}
    }

    for machine in INITIAL_MACHINE_FLEET:
        m_id = machine["machine_id"]
        eq_type = machine["equipment_type"]
        ranges = EQUIPMENT_REFERENCE_RANGES[eq_type]
        base_op_hours = machine["operating_hours"] - (days * 24)

        t_min, t_max = ranges["temperature"]["normal_min"], ranges["temperature"]["normal_max"]
        v_min, v_max = ranges["vibration"]["normal_min"], ranges["vibration"]["normal_max"]
        p_min, p_max = ranges["pressure"]["normal_min"], ranges["pressure"]["normal_max"]
        s_min, s_max = ranges["rotational_speed"]["normal_min"], ranges["rotational_speed"]["normal_max"]
        c_min, c_max = ranges["electrical_current"]["normal_min"], ranges["electrical_current"]["normal_max"]
        l_min, l_max = ranges["operating_load"]["normal_min"], ranges["operating_load"]["normal_max"]

        t_base = (t_min + t_max) / 2.0
        v_base = (v_min + v_max) / 2.0
        p_base = (p_min + p_max) / 2.0
        s_base = (s_min + s_max) / 2.0
        c_base = (c_min + c_max) / 2.0
        l_base = (l_min + l_max) / 2.0

        is_degrading = m_id in degrading_machines
        deg_info = degrading_machines.get(m_id, None)

        # Check if machine had past failure
        has_past_fail = m_id in past_failure_machines
        past_fail_day = past_failure_machines[m_id]["day"] if has_past_fail else -1

        for idx, ts in enumerate(timestamps):
            day_num = idx / 24.0
            cur_op_hours = max(0.0, base_op_hours + idx * freq_hours)

            # Ambient / diurnal cycle (slight 24h temperature fluctuation)
            hour_of_day = ts.hour
            diurnal = 2.0 * np.sin(2 * np.pi * (hour_of_day - 6) / 24)

            # Random natural variability
            temp = t_base + diurnal + np.random.normal(0, 1.2)
            vib = v_base + np.random.normal(0, 0.15)
            press = p_base + np.random.normal(0, (p_max - p_min) * 0.03)
            speed = s_base + np.random.normal(0, (s_max - s_min) * 0.02)
            curr = c_base + np.random.normal(0, (c_max - c_min) * 0.03)
            load = l_base + np.random.normal(0, 2.5)

            # Historical failure simulation (prior build up and repair reset)
            if has_past_fail:
                if (past_fail_day - 4) <= day_num < past_fail_day:
                    # Deterioration leading to failure
                    factor = (day_num - (past_fail_day - 4)) / 4.0
                    temp += factor * (ranges["temperature"]["crit_max"] - t_base) * 0.9
                    vib += factor * (ranges["vibration"]["crit_max"] - v_base) * 1.1
                    curr += factor * 35.0
                elif abs(day_num - past_fail_day) < 0.2:
                    # Failure event moment
                    temp = ranges["temperature"]["crit_max"] + np.random.uniform(2, 6)
                    vib = ranges["vibration"]["crit_max"] + np.random.uniform(1.5, 3.0)
                    load = 10.0  # Tripped / shut down
                    speed = 0.0
                elif past_fail_day <= day_num < (past_fail_day + 1.0):
                    # Under repair
                    temp = t_min
                    vib = 0.1
                    press = 0.0
                    speed = 0.0
                    curr = 0.0
                    load = 0.0
                elif day_num >= (past_fail_day + 1.0):
                    # Restored to pristine baseline after repair
                    pass

            # Active recent degradation simulation (for predicting future failure)
            if is_degrading and day_num >= deg_info["start_day"]:
                elapsed_deg_days = day_num - deg_info["start_day"]
                total_deg_span = days - deg_info["start_day"]
                # Exponential / sigmoid wear curve
                progress = min(1.0, elapsed_deg_days / max(1.0, total_deg_span))
                growth = np.exp(progress * 2.2) - 1.0
                norm_growth = growth / (np.exp(2.2) - 1.0) * deg_info["severity"]

                if deg_info["defect"] == "bearing_wear":
                    # Elevated vibration, harmonic friction heating
                    vib += norm_growth * (ranges["vibration"]["crit_max"] - v_base) * 1.2
                    temp += norm_growth * (ranges["temperature"]["warn_max"] - t_base) * 1.0
                    curr += norm_growth * (ranges["electrical_current"]["warn_max"] - c_base) * 0.6
                elif deg_info["defect"] == "impeller_unbalance":
                    # Severe 1X rotational vibration, aerodynamic pressure pulses
                    vib += norm_growth * (ranges["vibration"]["crit_max"] - v_base) * 1.3
                    press += np.sin(idx * 0.4) * norm_growth * 0.8
                    temp += norm_growth * 12.0
                elif deg_info["defect"] == "seal_degradation":
                    # Internal hydraulic bypass: pressure drops, temperature climbs, motor currents surge
                    press -= norm_growth * (p_base - ranges["pressure"]["warn_min"]) * 1.2
                    temp += norm_growth * (ranges["temperature"]["warn_max"] - t_base) * 1.1
                    curr += norm_growth * 25.0
                elif deg_info["defect"] == "cavitation":
                    # Fluctuating discharge pressure, high frequency vibration, erratic current
                    vib += norm_growth * (ranges["vibration"]["warn_max"] - v_base) * 0.9 + np.random.uniform(-0.4, 0.4)
                    press -= norm_growth * (p_base - ranges["pressure"].get("warn_min", p_min)) * 0.8
                    curr += norm_growth * 15.0

            # Clip within physical reality
            temp = max(15.0, round(float(temp), 2))
            vib = max(0.05, round(float(vib), 3))
            press = max(0.0, round(float(press), 2))
            speed = max(0.0, round(float(speed), 1))
            curr = max(0.0, round(float(curr), 2))
            load = min(105.0, max(0.0, round(float(load), 1)))

            sensor_rows.append({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "machine_id": m_id,
                "temperature": temp,
                "vibration": vib,
                "pressure": press,
                "rotational_speed": speed,
                "electrical_current": curr,
                "operating_load": load,
                "operating_hours": round(float(cur_op_hours), 1),
                "is_anomaly": 0,
                "anomaly_score": 0.0,
            })

        # Add past failure event if applicable
        if has_past_fail:
            fail_info = past_failure_machines[m_id]
            fail_ts = start_time + timedelta(days=fail_info["day"])
            failure_rows.append({
                "machine_id": m_id,
                "failure_timestamp": fail_ts.strftime("%Y-%m-%d %H:%M:%S"),
                "failure_category": fail_info["category"],
                "affected_component": fail_info["component"],
                "downtime_duration": fail_info["downtime"],
                "repair_expense": fail_info["cost"],
                "root_cause": fail_info["root_cause"],
            })
            # Add corresponding corrective maintenance record
            maint_ts = fail_ts + timedelta(hours=fail_info["downtime"])
            maintenance_rows.append({
                "machine_id": m_id,
                "maintenance_date": maint_ts.strftime("%Y-%m-%d %H:%M:%S"),
                "maintenance_type": "Corrective Emergency Repair",
                "components_inspected_or_replaced": f"Replaced {fail_info['component']}; aligned and balanced",
                "maintenance_duration": fail_info["downtime"],
                "maintenance_cost": fail_info["cost"],
                "technician_or_team_assignment": "Emergency Plant Mechanical Team",
                "work_order_status": "Completed",
                "notes": f"Restored machine to baseline operation following {fail_info['category']}.",
            })

        # Add routine scheduled PM records for all machines in past 30 days
        pm_day = random.randint(5, 20)
        pm_ts = start_time + timedelta(days=pm_day)
        maintenance_rows.append({
            "machine_id": m_id,
            "maintenance_date": pm_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "maintenance_type": "Preventive Periodic Inspection",
            "components_inspected_or_replaced": "Lubrication renewal, seal inspection, bolt torque check",
            "maintenance_duration": round(random.uniform(3.0, 6.0), 1),
            "maintenance_cost": round(random.uniform(2500.0, 7500.0), 2),
            "technician_or_team_assignment": "Shift Maintenance Team",
            "work_order_status": "Completed",
            "notes": "Standard manufacturer maintenance interval inspection; all tests passed.",
        })

    # 4. Generate Production Schedules (next 14 days)
    schedule_rows = []
    sched_start = end_time - timedelta(days=2)
    sched_end = end_time + timedelta(days=12)
    current_day = sched_start

    shifts = [
        ("Shift A (Morning)", 6, 14),
        ("Shift B (Evening)", 14, 22),
        ("Shift C (Night)", 22, 6),
    ]

    while current_day < sched_end:
        day_str = current_day.strftime("%Y-%m-%d")
        for area in PRODUCTION_AREAS:
            for s_name, start_hr, end_hr in shifts:
                s_start = datetime.strptime(f"{day_str} {start_hr:02d}:00:00", "%Y-%m-%d %H:%M:%S")
                if end_hr == 6:
                    s_end = s_start + timedelta(hours=8)
                else:
                    s_end = datetime.strptime(f"{day_str} {end_hr:02d}:00:00", "%Y-%m-%d %H:%M:%S")

                # Plan a shutdown window every 5 days for Blast Furnace and Hot Strip Mill
                is_shutdown = 0
                shut_type = "None"
                demand = 100.0
                avail = "Full"

                if "Hot Strip Mill" in area and current_day.day % 4 == 0 and s_name.startswith("Shift B"):
                    is_shutdown = 1
                    shut_type = "Planned Weekly Roll Change & PM Stoppage"
                    demand = 0.0
                    avail = "Maintenance Window Available"
                elif "Steel Melt Shop" in area and current_day.day % 5 == 0 and s_name.startswith("Shift C"):
                    is_shutdown = 1
                    shut_type = "Planned Off-Gas Scrubbing Shutdown"
                    demand = 0.0
                    avail = "Maintenance Window Available"
                elif "Blast Furnace" in area and current_day.day % 7 == 0 and s_name.startswith("Shift A"):
                    is_shutdown = 1
                    shut_type = "Tuyere & Pump Planned Inspection Window"
                    demand = 20.0
                    avail = "Maintenance Window Available"

                schedule_rows.append({
                    "production_area": area,
                    "start_time": s_start.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": s_end.strftime("%Y-%m-%d %H:%M:%S"),
                    "planned_shift": s_name,
                    "planned_shutdown": is_shutdown,
                    "shutdown_type": shut_type,
                    "production_demand_pct": demand,
                    "machine_availability_required": avail,
                    "notes": f"Operating schedule for {area} under {s_name}."
                })
        current_day += timedelta(days=1)

    df_sensors = pd.DataFrame(sensor_rows)
    df_failures = pd.DataFrame(failure_rows)
    df_maintenance = pd.DataFrame(maintenance_rows)
    df_schedules = pd.DataFrame(schedule_rows)

    if export_csv:
        SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        df_sensors.to_csv(SAMPLE_DATA_DIR / "sensor_readings.csv", index=False)
        df_failures.to_csv(SAMPLE_DATA_DIR / "failure_history.csv", index=False)
        df_maintenance.to_csv(SAMPLE_DATA_DIR / "maintenance_history.csv", index=False)
        df_schedules.to_csv(SAMPLE_DATA_DIR / "production_schedules.csv", index=False)

    return {
        "sensor_readings": df_sensors,
        "failure_history": df_failures,
        "maintenance_history": df_maintenance,
        "production_schedules": df_schedules,
    }


def seed_synthetic_data_into_db() -> Dict[str, int]:
    """Generate synthetic datasets and insert them directly into SQLite tables."""
    datasets = generate_all_synthetic_data(days=45, freq_hours=1, export_csv=True)

    with get_connection() as conn:
        cursor = conn.cursor()

        # Insert sensor readings
        cursor.execute("DELETE FROM sensor_readings;")
        datasets["sensor_readings"].to_sql("sensor_readings", conn, if_exists="append", index=False)

        # Insert failure events
        cursor.execute("DELETE FROM failure_events;")
        datasets["failure_history"].to_sql("failure_events", conn, if_exists="append", index=False)

        # Insert maintenance records
        cursor.execute("DELETE FROM maintenance_records;")
        datasets["maintenance_history"].to_sql("maintenance_records", conn, if_exists="append", index=False)

        # Insert production schedules
        cursor.execute("DELETE FROM production_schedules;")
        datasets["production_schedules"].to_sql("production_schedules", conn, if_exists="append", index=False)

        conn.commit()

    log_audit(
        "SYNTHETIC_DATA_GENERATION",
        "system",
        "all_tables",
        details=f"Seeded {len(datasets['sensor_readings'])} sensor readings, {len(datasets['failure_history'])} failures, {len(datasets['maintenance_history'])} maintenance records, {len(datasets['production_schedules'])} schedules."
    )

    return {
        "sensor_readings": len(datasets["sensor_readings"]),
        "failure_history": len(datasets["failure_history"]),
        "maintenance_history": len(datasets["maintenance_history"]),
        "production_schedules": len(datasets["production_schedules"]),
    }
