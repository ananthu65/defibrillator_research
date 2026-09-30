"""
feedback.py

Version 2 Feedback Generator

Populates feedback messages for each evaluated criterion.
"""

from assessment_pipeline.core.events import (
    CriterionEvaluation,
    CriterionResult,
)


PASS_MESSAGES = {
    "R1": "Gel/pads were applied correctly.",
    "R2": "Paddles were picked up one at a time.",
    "R3": "Paddles were placed firmly on the chest.",
    "R4": "Shock buttons were pressed correctly.",
    "R5": "Shock was successfully delivered.",
    "R6": "Paddles were removed after shock delivery.",
    "R7": "Chest compressions resumed promptly after shock.",
    "R8": "Shock was delivered within 5 seconds after stopping chest compressions.",
}


FAIL_MESSAGES = {
    "R1": "Apply gel/pads before attempting defibrillation.",
    "R2": "Pick up one paddle before taking the second.",
    "R3": "Place both paddles firmly on the patient's chest.",
    "R4": "Press both discharge buttons simultaneously.",
    "R5": "Deliver the shock after pressing both discharge buttons.",
    "R6": "Remove the paddles after shock delivery.",
    "R7": "Resume chest compressions within 2 seconds after shock.",
    "R8": "Deliver the shock within 5 seconds after stopping chest compressions.",
}


INFERRED_MESSAGES = {
    "R3": "Paddle placement was inferred from subsequent events.",
    "R4": "Button press was inferred from shock delivery.",
}


def generate_feedback(
    evaluations: list[CriterionEvaluation],
) -> list[CriterionEvaluation]:
    """
    Populate feedback messages for every criterion.
    """

    for evaluation in evaluations:

        if evaluation.result == CriterionResult.PASS_DIRECT:

            evaluation.feedback_message = PASS_MESSAGES.get(
                evaluation.criterion_id,
                "Criterion passed.",
            )

        elif evaluation.result == CriterionResult.PASS_INFERRED:

            evaluation.feedback_message = INFERRED_MESSAGES.get(
                evaluation.criterion_id,
                "Criterion passed using inferred evidence.",
            )

        elif evaluation.result == CriterionResult.FAIL:

            evaluation.feedback_message = FAIL_MESSAGES.get(
                evaluation.criterion_id,
                evaluation.failure_reason or "Criterion failed.",
            )

        elif evaluation.result == CriterionResult.UNABLE_TO_ASSESS:

            evaluation.feedback_message = (
                "Insufficient evidence to assess this criterion."
            )

        elif evaluation.result == CriterionResult.MANUAL_REVIEW:

            evaluation.feedback_message = (
                "Manual review is required."
            )

        elif evaluation.result == CriterionResult.CRITICAL_ERROR:

            evaluation.feedback_message = (
                "Critical safety error detected."
            )

    return evaluations