"""
assessment_pipeline.py

Version 2 Assessment Pipeline

Pipeline

Timeline
    ↓
Clinical Logic
    ↓
Rule Engine
    ↓
Feedback
    ↓
Final Assessment Report
"""

from assessment_pipeline.core.events import Event

from assessment_pipeline.core.clinical_logic import (
    apply_clinical_logic,
)

from assessment_pipeline.core.rule_engine import (
    evaluate_rules,
)

from assessment_pipeline.core.feedback import (
    generate_feedback,
)

from assessment_pipeline.core.final_assessment import (
    build_final_assessment,
)


class AssessmentPipeline:
    """
    Executes the complete Version 2 assessment pipeline.
    """

    def __init__(self, events: list[Event]):

        self.events = sorted(events, key=lambda e: e.timestamp)

    def run(self):

        #
        # Clinical Logic
        #

        clinical_events = apply_clinical_logic(
            self.events
        )

        #
        # Rule Evaluation
        #

        evaluations = evaluate_rules(
            clinical_events
        )

        #
        # Feedback Generation
        #

        evaluations = generate_feedback(
            evaluations
        )

        #
        # Final Assessment Report
        #

        report = build_final_assessment(
            evaluations
        )

        return report


def assess(events: list[Event]):
    """
    Convenience function.
    """

    pipeline = AssessmentPipeline(events)

    return pipeline.run()