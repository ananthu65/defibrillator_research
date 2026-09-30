"""Stable temporal ordering without inventing cross-modal evidence."""
from dataclasses import replace
from schemas.event import Event


def merge_timeline(*streams: list[Event], offsets: dict[str, float] | None = None) -> list[Event]:
    offsets = offsets or {}
    merged = []
    for stream in streams:
        for event in stream:
            offset = offsets.get(event.source, 0.0)
            merged.append(replace(event, start=event.start + offset, end=event.end + offset))
    merged.sort(key=lambda e: (e.start, e.end, e.source, e.event_name))
    used_ids = {e.event_id for e in merged if e.event_id is not None}
    if len(used_ids) != sum(e.event_id is not None for e in merged):
        raise ValueError("Duplicate event IDs in timeline")
    for index, event in enumerate(merged):
        if event.event_id is None:
            identifier = f"event_{index + 1:06d}"
            while identifier in used_ids:
                identifier += "_"
            used_ids.add(identifier)
            merged[index] = replace(event, event_id=identifier)
    return merged
