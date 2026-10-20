"""Shared-check tests."""
import unittest

from rules import checks
from rules.config import ClinicalValue, load_rules_config
from rules.context import build_context
from rules.coverage import TimelineHeader
from rules.outcome import (ASSUMED, FAIL, NOT_EVALUABLE, PASS_DIRECT, PASS_INFERRED, PENDING, UNABLE, RuleOutcome,
                           assumed, failed, flags_of, not_evaluable, passed, pending, unable)
from rules.prepare import prepare_timeline
from schemas.event import Event
from schemas.rule_result import RuleStatus

CONFIG = load_rules_config()
AUDIO_RAN = {"analyses_run": {"video": True, "audio": True}}


def ev(name, t, source="annotation", confidence=1.0, event_id=None):
    return Event(name, t, t, source, confidence, event_id=event_id or f"{name}@{t}")


def cmd(name, t, event_id=None, confidence=0.9):
    return Event(name, t, t + 1, "audio", confidence, event_id=event_id or f"{name}@{t}")


def context(events, header=None):
    head = None if header is None else TimelineHeader.from_dict(header, regions=tuple(CONFIG.engine.regions))
    return build_context(prepare_timeline(events, CONFIG), CONFIG, head)


SHOCK = ev("shock_delivered_on_screen", 30, event_id="shock")
APPROVED_5 = ClinicalValue("x", 5, approved_by="Dr X", approved_on="2026-10-10", source="s")


class Outcome(unittest.TestCase):
    def test_invalid_outcomes_are_rejected(self):
        for kwargs, message in (({"kind": "maybe"}, "unknown"), ({"kind": FAIL}, "failure code"),
                                ({"kind": PASS_DIRECT, "failure_code": "x"}, "failure code"),
                                ({"kind": PASS_DIRECT}, "cite"), ({"kind": NOT_EVALUABLE}, "blocked_by"),
                                ({"kind": UNABLE, "blocked_by": "R5"}, "blocked_by"),
                                ({"kind": UNABLE, "timestamps": {"t": -1}}, "timestamps")):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, message):
                RuleOutcome("R1", reason="r", **kwargs)

    def test_flags_and_evidence_are_deduplicated_in_order(self):
        outcome = unable("R1", "r", evidence=("a", "b", "a"), flags=("x", "y", "x"))
        self.assertEqual((outcome.evidence, outcome.flags), (("a", "b"), ("x", "y")))

    def test_mapping_to_the_shared_rule_result(self):
        cases = [(passed("R1", "ok", ("e",)), RuleStatus.PASS_DIRECT),
                 (passed("R1", "ok", ("e",), inferred=True), RuleStatus.PASS_INFERRED),
                 (failed("R1", "missing", "no gel"), RuleStatus.FAIL),
                 (unable("R1", "unclear"), RuleStatus.UNABLE_TO_ASSESS),
                 (not_evaluable("R1", "R5", "no shock"), RuleStatus.UNABLE_TO_ASSESS),
                 (pending("R1"), RuleStatus.UNABLE_TO_ASSESS),
                 (assumed("R8", "assumed apical first"), RuleStatus.UNABLE_TO_ASSESS)]
        for outcome, status in cases:
            with self.subTest(kind=outcome.kind):
                self.assertEqual(outcome.to_rule_result().status, status)

    def test_reason_text_carries_code_kind_timing_and_flags(self):
        result = failed("A8", "pre_shock_pause", "7 s", flags=("multiple_candidates",), timing_checked=True)
        self.assertEqual(result.to_rule_result().reason,
                         "7 s [failure code: pre_shock_pause; flags: multiple_candidates]")
        self.assertEqual(passed("R7", "restart", ("s",), timing_checked=False).to_rule_result().reason,
                         "restart [timing not checked]")
        self.assertEqual(not_evaluable("A1", "R5", "no shock").to_rule_result().reason, "no shock [not evaluable]")

    def test_evaluated_and_passed(self):
        self.assertTrue(passed("R1", "ok", ("e",)).passed)
        self.assertFalse(pending("R1").evaluated)
        self.assertFalse(assumed("R8", "a").evaluated)  # D-060
        self.assertTrue(unable("R1", "u").evaluated)

    def test_same_as_reports_one_check_under_two_ids(self):
        r7 = passed("R7", "restart in time", ("s",))
        self.assertEqual(r7.as_rule("A6").rule_id, "A6")
        self.assertEqual(r7.as_rule("A6").evidence, r7.evidence)

    def test_flags_of_merges_anchors_elapsed_and_strings(self):
        ctx = context([SHOCK, cmd("start_compressions_command", 36, "s"), cmd("start_compressions_command", 40, "s2")])
        merged = flags_of(ctx.shock, ctx.elapsed("shock", "start_compressions"), "extra", ("extra", "more"), None)
        self.assertEqual(merged, ("multiple_candidates", "extra", "more"))


