"""Consolidate adjacent observations of the same label, not clinical actions."""
from dataclasses import replace
from schemas.event import Event


def merge_observations(events: list[Event], max_gap: float = 0.1) -> list[Event]:
    if max_gap < 0:
        raise ValueError("max_gap must be nonnegative")
    groups = {}
    for event in events:
        key = (event.source, event.event_name, event.evidence_type, event.camera_angle)
        groups.setdefault(key, []).append(event)
    output = []
    for group in groups.values():
        current = None
        for event in sorted(group, key=lambda e: (e.start, e.end)):
            if current is not None and event.start <= current.end + max_gap:
                current = replace(current, end=max(current.end, event.end), confidence=max(current.confidence, event.confidence))
            else:
                if current is not None:
                    output.append(current)
                current = event
        if current is not None:
            output.append(current)
    return sorted(output, key=lambda e: (e.start, e.event_name))
