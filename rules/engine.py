"""New engine scaffold: no legacy assumptions are silently carried forward."""
from schemas.rule_result import RuleResult, RuleStatus
from importlib import import_module


def evaluate(events, config):
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported rules configuration")
    definitions = config.get("rules", [])
    identifiers = [r["id"] for r in definitions]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate rule IDs in config")
    event_ids = {e.event_id for e in events if e.event_id is not None}
    results = []
    for rule in definitions:
        if not rule.get("enabled", True):
            continue
        implementation = rule.get("implementation")
        if not implementation or rule.get("status") != "approved":
            results.append(RuleResult(rule["id"], RuleStatus.UNABLE_TO_ASSESS,
                                      "Pending supervisor-approved definition and new rule implementation"))
            continue
        module, separator, name = implementation.partition(":")
        if not separator or not module or not name:
            raise ValueError("Rule implementation must be module.path:function")
        settings = {**rule, "timing_limits": config.get("timing_limits", {})}
        result = getattr(import_module(module), name)(events, settings)
        if not isinstance(result, RuleResult) or result.rule_id != rule["id"]:
            raise TypeError(f"Rule {rule['id']} must return its own RuleResult")
        if not set(result.supporting_events) <= event_ids:
            raise ValueError(f"Rule {rule['id']} references evidence outside the supplied timeline")
        results.append(result)
    return results
