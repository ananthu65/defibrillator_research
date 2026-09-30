"""
final_assessment.py

Builds the final assessment output produced by the pipeline.
"""

from assessment_pipeline.core.events import CriterionEvaluation
from assessment_pipeline.core.assessment_report import (
    AssessmentReport,
    generate_assessment_report,
)


class FinalAssessment:

    def __init__(self, evaluations: list[CriterionEvaluation]):

        self.evaluations = evaluations

    def generate(self) -> AssessmentReport:

        return generate_assessment_report(
            self.evaluations
        )


def build_final_assessment(
    evaluations: list[CriterionEvaluation],
) -> AssessmentReport:

    assessment = FinalAssessment(evaluations)

    return assessment.generate()