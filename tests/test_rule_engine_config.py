import copy
import json
from pathlib import Path
import tempfile
import unittest

import yaml

from pipeline.config import ROOT
from rules.config import EngineSettings, RuleEngineConfig, load_rules_config
from rules.errors import ConfigError

RULES = yaml.safe_load((ROOT / "configs/rules.yaml").read_text(encoding="utf-8"))
ENGINE = yaml.safe_load((ROOT / "configs/rule_engine/engine.yaml").read_text(encoding="utf-8"))
DISPLAY = ["R1", "R2", "R8", "R3", "R4", "R5", "R6", "A1", "A2", "A3", "A4", "A5", "R7", "A6", "A7", "A8"]


def rules_config(**changes):
    value = copy.deepcopy(RULES)
    value.update(changes)
    return value


def rule(rule_id, **fields):
    return {"id": rule_id, "status": "pending", **fields}


class RepositoryConfig(unittest.TestCase):
    def setUp(self):
        self.config = load_rules_config()

    def test_rules_are_listed_in_display_order(self):
        self.assertEqual([r.id for r in self.config.rules], DISPLAY)

    def test_every_rule_is_pending_until_supervisor_approval(self):
        self.assertTrue(all(r.status == "pending" for r in self.config.rules))

    def test_a6_reuses_r7_and_a7_depends_on_a1_to_a5(self):
        self.assertEqual(self.config.rule("A6").same_as, "R7")
        self.assertIsNone(self.config.rule("A6").implementation)
        self.assertEqual(self.config.rule("A7").depends_on, ("A1", "A2", "A3", "A4", "A5"))

    def test_a8_limit_is_approved_by_the_supervisor(self):
        limit = self.config.limit("pre_shock_pause_seconds")
        self.assertEqual((limit.value, limit.provided_by, limit.provided_on, limit.source),
                         (5, "Arnikan", "2026-10-10", "team discussion"))
        self.assertEqual(limit.approved_by, "Dr. Senani Samarasinghe")
        self.assertIsNone(limit.approved_on)
        self.assertTrue(limit.date_pending)
        self.assertEqual(limit.note, "approval date to be confirmed")  # explanation only
        self.assertTrue(limit.approved)

    def test_unused_clinical_limits_are_kept_null_with_a_note(self):
        for name in ("shock_to_compressions_seconds", "gel_application_period_seconds", "stop_to_shock_seconds",
                     "shock_command_tolerance_seconds", "shock_to_removal_seconds", "charge_to_shock_seconds"):
            with self.subTest(name=name):
                limit = self.config.limit(name)
                self.assertIsNone(limit.value)
                self.assertFalse(limit.approved)
                self.assertIn("not used by any rule yet", limit.note)
        self.assertIsNone(self.config.limit("not_in_config").value)

    def test_engine_placeholders_and_undecided_policies_are_marked(self):
        self.assertIn("simultaneous_window_seconds", self.config.engine.placeholders)
        self.assertIn("placement_match_window_seconds", self.config.engine.placeholders)
        self.assertEqual(self.config.engine.undecided, [
            "coverage_policy.outcomes.unknown", "expected_counts.both_paddle_buttons_pressed",
            "expected_counts.gel_applied", "expected_counts.paddles_firmly_on_chest", "inferred_fail_outcome",
            "review_anomalies", "unable_to_verify_outcome"])
        self.assertIs(self.config.engine.value("assume_first_taken_is_apical"), False)
        self.assertIsNone(self.config.engine.value("unable_to_verify_outcome"))
        self.assertEqual(self.config.engine.coverage_outcomes["covered"].value, "fail")
        self.assertEqual(self.config.engine.coverage_outcomes["not_covered"].value, "unable_to_verify")

    def test_vocabulary_is_loaded_from_the_linked_file(self):
        self.assertEqual(self.config.vocabulary.canonical("annotation", "Gel applied"), "gel_applied")

    def test_config_stays_json_serialisable_for_pipeline_reports(self):
        json.dumps(RULES)  # pipeline/run.py copies the raw rules.yaml into the JSON report


class EvaluationOrder(unittest.TestCase):
    def test_dependencies_move_only_the_rules_that_need_it(self):
        reordered = [rule("A7", depends_on=["A1", "A3"]), rule("A6", same_as="R7"), rule("A1"),
                     rule("R1"), rule("R7"), rule("A3")]
        config = RuleEngineConfig.from_dict(rules_config(rules=reordered))
        self.assertEqual([r.id for r in config.rules], ["A7", "A6", "A1", "R1", "R7", "A3"])  # display order kept
        self.assertEqual(config.evaluation_order(), ["A1", "R1", "R7", "A6", "A3", "A7"])

    def test_event_dependencies_impose_no_order(self):
        config = RuleEngineConfig.from_dict(rules_config(rules=[rule("R6"), rule("R5"), rule("R2")]))
        self.assertEqual(config.evaluation_order(), ["R6", "R5", "R2"])


