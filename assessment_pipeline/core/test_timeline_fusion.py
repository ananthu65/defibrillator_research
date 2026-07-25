import logging

import pytest

from events import Event, EventSource
from timeline_fusion import merge_timelines


def test_normal_merge():
    audio = [
        Event(
            event_name="oxygen_away",
            timestamp=2.0,
            source=EventSource.AUDIO,
            confidence=0.90,
        )
    ]

    video = [
        Event(
            event_name="gel_applied",
            timestamp=1.0,
            source=EventSource.VIDEO,
            confidence=0.95,
        )
    ]

    merged = merge_timelines(audio, video)

    assert len(merged) == 2
    assert merged[0].event_name == "gel_applied"
    assert merged[1].event_name == "oxygen_away"


def test_duplicate_event_within_half_second():
    audio = [
        Event(
            event_name="shock_delivered",
            timestamp=10.2,
            source=EventSource.AUDIO,
            confidence=0.82,
        )
    ]

    video = [
        Event(
            event_name="shock_delivered",
            timestamp=10.5,
            source=EventSource.VIDEO,
            confidence=0.94,
        )
    ]

    merged = merge_timelines(audio, video)

    assert len(merged) == 1
    assert merged[0].confidence == 0.94
    assert merged[0].source == EventSource.VIDEO


def test_missing_timestamp_is_skipped(caplog):
    audio = [
        Event(
            event_name="oxygen_away",
            timestamp=None,
            source=EventSource.AUDIO,
            confidence=0.90,
        )
    ]

    video = [
        Event(
            event_name="gel_applied",
            timestamp=1.0,
            source=EventSource.VIDEO,
            confidence=0.95,
        )
    ]

    with caplog.at_level(logging.WARNING):
        merged = merge_timelines(audio, video)

    assert len(merged) == 1
    assert merged[0].event_name == "gel_applied"
    assert "Skipping event" in caplog.text