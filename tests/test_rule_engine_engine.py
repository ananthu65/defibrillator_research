import copy
import json
import types
import unittest
from unittest.mock import patch

import yaml

from pipeline.config import ROOT, load_yaml
from pipeline.merge_timeline import merge_timeline
from pipeline.run import assess as pipeline_assess
from rules import checks, registry
from rules.engine import assess, evaluate
from rules.errors import ConfigError, RegistryError, TimelineError
from rules.outcome import (ENGINE_ERROR, FAIL, NOT_EVALUABLE, PASS_DIRECT, PENDING, PENDING_REASON, failed,
                           passed, unable)
from rules.registry import RuleSpec
from schemas.event import Event
from schemas.rule_result import RuleResult, RuleStatus

RULES = yaml.safe_load((ROOT / "configs/rules.yaml").read_text(encoding="utf-8"))
SHOCK = Event("shock_delivered_on_screen", 30, 30, "annotation", 1.0, event_id="shock")
GEL = Event("Gel applied", 2, 2, "annotation", 1.0, event_id="gel")


def config(*rules):
    return {**copy.deepcopy(RULES), "rules": list(rules)}


def rule(rule_id, status="approved", **fields):
    return {"id": rule_id, "status": status, **fields}


def spec(rule_id, function, requires=()):
    return {rule_id: RuleSpec(rule_id, function, tuple(requires))}


def passing(rule_id):
    return lambda ctx, definition, results: passed(rule_id, "ok", ("shock",))


def calls(log, rule_id, outcome=None):
    def function(ctx, definition, results):
        log.append(rule_id)
        return outcome(rule_id) if outcome else passed(rule_id, "ok", ("shock",))
    return function


class Ordering(unittest.TestCase):
    def test_evaluation_order_follows_dependencies_and_reporting_follows_display_order(self):
        log = []
        registry_ = {**spec("A7", calls(log, "A7")), **spec("A1", calls(log, "A1")), **spec("R1", calls(log, "R1"))}
        result = assess([SHOCK], config(rule("A7", depends_on=["A1"]), rule("R1"), rule("A1")), registry=registry_)
        self.assertEqual(log, ["R1", "A1", "A7"])                       # A1 before A7
        self.assertEqual([o.rule_id for o in result.outcomes], ["A7", "R1", "A1"])  # display order

    def test_every_rule_is_always_evaluated_after_a_failure(self):
        log = []
        registry_ = {**spec("R1", calls(log, "R1", lambda r: failed(r, "missing", "no gel"))),
                     **spec("R2", calls(log, "R2"))}
        result = assess([SHOCK], config(rule("R1"), rule("R2")), registry=registry_)
        self.assertEqual(log, ["R1", "R2"])
        self.assertEqual([o.kind for o in result.outcomes], [FAIL, PASS_DIRECT])


class StatusAndReuse(unittest.TestCase):
    def test_pending_rules_are_reported_as_pending_and_not_called(self):
        log = []
        result = assess([SHOCK], config(rule("R1", status="pending")), registry=spec("R1", calls(log, "R1")))
        self.assertEqual((result.outcomes[0].kind, result.outcomes[0].reason, log), (PENDING, PENDING_REASON, []))

    def test_disabled_rules_are_not_reported(self):
        result = assess([SHOCK], config(rule("R1", enabled=False), rule("R2")), registry=spec("R2", passing("R2")))
        self.assertEqual([o.rule_id for o in result.outcomes], ["R2"])

    def test_same_as_reports_the_target_outcome_under_its_own_id(self):
        result = assess([SHOCK], config(rule("R7"), rule("A6", same_as="R7")), registry=spec("R7", passing("R7")))
        self.assertEqual([(o.rule_id, o.kind, o.evidence) for o in result.outcomes],
                         [("R7", PASS_DIRECT, ("shock",)), ("A6", PASS_DIRECT, ("shock",))])

    def test_same_as_a_pending_rule_is_pending(self):
        result = assess([SHOCK], config(rule("R7", status="pending"), rule("A6", same_as="R7")), registry={})
        self.assertEqual(result.outcome("A6").kind, PENDING)