class Dependencies(unittest.TestCase):
    def test_all_passed_means_go_on(self):
        self.assertIsNone(checks.depends("A7", ["A1"], {"A1": passed("A1", "ok", ("e",))}))

    def test_a_dependency_that_did_not_pass_blocks_the_rule(self):
        for result in (failed("A1", "missing", "m"), unable("A1", "u"), pending("A1"),
                       not_evaluable("A1", "R5", "n"), assumed("A1", "a")):
            with self.subTest(kind=result.kind):
                outcome = checks.depends("A7", ["A1"], {"A1": result})
                self.assertEqual((outcome.kind, outcome.blocked_by), (NOT_EVALUABLE, "A1"))
                self.assertIn("not evaluable because of A1", outcome.reason)

    def test_evaluation_order_mistakes_are_loud(self):
        with self.assertRaisesRegex(KeyError, "not been evaluated"):
            checks.depends("A7", ["A1"], {})


class RequiredFacts(unittest.TestCase):
    def test_present_fact_means_go_on(self):
        self.assertIsNone(checks.requires("A1", context([SHOCK]).shock, "R5"))

    def test_missing_shock_time_carries_its_flags(self):
        ctx = context([ev("shock_delivered_on_screen", 30, event_id="s1"), ev("shock_delivered_on_screen", 60, event_id="s2")])
        outcome = checks.requires("A1", ctx.shock, "R5")
        self.assertEqual((outcome.kind, outcome.blocked_by, outcome.flags), (NOT_EVALUABLE, "R5", ("multiple_shocks",)))


class RestartAmbiguity(unittest.TestCase):
    def test_ambiguous_restart_is_unable_to_verify_never_fail(self):
        ctx = context([cmd("start_compressions_command", 31, "early")])   # no shock time: timing unknown (D-054)
        outcome = checks.restart_ambiguity("R7", ctx)
        self.assertEqual((outcome.kind, outcome.evidence), (UNABLE, ("early",)))
        self.assertIn("no_shock_time", outcome.flags)

    def test_unambiguous_restart_means_go_on(self):
        self.assertIsNone(checks.restart_ambiguity("R7", context([SHOCK, cmd("start_compressions_command", 35)])))


class Occurrences(unittest.TestCase):
    """Command before the shock, as in A1/A3 (built in Increment 18)."""

    def evaluate(self, events, header=AUDIO_RAN):
        ctx = context(events, header)
        return checks.occurrences("A3", ctx, "stand_clear_command", valid=lambda e: e.start < ctx.shock.time,
                                  invalid_code="after_shock", what="stand clear", uses=(ctx.shock,))

    def test_valid_occurrence_passes_directly(self):
        outcome = self.evaluate([SHOCK, cmd("stand_clear_command", 25, "c")])
        self.assertEqual((outcome.kind, outcome.evidence, outcome.timestamps), (PASS_DIRECT, ("c",), {"stand_clear_command": 25}))

    def test_repeated_events_any_valid_occurrence_satisfies(self):
        # said after the shock first in the list order is irrelevant: one valid occurrence is enough
        outcome = self.evaluate([SHOCK, cmd("stand_clear_command", 40, "late"), cmd("stand_clear_command", 20, "early"),
                                 cmd("stand_clear_command", 25, "again")])
        self.assertEqual((outcome.kind, outcome.evidence), (PASS_DIRECT, ("early",)))

    def test_only_invalid_occurrences_fail_with_the_rule_code(self):
        outcome = self.evaluate([SHOCK, cmd("stand_clear_command", 40, "late")])
        self.assertEqual((outcome.kind, outcome.failure_code, outcome.evidence), (FAIL, "after_shock", ("late",)))

    def test_invalid_confident_but_valid_low_confidence_is_never_fail(self):
        outcome = self.evaluate([SHOCK, cmd("stand_clear_command", 40, "late"),
                                 cmd("stand_clear_command", 20, "weak", confidence=0.2)])
        self.assertEqual((outcome.kind, outcome.evidence), (UNABLE, ("weak",)))
        self.assertIn("low_confidence_evidence", outcome.flags)

    def test_no_occurrence_goes_to_the_missing_ladder(self):
        self.assertEqual((self.evaluate([SHOCK]).kind, self.evaluate([SHOCK]).failure_code), (FAIL, "missing"))

    def test_anchor_flags_are_carried_onto_the_result(self):
        ctx = context([SHOCK, ev("first_paddle_firmly_on_the_chest", 12), ev("first_paddle_firmly_on_the_chest", 14),
                       cmd("stand_clear_command", 25, "c")], AUDIO_RAN)
        placed = ctx.anchor("first_placement")
        outcome = checks.occurrences("A3", ctx, "stand_clear_command", valid=lambda e: e.start < ctx.shock.time,
                                     invalid_code="after_shock", what="stand clear", uses=(placed,))
        self.assertEqual(outcome.kind, PASS_DIRECT)
        self.assertIn("multiple_candidates", outcome.flags)


