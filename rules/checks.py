"""Shared checks every rule uses, in the order of the rule ladder (P-014, diagrams.md (c)).

  1. depends()            rules it depends on evaluated and passed?            (P-019)
  2. requires()           facts it needs present (e.g. the shock time)?        (P-020)
  3. restart_ambiguity()  restart needed but timing-ambiguous?                 (P-021)
  4. occurrences()        evidence present: a valid occurrence → Pass,
                          only mistaken ones → Fail                            (P-022)
  5. missing()            weak or missing: approved inference first (D-057),
                          then ctx.missing() (coverage, low confidence)        (P-023)
  plus time_limit() / timed() for limits (P-024) and relation() for order (P-025).
  relation_between() / timed_between() compare two events, choosing the window by modality and
  treating a segment-timed audio event as an interval (D-125); partly_evaluable() is D-121.

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
ORDER_PARTIALLY_CHECKED = "order_partially_checked"   # some steps' order couldn't be checked (unseen, one segment)
TIMING_UNCERTAIN = "timing_uncertain"   # a limit can't be judged: segment-timed events straddle it (D-125)
FLAGS = (TIMING_NOT_CHECKED, LIMIT_NOT_APPROVED, ORDER_NOT_CHECKED, ORDER_PARTIALLY_CHECKED, TIMING_UNCERTAIN)

BEFORE, SIMULTANEOUS, AFTER = "before", "simultaneous", "after"


# ---- 1-3: can the rule be evaluated at all? -----------------------------------------------------

def depends(rule_id, depends_on, results):
    """P-019: a rule needing another rule's result is not evaluable unless that rule passed (D-119: a
    mistake in one step is never evidence of a mistake in another; a step fails only on its own evidence)."""
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


def partly_evaluable(rule_id, anchor, blocked_by, checked, *, evidence=(), timestamps=None, uses=(), flags=()):
    """D-121: the part needing `anchor` can't be judged, so the rule is not evaluable because of `blocked_by`;
    `checked` names the parts that were still checked (no mistake in them), with their evidence."""
    return not_evaluable(rule_id, blocked_by, f"not evaluable because of {blocked_by}: {anchor.reason}; checked: "
                         f"{checked}", uses=(anchor, *uses), flags=flags, evidence=evidence, timestamps=timestamps)


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


# ---- comparing two events: modality windows and segment-timed audio (D-123, D-125) ------------------

def segment_timed(event):
    """An audio command event carries its Whisper segment's start and end (D-125): the command itself lies
    somewhere in it. Word-timed events (metadata time_basis: word) and all video or annotation events are
    at their start."""
    return event.source == "audio" and event.metadata.get("time_basis") != "word"


def time_bounds(event):
    """(earliest, latest) time of an event."""
    return (event.start, event.end) if segment_timed(event) else (event.start, event.start)


def window_between(ctx, a, b):
    """The comparison window: cross_modal_tolerance_seconds between audio and non-audio events, else
    simultaneous_window_seconds."""
    if (a.source == "audio") != (b.source == "audio"):
        return ctx.config.engine.value("cross_modal_tolerance_seconds")
    return simultaneous_window(ctx)


def same_segment(a, b):
    """Two commands said in one Whisper segment: their mutual order is not known."""
    return segment_timed(a) and segment_timed(b) and (a.start, a.end) == (b.start, b.end)


def relation_between(ctx, a, b):
    """P-025 for two events: `a` before / simultaneous / after `b`. A segment-timed event may lie anywhere in its
    interval, so `a` is before `b` only when it is certainly before (beyond the window); overlapping intervals
    are a tie. For two point events this is relation()."""
    window = window_between(ctx, a, b)
    a_first, a_last = time_bounds(a)
    b_first, b_last = time_bounds(b)
    if a_last < b_first - window:
        return BEFORE
    if a_first > b_last + window:
        return AFTER
    return SIMULTANEOUS


def duration_bounds(start, end):
    """(shortest, longest) possible time from event `start` to event `end`."""
    (s_first, s_last), (e_first, e_last) = time_bounds(start), time_bounds(end)
    return max(0.0, e_first - s_last), max(0.0, e_last - s_first)


def bounded_time_limit(shortest, longest, limit):
    """P-024 on bounds (D-125): checked and within only if the longest possible duration is within the limit,
    checked and exceeded only if the shortest exceeds it; in between, timing_uncertain."""
    if shortest == longest:
        return time_limit(shortest, limit)
    check = time_limit(longest, limit)
    if not check.checked:   # no usable limit: as time_limit
        return check
    if longest <= limit.value:
        return TimingCheck(True, True, longest, limit.value,
                           f"{shortest:g}–{longest:g} s against a limit of {limit.value:g} s")
    if shortest > limit.value:
        return TimingCheck(True, False, shortest, limit.value,
                           f"{shortest:g}–{longest:g} s against a limit of {limit.value:g} s")
    return TimingCheck(False, None, None, limit.value, f"timing uncertain: {shortest:g}–{longest:g} s against a "
                       f"limit of {limit.value:g} s (segment-timed audio)", (TIMING_UNCERTAIN,))


def timed_between(rule_id, start, end, limit, *, code, what, evidence, uses=()):
    """Pass, Fail or (timing uncertain) Unable to Verify on a limit between two events, judged on bounds."""
    shortest, longest = duration_bounds(start, end)
    check = bounded_time_limit(shortest, longest, limit)
    uses = (*uses, check)
    timestamps = {"shortest_seconds": shortest, "longest_seconds": longest}
    if TIMING_UNCERTAIN in check.flags:
        return unable(rule_id, f"{what}: {check.note}", evidence=evidence, uses=uses, timestamps=timestamps)
    if check.checked and not check.within:
        return failed(rule_id, code, f"{what}: {check.note}", evidence=evidence, uses=uses, timestamps=timestamps,
                      timing_checked=True)
    return passed(rule_id, f"{what}: {check.note}", evidence, uses=uses, timestamps=timestamps,
                  timing_checked=check.checked)


__all__ = ["depends", "requires", "restart_ambiguity", "occurrences", "missing", "first_valid", "infer_from",
           "time_limit", "timed", "relation", "simultaneous_window", "Inference", "TimingCheck", "FLAGS", "flags_of",
           "partly_evaluable", "segment_timed", "time_bounds", "window_between", "same_segment", "relation_between",
           "duration_bounds", "bounded_time_limit", "timed_between"]
