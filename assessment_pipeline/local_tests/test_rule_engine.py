"""
test_rule_engine.py

Unit tests for Version 1 Rule Engine.
"""

from assessment_pipeline.core.events import (
    Event,
    EventSource,
    EvidenceType,
    CriterionResult,
)

from assessment_pipeline.core.rule_engine import (
    evaluate_rules,
)


def create_event(name: str, timestamp: float):

    return Event(
        event_name=name,
        timestamp=timestamp,
        source=EventSource.VIDEO,
        confidence=0.99,
        evidence_type=EvidenceType.DIRECT,
    )


def test_complete_procedure():

    events = [

        create_event("gel_applied", 1.0),

        create_event("take_first_paddle", 2.0),

        create_event("take_second_paddle", 3.0),

        create_event("place_paddles", 5.0),

        create_event("shock_button_pressed", 6.0),

        create_event("shock_delivered", 7.0),

        create_event("remove_paddles", 8.0),

        Event(
            event_name="start_chest_compressions",
            timestamp=10.0,
            source=EventSource.AUDIO,
            confidence=0.98,
            evidence_type=EvidenceType.DIRECT,
        ),

    ]

    results = evaluate_rules(events)

    assert len(results) == 7

    for result in results:

        assert result.result == CriterionResult.PASS_DIRECT


def test_missing_event():

    events = [

        create_event("gel_applied", 1.0),

        create_event("take_first_paddle", 2.0),

        create_event("take_second_paddle", 3.0),

        #
        # place_paddles is intentionally missing
        #

        create_event("shock_button_pressed", 6.0),

        create_event("shock_delivered", 7.0),

        create_event("remove_paddles", 8.0),

    ]

    results = evaluate_rules(events)

    r3 = next(r for r in results if r.criterion_id == "R3")

    assert r3.result == CriterionResult.FAIL


def test_wrong_order():

    events = [

        create_event("gel_applied", 1.0),

        create_event("take_second_paddle", 2.0),

        create_event("take_first_paddle", 3.0),

        create_event("place_paddles", 4.0),

        create_event("shock_button_pressed", 5.0),

        create_event("shock_delivered", 6.0),

        create_event("remove_paddles", 7.0),

    ]

    results = evaluate_rules(events)

    r2 = next(r for r in results if r.criterion_id == "R2")

    assert r2.result == CriterionResult.FAIL