class InvalidRulesConfig(unittest.TestCase):
    def assertRejected(self, message, **changes):
        with self.assertRaisesRegex(ConfigError, message):
            RuleEngineConfig.from_dict(rules_config(**changes))

    def test_wrong_schema_version(self):
        self.assertRejected("schema_version", schema_version=2)

    def test_no_rules(self):
        self.assertRejected("nonempty list", rules=[])

    def test_duplicate_id(self):
        self.assertRejected(r"rules\.R1: duplicate", rules=[rule("R1"), rule("R1")])

    def test_unknown_rule_key(self):
        self.assertRejected(r"unknown keys \['dependson'\]", rules=[rule("R1", dependson=["R2"])])

    def test_bad_status(self):
        self.assertRejected("status must be one of", rules=[rule("R1", status="draft")])

    def test_bad_implementation(self):
        self.assertRejected("module.path:function", rules=[rule("R1", implementation="rules.video_rules")])

    def test_same_as_with_its_own_implementation(self):
        self.assertRejected("has no implementation",
                            rules=[rule("R7"), rule("A6", same_as="R7", implementation="m:f")])

    def test_same_as_chain(self):
        self.assertRejected("own check", rules=[rule("R7"), rule("A6", same_as="R7"), rule("X", same_as="A6")])

    def test_unknown_dependency(self):
        self.assertRejected("unknown rule 'A9'", rules=[rule("A7", depends_on=["A9"])])

    def test_self_dependency(self):
        self.assertRejected("depends on itself", rules=[rule("A7", depends_on=["A7"])])

    def test_circular_dependency_names_the_cycle(self):
        self.assertRejected("circular rule-result dependency: A1 -> A2 -> A3 -> A1", rules=[
            rule("A1", depends_on=["A2"]), rule("A2", depends_on=["A3"]), rule("A3", depends_on=["A1"]), rule("R1")])

    def test_cycle_through_same_as(self):
        self.assertRejected("circular", rules=[rule("R7", depends_on=["A6"]), rule("A6", same_as="R7")])

    def test_plain_number_limit_has_no_provenance(self):
        self.assertRejected("record with its provenance", timing_limits={"stop_to_shock_seconds": 10})

    def test_unknown_limit_key(self):
        self.assertRejected("unknown keys", timing_limits={"x": {"value": 1, "source": "s", "aproved_by": "A"}})

    def test_value_without_source(self):
        self.assertRejected("needs a source", timing_limits={"x": {"value": 5}})

    def test_negative_value(self):
        self.assertRejected("nonnegative", timing_limits={"x": {"value": -1, "source": "s"}})

    def test_unquoted_date(self):
        import datetime
        self.assertRejected("quoted date", timing_limits={"x": {"value": 5, "source": "s",
                                                                "provided_on": datetime.date(2026, 10, 10)}})

    def test_approval_date_without_approver(self):
        self.assertRejected("approved_on needs approved_by",
                            timing_limits={"x": {"value": 5, "source": "s", "approved_on": "2026-10-10"}})

    def test_approver_without_date_needs_date_pending_true(self):
        base = {"value": 5, "source": "s", "approved_by": "Dr X", "note": "approval date to be confirmed"}
        self.assertRejected("only when date_pending: true", timing_limits={"x": base})  # flag missing
        self.assertRejected("only when date_pending: true", timing_limits={"x": {**base, "date_pending": False}})
        for wrong in ("yes", 1, None):
            with self.subTest(date_pending=wrong):
                self.assertRejected("date_pending must be true or false",
                                    timing_limits={"x": {**base, "date_pending": wrong}})

    def test_note_text_alone_is_never_interpreted(self):
        self.assertRejected("only when date_pending: true", timing_limits={"x": {
            "value": 5, "source": "s", "approved_by": "Dr X", "note": "Date to be confirmed by the supervisor"}})

    def test_approver_without_date_is_allowed_with_date_pending(self):
        config = RuleEngineConfig.from_dict(rules_config(timing_limits={"x": {
            "value": 5, "source": "s", "approved_by": "Dr X", "date_pending": True}}))
        self.assertTrue(config.limit("x").approved)
        self.assertTrue(config.limit("x").date_pending)
        self.assertIsNone(config.limit("x").approved_on)

    def test_date_pending_with_a_date_or_without_an_approver_is_rejected(self):
        self.assertRejected("needs approved_by and approved_on: null", timing_limits={"x": {
            "value": 5, "source": "s", "approved_by": "Dr X", "approved_on": "2026-10-10", "date_pending": True}})
        self.assertRejected("needs approved_by and approved_on: null", timing_limits={"x": {
            "value": 5, "source": "s", "date_pending": True}})

    def test_dated_approval_needs_no_flag(self):
        config = RuleEngineConfig.from_dict(rules_config(timing_limits={"x": {
            "value": 5, "source": "s", "approved_by": "Dr X", "approved_on": "2026-10-10"}}))
        self.assertFalse(config.limit("x").date_pending)

    def test_approval_without_value(self):
        self.assertRejected("needs a value", timing_limits={"x": {"approved_by": "Dr X", "approved_on": "2026-10-10"}})

    def test_null_limit_is_allowed_for_an_approved_rule(self):
        config = RuleEngineConfig.from_dict(rules_config(rules=[rule("R7", status="approved",
                                                                     implementation="rules.audio_rules:r7")]))
        self.assertIsNone(config.limit("shock_to_compressions_seconds").value)

    def test_approved_limit(self):
        config = RuleEngineConfig.from_dict(rules_config(timing_limits={"x": {
            "value": 5, "source": "s", "approved_by": "Dr X", "approved_on": "2026-11-01"}}))
        self.assertTrue(config.limit("x").approved)

    def test_missing_linked_file(self):
        self.assertRejected("file not found: configs/missing.yaml", engine="configs/missing.yaml")

    def test_invalid_yaml_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.yaml"
            path.write_text("rules: [unclosed", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "invalid YAML"):
                load_rules_config(path)


