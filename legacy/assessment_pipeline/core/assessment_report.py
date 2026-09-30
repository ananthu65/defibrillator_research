"""
assessment_report.py

Generates the final assessment checklist and feedback
from Rule Engine outputs.
"""

from dataclasses import dataclass, field

from assessment_pipeline.core.events import (
    CriterionEvaluation,
    CriterionResult,
)


@dataclass
class ChecklistItem:
    item_id: str
    description: str
    passed: bool
    inferred: bool = False
    comments: str = ""


@dataclass
class AssessmentReport:
    checklist: list[ChecklistItem] = field(default_factory=list)
    feedback: list[str] = field(default_factory=list)


CHECKLIST = {

    "R1": ("1.5", "Apply gel / pads"),

    "R2": ("2.1", "Takes one paddle at a time"),

    "R3": ("2.2", "Places paddles firmly on the chest"),

    "R4": ("2.3", "Presses both paddles simultaneously"),

    "R5": ("1.6", "DC Shock / Discharge"),

    "R6": ("2.4", "Takes off electric paddles after shock"),

    "R7": ("2.5", "Resumes chest compressions promptly"),

    "R8": ("1.4", "Stop chest compressions → Shock within 5 seconds"),
}


class AssessmentReportGenerator:

    def generate(
        self,
        evaluations: list[CriterionEvaluation],
    ) -> AssessmentReport:

        report = AssessmentReport()

        for evaluation in evaluations:

            if evaluation.criterion_id not in CHECKLIST:
                continue

            item_no, description = CHECKLIST[evaluation.criterion_id]

            passed = evaluation.result in (
                CriterionResult.PASS_DIRECT,
                CriterionResult.PASS_INFERRED,
            )

            inferred = (
                evaluation.result
                == CriterionResult.PASS_INFERRED
            )

            report.checklist.append(

                ChecklistItem(
                    item_id=item_no,
                    description=description,
                    passed=passed,
                    inferred=inferred,
                    comments=evaluation.failure_reason or "",
                )

            )

            if evaluation.feedback_message:
                report.feedback.append(
                    evaluation.feedback_message
                )

            elif evaluation.failure_reason:
                report.feedback.append(
                    evaluation.failure_reason
                )

        return report


def generate_assessment_report(
    evaluations: list[CriterionEvaluation],
) -> AssessmentReport:

    generator = AssessmentReportGenerator()

    return generator.generate(evaluations)