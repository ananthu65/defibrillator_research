"""
clinical_logic.py

Clinical Logic Engine

Version 2

Applies deterministic clinical inference to the unified event
timeline before rule evaluation.
"""

from assessment_pipeline.core.events import (
    Event,
    EvidenceType,
)


def apply_clinical_logic(
    timeline: list[Event],
) -> list[Event]:
    """
    Apply deterministic clinical inference.

    Current Version 2:
    - No new events are created.
    - Timeline is returned unchanged.

    Future versions may infer additional events while
    preserving the original observations.
    """

    return sorted(
        timeline,
        key=lambda event: event.timestamp,
    )


# ------------------------------------------------------------------
# Helper Functions (reserved for future inference logic)
# ------------------------------------------------------------------

def create_inferred_event(
    event_name: str,
    timestamp: float,
    source_event: Event,
) -> Event:
    """
    Create an inferred event from an observed event.

    This function is reserved for future inference rules.
    """

    return Event(
        event_name=event_name,
        timestamp=timestamp,
        source=source_event.source,
        confidence=source_event.confidence,
        evidence_type=EvidenceType.INFERRED,
        inferred_from=source_event.event_name,
        raw_data=source_event.raw_data,
    )