class InvalidEngineSettings(unittest.TestCase):
    def assertRejected(self, message, mutate):
        data = copy.deepcopy(ENGINE)
        mutate(data)
        with self.assertRaisesRegex(ConfigError, message):
            EngineSettings.from_dict(data)

    def test_missing_setting_is_an_error_not_a_default(self):
        self.assertRejected(r"missing keys \['simultaneous_window_seconds'\]",
                            lambda d: d.pop("simultaneous_window_seconds"))

    def test_unknown_setting(self):
        self.assertRejected(r"unknown keys \['simultanous_window_seconds'\]",
                            lambda d: d.update(simultanous_window_seconds=0.5))

    def test_confidence_out_of_range(self):
        self.assertRejected("between 0 and 1", lambda d: d["confidence_thresholds"].update(video=1.5))

    def test_missing_source_threshold(self):
        self.assertRejected("missing keys", lambda d: d["confidence_thresholds"].pop("audio"))

    def test_negative_window(self):
        self.assertRejected("nonnegative", lambda d: d.update(placement_match_window_seconds={"value": -0.1}))

    def test_fallback_must_be_boolean(self):
        self.assertRejected("true or false", lambda d: d.update(assume_first_taken_is_apical="no"))

    def test_bad_coverage_outcome(self):
        self.assertRejected("must be one of", lambda d: d["coverage_policy"]["outcomes"].update(covered="pass"))

    def test_bad_overall_outcome(self):
        self.assertRejected("must be one of", lambda d: d.update(unable_to_verify_outcome={"value": "pass"}))

    def test_null_only_while_undecided(self):
        self.assertRejected("only while undecided", lambda d: d.update(unable_to_verify_outcome={"value": None}))

    def test_bad_expected_counts_are_rejected(self):
        for value in ("two", {"exactly": 0}, {"exactly": True}, {"exactly": 1.5}, {"between": 1},
                      {"exactly": 1, "at_most": 2}, {}):
            with self.subTest(value=value):
                self.assertRejected("unlimited or one of", lambda d: d["expected_counts"].update(
                    first_paddle_taken={"value": value, "placeholder": True}))

    def test_expected_count_null_only_while_undecided(self):
        self.assertRejected("only while undecided", lambda d: d["expected_counts"].update(gel_applied={"value": None}))

    def test_every_count_form_is_accepted(self):
        for value in ({"exactly": 1}, {"at_least": 2}, {"at_most": 3}, "unlimited"):
            with self.subTest(value=value):
                data = copy.deepcopy(ENGINE)
                data["expected_counts"]["gel_applied"] = {"value": value}  # a count is always written as a record
                self.assertEqual(EngineSettings.from_dict(data).expected_counts["gel_applied"].value, value)

    def test_expected_counts_must_cover_the_vocabulary_exactly(self):
        for mutate, message in ((lambda d: d["expected_counts"].pop("gel_applied"), r"missing \['gel_applied'\]"),
                                (lambda d: d["expected_counts"].update(gel_aplied="unlimited"),
                                 r"not in the vocabulary \['gel_aplied'\]")):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                data = copy.deepcopy(ENGINE)
                mutate(data)
                path = Path(directory) / "engine.yaml"
                path.write_text(yaml.safe_dump(data), encoding="utf-8")
                with self.assertRaisesRegex(ConfigError, message):
                    RuleEngineConfig.from_dict({**copy.deepcopy(RULES), "engine": str(path)})

    def test_every_allowed_policy_value_is_accepted(self):
        for name, values in (("inferred_fail_outcome", ["fail", "unable_to_verify"]),
                             ("unable_to_verify_outcome", ["fail", "faculty_review"])):
            for value in values:
                with self.subTest(name=name, value=value):
                    data = copy.deepcopy(ENGINE)
                    data[name] = value
                    self.assertEqual(EngineSettings.from_dict(data).value(name), value)


if __name__ == "__main__":
    unittest.main()
