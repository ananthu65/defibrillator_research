"""A rule function accepts (timeline, rule_config) and returns one RuleResult."""
from typing import Protocol
from schemas.event import Event
from schemas.rule_result import RuleResult


class Rule(Protocol):
    def __call__(self, timeline: list[Event], config: dict) -> RuleResult: ...
