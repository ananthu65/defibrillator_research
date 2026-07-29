"""
rule_engine.py

Version 2 Rule Evaluation Engine

Evaluation sequence

1. Presence
2. Dependencies
3. Order
4. Timing
5. Inference

The Rule Engine performs deterministic assessment only.
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

            inferred = self._infer_event(rule)

            if inferred is not None:

                return CriterionEvaluation(
                    criterion_id=rule.criterion_id,
                    result=CriterionResult.PASS_INFERRED,
                    evidence_type=EvidenceType.INFERRED,
                    supporting_events=[inferred.event_name],
                    feedback_message=(
                        f"{rule.event_name} inferred from "
                        f"{inferred.event_name}"
                    ),
                    timestamps={
                        inferred.event_name: inferred.timestamp,
                    },
                )

            return CriterionEvaluation(
                criterion_id=rule.criterion_id,
                result=CriterionResult.FAIL,
                failure_reason=f"Missing event: {rule.event_name}",
                supporting_events=[],
            )

        #
        # Dependencies
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
        # Order
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
            # Timing
            #

            if rule.max_delay is not None:

                elapsed = event.timestamp - previous.timestamp

                if elapsed > rule.max_delay:

                    return CriterionEvaluation(
                        criterion_id=rule.criterion_id,
                        result=CriterionResult.FAIL,
                        failure_reason=(
                            f"Maximum delay exceeded "
                            f"({elapsed:.2f}s > {rule.max_delay:.2f}s)"
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

    def _infer_event(self, rule: Rule):

        for supporting_event in rule.infer_from:

            event = self._find_event(supporting_event)

            if event is not None:
                return event

        return None


# ---------------------------------------------------------
# Convenience Function
# ---------------------------------------------------------

def evaluate_rules(events: list[Event]) -> list[CriterionEvaluation]:

    engine = RuleEngine(events)

    return engine.evaluate()