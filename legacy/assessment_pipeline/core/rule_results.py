"""
rule_results.py

Standard result objects returned by the Rule Evaluation Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class RuleResult(Enum):
    """Possible outcomes of rule evaluation."""

    PASS_DIRECT = "PASS_DIRECT"
    PASS_INFERRED = "PASS_INFERRED"
    FAIL = "FAIL"
    UNABLE_TO_ASSESS = "UNABLE_TO_ASSESS"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    CRITICAL_ERROR = "CRITICAL_ERROR"


class EvidenceType(Enum):
    """How the assessment evidence was obtained."""

    DIRECT = "DIRECT"
    INFERRED = "INFERRED"


@dataclass(frozen=True)
class CriterionEvaluation:
    """
    Standard output produced by every rule.
    """

    criterion_id: str
    result: RuleResult
    evidence_type: EvidenceType

    supporting_events: List[str] = field(default_factory=list)

    failure_reason: str = ""

    feedback_message: str = ""

    timestamps: List[float] = field(default_factory=list)