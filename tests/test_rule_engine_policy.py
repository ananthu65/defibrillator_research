import copy
from dataclasses import replace
import unittest

import yaml

from pipeline.config import ROOT
from rules.config import EngineSettings, RuleEngineConfig
from rules.engine import assess
from rules.errors import ConfigError
from rules.outcome import assumed, engine_error, failed, not_evaluable, passed, pending, unable
from rules.policy import (DEVELOPMENT_DATA, FACULTY_REVIEW, INCOMPLETE, NO_RULES_EVALUATED, OVERALL_POLICY_UNDECIDED,
                          PASS, TIMELINE_NEEDS_REVIEW, UNVERIFIED, decide)
from rules.registry import RuleSpec
from schemas.event import Event

RULES = yaml.safe_load((ROOT / "configs/rules.yaml").read_text(encoding="utf-8"))
ENGINE = yaml.safe_load((ROOT / "configs/rule_engine/engine.yaml").read_text(encoding="utf-8"))
CONFIG = RuleEngineConfig.from_dict(RULES)  # the real catalogue: titles, A6 same_as R7


def with_engine(**settings):
    data = copy.deepcopy(ENGINE)
    data.update(settings)
    return replace(CONFIG, engine=EngineSettings.from_dict(data))


def ok(rule_id, **kwargs):
    return passed(rule_id, "ok", ("e",), **kwargs)


ALL_PASS = [ok("R1"), ok("R2"), ok("R7"), ok("A6")]


class FailRow(unittest.TestCase):
    def test_any_fail_is_fail_and_every_fail_is_listed(self):
        overall = decide([failed("R1", "applied_once", "gel once"), ok("R2"),
                          failed("A8", "pre_shock_pause", "7 s")], CONFIG)
        self.assertEqual(overall.result, "fail")
        self.assertEqual([(m.rule_ids, m.failure_code, m.title) for m in overall.mistakes],
                         [(("R1",), "applied_once", "Gel applied twice"), (("A8",), "pre_shock_pause", "Pre-shock pause")])
        self.assertEqual(overall.deciding, overall.mistakes)
        self.assertIn("D-001", overall.decided_by)

    def test_fail_beats_everything_else(self):
        overall = decide([failed("R1", "missing", "no gel"), pending("R2"), engine_error("R3", ValueError("x")),
                          unable("A1", "u"), assumed("R8", "a")], CONFIG)
        self.assertEqual(overall.result, "fail")
        self.assertEqual(len(overall.incomplete), 3)  # still reported for the reviewer
        self.assertEqual(len(overall.unverified), 1)

    def test_fail_with_a_timeline_anomaly_stays_fail_but_is_flagged(self):
        overall = decide([failed("R1", "missing", "no gel")], CONFIG, anomalies=["multiple_shocks"])
        self.assertEqual((overall.result, overall.timeline_anomalies), ("fail", ("multiple_shocks",)))
        self.assertIn(TIMELINE_NEEDS_REVIEW, overall.flags)
        self.assertIn("timeline needs review (multiple_shocks)", overall.summary)


class IncompleteRow(unittest.TestCase):
    def check(self, outcomes, category, **kwargs):
        overall = decide(outcomes, CONFIG, **kwargs)
        self.assertEqual(overall.result, INCOMPLETE)
        self.assertIn(category, overall.summary)
        return overall

    def test_pending_rule(self):
        overall = self.check([*ALL_PASS, pending("R8")], "rules not yet approved for R8")
        self.assertEqual([c.rule_ids for c in overall.deciding], [("R8",)])

    def test_assumed_r8(self):
        self.check([*ALL_PASS, assumed("R8", "assumed apical first")], "assumed result, to be checked by the evaluator for R8")

    def test_timing_not_checked(self):
        self.check([ok("R1"), ok("R7", flags=("timing_not_checked",)), ok("A6", flags=("timing_not_checked",))],
                   "timing not checked for R7/A6")

    def test_limit_not_approved(self):
        self.check([ok("R1"), ok("A8", flags=("timing_not_checked", "limit_not_approved"))], "limit not approved for A8")

    def test_engine_error_keeps_its_message(self):
        overall = self.check([*ALL_PASS, engine_error("R5", ZeroDivisionError("boom"))], "engine error for R5")
        self.assertIn("ZeroDivisionError: boom", overall.deciding[0].reason)

    def test_timeline_anomaly_alone_blocks_pass(self):
        overall = self.check(ALL_PASS, "the timeline needs review (unknown_labels_present)",
                             anomalies=["unknown_labels_present"])
        self.assertIn(TIMELINE_NEEDS_REVIEW, overall.flags)

    def test_incomplete_beats_unable_to_verify(self):
        self.check([unable("A1", "u"), pending("R8")], "rules not yet approved")

    def test_a_data_problem_never_fails_a_learner_even_if_unable_to_verify_becomes_fail(self):
        # D-069: the anomaly is checked before the Unable-to-Verify setting
        overall = decide([ok("R1"), unable("A1", "u")], with_engine(unable_to_verify_outcome="fail"),
                         anomalies=["multiple_shocks"])
        self.assertEqual(overall.result, INCOMPLETE)
        self.assertIn(TIMELINE_NEEDS_REVIEW, overall.flags)

    def test_no_rules_to_evaluate(self):
        overall = decide([], CONFIG)
        self.assertEqual((overall.result, overall.flags), (INCOMPLETE, (NO_RULES_EVALUATED,)))

    def test_every_rule_disabled_through_the_engine(self):
        rules = [{**r, "enabled": False} for r in RULES["rules"]]
        result = assess([Event("Gel applied", 1, 1, "annotation", 1.0, event_id="g")], {**RULES, "rules": rules},
                        registry={})
        self.assertEqual((result.outcomes, result.overall.result), ((), INCOMPLETE))

    def test_anomaly_outside_the_review_list_is_ignored(self):
        config = with_engine(review_anomalies={"value": ["multiple_shocks"]})
        overall = decide(ALL_PASS, config, anomalies=["mixed_evidence_sources"])
        self.assertEqual((overall.result, overall.timeline_anomalies), (PASS, ()))