class Dependencies(unittest.TestCase):
    def test_a_rule_whose_dependency_did_not_pass_is_not_evaluable(self):
        for target_outcome in (lambda r: failed(r, "missing", "m"), lambda r: unable(r, "u")):
            with self.subTest():
                log = []
                registry_ = {**spec("A1", calls(log, "A1", target_outcome)), **spec("A7", calls(log, "A7"))}
                result = assess([SHOCK], config(rule("A1"), rule("A7", depends_on=["A1"])), registry=registry_)
                a7 = result.outcome("A7")
                self.assertEqual((a7.kind, a7.blocked_by, log), (NOT_EVALUABLE, "A1", ["A1"]))

    def test_a_pending_dependency_blocks(self):
        result = assess([SHOCK], config(rule("A1", status="pending"), rule("A7", depends_on=["A1"])),
                        registry=spec("A7", passing("A7")))
        self.assertEqual(result.outcome("A7").blocked_by, "A1")


class EngineErrors(unittest.TestCase):
    """D-063: a rule that raises is recorded as engine_error and never stops the assessment."""

    def broken(self, ctx, definition, results):
        raise ZeroDivisionError("division by zero in R2")

    def test_exception_is_recorded_with_its_message_and_other_rules_still_run(self):
        log = []
        registry_ = {**spec("R1", calls(log, "R1")), **spec("R2", self.broken), **spec("R3", calls(log, "R3"))}
        result = assess([SHOCK], config(rule("R1"), rule("R2"), rule("R3")), registry=registry_)
        r2 = result.outcome("R2")
        self.assertEqual(r2.kind, ENGINE_ERROR)
        self.assertIn("ZeroDivisionError: division by zero in R2", r2.reason)
        self.assertEqual(log, ["R1", "R3"])
        self.assertFalse(r2.evaluated)  # the overall result will be incomplete (Increment 8)
        self.assertEqual(r2.to_rule_result().status, RuleStatus.UNABLE_TO_ASSESS)
        self.assertIn("engine error", r2.to_rule_result().reason)

    def test_rules_depending_on_an_errored_rule_are_not_evaluable(self):
        registry_ = {**spec("A1", self.broken), **spec("A7", passing("A7"))}
        a7 = assess([SHOCK], config(rule("A1"), rule("A7", depends_on=["A1"])), registry=registry_).outcome("A7")
        self.assertEqual((a7.kind, a7.blocked_by), (NOT_EVALUABLE, "A1"))
        self.assertIn("engine error", a7.reason)

    def test_same_as_an_errored_rule_reports_the_error(self):
        result = assess([SHOCK], config(rule("R7"), rule("A6", same_as="R7")), registry=spec("R7", self.broken))
        self.assertEqual(result.outcome("A6").kind, ENGINE_ERROR)

    def test_invalid_returns_are_engine_errors_too(self):
        cases = {"returns None": lambda ctx, d, r: None,
                 "wrong rule ID": lambda ctx, d, r: passed("R9", "ok", ("shock",)),
                 "evidence outside the timeline": lambda ctx, d, r: passed("R1", "ok", ("ghost",))}
        for name, function in cases.items():
            with self.subTest(case=name):
                outcome = assess([SHOCK], config(rule("R1")), registry=spec("R1", function)).outcomes[0]
                self.assertEqual(outcome.kind, ENGINE_ERROR)

    def test_bad_input_still_stops_the_assessment(self):
        with self.assertRaises(TimelineError):  # malformed input is not a rule error
            assess([{"event_name": "x"}], config(rule("R1")), registry=spec("R1", passing("R1")))


class RegisteredRulesUseTheContext(unittest.TestCase):
    def test_a_rule_built_from_shared_checks(self):
        def a3(ctx, definition, results):
            return (checks.requires("A3", ctx.shock, "R5") or
                    checks.occurrences("A3", ctx, "stand_clear_command", valid=lambda e: e.start < ctx.shock.time,
                                       invalid_code="after_shock", what="stand clear", uses=(ctx.shock,)))
        command = Event("stand_clear_command", 25, 26, "audio", 0.9, event_id="c")
        result = assess([SHOCK, command], config(rule("A3")), registry=spec("A3", a3, requires=("stand_clear_command",)))
        self.assertEqual((result.outcomes[0].kind, result.outcomes[0].evidence), (PASS_DIRECT, ("c",)))

    def test_required_events_are_checked_against_the_vocabulary(self):
        with self.assertRaisesRegex(ConfigError, "not in the vocabulary: \\['stand_clear'\\]"):
            assess([SHOCK], config(rule("A3")), registry=spec("A3", passing("A3"), requires=("stand_clear",)))
        with self.assertRaises(RegistryError) as caught:
            assess([SHOCK], config(rule("A3")), registry=spec("A3", passing("A3"), requires=("stand_clear",)))
        self.assertEqual(caught.exception.code, "unknown_required_event")

    def test_header_reaches_coverage(self):
        from rules.coverage import TimelineHeader

        def a3(ctx, definition, results):
            return checks.missing("A3", ctx, "stand_clear_command", what="stand clear")
        header = TimelineHeader.from_dict({"analyses_run": {"audio": True}})
        result = assess([SHOCK], config(rule("A3")), header=header, registry=spec("A3", a3))
        self.assertEqual(result.outcomes[0].kind, FAIL)


