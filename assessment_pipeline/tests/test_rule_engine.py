"""
test_rule_engine.py

Unit tests for the Version 2 Rule Engine.
"""

import pytest

from assessment_pipeline.core.events import CriterionResult
from assessment_pipeline.core.rule_engine import evaluate_rules

from assessment_pipeline.tests.sample_events import (
    perfect_defibrillation_events,
    delayed_cpr_events,
    delayed_shock_events,
    missing_gel_events,
    inferred_button_press_events,
    empty_events,
)


def _find(results, criterion_id):
    """
    Return the evaluation for a criterion.
    """

    for result in results:
        if result.criterion_id == criterion_id:
            return result

    raise AssertionError(f"{criterion_id} not found.")


# ------------------------------------------------------------------
# Perfect Scenario
# ------------------------------------------------------------------

def test_perfect_scenario_passes():
    events = perfect_defibrillation_events()

    results = evaluate_rules(events)

    for criterion in results:
        assert criterion.result in (
            CriterionResult.PASS_DIRECT,
            CriterionResult.PASS_INFERRED,
        )


# ------------------------------------------------------------------
# Missing Event
# ------------------------------------------------------------------

def test_missing_gel_fails():
    events = missing_gel_events()

    results = evaluate_rules(events)

    r1 = _find(results, "R1")

    assert r1.result == CriterionResult.FAIL


# ------------------------------------------------------------------
# Timing Rule R7
# ------------------------------------------------------------------

def test_delayed_cpr_fails():
    events = delayed_cpr_events()

    results = evaluate_rules(events)

    r7 = _find(results, "R7")

    assert r7.result == CriterionResult.FAIL


# ------------------------------------------------------------------
# Timing Rule R8
# ------------------------------------------------------------------

def test_delayed_shock_fails():
    events = delayed_shock_events()

    results = evaluate_rules(events)

    r8 = _find(results, "R8")

    assert r8.result == CriterionResult.FAIL


# ------------------------------------------------------------------
# Inference
# ------------------------------------------------------------------

def test_button_press_can_be_inferred():
    events = inferred_button_press_events()

    results = evaluate_rules(events)

    r4 = _find(results, "R4")

    assert r4.result == CriterionResult.PASS_INFERRED


# ------------------------------------------------------------------
# Empty Timeline
# ------------------------------------------------------------------

def test_empty_timeline():
    events = empty_events()

    results = evaluate_rules(events)

    assert len(results) > 0

    for result in results:

        assert result.result in (
            CriterionResult.FAIL,
            CriterionResult.UNABLE_TO_ASSESS,
            CriterionResult.MANUAL_REVIEW,
            CriterionResult.CRITICAL_ERROR,
        )


# ------------------------------------------------------------------
# Rule Count
# ------------------------------------------------------------------

def test_all_rules_are_evaluated():
    events = perfect_defibrillation_events()

    results = evaluate_rules(events)

    rule_ids = {
        result.criterion_id
        for result in results
    }

    assert rule_ids == {
        "R1",
        "R2",
        "R3",
        "R4",
        "R5",
        "R6",
        "R7",
        "R8",
    }


# ------------------------------------------------------------------
# Evaluation Type
# ------------------------------------------------------------------

def test_returns_criterion_evaluations():
    events = perfect_defibrillation_events()

    results = evaluate_rules(events)

    assert isinstance(results, list)

    assert len(results) > 0