class UnverifiedRow(unittest.TestCase):
    def test_undecided_setting(self):
        overall = decide([ok("R1"), unable("A1", "unclear audio"), not_evaluable("A7", "A1", "because of A1")], CONFIG)
        self.assertEqual(overall.result, UNVERIFIED)
        self.assertIn(OVERALL_POLICY_UNDECIDED, overall.flags)
        self.assertIn("unable_to_verify_outcome = None (undecided, OQ-002", overall.decided_by)
        self.assertEqual([c.rule_ids for c in overall.deciding], [("A1",), ("A7",)])

    def test_each_decided_setting(self):
        for value, expected in (("fail", "fail"), ("faculty_review", FACULTY_REVIEW)):
            with self.subTest(value=value):
                overall = decide([ok("R1"), unable("A1", "u")], with_engine(unable_to_verify_outcome=value))
                self.assertEqual(overall.result, expected)
                self.assertNotIn(OVERALL_POLICY_UNDECIDED, overall.flags)
                self.assertIn(f"= {value} (decided", overall.decided_by)

    def test_not_evaluable_counts_like_unable_to_verify(self):
        overall = decide([ok("R1"), not_evaluable("A1", "R5", "no shock")], with_engine(unable_to_verify_outcome="fail"))
        self.assertEqual(overall.result, "fail")
        self.assertEqual(overall.mistakes, ())  # not a named mistake: it was the setting that decided


class PassRow(unittest.TestCase):
    def test_every_rule_evaluated_and_passed(self):
        overall = decide([*ALL_PASS, ok("R3", inferred=True)], CONFIG)
        self.assertEqual((overall.result, overall.deciding, overall.flags), (PASS, (), ()))


class SameAsReportedOnce(unittest.TestCase):
    def test_r7_and_a6_are_one_mistake(self):
        overall = decide([ok("R1"), failed("R7", "too_late", "12 s"), failed("A6", "too_late", "12 s")], CONFIG)
        self.assertEqual([(m.rule_ids, m.failure_code) for m in overall.mistakes], [(("R7", "A6"), "too_late")])
        self.assertIn("R7/A6 failed", overall.summary)


class DevelopmentData(unittest.TestCase):
    def test_annotation_results_are_marked_as_development_data(self):
        for outcomes in ([ok("R1", flags=("annotation_coverage_assumed",)), ok("R2")],
                         [failed("R1", "missing", "m", flags=("annotation_coverage_assumed",))]):
            with self.subTest(result=outcomes[0].kind):
                overall = decide(outcomes, CONFIG)
                self.assertTrue(overall.development_data)
                self.assertIn(DEVELOPMENT_DATA, overall.flags)

    def test_model_results_are_not(self):
        self.assertFalse(decide(ALL_PASS, CONFIG).development_data)


class ThroughTheEngine(unittest.TestCase):
    def test_real_catalogue_is_incomplete_with_r7_a6_once(self):
        result = assess([Event("Gel applied", 1, 1, "annotation", 1.0, event_id="g")], RULES)
        self.assertEqual(result.overall.result, INCOMPLETE)
        self.assertEqual(len(result.overall.incomplete), 15)
        self.assertIn(("R7", "A6"), [c.rule_ids for c in result.overall.incomplete])

    def test_timeline_anomalies_reach_the_policy(self):
        shocks = [Event("shock_delivered_on_screen", t, t, "annotation", 1.0, event_id=f"s{t}") for t in (30, 60)]
        config = {**RULES, "rules": [{"id": "R1", "status": "approved"}]}
        result = assess(shocks, config, registry={"R1": RuleSpec("R1", lambda c, d, r: passed("R1", "ok", ("s30",)))})
        # Two shocks also break the expected count of exactly one (D-071), so both are listed.
        self.assertEqual(result.overall.timeline_anomalies, ("multiple_shocks", "count_violation"))
        self.assertEqual(result.overall.result, INCOMPLETE)


class ReviewAnomalySetting(unittest.TestCase):
    def test_invalid_lists_are_rejected(self):
        for value in (["multiple_shock"], ["multiple_shocks", "multiple_shocks"], "multiple_shocks"):
            with self.subTest(value=value), self.assertRaisesRegex(ConfigError, "distinct anomaly codes"):
                with_engine(review_anomalies={"value": value})

    def test_decided_list_d069_and_d072(self):
        setting = CONFIG.engine.settings["review_anomalies"]
        self.assertEqual(setting.value, ["unknown_labels_present", "multiple_shocks", "mixed_evidence_sources",
                                         "count_violation", "paddle_identity_conflict"])
        self.assertFalse(setting.undecided)

    def test_count_violation_alone_makes_the_result_incomplete_never_fail(self):
        takes = [Event("first_paddle_taken", t, t, "annotation", 1.0, event_id=f"t{t}") for t in (5, 9)]
        config = {**RULES, "rules": [{"id": "R1", "status": "approved"}]}
        result = assess(takes, config, registry={"R1": RuleSpec("R1", lambda c, d, r: passed("R1", "ok", ("t5",)))})
        self.assertEqual(result.overall.timeline_anomalies, ("count_violation",))
        self.assertEqual(result.overall.result, INCOMPLETE)
        self.assertIn(TIMELINE_NEEDS_REVIEW, result.overall.flags)


if __name__ == "__main__":
    unittest.main()
