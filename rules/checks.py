"""Shared checks every rule uses, in the order of the rule ladder (P-014, diagrams.md (c)).

  1. depends()            rules it depends on evaluated and passed?            (P-019)
  2. requires()           facts it needs present (e.g. the shock time)?        (P-020)
  3. restart_ambiguity()  restart needed but timing-ambiguous?                 (P-021)
  4. occurrences()        evidence present: a valid occurrence → Pass,
                          only mistaken ones → Fail                            (P-022)
  5. missing()            weak or missing: approved inference first (D-057),
                          then ctx.missing() (coverage, low confidence)        (P-023)
  plus time_limit() / timed() for limits (P-024) and relation() for order (P-025).

Every check returns either a RuleOutcome or None ("go on to the next step"). Every outcome carries
the flags of the anchors, elapsed times and checks it used (flags_of). Times are event start
times (D-011). Low confidence is never absence: every missing event goes through ctx.missing().
"""
from dataclasses import dataclass
from rules.coverage import LOW_CONFIDENCE_FLAG
from rules.outcome import failed, flags_of, not_evaluable, passed, unable

TIMING_NOT_CHECKED = "timing_not_checked"
LIMIT_NOT_APPROVED = "limit_not_approved"
ORDER_NOT_CHECKED = "order_not_checked"   # an order requirement is not set (e.g. R5's preceding steps, D-100)
FLAGS = (TIMING_NOT_CHECKED, LIMIT_NOT_APPROVED, ORDER_NOT_CHECKED)

BEFORE, SIMULTANEOUS, AFTER = "before", "simultaneous", "after"


# ---- 1-3: can the rule be evaluated at all? -----------------------------------------------------

def depends(rule_id, depends_on, results):
    """P-019: a rule needing another rule's result is not evaluable unless that rule passed (D-003)."""
    for dependency in depends_on:
        if dependency not in results:
            raise KeyError(f"{rule_id} depends on {dependency}, which has not been evaluated yet")
        result = results[dependency]
        if not result.passed:
            return not_evaluable(rule_id, dependency, f"not evaluable because of {dependency} "
                                 f"({result.kind.replace('_', ' ')})")
    return None


def requires(rule_id, anchor, blocked_by):
    """P-020: a missing fact (e.g. no shock time) makes the rule not evaluable because of the step providing it."""
    if anchor.present:
        return None
    return not_evaluable(rule_id, blocked_by, f"not evaluable because of {blocked_by}: {anchor.reason}", uses=(anchor,))


def restart_ambiguity(rule_id, ctx):
    """P-021: rules needing the restart (R7/A6, A8) give Unable to Verify when it is timing-ambiguous (D-054)."""
    anchor = ctx.anchor("start_compressions")
    if not anchor.ambiguous:
        return None
    return unable(rule_id, "the restart command cannot be identified: a start or resume command may have come "
                  "after the real shock", evidence=anchor.ambiguous, uses=(anchor,))


# ---- 4-5: evidence ------------------------------------------------------------------------------

def first_valid(events, valid=lambda event: True):
    """Repeated events: any valid occurrence satisfies the rule; the earliest valid one is cited (D-012)."""
    return next((event for event in events if valid(event)), None)


@dataclass(frozen=True)
class Inference:
    event_id: str
    event_name: str
    time: float


def infer_from(ctx, event_names):
    """The earliest confidently confirmed supporting event among event_names, or None."""
    found = sorted((e for name in event_names for e in ctx.named(name)), key=lambda e: (e.start, e.event_id))
    return Inference(found[0].event_id, found[0].event_name, found[0].start) if found else None


def occurrences(rule_id, ctx, event_name, *, valid, invalid_code, what, inference=(), window=None, uses=()):
    """P-022: a valid occurrence → Pass – Direct; only mistaken occurrences → Fail; none → missing()."""
    events = ctx.named(event_name)
    ok = first_valid(events, valid)
    if ok is not None:
        return passed(rule_id, f"{what} at {ok.start:g} s", (ok.event_id,), uses=uses, timestamps={event_name: ok.start})
    if events:
        weak = ctx.missing(event_name, window)
        if LOW_CONFIDENCE_FLAG in weak.flags:  # a low-confidence occurrence may have been the valid one
            return unable(rule_id, f"{what}: the confident occurrences are not valid, but a low-confidence one "
                          "may be", evidence=weak.low_confidence_event_ids, uses=(*uses, weak))
        return failed(rule_id, invalid_code, f"{what}: no occurrence is valid",
                      evidence=tuple(e.event_id for e in events), uses=uses, timestamps={event_name: events[0].start})
    return missing(rule_id, ctx, event_name, what=what, inference=inference, window=window, uses=uses)


