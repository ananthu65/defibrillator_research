"""The two kinds of rule the engine can run.

Registered rules (rules/registry.py, the normal way): (ctx, definition, results) -> RuleOutcome.
Path rules (`implementation: module:function` in rules.yaml, kept for the shared contract):
(timeline, rule_config) -> RuleResult.
"""
from typing import Protocol
from schemas.event import Event
from schemas.rule_result import RuleResult


class Rule(Protocol):
    def __call__(self, timeline: list[Event], config: dict) -> RuleResult: ...


class RegisteredRule(Protocol):
    def __call__(self, ctx, definition, results: dict): ...
