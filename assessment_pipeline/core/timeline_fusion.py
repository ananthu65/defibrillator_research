import logging
from typing import List

from events import Event

logger = logging.getLogger(__name__)

DUPLICATE_WINDOW_SECONDS = 0.5


def _valid_timestamp(timestamp) -> bool:
    """Return True if the timestamp is a valid numeric value."""
    return isinstance(timestamp, (int, float))


def merge_timelines(
    audio_events: List[Event],
    video_events: List[Event],
) -> List[Event]:
    """
    Merge audio and video events into a single time-sorted timeline.

    Rules:
    - Invalid timestamps are skipped with a warning.
    - Events with the same event_name occurring within 0.5 seconds
      are treated as duplicates, keeping the higher-confidence event.
    """

    valid_events = []

    for event in list(audio_events) + list(video_events):
        if not _valid_timestamp(event.timestamp):
            logger.warning(
                "Skipping event '%s' due to invalid timestamp: %r",
                event.event_name,
                event.timestamp,
            )
            continue

        valid_events.append(event)

    valid_events.sort(key=lambda e: e.timestamp)

    merged = []

    for event in valid_events:
        duplicate_index = None

        for i, existing in enumerate(merged):
            if (
                existing.event_name == event.event_name
                and abs(existing.timestamp - event.timestamp)
                <= DUPLICATE_WINDOW_SECONDS
            ):
                duplicate_index = i
                break

        if duplicate_index is None:
            merged.append(event)
        else:
            if event.confidence > merged[duplicate_index].confidence:
                merged[duplicate_index] = event

    merged.sort(key=lambda e: e.timestamp)

    return merged