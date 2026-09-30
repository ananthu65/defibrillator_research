"""
Audio Rule Evaluation Engine (Basic Version)

Current version checks:
1. Presence of required audio commands
2. Correct order of commands

Timing rules are NOT implemented yet.
"""

from events import CriterionEvaluation, CriterionResult

# ---------------------------------------------------------
# Expected audio sequence
# ---------------------------------------------------------

EXPECTED_AUDIO_SEQUENCE = [
    ("A1", "oxygen_away"),
    ("A2", "continue_chest_compressions"),
    ("A3", "all_stand_clear"),
    ("A4", "stop_chest_compressions"),
    ("A5", "start_chest_compressions"),
]


# ---------------------------------------------------------
# Helper
# ---------------------------------------------------------

def find_event(events, event_name):
    """
    Returns the first matching event.
    """

    for event in events:
        if event.event_name == event_name:
            return event

    return None


# ---------------------------------------------------------
# Presence Evaluation
# ---------------------------------------------------------

def evaluate_presence(events):
    """
    Evaluate whether each required audio event exists.
    """

    results = []

    for criterion_id, event_name in EXPECTED_AUDIO_SEQUENCE:

        event = find_event(events, event_name)

        if event is None:

            results.append(
                CriterionEvaluation(
                    criterion_id=criterion_id,
                    result=CriterionResult.FAIL,
                    supporting_events=[],
                    failure_reason="Event not detected",
                    feedback_message=f"{event_name} was not detected."
                )
            )

        else:

            results.append(
                CriterionEvaluation(
                    criterion_id=criterion_id,
                    result=CriterionResult.PASS_DIRECT,
                    supporting_events=[event_name],
                    feedback_message=f"{event_name} detected.",
                    timestamps={
                        "detected_at": event.timestamp
                    }
                )
            )

    return results


# ---------------------------------------------------------
# Order Evaluation
# ---------------------------------------------------------

def evaluate_order(events):
    """
    Returns a list of order violations.

    Empty list means correct order.
    """

    violations = []

    detected = []

    for _, event_name in EXPECTED_AUDIO_SEQUENCE:

        event = find_event(events, event_name)

        if event is not None:
            detected.append((event_name, event.timestamp))

    for i in range(len(detected) - 1):

        current_name, current_time = detected[i]
        next_name, next_time = detected[i + 1]

        expected_index_current = [
            e for _, e in EXPECTED_AUDIO_SEQUENCE
        ].index(current_name)

        expected_index_next = [
            e for _, e in EXPECTED_AUDIO_SEQUENCE
        ].index(next_name)

        if expected_index_current > expected_index_next:

            violations.append(
                {
                    "expected_before": next_name,
                    "observed_before": current_name
                }
            )

    return violations


# ---------------------------------------------------------
# Main Evaluation Function
# ---------------------------------------------------------

def evaluate_audio_rules(events):
    """
    Main function for audio rule evaluation.
    """

    presence_results = evaluate_presence(events)

    order_violations = evaluate_order(events)

    return {
        "presence_results": presence_results,
        "order_violations": order_violations,
    }