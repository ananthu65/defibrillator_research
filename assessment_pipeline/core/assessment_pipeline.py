"""
assessment_pipeline.py

Main entry point for the rule-based assessment pipeline.

Pipeline

Timeline
    ↓
Rule Engine
    ↓
Feedback
    ↓
Assessment Results
"""

from assessment_pipeline.core.events import (
    Event,
    CriterionEvaluation,
)

from assessment_pipeline.core.rule_engine import (
    evaluate_rules,
)

from assessment_pipeline.core.feedback import (
    generate_feedback,
)


class AssessmentPipeline:
    """
    Executes the complete assessment pipeline.
    """

    def __init__(self, events: list[Event]):

        self.events = sorted(events, key=lambda e: e.timestamp)

    def run(self) -> list[CriterionEvaluation]:
        """
        Execute the assessment pipeline.
        """

        #
        # Evaluate Rules
        #

        evaluations = evaluate_rules(self.events)

        #
        # Generate Feedback
        #

        evaluations = generate_feedback(evaluations)

        return evaluations


def assess(events: list[Event]) -> list[CriterionEvaluation]:
    """
    Convenience function.

    Example
    -------
    results = assess(events)
    """

    pipeline = AssessmentPipeline(events)

    return pipeline.run()