from events import Event, EventSource
from core.audio_rules import evaluate_audio_rules


def test_correct_audio_sequence():

    events = [

        Event(
            event_name="oxygen_away",
            timestamp=2.0,
            source=EventSource.AUDIO,
            confidence=0.95
        ),

        Event(
            event_name="continue_chest_compressions",
            timestamp=4.0,
            source=EventSource.AUDIO,
            confidence=0.95
        ),

        Event(
            event_name="all_stand_clear",
            timestamp=8.0,
            source=EventSource.AUDIO,
            confidence=0.95
        ),

        Event(
            event_name="stop_chest_compressions",
            timestamp=9.0,
            source=EventSource.AUDIO,
            confidence=0.95
        ),

        Event(
            event_name="start_chest_compressions",
            timestamp=16.0,
            source=EventSource.AUDIO,
            confidence=0.95
        ),
    ]

    results = evaluate_audio_rules(events)

    assert len(results["presence_results"]) == 5

    assert results["order_violations"] == []


def test_missing_command():

    events = [

        Event(
            event_name="oxygen_away",
            timestamp=2.0,
            source=EventSource.AUDIO,
            confidence=0.95
        ),

        Event(
            event_name="continue_chest_compressions",
            timestamp=4.0,
            source=EventSource.AUDIO,
            confidence=0.95
        ),
    ]

    results = evaluate_audio_rules(events)

    failed = [
        r for r in results["presence_results"]
        if r.result.value == "fail"
    ]

    assert len(failed) == 3


def test_wrong_order():

    events = [

        Event(
            event_name="oxygen_away",
            timestamp=2.0,
            source=EventSource.AUDIO,
            confidence=0.95
        ),

        Event(
            event_name="stop_chest_compressions",
            timestamp=5.0,
            source=EventSource.AUDIO,
            confidence=0.95
        ),

        Event(
            event_name="continue_chest_compressions",
            timestamp=7.0,
            source=EventSource.AUDIO,
            confidence=0.95
        ),
    ]

    results = evaluate_audio_rules(events)

    assert len(results["order_violations"]) == 1