"""
clinical_logic.py

Clinical Logic Engine

Version 1

The engine currently forwards the timeline unchanged.

Future versions may infer additional clinical events
based on combinations of audio and video evidence.
"""

from assessment_pipeline.core.events import Event


def apply_clinical_logic(
    timeline: list[Event]
) -> list[Event]:
    """
    Apply clinical interpretation to the timeline.

    Version 1 performs no inference.

    Parameters
    ----------
    timeline
        Chronological event timeline.

    Returns
    -------
    list[Event]
        Timeline ready for rule evaluation.
    """

    return timeline