class Registry(unittest.TestCase):
    def tearDown(self):
        registry._REGISTRY.pop("TEST_RULE", None)

    def test_decorator_registers_the_rule_next_to_its_logic(self):
        @registry.rule("TEST_RULE", requires=("gel_applied",), description="test")
        def test_rule(ctx, definition, results):
            return passed("TEST_RULE", "ok", ("gel",))
        self.assertIs(registry.discover()["TEST_RULE"].function, test_rule)
        self.assertEqual(test_rule.rule_spec.requires, ("gel_applied",))

    def test_two_different_functions_for_one_id_are_rejected_naming_both(self):
        @registry.rule("TEST_RULE")
        def first(ctx, definition, results):
            return None
        with self.assertRaises(RegistryError) as caught:
            @registry.rule("TEST_RULE")
            def second(ctx, definition, results):
                return None
        message = str(caught.exception)
        self.assertEqual(caught.exception.code, "duplicate_rule_registration")
        self.assertIn("<locals>.first (", message)
        self.assertIn("<locals>.second (", message)
        self.assertEqual(message.count("test_rule_engine_engine.py:"), 2)  # file and line of each

    def test_the_same_function_registered_again_is_not_a_duplicate(self):
        def same(ctx, definition, results):
            return None
        registry.rule("TEST_RULE")(same)
        registry.rule("TEST_RULE")(same)  # e.g. its module imported a second time
        self.assertIs(registry.discover()["TEST_RULE"].function, same)

    def test_discovery_imports_rule_modules(self):
        registry.discover()
        import sys
        self.assertIn("rules.video_rules", sys.modules)
        self.assertIn("rules.audio_rules", sys.modules)

    def test_implementation_path_can_point_at_a_registered_rule(self):
        module = types.ModuleType("research_registered_rules")

        @registry.rule("TEST_RULE")
        def custom(ctx, definition, results):
            return passed("TEST_RULE", "ok", ("shock",))
        module.custom = custom
        with patch.dict("sys.modules", research_registered_rules=module):
            outcome = assess([SHOCK], config(rule("TEST_RULE", implementation="research_registered_rules:custom")),
                             registry={}).outcomes[0]
        self.assertEqual(outcome.kind, PASS_DIRECT)


