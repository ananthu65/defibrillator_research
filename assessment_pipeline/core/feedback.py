"""
feedback.py

Generates human-readable feedback from rule evaluations.

Version 1:
- Fixed PASS/FAIL messages.
- No scoring.
"""

from assessment_pipeline.core.events import (
    CriterionEvaluation,
    CriterionResult,
)


PASS_MESSAGES = {
    "R1": "Gel was applied correctly.",
    "R2": "Paddles were taken one at a time.",
    "R3": "Paddles were placed correctly.",
    "R4": "Shock button was pressed correctly.",
    "R5": "Shock delivery was confirmed.",
    "R6": "Paddles were removed after shock.",
    "R7": "Chest compressions were restarted promptly.",
}


FAIL_MESSAGES = {
    "R1": "Apply gel before using the paddles.",
    "R2": "Take one paddle first, then the second paddle.",
    "R3": "Place both paddles correctly before shock.",
    "R4": "Press the shock button only after correct paddle placement.",
    "R5": "Deliver the shock after completing the required steps.",
    "R6": "Remove the paddles after shock delivery.",
    "R7": "Restart chest compressions after shock.",
}


def generate_feedback(
    evaluations: list[CriterionEvaluation],
) -> list[CriterionEvaluation]:
    """
    Adds feedback messages to each CriterionEvaluation.

    Returns the same list with feedback populated.
    """

    for evaluation in evaluations:

        if evaluation.result in (
            CriterionResult.PASS_DIRECT,
            CriterionResult.PASS_INFERRED,
        ):

            evaluation.feedback_message = PASS_MESSAGES.get(
                evaluation.criterion_id,
                "Criterion passed.",
            )

        elif evaluation.result == CriterionResult.FAIL:

            evaluation.feedback_message = FAIL_MESSAGES.get(
                evaluation.criterion_id,
                evaluation.failure_reason or "Criterion failed.",
            )

        elif evaluation.result == CriterionResult.UNABLE_TO_ASSESS:

            evaluation.feedback_message = (
                "Unable to assess this criterion."
            )

        elif evaluation.result == CriterionResult.MANUAL_REVIEW:

            evaluation.feedback_message = (
                "Manual review is required."
            )

        elif evaluation.result == CriterionResult.CRITICAL_ERROR:

            evaluation.feedback_message = (
                "Critical error detected."
            )

    return evaluations