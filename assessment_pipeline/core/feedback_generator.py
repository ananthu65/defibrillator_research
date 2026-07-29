"""
feedback_generator.py

Version 2 Feedback Generator

Converts Rule Engine outputs into user-readable assessment
feedback.

The Feedback Generator performs no assessment.
It formats the results produced by the Rule Evaluation Engine.
"""

from assessment_pipeline.core.events import CriterionEvaluation, CriterionResult


class FeedbackGenerator:
    """
    Generates user-facing feedback from rule evaluation results.
    """

    def generate(self, evaluations: list[CriterionEvaluation]) -> list[str]:

        feedback = []

        for evaluation in evaluations:

            if evaluation.feedback_message:
                feedback.append(evaluation.feedback_message)
                continue

            if evaluation.result == CriterionResult.PASS_DIRECT:
                feedback.append(
                    f"{evaluation.criterion_id}: Passed."
                )

            elif evaluation.result == CriterionResult.PASS_INFERRED:
                feedback.append(
                    f"{evaluation.criterion_id}: Passed using inferred evidence."
                )

            elif evaluation.result == CriterionResult.FAIL:
                feedback.append(
                    f"{evaluation.criterion_id}: Failed. "
                    f"{evaluation.failure_reason}"
                )

            elif evaluation.result == CriterionResult.UNABLE_TO_ASSESS:
                feedback.append(
                    f"{evaluation.criterion_id}: Unable to assess."
                )

            elif evaluation.result == CriterionResult.MANUAL_REVIEW:
                feedback.append(
                    f"{evaluation.criterion_id}: Manual review required."
                )

            elif evaluation.result == CriterionResult.CRITICAL_ERROR:
                feedback.append(
                    f"{evaluation.criterion_id}: Critical safety error."
                )

        return feedback


def generate_feedback(
    evaluations: list[CriterionEvaluation],
) -> list[str]:
    """
    Convenience function.
    """

    generator = FeedbackGenerator()

    return generator.generate(evaluations)