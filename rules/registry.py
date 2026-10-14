"""Rule registry: a rule declares its ID and the events it needs next to its logic.

    @rule("A3", requires=("stand_clear_command",), description="All stand clear before the shock")
    def all_stand_clear(ctx, definition, results):
        return checks.requires(...) or checks.occurrences(...)

The engine discovers every module named `*_rules` in the `rules` package, so adding a rule (or a
rule module) needs no engine change. Display order, status, dependencies and clinical values stay
in configs/rules.yaml (D-005, D-006). Registering two different functions under one ID is an error
naming both (D-064).
"""
from dataclasses import dataclass
from importlib import import_module
import pkgutil
from rules.errors import RegistryError

_REGISTRY = {}


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    function: object
    requires: tuple[str, ...] = ()   # canonical events the rule reads; checked against the vocabulary
    description: str = ""


def location(function):
    """module.function (file:line), to name a rule's implementation in error messages."""
    code = getattr(function, "__code__", None)
    where = f" ({code.co_filename}:{code.co_firstlineno})" if code else ""
    return f"{function.__module__}.{function.__qualname__}{where}"


def rule(rule_id, *, requires=(), description=""):
    """Register a rule function (ctx, definition, results) -> RuleOutcome."""
    def register(function):
        existing = _REGISTRY.get(rule_id)
        same_place = existing is not None and (existing.function.__module__, existing.function.__qualname__) == \
            (function.__module__, function.__qualname__)  # the same function imported again
        if existing is not None and not same_place:
            raise RegistryError("duplicate_rule_registration", f"rule {rule_id} is registered twice: "
                                f"{location(existing.function)} and {location(function)}")
        spec = RuleSpec(rule_id, function, tuple(requires), description)
        _REGISTRY[rule_id] = spec
        function.rule_spec = spec
        return function
    return register


def discover(package="rules"):
    """Import every `*_rules` module in the package; return the registered rules by ID."""
    module = import_module(package)
    for info in pkgutil.iter_modules(module.__path__):
        if info.name.endswith("_rules"):
            import_module(f"{package}.{info.name}")
    return dict(_REGISTRY)
