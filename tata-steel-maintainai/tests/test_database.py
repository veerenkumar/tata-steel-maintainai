"""
Automated unit tests for SQLite database layer and audit logging.
"""

import pytest
import sqlite3
import pandas as pd
from datetime import datetime

from database.db import (
    get_connection,
    init_db,
    fetch_df,
    execute_query,
    log_audit,
    get_all_machines,
    get_machine_by_id,
)


def test_database_initialization_and_seeding():
    """Verify database initializes tables and seeds machines, technicians, and parts."""
    init_db(force_recreate=False)
    fleet = get_all_machines()
    assert len(fleet) >= 12
    assert "BF-PUMP-001" in fleet["machine_id"].values
    assert "RM-MOTOR-002" in fleet["machine_id"].values


def test_fetch_machine_by_id():
    """Verify single machine retrieval by ID."""
    machine = get_machine_by_id("BF-PUMP-001")
    assert machine is not None
    assert machine["machine_id"] == "BF-PUMP-001"
    assert machine["equipment_type"] == "Blast furnace auxiliary equipment"
    assert machine["criticality"] == "Tier 1 - Critical"

    missing = get_machine_by_id("NON-EXISTENT-999")
    assert missing is None


def test_audit_logging_and_querying():
    """Verify audit log insertion and retrieval."""
    action = "UNIT_TEST_ACTION"
    details = "Automated test verification string"
    log_audit(action_type=action, entity_type="test", entity_id="ID-1", details=details)

    df_audit = fetch_df("SELECT * FROM audit_logs WHERE action_type = ? ORDER BY id DESC LIMIT 1;", (action,))
    assert not df_audit.empty
    assert df_audit.iloc[0]["action_type"] == action
    assert df_audit.iloc[0]["details"] == details
