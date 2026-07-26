"""
rule_engine.py

Version 1 Rule Evaluation Engine

Checks:
- Presence
- Dependencies
- Order

Future versions:
- Timing
- Inference
- Confidence
"""

from assessment_pipeline.core.events import (
    Event,
    CriterionEvaluation,
    CriterionResult,
    EvidenceType,
)

from assessment_pipeline.core.rule_definitions import (
    RULES,
    Rule,
)


class RuleEngine:

    def __init__(self, events: list[Event]):

        self.events = sorted(events, key=lambda e: e.timestamp)

    # -----------------------------------------------------
    # Public API
    # -----------------------------------------------------

    def evaluate(self) -> list[CriterionEvaluation]:

        evaluations = []

        for rule in RULES:
            evaluations.append(
                self._evaluate_rule(rule)
            )

        return evaluations

    # -----------------------------------------------------
    # Rule Evaluation
    # -----------------------------------------------------

    def _evaluate_rule(self, rule: Rule) -> CriterionEvaluation:

        event = self._find_event(rule.event_name)

        #
        # Presence
        #

        if event is None:

            return CriterionEvaluation(
                criterion_id=rule.criterion_id,
                result=CriterionResult.FAIL,
                failure_reason=f"Missing event: {rule.event_name}",
                supporting_events=[],
            )

        #
        # Dependency Check
        #

        for dependency in rule.depends_on:

            dependency_event = self._find_event(dependency)

            if dependency_event is None:

                return CriterionEvaluation(
                    criterion_id=rule.criterion_id,
                    result=CriterionResult.FAIL,
                    failure_reason=f"Missing dependency: {dependency}",
                    supporting_events=[dependency],
                )

        #
        # Order Check
        #

        if rule.must_follow is not None:

            previous = self._find_event(rule.must_follow)

            if previous is None:

                return CriterionEvaluation(
                    criterion_id=rule.criterion_id,
                    result=CriterionResult.FAIL,
                    failure_reason=f"Missing previous event: {rule.must_follow}",
                    supporting_events=[rule.must_follow],
                )

            if previous.timestamp >= event.timestamp:

                return CriterionEvaluation(
                    criterion_id=rule.criterion_id,
                    result=CriterionResult.FAIL,
                    failure_reason=(
                        f"{rule.event_name} occurred before "
                        f"{rule.must_follow}"
                    ),
                    supporting_events=[
                        rule.must_follow,
                        rule.event_name,
                    ],
                    timestamps={
                        rule.must_follow: previous.timestamp,
                        rule.event_name: event.timestamp,
                    },
                )

        #
        # PASS
        #

        return CriterionEvaluation(
            criterion_id=rule.criterion_id,
            result=CriterionResult.PASS_DIRECT,
            evidence_type=EvidenceType.DIRECT,
            supporting_events=[event.event_name],
            timestamps={
                event.event_name: event.timestamp,
            },
        )

    # -----------------------------------------------------
    # Helpers
    # -----------------------------------------------------

    def _find_event(self, event_name: str):

        for event in self.events:

            if event.event_name == event_name:
                return event

        return None


# ---------------------------------------------------------
# Convenience Function
# ---------------------------------------------------------

def evaluate_rules(events: list[Event]) -> list[CriterionEvaluation]:

    engine = RuleEngine(events)

    return engine.evaluate()