class MissingLadder(unittest.TestCase):
    """Diagram (c): weak or missing evidence → approved inference first → coverage (ctx.missing)."""

    def test_inference_is_checked_before_coverage(self):
        # R3-like: no direct placement evidence, the shock on screen confirmed; coverage alone would say Fail
        ctx = context([SHOCK], AUDIO_RAN)
        outcome = checks.missing("R3", ctx, "paddles_firmly_on_chest", what="paddles on chest",
                                 inference=("shock_delivered_on_screen",))
        self.assertEqual((outcome.kind, outcome.evidence), (PASS_INFERRED, ("shock",)))
        self.assertIn("inferred from shock_delivered_on_screen", outcome.reason)

    def test_earliest_supporting_event_is_cited(self):
        # the shared check is generic: of several supporting events, the earliest is cited
        ctx = context([SHOCK, ev("both_paddle_buttons_pressed", 28, event_id="press")], AUDIO_RAN)
        outcome = checks.missing("R3", ctx, "paddles_firmly_on_chest", what="paddles on chest",
                                 inference=("shock_delivered_on_screen", "both_paddle_buttons_pressed"))
        self.assertEqual(outcome.evidence, ("press",))

    def test_no_inference_available_falls_through_to_coverage(self):
        outcome = checks.missing("R3", context([ev("Gel applied", 1)], AUDIO_RAN), "paddles_firmly_on_chest",
                                 what="paddles", inference=("shock_delivered_on_screen",))
        self.assertEqual((outcome.kind, outcome.failure_code), (FAIL, "missing"))

    def test_coverage_outcomes(self):
        for header, kind, flags in ((AUDIO_RAN, FAIL, ()),
                                    ({"analyses_run": {"audio": False}}, UNABLE, ()),
                                    (None, UNABLE, ("coverage_policy_undecided",))):
            with self.subTest(header=header):
                outcome = checks.missing("A3", context([SHOCK], header), "stand_clear_command", what="stand clear")
                self.assertEqual((outcome.kind, outcome.flags), (kind, flags))

    def test_low_confidence_is_never_fail_even_when_covered(self):
        outcome = checks.missing("A3", context([SHOCK, cmd("stand_clear_command", 20, "weak", confidence=0.2)], AUDIO_RAN),
                                 "stand_clear_command", what="stand clear")
        self.assertEqual((outcome.kind, outcome.evidence, outcome.flags), (UNABLE, ("weak",), ("low_confidence_evidence",)))

    def test_low_confidence_ambiguous_command_is_never_fail(self):
        ctx = context([SHOCK, cmd("resume_compressions_command", 35, "weak", confidence=0.2)], AUDIO_RAN)
        outcome = checks.missing("R7", ctx, "start_compressions_command", what="restart")
        self.assertEqual((outcome.kind, outcome.evidence), (UNABLE, ("weak",)))

    def test_custom_failure_code(self):
        outcome = checks.missing("R2", context([ev("Gel applied", 1)], AUDIO_RAN), "first_paddle_taken",
                                 what="first paddle taken", code="first_missing")
        self.assertEqual(outcome.failure_code, "first_missing")


