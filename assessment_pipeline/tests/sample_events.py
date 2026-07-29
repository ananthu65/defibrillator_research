"""
sample_events.py

Reusable event fixtures for testing the
Version 2 Defibrillation Assessment Pipeline.
"""

from assessment_pipeline.core.events import (
    Event,
    EventSource,
    EvidenceType,
)


def _event(
    name: str,
    timestamp: float,
) -> Event:
    """
    Create a standard test event.
    """

    return Event(
        event_name=name,
        timestamp=timestamp,
        source=EventSource.VIDEO,
        confidence=1.0,
        evidence_type=EvidenceType.DIRECT,
        raw_data={},
    )


def perfect_defibrillation_events() -> list[Event]:
    """
    Complete successful scenario.
    """

    return [
        _event("gel_applied", 1.0),
        _event("take_first_paddle", 2.0),
        _event("take_second_paddle", 3.0),
        _event("place_paddles", 4.0),
        _event("stop_chest_compressions", 9.0),
        _event("shock_button_pressed", 10.0),
        _event("shock_delivered", 10.2),
        _event("remove_paddles", 11.0),
        _event("start_chest_compressions", 11.8),
    ]


def delayed_cpr_events() -> list[Event]:
    """
    CPR restarted too late.
    """

    return [
        _event("gel_applied", 1.0),
        _event("take_first_paddle", 2.0),
        _event("take_second_paddle", 3.0),
        _event("place_paddles", 4.0),
        _event("stop_chest_compressions", 9.0),
        _event("shock_button_pressed", 10.0),
        _event("shock_delivered", 10.2),
        _event("remove_paddles", 11.0),
        _event("start_chest_compressions", 14.5),
    ]


def delayed_shock_events() -> list[Event]:
    """
    Shock delivered too late after stopping CPR.
    """

    return [
        _event("gel_applied", 1.0),
        _event("take_first_paddle", 2.0),
        _event("take_second_paddle", 3.0),
        _event("place_paddles", 4.0),
        _event("stop_chest_compressions", 9.0),
        _event("shock_button_pressed", 15.0),
        _event("shock_delivered", 15.2),
        _event("remove_paddles", 16.0),
        _event("start_chest_compressions", 16.5),
    ]


def missing_gel_events() -> list[Event]:
    """
    Gel application omitted.
    """

    return [
        _event("take_first_paddle", 2.0),
        _event("take_second_paddle", 3.0),
        _event("place_paddles", 4.0),
        _event("stop_chest_compressions", 9.0),
        _event("shock_button_pressed", 10.0),
        _event("shock_delivered", 10.2),
        _event("remove_paddles", 11.0),
        _event("start_chest_compressions", 11.8),
    ]


def inferred_button_press_events() -> list[Event]:
    """
    Button press intentionally omitted so the
    Rule Engine should infer it from shock delivery.
    """

    return [
        _event("gel_applied", 1.0),
        _event("take_first_paddle", 2.0),
        _event("take_second_paddle", 3.0),
        _event("place_paddles", 4.0),
        _event("stop_chest_compressions", 9.0),
        _event("shock_delivered", 10.2),
        _event("remove_paddles", 11.0),
        _event("start_chest_compressions", 11.8),
    ]


def empty_events() -> list[Event]:
    """
    Empty event stream.
    """

    return []