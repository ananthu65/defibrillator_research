"""Overall result policy (P-017): one result for the whole procedure, with its explanation.

Applied in this order:
  1. any evaluated rule Fail                                         -> fail          (D-001)
  2. otherwise anything incomplete: a pending rule (D-055), an assumed
     result (D-060), timing not checked or limit not approved (D-062),
     an engine error (D-063), a timeline anomaly needing review
     (review_anomalies, D-069), or no rule evaluated at all           -> incomplete
  3. otherwise any Unable to Verify or Not evaluable (D-056)          -> the unable_to_verify_outcome
     setting: fail | faculty_review; while undecided, unable_to_verify (OQ-002)
  4. otherwise                                                        -> pass
A Fail on a timeline with a review anomaly stays Fail, flagged timeline_needs_review. Any result
built on annotation data (annotation_coverage_assumed) is marked as development data. A result
from a demo config (demo: true) is flagged demo_only: its rules are not approved (D-114).
"""
from dataclasses import dataclass
from rules.checks import LIMIT_NOT_APPROVED, ORDER_NOT_CHECKED, TIMING_NOT_CHECKED
from rules.coverage import ANNOTATION_COVERAGE_ASSUMED  # a header flag the engine carries onto every result (P-001)
from rules.outcome import ASSUMED, ENGINE_ERROR, FAIL, NOT_EVALUABLE, PENDING, UNABLE

PASS, INCOMPLETE, FACULTY_REVIEW, UNVERIFIED = "pass", "incomplete", "faculty_review", "unable_to_verify"
RESULTS = (PASS, FAIL, INCOMPLETE, FACULTY_REVIEW, UNVERIFIED)

TIMELINE_NEEDS_REVIEW = "timeline_needs_review"
DEVELOPMENT_DATA = "development_data"
OVERALL_POLICY_UNDECIDED = "overall_policy_undecided"
NO_RULES_EVALUATED = "no_rules_evaluated"
DEMO_ONLY = "demo_only"   # the config is a demo: its rules are marked approved without the supervisor (D-114)
FLAGS = (TIMELINE_NEEDS_REVIEW, DEVELOPMENT_DATA, OVERALL_POLICY_UNDECIDED, NO_RULES_EVALUATED, DEMO_ONLY)
DEMO_NOTICE = "DEMO ONLY: rules not approved by the supervisor"


@dataclass(frozen=True)
class Contribution:
    """One rule's part in the overall result. A same_as pair (R7/A6) is one entry (D-044)."""
    rule_ids: tuple[str, ...]
    kind: str
    reason: str
    failure_code: str | None = None
    title: str = ""
    category: str = ""   # why it makes the result incomplete (e.g. "timing not checked"), else empty


@dataclass(frozen=True)
class OverallResult:
    result: str                                   # pass | fail | incomplete | faculty_review | unable_to_verify
    summary: str
    deciding: tuple[Contribution, ...] = ()       # the rules that decided the result
    mistakes: tuple[Contribution, ...] = ()       # every Fail, with its failure code (named mistake)
    incomplete: tuple[Contribution, ...] = ()     # every rule that keeps the result from being complete
    unverified: tuple[Contribution, ...] = ()     # every Unable to Verify / Not evaluable rule
    decided_by: str = ""                          # the policy step or setting that decided it
    timeline_anomalies: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()
    development_data: bool = False


