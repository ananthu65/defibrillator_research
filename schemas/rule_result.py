"""Rule decisions, kept separate from model observations."""
from dataclasses import asdict, dataclass, field
from enum import Enum
import math


class RuleStatus(str, Enum):
    PASS_DIRECT = "pass_direct"
    PASS_INFERRED = "pass_inferred"
    FAIL = "fail"
    UNABLE_TO_ASSESS = "unable_to_assess"
    MANUAL_REVIEW = "manual_review"
    CRITICAL_ERROR = "critical_error"


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    status: RuleStatus
    reason: str
    supporting_events: list[str] = field(default_factory=list)
    timestamps: dict[str, float] = field(default_factory=dict)
    schema_version: int = 1

    def __post_init__(self):
        if self.schema_version != 1:
            raise ValueError("Unsupported rule-result schema version")
        object.__setattr__(self, "status", RuleStatus(self.status))
        if not self.rule_id or not self.reason:
            raise ValueError("Rule results require an ID and a reason")
        if any(not math.isfinite(t) or t < 0 for t in self.timestamps.values()):
            raise ValueError("Rule timestamps must be finite and nonnegative")
        if self.status in {RuleStatus.PASS_DIRECT, RuleStatus.PASS_INFERRED} and not self.supporting_events:
            raise ValueError("Passing results must identify supporting event IDs")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        return cls(**value)
