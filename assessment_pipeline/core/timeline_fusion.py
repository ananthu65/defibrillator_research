"""
timeline_fusion.py

Timeline Fusion Engine

Version 1 Responsibilities

- Merge audio events
- Merge video events
- Sort chronologically

No clinical reasoning is performed here.
"""

from assessment_pipeline.core.events import Event


def merge_timelines(
    audio_events: list[Event],
    video_events: list[Event]
) -> list[Event]:
    """
    Merge audio and video events into one chronological timeline.

    Parameters
    ----------
    audio_events
        Events detected by the audio analysis engine.

    video_events
        Events detected by the video analysis engine.

    Returns
    -------
    list[Event]
        Chronologically sorted timeline.
    """

    timeline = []

    timeline.extend(audio_events)

    timeline.extend(video_events)

    timeline.sort(key=lambda event: event.timestamp)

    return timeline