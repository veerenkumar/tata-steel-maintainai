"""
Automated unit tests for ML model inference and prediction engine.
"""

import pytest
from src.prediction_engine import predict_machine_failure, generate_fleet_predictions


def test_predict_machine_failure():
    """Verify single machine failure prediction returns valid probabilities and keys."""
    pred = predict_machine_failure("BF-PUMP-001", horizon_hours=72, persist=False)
    assert "failure_probability" in pred
    assert "risk_category" in pred
    assert "composite_risk_score" in pred
    assert "top_contributing_features" in pred
    assert "limitations_disclaimer" in pred

    prob = pred["failure_probability"]
    assert 0.0 <= prob <= 1.0

    score = pred["composite_risk_score"]
    assert 0.0 <= score <= 100.0


def test_generate_fleet_predictions():
    """Verify fleet-wide predictions cover all registered assets."""
    df_fleet = generate_fleet_predictions(horizon_hours=72, persist=False)
    assert len(df_fleet) >= 12
    assert "machine_id" in df_fleet.columns
    assert "failure_probability" in df_fleet.columns
    assert "risk_category" in df_fleet.columns
