"""RuleOutcome: the rule engine's own result for one rule, before it becomes a shared RuleResult.

Kinds, and how the overall policy (P-017) treats them:
  pass_direct, pass_inferred, fail  -> evaluated
  unable_to_verify, not_evaluable   -> evaluated but not verified; count like Unable to Verify (D-056)
  pending, assumed                  -> not evaluated; the overall result cannot be Pass (D-055, D-060)
They map onto the existing shared statuses only (D-045, D-038): passes and fail keep their status,
everything else becomes unable_to_assess, told apart by the reason text.
"""
from dataclasses import dataclass, field, replace
import math
from schemas.rule_result import RuleResult, RuleStatus

PASS_DIRECT, PASS_INFERRED, FAIL = "pass_direct", "pass_inferred", "fail"
UNABLE, NOT_EVALUABLE, PENDING, ASSUMED = "unable_to_verify", "not_evaluable", "pending", "assumed"
KINDS = (PASS_DIRECT, PASS_INFERRED, FAIL, UNABLE, NOT_EVALUABLE, PENDING, ASSUMED)
PASSES = (PASS_DIRECT, PASS_INFERRED)
NOT_EVALUATED = (PENDING, ASSUMED)
_STATUS = {PASS_DIRECT: RuleStatus.PASS_DIRECT, PASS_INFERRED: RuleStatus.PASS_INFERRED, FAIL: RuleStatus.FAIL}


@dataclass(frozen=True)
class RuleOutcome:
    rule_id: str
    kind: str
    reason: str
    failure_code: str | None = None
    evidence: tuple[str, ...] = ()              # event IDs the result rests on
    timestamps: dict[str, float] = field(default_factory=dict)
    flags: tuple[str, ...] = ()                 # carried from every anchor, elapsed time and check used
    blocked_by: str | None = None               # not_evaluable: the rule or step it depends on
    timing_checked: bool | None = None          # None when the rule has no time limit

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown outcome kind {self.kind!r}")
        if not self.rule_id or not self.reason:
            raise ValueError("an outcome needs a rule ID and a reason")
        if (self.kind == FAIL) != (self.failure_code is not None):
            raise ValueError("a Fail needs a failure code, and only a Fail has one")
        if self.kind in PASSES and not self.evidence:
            raise ValueError("a Pass must cite the events it rests on")
        if (self.kind == NOT_EVALUABLE) != (self.blocked_by is not None):
            raise ValueError("not_evaluable needs blocked_by, and only not_evaluable has it")
        if any(not math.isfinite(t) or t < 0 for t in self.timestamps.values()):
            raise ValueError("timestamps must be finite and nonnegative")
        object.__setattr__(self, "flags", tuple(dict.fromkeys(self.flags)))
        object.__setattr__(self, "evidence", tuple(dict.fromkeys(self.evidence)))

    @property
    def passed(self):
        return self.kind in PASSES

    @property
    def evaluated(self):
        return self.kind not in NOT_EVALUATED

    def as_rule(self, rule_id):
        """The same outcome reported under another ID (same_as, e.g. A6 = R7, D-044)."""
        return replace(self, rule_id=rule_id)

    def to_rule_result(self):
        details = []
        if self.failure_code:
            details.append(f"failure code: {self.failure_code}")
        if self.kind in (UNABLE, NOT_EVALUABLE, PENDING, ASSUMED):
            details.append(self.kind.replace("_", " "))
        if self.timing_checked is False:
            details.append("timing not checked")
        if self.flags:
            details.append("flags: " + ", ".join(self.flags))
        reason = self.reason + (f" [{'; '.join(details)}]" if details else "")
        return RuleResult(self.rule_id, _STATUS.get(self.kind, RuleStatus.UNABLE_TO_ASSESS), reason,
                          list(self.evidence), dict(self.timestamps))


def flags_of(*sources):
    """Merge the flags of everything a result used (anchors, elapsed times, checks, missing outcomes)."""
    merged = []
    for source in sources:
        if source is None:
            continue
        merged.extend((source,) if isinstance(source, str) else getattr(source, "flags", source))
    return tuple(dict.fromkeys(merged))


def passed(rule_id, reason, evidence, *, inferred=False, uses=(), flags=(), timestamps=None, timing_checked=None):
    return RuleOutcome(rule_id, PASS_INFERRED if inferred else PASS_DIRECT, reason, None, tuple(evidence),
                       dict(timestamps or {}), flags_of(*uses, flags), None, timing_checked)


def failed(rule_id, code, reason, *, evidence=(), uses=(), flags=(), timestamps=None, timing_checked=None):
    return RuleOutcome(rule_id, FAIL, reason, code, tuple(evidence), dict(timestamps or {}),
                       flags_of(*uses, flags), None, timing_checked)


def unable(rule_id, reason, *, evidence=(), uses=(), flags=(), timestamps=None):
    return RuleOutcome(rule_id, UNABLE, reason, None, tuple(evidence), dict(timestamps or {}), flags_of(*uses, flags))


def not_evaluable(rule_id, blocked_by, reason, *, uses=(), flags=()):
    return RuleOutcome(rule_id, NOT_EVALUABLE, reason, flags=flags_of(*uses, flags), blocked_by=blocked_by)


def pending(rule_id, reason="pending supervisor-approved definition"):
    return RuleOutcome(rule_id, PENDING, reason)


def assumed(rule_id, reason, *, evidence=(), uses=(), flags=()):
    return RuleOutcome(rule_id, ASSUMED, reason, None, tuple(evidence), flags=flags_of(*uses, flags))
