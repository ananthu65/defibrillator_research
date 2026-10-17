"""Render an Assessment as a JSON-serialisable report (P-027).

The report's structure is the contract with the feedback module and the app, documented in
docs/rule_engine/output_contract.md. REPORT_VERSION changes whenever that structure changes
(D-070), and the contract document must change with it (checked by tests).
"""
from dataclasses import asdict

REPORT_VERSION = 3   # 2: count anomalies (D-071); 3: header visibility and flags (D-092, Increment 10)
REPORT_KIND = "rule_engine_report"


def report(assessment):
    """The full report for one Assessment, as plain dicts and lists (json.dumps-ready)."""
    overall = assessment.overall
    config = assessment.config
    titles = {r.id: r.title for r in config.rules}
    return {
        "report_version": REPORT_VERSION,
        "kind": REPORT_KIND,
        "development_data": overall.development_data,
        "overall": _overall(overall),
        "rules": [_rule(o, titles.get(o.rule_id, o.rule_id)) for o in assessment.outcomes],
        "timeline": _timeline(assessment.prepared),
        "context": _context(assessment.context),
        "configuration": _configuration(config),
    }


def _contributions(items):
    return [_plain(asdict(c)) for c in items]


def _overall(overall):
    contributions = _contributions
    return {"result": overall.result, "summary": overall.summary, "decided_by": overall.decided_by,
            "flags": list(overall.flags), "timeline_anomalies": list(overall.timeline_anomalies),
            "deciding": contributions(overall.deciding), "mistakes": contributions(overall.mistakes),
            "incomplete": contributions(overall.incomplete), "unverified": contributions(overall.unverified)}


def _rule(outcome, title):
    shared = outcome.to_rule_result()
    return {"rule_id": outcome.rule_id, "title": title, "kind": outcome.kind, "status": shared.status.value,
            "evaluated": outcome.evaluated, "passed": outcome.passed, "reason": outcome.reason,
            "shared_reason": shared.reason, "failure_code": outcome.failure_code,
            "evidence": list(outcome.evidence), "timestamps": dict(outcome.timestamps),
            "flags": list(outcome.flags), "blocked_by": outcome.blocked_by,
            "timing_checked": outcome.timing_checked}


def _issue(item):
    return {"event_id": item.event_id, "source": item.source, "label": item.label}


def _timeline(prepared):
    issue = _issue
    return {"events": [e.to_dict() for e in prepared.events],
            "excluded": [_plain(asdict(e)) for e in prepared.excluded],
            "anomalies": [_plain(asdict(a)) for a in prepared.anomalies],
            "unknown_labels": [issue(i) for i in prepared.unknown_labels],
            "unused_labels": [issue(i) for i in prepared.unused_labels],
            "unresolved_labels": [issue(i) for i in prepared.unresolved_labels],
            "sources": sorted(prepared.sources)}


def _context(ctx):
    header = ctx.coverage.header
    return {"header": None if header is None else _plain(asdict(header)),
            "anchors": {name: _plain(asdict(anchor)) for name, anchor in ctx.anchors.items()},
            "resolutions": [_plain(asdict(r)) for r in ctx.resolutions],
            "zone_visibility": {region: _plain(asdict(status)) for region, status in ctx.zone_visibility.items()}}


def _configuration(config):
    return {"placeholders": config.engine.placeholders, "undecided": config.engine.undecided,
            "timing_limits": {name: {**_plain(asdict(value)), "approved": value.approved}
                              for name, value in config.timing_limits.items()},
            "rules": [{"id": r.id, "status": r.status, "enabled": r.enabled, "same_as": r.same_as,
                       "depends_on": list(r.depends_on)} for r in config.rules]}


def _plain(value):
    """Tuples to lists, recursively, so the report compares equal to its own JSON round trip."""
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value