def missing(rule_id, ctx, event_name, *, what, inference=(), window=None, code="missing", uses=()):
    """P-023: weak or missing evidence. An approved inference is checked first (D-057); otherwise
    ctx.missing() decides (P-008, P-013), so low-confidence evidence is never a Fail (D-010)."""
    if inference:
        support = infer_from(ctx, inference)
        if support is not None:
            return passed(rule_id, f"{what} inferred from {support.event_name} at {support.time:g} s",
                          (support.event_id,), inferred=True, uses=uses, timestamps={support.event_name: support.time})
    found = ctx.missing(event_name, window)
    reason = (f"{what}: no confident {event_name} (coverage {found.coverage.status}, {found.coverage.basis}; "
              f"decided by {found.decided_by})")
    if found.outcome == "fail":
        return failed(rule_id, code, reason, uses=(*uses, found))
    return unable(rule_id, reason, evidence=found.low_confidence_event_ids, uses=(*uses, found))


# ---- timing and order ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TimingCheck:
    checked: bool
    within: bool | None
    seconds: float | None
    limit: float | None
    note: str
    flags: tuple[str, ...] = ()


def time_limit(seconds, limit):
    """P-024: compare an interval with an approved clinical limit. A null (or unapproved) limit means
    "timing not checked": the rule then judges presence and order only (D-005). An approved
    "no limit" (no_limit: true) is a decision that timing doesn't matter: checked and within (D-103)."""
    if limit.no_limit:
        if limit.approved:
            return TimingCheck(True, True, seconds, None, "no time limit applies (approved)")
        return TimingCheck(False, None, seconds, None, "timing not checked: 'no limit' is not approved",
                           (TIMING_NOT_CHECKED, LIMIT_NOT_APPROVED))
    if limit.value is None:
        return TimingCheck(False, None, seconds, None, "timing not checked: no approved limit", (TIMING_NOT_CHECKED,))
    if not limit.approved:
        return TimingCheck(False, None, seconds, limit.value, "timing not checked: the limit is not approved",
                           (TIMING_NOT_CHECKED, LIMIT_NOT_APPROVED))
    if seconds is None:
        return TimingCheck(False, None, None, limit.value, "timing not checked: the interval could not be measured",
                           (TIMING_NOT_CHECKED,))
    return TimingCheck(True, seconds <= limit.value, seconds, limit.value,
                       f"{seconds:g} s against a limit of {limit.value:g} s")


def timed(rule_id, elapsed, limit, *, code, what, evidence, uses=()):
    """Pass or Fail on a time limit, carrying the flags of the elapsed time and of the check."""
    check = time_limit(elapsed.seconds, limit)
    uses = (*uses, elapsed, check)
    timestamps = {"seconds": elapsed.seconds} if elapsed.seconds is not None else {}
    if check.checked and not check.within:
        return failed(rule_id, code, f"{what}: {check.note}", evidence=evidence, uses=uses, timestamps=timestamps,
                      timing_checked=True)
    return passed(rule_id, f"{what}: {check.note}", evidence, uses=uses, timestamps=timestamps,
                  timing_checked=check.checked)


def relation(first, second, window):
    """P-025: how time `first` relates to `second`: before, simultaneous (within the window) or after."""
    if first is None or second is None:
        return None
    if abs(first - second) <= window:
        return SIMULTANEOUS
    return BEFORE if first < second else AFTER


def simultaneous_window(ctx):
    return ctx.config.engine.value("simultaneous_window_seconds")


__all__ = ["depends", "requires", "restart_ambiguity", "occurrences", "missing", "first_valid", "infer_from",
           "time_limit", "timed", "relation", "simultaneous_window", "Inference", "TimingCheck", "FLAGS", "flags_of"]
