import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

import yaml

from pipeline.config import ROOT
from rules.coverage import TimelineHeader
from rules.engine import assess
from rules.outcome import failed, passed
from rules.policy import ANNOTATION_COVERAGE_ASSUMED
from rules.registry import RuleSpec
from rules.render import REPORT_KIND, REPORT_VERSION, report
from rules.run import EXIT_NO_ASSESSMENT, load_timeline, main
from schemas.event import Event

RULES = yaml.safe_load((ROOT / "configs/rules.yaml").read_text(encoding="utf-8"))
SAMPLE = ROOT / "tests/fixtures/sample_timeline.json"
SHOCK = Event("shock_delivered_on_screen", 30, 30, "annotation", 1.0, event_id="shock", camera_angle="LL")
HEADER = {"recording_id": "P03_LL", "camera_angle": "LL", "duration_seconds": 95.0,
          "analyses_run": {"video": True, "audio": False}}


def approved(*rule_ids):
    data = copy.deepcopy(RULES)
    for definition in data["rules"]:
        if definition["id"] in rule_ids:
            definition["status"] = "approved"
    return data


def returns(outcome):
    return lambda ctx, definition, results: outcome


class ReportShape(unittest.TestCase):
    def setUp(self):
        registry = {"R7": RuleSpec("R7", returns(passed("R7", "restart at 33 s", ("shock",)))),
                    "R1": RuleSpec("R1", returns(failed("R1", "applied_once", "gel applied once")))}
        self.document = report(assess([SHOCK], approved("R1", "R7", "A6"), registry=registry))

    def test_top_level_keys_and_version(self):
        self.assertEqual(list(self.document), ["report_version", "kind", "development_data", "demo_notice", "overall",
                                               "rules", "timeline", "context", "configuration"])
        self.assertIsNone(self.document["demo_notice"])   # only a demo config sets it (D-114)
        self.assertEqual((self.document["report_version"], self.document["kind"]), (REPORT_VERSION, REPORT_KIND))

    def test_report_survives_a_json_round_trip_unchanged(self):
        self.assertEqual(json.loads(json.dumps(self.document)), self.document)

    def test_every_enabled_rule_is_reported_in_display_order_with_its_title(self):
        ids = [r["id"] for r in RULES["rules"] if r.get("enabled", True)]
        self.assertEqual([r["rule_id"] for r in self.document["rules"]], ids)
        r1 = self.document["rules"][0]
        self.assertEqual((r1["title"], r1["kind"], r1["status"], r1["failure_code"], r1["passed"]),
                         ("Gel applied twice", "fail", "fail", "applied_once", False))
        self.assertIn("[failure code: applied_once]", r1["shared_reason"])

    def test_pending_rules_report_shared_status_unable_to_assess(self):
        r2 = next(r for r in self.document["rules"] if r["rule_id"] == "R2")
        self.assertEqual((r2["kind"], r2["status"], r2["evaluated"]), ("pending", "unable_to_assess", False))

    def test_overall_names_the_mistake_and_groups_r7_with_a6(self):
        overall = self.document["overall"]
        self.assertEqual(overall["result"], "fail")
        self.assertEqual([(m["rule_ids"], m["failure_code"], m["title"]) for m in overall["mistakes"]],
                         [(["R1"], "applied_once", "Gel applied twice")])
        a6 = next(r for r in self.document["rules"] if r["rule_id"] == "A6")
        self.assertEqual((a6["kind"], a6["evidence"]), ("pass_direct", ["shock"]))

    def test_context_and_configuration_are_included(self):
        self.assertEqual(self.document["context"]["anchors"]["shock"]["event_id"], "shock")
        self.assertIn("unable_to_verify_outcome", self.document["configuration"]["undecided"])
        self.assertFalse(self.document["configuration"]["timing_limits"]["shock_to_compressions_seconds"]["approved"])
        self.assertFalse(self.document["development_data"])

    def test_development_data_is_shown_at_the_top(self):
        registry = {"R1": RuleSpec("R1", returns(passed("R1", "ok", ("shock",), flags=(ANNOTATION_COVERAGE_ASSUMED,))))}
        document = report(assess([SHOCK], approved("R1"), registry=registry))
        self.assertTrue(document["development_data"])
        self.assertIn("development_data", document["overall"]["flags"])

    def test_header_is_reported(self):
        header = TimelineHeader.from_dict(HEADER, regions=("apical_zone", "sternal_zone"))
        document = report(assess([SHOCK], RULES, header=header, registry={}))
        self.assertEqual(document["context"]["header"]["recording_id"], "P03_LL")


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)
        self.output = self.path / "out" / "report.json"

    def run_main(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main([*args, "--output", str(self.output)])
        return code, stdout.getvalue(), stderr.getvalue()

    def write(self, name, value):
        path = self.path / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return str(path)

    def test_sample_timeline_writes_the_report(self):
        code, stdout, _ = self.run_main("--events", str(SAMPLE))
        self.assertEqual(code, 0)
        document = json.loads(self.output.read_text(encoding="utf-8"))
        events, _ = load_timeline(SAMPLE)
        self.assertEqual(document, report(assess(events, RULES)))
        self.assertIn("Overall: incomplete", stdout)
        self.assertIn("R1  pending", stdout)

    def test_missing_ids_are_assigned_in_file_order(self):
        events, header = load_timeline(SAMPLE)
        self.assertEqual([e.event_id for e in events], ["event_000001", "event_000002", "event_000003"])
        self.assertIsNone(header)

    def test_assigned_ids_never_clash_with_given_ones(self):
        path = self.write("t.json", [{**SHOCK.to_dict(), "event_id": "event_000002"},
                                     {**SHOCK.to_dict(), "event_id": None, "start": 40, "end": 40}])
        events, _ = load_timeline(path)
        self.assertEqual([e.event_id for e in events], ["event_000002", "event_000002_"])

    def test_header_inside_the_timeline_file(self):
        path = self.write("t.json", {"header": HEADER, "events": [SHOCK.to_dict()]})
        self.assertEqual(self.run_main("--events", path)[0], 0)
        document = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(document["context"]["header"]["analyses_run"], {"video": True, "audio": False})

    def test_header_file_overrides_the_one_inside(self):
        path = self.write("t.json", {"header": {**HEADER, "recording_id": "other"}, "events": [SHOCK.to_dict()]})
        header = self.write("h.json", HEADER)
        self.assertEqual(self.run_main("--events", path, "--header", header)[0], 0)
        document = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(document["context"]["header"]["recording_id"], "P03_LL")

    def assertNoAssessment(self, *args, message):
        code, _, stderr = self.run_main(*args)
        self.assertEqual(code, EXIT_NO_ASSESSMENT)
        self.assertIn("No assessment produced", stderr)
        self.assertIn(message, stderr)
        self.assertFalse(self.output.exists())

    def test_rejected_timeline_writes_no_report(self):
        path = self.write("t.json", [SHOCK.to_dict(), SHOCK.to_dict()])
        self.assertNoAssessment("--events", path, message="duplicate")

    def test_not_a_list_writes_no_report(self):
        self.assertNoAssessment("--events", self.write("t.json", 3), message="expected a list")

    def test_not_an_event_writes_no_report(self):
        self.assertNoAssessment("--events", self.write("t.json", [{"event_name": "x"}]), message="item 1")

    def test_header_contradicting_the_events_writes_no_report(self):
        path = self.write("t.json", {"header": {**HEADER, "camera_angle": "T"}, "events": [SHOCK.to_dict()]})
        self.assertNoAssessment("--events", path, message="camera")

    def test_bad_config_writes_no_report(self):
        config = self.write("rules.json", {"schema_version": 99, "rules": []})
        self.assertNoAssessment("--events", str(SAMPLE), "--config", config, message="schema_version")

    def test_unreadable_file_writes_no_report(self):
        bad = self.path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        self.assertNoAssessment("--events", str(bad), message="Expecting")
        self.assertNoAssessment("--events", str(self.path / "missing.json"), message="missing.json")


if __name__ == "__main__":
    unittest.main()
