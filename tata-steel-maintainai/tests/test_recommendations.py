"""
Automated unit tests for recommendation engine and human decision workflow.
"""

import pytest
from src.recommendation_engine import (
    generate_recommendation_for_machine,
    generate_fleet_recommendations,
    update_recommendation_decision,
)
from database.db import fetch_df


def test_generate_recommendation():
    """Verify recommendation generation and fields."""
    rec = generate_recommendation_for_machine("BF-PUMP-001", persist=True)
    assert rec is not None
    assert "recommendation_id" in rec
    assert "suggested_action" in rec
    assert "priority" in rec
    assert "estimated_maintenance_cost" in rec
    assert rec["approval_status"] == "Pending"


def test_update_recommendation_decision_workflow():
    """Verify approve, reject, defer decisions persist in database."""
    rec = generate_recommendation_for_machine("RM-MOTOR-002", persist=True)
    rec_id = rec["recommendation_id"]

    # Approve
    res = update_recommendation_decision(rec_id, "Approved", notes="Approved during shift meeting", decided_by="Chief Engineer")
    assert res["success"] is True

    # Verify persisted in DB
    df = fetch_df("SELECT * FROM maintenance_recommendations WHERE recommendation_id = ?;", (rec_id,))
    assert df.iloc[0]["approval_status"] == "Approved"
    assert df.iloc[0]["approved_by"] == "Chief Engineer"
