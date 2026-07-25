"""
events.py

Shared event data structures used across all pipeline engines
(Timeline Fusion, Clinical Logic, Rule Evaluation, Scoring).

Every engine consumes and/or produces objects built from this schema,
so this file should not depend on any other engine's code.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EventSource(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"


class EvidenceType(str, Enum):
    DIRECT = "direct"       # directly observed
    INFERRED = "inferred"   # derived from a supporting event, per approved inference rules


@dataclass
class Event:
    """A single detected occurrence — one row of the unified timeline."""
    event_name: str          # e.g. "gel_applied", "shock_delivered_on_screen", "audio_all_stand_clear"
    timestamp: float         # seconds from start of video
    source: EventSource
    confidence: float        # 0.0-1.0
    evidence_type: EvidenceType = EvidenceType.DIRECT
    inferred_from: Optional[str] = None  # event_name of the supporting event, if inferred
    raw_data: dict = field(default_factory=dict)  # anything engine-specific (bounding box, transcript text, etc.)


class CriterionResult(str, Enum):
    PASS_DIRECT = "pass_direct"
    PASS_INFERRED = "pass_inferred"
    FAIL = "fail"
    UNABLE_TO_ASSESS = "unable_to_assess"
    MANUAL_REVIEW = "manual_review"
    CRITICAL_ERROR = "critical_error"


@dataclass
class CriterionEvaluation:
    """Output of the Rule Evaluation Engine for a single criterion (R1-R7, A1-A7)."""
    criterion_id: str        # e.g. "R1", "A3"
    result: CriterionResult
    evidence_type: Optional[EvidenceType] = None
    supporting_events: list = field(default_factory=list)  # event_names used as evidence
    failure_reason: Optional[str] = None
    feedback_message: str = ""
    timestamps: dict = field(default_factory=dict)  # any timestamps relevant to this decision