class Timing(unittest.TestCase):
    def test_null_limit_means_timing_not_checked(self):
        check = checks.time_limit(12, ClinicalValue("shock_to_compressions_seconds"))
        self.assertEqual((check.checked, check.within, check.flags), (False, None, ("timing_not_checked",)))

    def test_unapproved_limit_is_not_used(self):
        check = checks.time_limit(12, ClinicalValue("x", 5, provided_by="A", source="s"))
        self.assertEqual((check.checked, check.flags), (False, ("timing_not_checked", "limit_not_approved")))

    def test_unmeasurable_interval(self):
        self.assertEqual(checks.time_limit(None, APPROVED_5).flags, ("timing_not_checked",))

    def test_approved_no_limit_checks_and_passes_fully(self):
        no_limit = ClinicalValue("x", None, approved_by="Dr X", approved_on="2026-10-10", source="s", no_limit=True)
        for seconds in (3, 300, None):
            with self.subTest(seconds=seconds):
                check = checks.time_limit(seconds, no_limit)
                self.assertEqual((check.checked, check.within, check.flags), (True, True, ()))
        ctx = context([SHOCK, cmd("stop_compressions_command", 27, "stop"), cmd("start_compressions_command", 90, "start")])
        outcome = checks.timed("A8", ctx.elapsed("stop_compressions", "start_compressions"), no_limit,
                               code="pre_shock_pause", what="stop to restart", evidence=("stop", "start"))
        self.assertEqual((outcome.kind, outcome.timing_checked, outcome.flags), (PASS_DIRECT, True, ()))   # D-103

    def test_unapproved_no_limit_is_not_used(self):
        check = checks.time_limit(3, ClinicalValue("x", None, source="s", no_limit=True))
        self.assertEqual((check.checked, check.flags), (False, ("timing_not_checked", "limit_not_approved")))

    def test_within_at_and_over_the_limit(self):
        self.assertEqual([checks.time_limit(s, APPROVED_5).within for s in (4.9, 5, 5.1)], [True, True, False])

    def test_the_repository_a8_limit_is_usable(self):
        self.assertTrue(checks.time_limit(4, CONFIG.limit("pre_shock_pause_seconds")).checked)

    def test_timed_passes_without_a_limit_but_says_so(self):
        ctx = context([SHOCK, cmd("stop_compressions_command", 27, "stop"), cmd("start_compressions_command", 40, "start")])
        outcome = checks.timed("R7", ctx.elapsed("shock", "start_compressions"), CONFIG.limit("shock_to_compressions_seconds"),
                               code="too_late", what="shock to restart", evidence=("start",))
        self.assertEqual((outcome.kind, outcome.timing_checked), (PASS_DIRECT, False))
        self.assertIn("timing_not_checked", outcome.flags)
        self.assertIn("[timing not checked; flags: timing_not_checked]", outcome.to_rule_result().reason)

    def test_timed_fails_over_the_limit_and_carries_elapsed_flags(self):
        ctx = context([SHOCK, cmd("stop_compressions_command", 25, "stop"), cmd("start_compressions_command", 40, "start"),
                       cmd("start_compressions_command", 45, "again")])
        outcome = checks.timed("A8", ctx.elapsed("stop_compressions", "start_compressions"), APPROVED_5,
                               code="pre_shock_pause", what="stop to restart", evidence=("stop", "start"))
        self.assertEqual((outcome.kind, outcome.failure_code, outcome.timestamps), (FAIL, "pre_shock_pause", {"seconds": 15}))
        self.assertIn("multiple_candidates", outcome.flags)  # the elapsed time's flags travel with the result

    def test_timed_within_the_limit(self):
        ctx = context([SHOCK, cmd("stop_compressions_command", 27, "stop"), cmd("start_compressions_command", 31, "start")])
        outcome = checks.timed("A8", ctx.elapsed("stop_compressions", "start_compressions"), APPROVED_5,
                               code="pre_shock_pause", what="stop to restart", evidence=("stop", "start"))
        self.assertEqual((outcome.kind, outcome.timing_checked, outcome.flags), (PASS_DIRECT, True, ()))


class Order(unittest.TestCase):
    def test_relation_uses_the_simultaneous_window(self):
        window = checks.simultaneous_window(context([SHOCK]))  # 0.5 s placeholder
        self.assertEqual([checks.relation(10, t, window) for t in (12, 10.5, 9.6, 9)],
                         ["before", "simultaneous", "simultaneous", "after"])

    def test_relation_with_an_absent_time(self):
        self.assertIsNone(checks.relation(None, 3, 0.5))


if __name__ == "__main__":
    unittest.main()