class RegistryMatchesConfig(unittest.TestCase):
    """D-064: checked when the engine loads, before anything is assessed."""

    def assertRejected(self, code, message, rules, registry_):
        with self.assertRaisesRegex(RegistryError, message) as caught:
            assess([SHOCK], config(*rules), registry=registry_)
        self.assertEqual(caught.exception.code, code)

    def test_approved_rule_without_an_implementation_is_an_error_not_pending(self):
        self.assertRejected("approved_rule_not_registered", "rule R1 is approved in rules.yaml but no implementation",
                            [rule("R1"), rule("R2")], spec("R2", passing("R2")))

    def test_registered_rule_missing_from_the_catalogue_is_an_error(self):
        self.assertRejected("registered_rule_not_in_config",
                            "rule R11 is registered at .*passing.* but is not in the catalogue configs/rules.yaml",
                            [rule("R1")], {**spec("R1", passing("R1")), **spec("R11", passing("R11"))})

    def test_a_one_rule_config_works_with_other_rules_registered(self):
        # D-064 (OQ-043): the smaller config decides which rules run; the others are simply not run
        log = []
        registry_ = {**spec("R1", calls(log, "R1")), **spec("R2", calls(log, "R2")), **spec("A3", calls(log, "A3"))}
        result = assess([SHOCK], config(rule("R1")), registry=registry_)
        self.assertEqual([o.rule_id for o in result.outcomes], ["R1"])
        self.assertEqual(log, ["R1"])

    def test_the_catalogue_check_does_not_depend_on_the_config_path(self):
        # a copy of rules.yaml elsewhere, even one that lists R11, cannot make an unknown ID acceptable
        import tempfile
        from pathlib import Path
        from rules.config import load_rules_config
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "rules_copy.yaml"
            data = copy.deepcopy(RULES)
            data["rules"].append(rule("R11"))
            copied.write_text(yaml.safe_dump(data), encoding="utf-8")
            loaded = load_rules_config(copied)
            self.assertIn("R11", [r.id for r in loaded.rules])
            with self.assertRaises(RegistryError) as caught:
                assess([SHOCK], loaded, registry={**spec("R11", passing("R11"))})
            self.assertEqual(caught.exception.code, "registered_rule_not_in_config")

    def test_allowed_without_a_registration(self):
        for rules, reason in (([rule("R1", status="pending")], "pending"),
                              ([rule("R1", enabled=False)], "disabled"),
                              ([rule("R7", status="pending"), rule("A6", same_as="R7")], "same_as")):
            with self.subTest(reason=reason):
                assess([SHOCK], config(*rules), registry={})

    def test_a_shared_contract_path_rule_needs_no_registration(self):
        module = types.ModuleType("research_path_rules")
        module.custom = lambda timeline, settings: RuleResult("R1", RuleStatus.UNABLE_TO_ASSESS, "r")
        with patch.dict("sys.modules", research_path_rules=module):
            assess([SHOCK], config(rule("R1", implementation="research_path_rules:custom")), registry={})

    def test_the_repository_rule_modules_match_rules_yaml(self):
        assess([SHOCK], RULES)  # the real registry against the real catalogue


class SharedContract(unittest.TestCase):
    def test_path_rule_result_is_reported_exactly_as_returned(self):
        module = types.ModuleType("research_path_rules")
        returned = RuleResult("R1", RuleStatus.MANUAL_REVIEW, "custom reason", ["shock"], {"t": 30.0})
        module.custom = lambda timeline, settings: returned
        with patch.dict("sys.modules", research_path_rules=module):
            results = evaluate([SHOCK], config(rule("R1", implementation="research_path_rules:custom")))
        self.assertEqual(results, [returned])

    def test_path_rule_receives_the_rule_settings(self):
        module, seen = types.ModuleType("research_path_rules"), {}

        def custom(timeline, settings):
            seen.update(settings)
            return RuleResult("R1", RuleStatus.UNABLE_TO_ASSESS, "r")
        module.custom = custom
        with patch.dict("sys.modules", research_path_rules=module):
            evaluate([SHOCK], config(rule("R1", implementation="research_path_rules:custom", parameters={"k": 1})))
        self.assertEqual((seen["id"], seen["parameters"]), ("R1", {"k": 1}))
        self.assertEqual(seen["timing_limits"]["pre_shock_pause_seconds"]["value"], 5)


class PipelineOutputUnchanged(unittest.TestCase):
    """While every rule is pending, the pipeline report is exactly what it was before Increment 7."""

    def test_pipeline_output_matches_the_pre_increment_7_reference(self):
        golden = json.loads((ROOT / "tests/fixtures/rule_engine/pipeline_all_pending.json").read_text(encoding="utf-8"))
        events = [Event.from_dict(e) for e in json.loads((ROOT / "tests/fixtures/sample_timeline.json").read_text())]
        report = json.loads(json.dumps(pipeline_assess(load_yaml(ROOT / "configs/pipeline.yaml"), events=events)))
        for key in golden:
            with self.subTest(key=key):
                self.assertEqual(report[key], golden[key])

    def test_real_config_gives_sixteen_pending_rules(self):
        events = merge_timeline([Event.from_dict(e) for e in
                                 json.loads((ROOT / "tests/fixtures/sample_timeline.json").read_text())])
        result = assess(events, RULES)
        self.assertEqual(len(result.outcomes), 16)
        self.assertTrue(all(o.kind == PENDING and o.reason == PENDING_REASON for o in result.outcomes))


if __name__ == "__main__":
    unittest.main()
