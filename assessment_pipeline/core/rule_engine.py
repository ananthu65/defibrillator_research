"""
rule_engine.py

Version 1 Rule Evaluation Engine

Responsibilities
----------------
1. Check whether every required event exists.
2. Check whether events occur in the expected order.
3. Return one CriterionEvaluation for every rule.

Version 1 intentionally ignores

- timing
- confidence thresholds
- inference
- critical errors

Those will be added in later versions.
"""

from assessment_pipeline.core.events import (
    Event,
    CriterionEvaluation,
    CriterionResult,
)

from assessment_pipeline.core.rule_definitions import RULES


class RuleEngine:
    """
    Rule Evaluation Engine.
    """

    def __init__(self, events: list[Event]):

        self.events = events

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    def evaluate(self) -> list[CriterionEvaluation]:

        evaluations = []

        for rule in RULES:

            evaluations.append(self._evaluate_rule(rule))

        return evaluations

    # --------------------------------------------------------
    # Rule Evaluation
    # --------------------------------------------------------

    def _evaluate_rule(self, rule):

        event = self._find_event(rule.event_name)

        # -------------------------
        # Presence Check
        # -------------------------

        if event is None:

            return CriterionEvaluation(
                criterion_id=rule.criterion_id,
                result=CriterionResult.FAIL,
                reason=f"Required event '{rule.event_name}' not found.",
                evidence=[rule.event_name],
            )

        # -------------------------
        # Order Check
        # -------------------------

        if rule.must_follow is not None:

            previous_event = self._find_event(rule.must_follow)

            if previous_event is None:

                return CriterionEvaluation(
                    criterion_id=rule.criterion_id,
                    result=CriterionResult.FAIL,
                    reason=f"Required previous event '{rule.must_follow}' not found.",
                    evidence=[rule.must_follow],
                )

            if previous_event.timestamp >= event.timestamp:

                return CriterionEvaluation(
                    criterion_id=rule.criterion_id,
                    result=CriterionResult.FAIL,
                    reason=(
                        f"'{rule.event_name}' occurred before "
                        f"'{rule.must_follow}'."
                    ),
                    evidence=[
                        rule.must_follow,
                        rule.event_name,
                    ],
                )

        # -------------------------
        # Dependency Check
        # -------------------------

        missing = []

        for dependency in rule.depends_on:

            if self._find_event(dependency) is None:
                missing.append(dependency)

        if missing:

            return CriterionEvaluation(
                criterion_id=rule.criterion_id,
                result=CriterionResult.FAIL,
                reason="Missing dependency events.",
                evidence=missing,
            )

        # -------------------------
        # PASS
        # -------------------------

        return CriterionEvaluation(
            criterion_id=rule.criterion_id,
            result=CriterionResult.PASS,
            reason=None,
            evidence=[rule.event_name],
        )

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    def _find_event(self, event_name):

        for event in self.events:

            if event.event_name == event_name:
                return event

        return None


# ------------------------------------------------------------
# Convenience Function
# ------------------------------------------------------------

def evaluate_rules(events: list[Event]) -> list[CriterionEvaluation]:
    """
    Evaluate all assessment rules.
    """

    engine = RuleEngine(events)

    return engine.evaluate()