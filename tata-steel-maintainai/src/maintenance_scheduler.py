"""
Maintenance Scheduling Optimizer for TATA STEEL MAINTAINAI.
Constraint-based optimization engine matching equipment maintenance needs
with planned plant shutdowns, technician skill availability, and spare-parts inventory.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

from database.db import get_connection, log_audit, execute_query


def get_required_specialization(equipment_type: str) -> str:
    """Map machinery equipment type to primary technician engineering discipline."""
    eq_lower = equipment_type.lower()
    if "motor" in eq_lower:
        return "Electrical"
    elif "hydraulic" in eq_lower:
        return "Hydraulic"
    elif "fan" in eq_lower or "blower" in eq_lower or "pump" in eq_lower or "rolling" in eq_lower:
        return "Mechanical"
    elif "conveyor" in eq_lower:
        return "Mechanical"
    elif "cooling" in eq_lower:
        return "Mechanical"
    else:
        return "Mechanical"


def optimize_maintenance_schedule(
    horizon_days: int = 14,
    auto_create_work_orders: bool = False
) -> Dict[str, Any]:
    """
    Run constraint-based scheduling optimizer.
    Evaluates:
      1. Approved & high-priority recommendations
      2. Planned production shutdown windows by production area
      3. Technician skill specializations and shift assignments
      4. Spare parts stock levels
    Generates proposed maintenance calendar, flags resource conflicts, and explains infeasibilities.
    """
    with get_connection() as conn:
        # 1. Fetch pending & approved recommendations
        recs_df = pd.read_sql_query(
            """
            SELECT r.*, m.production_area, m.equipment_type, m.criticality, m.downtime_cost_per_hour
            FROM maintenance_recommendations r
            JOIN machines m ON r.machine_id = m.machine_id
            WHERE r.approval_status IN ('Approved', 'Pending')
            ORDER BY
                CASE r.priority
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    ELSE 4
                END,
                r.predicted_failure_probability DESC;
            """,
            conn
        )

        # 2. Fetch technicians
        techs_df = pd.read_sql_query("SELECT * FROM technicians WHERE status = 'Available';", conn)

        # 3. Fetch spare parts
        parts_df = pd.read_sql_query("SELECT * FROM spare_parts;", conn)

        # 4. Fetch production schedules (upcoming shutdown windows)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        schedules_df = pd.read_sql_query(
            "SELECT * FROM production_schedules WHERE end_time >= ? ORDER BY start_time ASC;",
            conn,
            params=(now_str,)
        )

    if recs_df.empty:
        return {
            "status": "NO_TASKS",
            "message": "No maintenance recommendations pending scheduling.",
            "calendar": [],
            "conflicts": [],
            "infeasible_tasks": [],
        }

    # Tracking resource allocations to detect conflicts
    allocated_tech_slots: Dict[str, List[Tuple[pd.Timestamp, pd.Timestamp]]] = {
        t["tech_id"]: [] for _, t in techs_df.iterrows()
    }
    part_stock_map: Dict[str, int] = {
        p["part_id"]: int(p["stock_quantity"]) for _, p in parts_df.iterrows()
    }

    calendar = []
    conflicts = []
    infeasible_tasks = []

    for _, rec in recs_df.iterrows():
        m_id = rec["machine_id"]
        rec_id = rec["recommendation_id"]
        area = rec["production_area"]
        eq_type = rec["equipment_type"]
        duration_hrs = float(rec["estimated_maintenance_duration"])
        priority = rec["priority"]
        req_specialization = get_required_specialization(eq_type)

        # 1. Check Spare Parts Feasibility
        req_parts_str = str(rec["required_parts"])
        part_allocated = None
        has_stock = True

        for _, p in parts_df.iterrows():
            if p["part_id"] in req_parts_str:
                if part_stock_map.get(p["part_id"], 0) > 0:
                    part_allocated = p["part_id"]
                    part_stock_map[p["part_id"]] -= 1
                else:
                    has_stock = False
                    infeasible_tasks.append({
                        "recommendation_id": rec_id,
                        "machine_id": m_id,
                        "reason": f"Required spare part '{p['name']} ({p['part_id']})' out of stock. Lead time: {p['reorder_lead_days']} days.",
                        "resolution": "Emergency procurement or expedite reorder required.",
                    })
                break

        if not has_stock:
            continue

        # 2. Find Candidate Window in Production Schedule
        area_schedules = schedules_df[schedules_df["production_area"] == area].copy()
        shutdown_windows = area_schedules[area_schedules["planned_shutdown"] == 1]

        chosen_window = None
        is_shutdown_window = False

        # Prefer planned plant shutdown window with sufficient duration
        for _, s_row in shutdown_windows.iterrows():
            w_start = pd.to_datetime(s_row["start_time"])
            w_end = pd.to_datetime(s_row["end_time"])
            window_span = (w_end - w_start).total_seconds() / 3600.0

            if window_span >= duration_hrs:
                chosen_window = (w_start, w_start + timedelta(hours=duration_hrs))
                is_shutdown_window = True
                break

        # If no shutdown window matches and priority is Critical / High, schedule in upcoming low-demand shift
        if not chosen_window:
            if priority in ["Critical", "High"]:
                # Pick earliest available shift
                earliest_shift = area_schedules.iloc[0]
                w_start = pd.to_datetime(earliest_shift["start_time"]) + timedelta(hours=1)
                chosen_window = (w_start, w_start + timedelta(hours=duration_hrs))
                is_shutdown_window = False
                conflicts.append({
                    "recommendation_id": rec_id,
                    "machine_id": m_id,
                    "type": "Production Shift Interruption Warning",
                    "details": f"High risk machine requires intervention during active operating shift ({earliest_shift['planned_shift']}). Temporary line derating required.",
                })
            else:
                # Postpone routine/medium task to next weekly stoppage
                infeasible_tasks.append({
                    "recommendation_id": rec_id,
                    "machine_id": m_id,
                    "reason": f"No planned shutdown window in {area} within the next 7 days.",
                    "resolution": "Defer task to upcoming monthly plant campaign shutdown.",
                })
                continue

        # 3. Match Qualified Technician
        cand_techs = techs_df[techs_df["specialization"] == req_specialization]
        if cand_techs.empty:
            cand_techs = techs_df  # Fallback to any available senior technician

        assigned_tech = None
        for _, t_row in cand_techs.iterrows():
            t_id = t_row["tech_id"]
            existing_slots = allocated_tech_slots.get(t_id, [])

            # Check overlap
            overlap = False
            for s_start, s_end in existing_slots:
                if not (chosen_window[1] <= s_start or chosen_window[0] >= s_end):
                    overlap = True
                    break

            if not overlap:
                assigned_tech = t_row.to_dict()
                allocated_tech_slots[t_id].append(chosen_window)
                break

        if not assigned_tech:
            conflicts.append({
                "recommendation_id": rec_id,
                "machine_id": m_id,
                "type": "Technician Allocation Conflict",
                "details": f"All qualified {req_specialization} technicians busy during target window {chosen_window[0].strftime('%Y-%m-%d %H:%M')}.",
            })
            assigned_tech = cand_techs.iloc[0].to_dict()  # Allocate with conflict flag

        # Compile Calendar Item
        est_labor_cost = duration_hrs * float(assigned_tech["hourly_rate"])
        est_total_cost = float(rec["estimated_maintenance_cost"]) + est_labor_cost

        item = {
            "schedule_id": f"SCHED-{m_id}-{chosen_window[0].strftime('%m%d%H')}",
            "recommendation_id": rec_id,
            "machine_id": m_id,
            "equipment_type": eq_type,
            "production_area": area,
            "priority": priority,
            "scheduled_start": chosen_window[0].strftime("%Y-%m-%d %H:%M:%S"),
            "scheduled_end": chosen_window[1].strftime("%Y-%m-%d %H:%M:%S"),
            "duration_hours": duration_hrs,
            "is_shutdown_window": "Planned Shutdown (Zero Disruption)" if is_shutdown_window else "Active Shift (Requires Derating)",
            "assigned_technician": f"{assigned_tech['name']} ({assigned_tech['specialization']})",
            "technician_id": assigned_tech["tech_id"],
            "allocated_part": part_allocated or "Standard Consumables Kit",
            "estimated_cost": round(est_total_cost, 2),
            "approval_status": rec["approval_status"],
            "action_summary": rec["suggested_action"],
        }
        calendar.append(item)

        # Automatically persist Work Orders if requested or approved
        if auto_create_work_orders or rec["approval_status"] == "Approved":
            create_or_update_work_order(item)

    return {
        "status": "OPTIMIZED",
        "total_scheduled": len(calendar),
        "calendar": calendar,
        "conflicts": conflicts,
        "infeasible_tasks": infeasible_tasks,
    }


def create_or_update_work_order(schedule_item: Dict[str, Any]) -> str:
    """Create or update formal maintenance work order in SQLite database."""
    wo_id = f"WO-{schedule_item['machine_id']}-{datetime.now().strftime('%Y%m%d%H%M')}"

    with get_connection() as conn:
        cursor = conn.cursor()
        # Check if already exists for recommendation
        cursor.execute(
            "SELECT work_order_id FROM maintenance_work_orders WHERE recommendation_id = ?;",
            (schedule_item["recommendation_id"],)
        )
        existing = cursor.fetchone()
        if existing:
            wo_id = existing[0]
            cursor.execute(
                """
                UPDATE maintenance_work_orders SET
                    scheduled_start = ?, scheduled_end = ?,
                    assigned_technician_id = ?, allocated_parts = ?,
                    estimated_cost = ?, updated_at = CURRENT_TIMESTAMP
                WHERE work_order_id = ?;
                """,
                (
                    schedule_item["scheduled_start"],
                    schedule_item["scheduled_end"],
                    schedule_item["technician_id"],
                    schedule_item["allocated_part"],
                    schedule_item["estimated_cost"],
                    wo_id
                )
            )
        else:
            cursor.execute(
                """
                INSERT INTO maintenance_work_orders (
                    work_order_id, recommendation_id, machine_id, task_priority,
                    scheduled_start, scheduled_end, assigned_technician_id,
                    allocated_parts, estimated_cost, status, actual_failure_occurred
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Scheduled', 0);
                """,
                (
                    wo_id,
                    schedule_item["recommendation_id"],
                    schedule_item["machine_id"],
                    schedule_item["priority"],
                    schedule_item["scheduled_start"],
                    schedule_item["scheduled_end"],
                    schedule_item["technician_id"],
                    schedule_item["allocated_part"],
                    schedule_item["estimated_cost"]
                )
            )
        conn.commit()

    log_audit("WORK_ORDER_CREATE", "maintenance_work_orders", wo_id, details=f"Scheduled for {schedule_item['machine_id']} ({schedule_item['scheduled_start']})")
    return wo_id
