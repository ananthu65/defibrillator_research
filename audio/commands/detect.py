"""Configurable phrase matches produce observations, never rubric scores."""
import re
from schemas.event import Event


def detect_commands(segments, phrases):
    events = []
    for segment in segments:
        text = re.sub(r"[^a-z0-9]+", " ", segment.text.lower()).strip()
        for event_name, alternatives in phrases.items():
            normalized = [re.sub(r"[^a-z0-9]+", " ", p.lower()).strip() for p in alternatives]
            if any(p and f" {p} " in f" {text} " for p in normalized):
                if segment.confidence is None:
                    raise ValueError("ASR confidence is required before emitting a command event")
                events.append(Event(event_name, segment.start, segment.end, "audio", segment.confidence,
                                    metadata={"text": segment.text, "confidence_kind": "asr_proxy"}))
    return events
