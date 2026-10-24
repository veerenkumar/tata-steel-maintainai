"""
Automated unit tests for constraint-based maintenance scheduling optimizer.
"""

import pytest
from src.maintenance_scheduler import optimize_maintenance_schedule, get_required_specialization


def test_specialization_mapping():
    """Verify equipment types map to appropriate technical disciplines."""
    assert get_required_specialization("Industrial motors") == "Electrical"
    assert get_required_specialization("Hydraulic systems") == "Hydraulic"
    assert get_required_specialization("Blast furnace auxiliary equipment") == "Mechanical"
    assert get_required_specialization("Industrial fans and blowers") == "Mechanical"


def test_optimize_maintenance_schedule():
    """Verify schedule generation, technician matching, and conflict reporting."""
    result = optimize_maintenance_schedule(horizon_days=14, auto_create_work_orders=False)
    assert "status" in result
    assert "calendar" in result
    assert "conflicts" in result
    assert "infeasible_tasks" in result

    if result["calendar"]:
        item = result["calendar"][0]
        assert "machine_id" in item
        assert "scheduled_start" in item
        assert "assigned_technician" in item
        assert "estimated_cost" in item