def decide(outcomes, config, anomalies=()):
    """outcomes: RuleOutcome per enabled rule (display order); anomalies: timeline anomaly codes."""
    pairs = _grouped(outcomes, config)
    groups = [group for group, _ in pairs]
    review = tuple(a for a in dict.fromkeys(anomalies) if a in config.engine.value("review_anomalies"))
    development = any(ANNOTATION_COVERAGE_ASSUMED in o.flags for o in outcomes)
    flags = ((DEVELOPMENT_DATA,) if development else ()) + ((DEMO_ONLY,) if getattr(config, "demo", False) else ())
    fails = tuple(g for g in groups if g.kind == FAIL)
    incomplete = tuple(_incomplete(pairs))
    unverified = tuple(g for g in groups if g.kind in (UNABLE, NOT_EVALUABLE))
    common = dict(mistakes=fails, incomplete=incomplete, unverified=unverified, timeline_anomalies=review,
                  development_data=development)

    if fails:
        flags += (TIMELINE_NEEDS_REVIEW,) if review else ()
        note = f"; the timeline needs review ({', '.join(review)})" if review else ""
        return OverallResult(FAIL, f"Fail: {_names(fails)} failed{note}", fails,
                             decided_by="any evaluated rule Fail (D-001)", flags=flags, **common)
    if not groups:
        return OverallResult(INCOMPLETE, "Incomplete: no rule was evaluated", (), decided_by="no rules evaluated",
                             flags=flags + (NO_RULES_EVALUATED,), **common)
    if incomplete or review:
        by_category = {}
        for c in incomplete:
            by_category.setdefault(c.category, []).append("/".join(c.rule_ids))
        parts = [f"{category} for {', '.join(ids)}" for category, ids in by_category.items()]
        parts += [f"the timeline needs review ({', '.join(review)})"] if review else []
        flags += (TIMELINE_NEEDS_REVIEW,) if review else ()
        return OverallResult(INCOMPLETE, "Incomplete: " + "; ".join(parts), incomplete,
                             decided_by="incomplete rules or a timeline needing review (D-055, D-060, D-062, D-063)",
                             flags=flags, **common)
    if unverified:
        setting = config.engine.settings["unable_to_verify_outcome"]
        if setting.value is None or setting.undecided:
            result, flags = UNVERIFIED, flags + (OVERALL_POLICY_UNDECIDED,)
        else:
            result = setting.value
        state = "undecided, OQ-002" if setting.undecided else "decided"
        return OverallResult(result, f"{result.replace('_', ' ').capitalize()}: {_names(unverified)} could not be "
                             "verified", unverified, decided_by=f"engine.yaml unable_to_verify_outcome = "
                             f"{setting.value} ({state}; D-042, D-056)", flags=flags, **common)
    return OverallResult(PASS, "Pass: every rule was evaluated and passed, with timing checked", (),
                         decided_by="every rule evaluated and passed", flags=flags, **common)


def _grouped(outcomes, config):
    """One Contribution per outcome, merging a same_as rule into the rule it reuses (R7/A6 once)."""
    definitions = {r.id: r for r in config.rules}
    groups, index = [], {}
    for outcome in outcomes:
        definition = definitions.get(outcome.rule_id)
        key = (definition.same_as if definition is not None and definition.same_as else outcome.rule_id)
        if key in index:
            entry = groups[index[key]]
            groups[index[key]] = Contribution(entry.rule_ids + (outcome.rule_id,), entry.kind, entry.reason,
                                              entry.failure_code, entry.title)
            continue
        index[key] = len(groups)
        title = definitions[key].title if key in definitions else outcome.rule_id
        groups.append(Contribution((outcome.rule_id,), outcome.kind, outcome.reason, outcome.failure_code, title))
    return _with_flags(groups, outcomes, definitions)


def _with_flags(groups, outcomes, definitions):
    flags = {o.rule_id: o.flags for o in outcomes}
    return [(group, flags[group.rule_ids[0]]) for group in groups]


def _incomplete(pairs):
    for group, flags in pairs:
        if group.kind == PENDING:
            yield _as(group, "rules not yet approved")
        elif group.kind == ASSUMED:
            yield _as(group, "assumed result, to be checked by the evaluator")
        elif group.kind == ENGINE_ERROR:
            yield _as(group, "engine error")
        elif TIMING_NOT_CHECKED in flags or LIMIT_NOT_APPROVED in flags:
            yield _as(group, "limit not approved" if LIMIT_NOT_APPROVED in flags else "timing not checked")
        elif ORDER_NOT_CHECKED in flags:   # D-100: like unchecked timing (D-062), never an overall Pass
            yield _as(group, "order not checked")


def _as(group, category):
    return Contribution(group.rule_ids, group.kind, group.reason, group.failure_code, group.title, category)


def _names(contributions):
    return ", ".join("/".join(c.rule_ids) for c in contributions)
