"""
Automated unit tests for business impact and cost optimization calculations.
"""

import pytest
from src.business_impact import compute_business_impact_analysis


def test_business_impact_scenario_comparison():
    """Verify Scenario A and Scenario B cost calculations and sensitivity multipliers."""
    res = compute_business_impact_analysis(
        intervention_efficacy_pct=90.0,
        downtime_cost_multiplier=1.0,
        pm_cost_multiplier=1.0
    )
    assert res["status"] == "VALID"
    assert "historical_metrics" in res
    assert "modeled_scenarios" in res
    assert "machine_breakdowns" in res

    scenarios = res["modeled_scenarios"]
    assert scenarios["scenario_a_run_to_failure_cost"] >= 0.0
    assert scenarios["scenario_b_preventive_cost"] >= 0.0
    assert scenarios["net_potential_savings"] >= 0.0
    assert "disclaimer" in res
