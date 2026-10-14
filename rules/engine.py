"""Rule engine: run every rule on one timeline, in evaluation order, and report in display order.

    events + config ──► prepare (P-002..P-005) ──► context (P-006..P-013) ──► each rule (P-014) ──► outcomes

`assess()` returns the full Assessment. `evaluate()` keeps its original signature and returns the
shared RuleResult list that pipeline/run.py expects.

Every rule is always evaluated (D-002). Pending rules are reported as pending (D-043). A rule
reusing another's check (same_as) reports that rule's outcome under its own ID (D-044). A rule
whose dependencies did not pass is not evaluable because of them (D-003). A registered rule that
raises, or returns something invalid, is recorded as engine_error and never stops the other
rules (D-063).
"""
from dataclasses import asdict, dataclass
from importlib import import_module
from rules import checks
from rules import registry as rule_registry
from rules.config import DEFAULT_PATH as CATALOGUE_PATH, RuleEngineConfig, load_rules_config
from rules.context import build_context
from rules.errors import RegistryError
from rules.outcome import FAIL, PASS_DIRECT, PASS_INFERRED, UNABLE, RuleOutcome, engine_error, pending
from rules.policy import decide
from rules.prepare import prepare_timeline
from schemas.rule_result import RuleResult, RuleStatus

DISABLED_REASON = "Disabled in configuration"
UNSPECIFIED_FAILURE = "unspecified"   # a shared-contract path rule's Fail carries no failure code
FAILURE_CODES = (UNSPECIFIED_FAILURE,)


@dataclass(frozen=True)
class Assessment:
    outcomes: tuple[RuleOutcome, ...]   # enabled rules, in display order
    prepared: object
    context: object
    config: RuleEngineConfig
    overall: object = None              # OverallResult (P-017)

    def outcome(self, rule_id):
        return next(o for o in self.outcomes if o.rule_id == rule_id)


def assess(events, config, header=None, registry=None):
    """Assess one timeline. Raises ConfigError / TimelineError when no assessment can be produced."""
    config = config if isinstance(config, RuleEngineConfig) else RuleEngineConfig.from_dict(config)
    registry = rule_registry.discover() if registry is None else registry
    _check_registry(registry, config)
    events = list(events)
    prepared = prepare_timeline(events, config)
    context = build_context(prepared, config, header)
    event_ids = {e.event_id for e in events}
    definitions = {r.id: r for r in config.rules}
    results = {}
    for rule_id in config.evaluation_order():
        results[rule_id] = _evaluate(definitions[rule_id], context, results, registry, events, event_ids, config)
    outcomes = tuple(results[r.id] for r in config.rules if r.enabled)
    overall = decide(outcomes, config, anomalies=[a.code for a in prepared.anomalies])
    return Assessment(outcomes, prepared, context, config, overall)


def evaluate(events, config):
    """Shared contract for pipeline/run.py: one RuleResult per enabled rule, in display order."""
    return [outcome.to_rule_result() for outcome in assess(events, config).outcomes]


def _evaluate(definition, context, results, registry, events, event_ids, config):
    rule_id = definition.id
    if not definition.enabled:
        return pending(rule_id, DISABLED_REASON)
    if definition.status != "approved":
        return pending(rule_id)
    if definition.same_as:
        return results[definition.same_as].as_rule(rule_id)
    blocked = checks.depends(rule_id, definition.depends_on, results)
    if blocked is not None:
        return blocked
    if definition.implementation:
        function = _import(definition.implementation)
        if not hasattr(function, "rule_spec"):
            return _path_rule(function, definition, events, event_ids, config)
    else:
        function = registry[rule_id].function  # presence checked at load (_check_registry)
    try:
        outcome = function(context, definition, results)
        _check_outcome(outcome, rule_id, event_ids)
    except Exception as error:  # D-063: recorded, never stops the assessment
        return engine_error(rule_id, error)
    return outcome


def _check_outcome(outcome, rule_id, event_ids):
    if not isinstance(outcome, RuleOutcome):
        raise TypeError(f"rule returned {type(outcome).__name__}, not a RuleOutcome")
    if outcome.rule_id != rule_id:
        raise ValueError(f"rule returned an outcome for {outcome.rule_id!r}")
    outside = set(outcome.evidence) - event_ids
    if outside:
        raise ValueError(f"rule cites evidence outside the supplied timeline: {sorted(outside)}")


def _path_rule(function, definition, events, event_ids, config):
    """Shared contract (docs/contracts.md): (timeline, rule_config) -> RuleResult. Contract violations raise."""
    settings = {"id": definition.id, "title": definition.title, "status": definition.status,
                "enabled": definition.enabled, "implementation": definition.implementation,
                "depends_on": list(definition.depends_on), "parameters": dict(definition.parameters),
                "timing_limits": {name: asdict(value) for name, value in config.timing_limits.items()}}
    result = function(events, settings)
    if not isinstance(result, RuleResult) or result.rule_id != definition.id:
        raise TypeError(f"Rule {definition.id} must return its own RuleResult")
    if not set(result.supporting_events) <= event_ids:
        raise ValueError(f"Rule {definition.id} references evidence outside the supplied timeline")
    kind = {RuleStatus.PASS_DIRECT: PASS_DIRECT, RuleStatus.PASS_INFERRED: PASS_INFERRED,
            RuleStatus.FAIL: FAIL}.get(result.status, UNABLE)
    return RuleOutcome(definition.id, kind, result.reason, UNSPECIFIED_FAILURE if kind == FAIL else None,
                       tuple(result.supporting_events), dict(result.timestamps), original=result)


def _import(implementation):
    module, _, name = implementation.partition(":")
    return getattr(import_module(module), name)


def _check_registry(registry, config):
    """D-064: registered rules and rules.yaml must match before anything is assessed.

    Registered IDs are always checked against the full catalogue in configs/rules.yaml, whatever
    config is being assessed: a smaller config only decides which rules are evaluated, and
    registered rules outside it are simply not run.
    """
    catalogue = {r.id for r in load_rules_config(CATALOGUE_PATH).rules}
    for spec in registry.values():
        if spec.rule_id not in catalogue:
            raise RegistryError("registered_rule_not_in_config", f"rule {spec.rule_id} is registered at "
                                f"{rule_registry.location(spec.function)} but is not in the catalogue "
                                f"configs/rules.yaml (a typo in the ID?)")
        unknown = [name for name in spec.requires if name not in config.vocabulary.events]
        if unknown:
            raise RegistryError("unknown_required_event",
                                f"rule {spec.rule_id} requires events not in the vocabulary: {unknown}")
    for definition in config.rules:
        if (definition.enabled and definition.status == "approved" and not definition.same_as
                and not definition.implementation and definition.id not in registry):
            raise RegistryError("approved_rule_not_registered", f"rule {definition.id} is approved in rules.yaml "
                                "but no implementation is registered (no @rule and no implementation path)")
