"""The rule engine demo (D-114): every scenario keeps its expected results, and demo output is marked."""
import contextlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

import yaml

from annotation.export_rule_engine_records import load_config as load_export_config
from pipeline.config import ROOT
from rules import demo
from rules.adapters.annotation import RECORD_KIND
from rules.config import load_rules_config
from rules.registry import discover

CATALOGUE_PATH = ROOT / "configs/rules.yaml"
SCENARIOS = demo.load_scenarios()


class Scenarios(unittest.TestCase):
    def test_every_scenario_gives_its_expected_results(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario["id"]):
                document, _ = demo.run_scenario(scenario)
                self.assertEqual(demo.differences(scenario, document), [])

    def test_the_key_pathways_are_covered(self):
        expected = {(rule, code) for s in SCENARIOS for rule, (_, code) in s["expected"]["rules"].items() if code}
        self.assertLessEqual({("R2", "simultaneous"), ("R8", "simultaneous"), ("R1", "after_placement"),
                              ("R6", "removed_before_shock")}, expected)
        kinds = {(s["id"], rule): kind for s in SCENARIOS for rule, (kind, _) in s["expected"]["rules"].items()}
        self.assertEqual(kinds[("screen_not_visible", "R6")], "not_evaluable")
        self.assertEqual(kinds[("low_confidence_removal", "R6")], "unable_to_verify")
        self.assertEqual({s["expected"]["overall"] for s in SCENARIOS if s["id"] in ("correct_procedure", "pending_rules")},
                         {"incomplete"})

    def test_scenarios_hold_no_participant_data(self):
        for path in sorted(demo.SCENARIOS.glob("*.json")):
            with self.subTest(path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIsNone(re.search(r"P\d\d_(LL|LS|T)\b", text))
                data = json.loads(text)
                self.assertTrue(data["header"]["recording_id"].startswith("DEMO_"))
                self.assertTrue(all(not {"task_id", "participant_id"} & set(e["metadata"]) for e in data["events"]))
        listed = {s["file"] for s in SCENARIOS}
        self.assertEqual(listed, {p.name for p in demo.SCENARIOS.glob("*.json")})


class DemoConfig(unittest.TestCase):
    def setUp(self):
        self.demo = yaml.safe_load(demo.DEMO_CONFIG.read_text(encoding="utf-8"))
        self.real = yaml.safe_load(CATALOGUE_PATH.read_text(encoding="utf-8"))

    def test_built_rules_approved_and_the_rest_disabled(self):
        built = set(discover())
        for entry in self.demo["rules"]:
            with self.subTest(entry["id"]):
                if entry["id"] in built:
                    self.assertEqual((entry["status"], entry.get("enabled", True)), ("approved", True))
                else:
                    self.assertEqual((entry["status"], entry["enabled"]), ("pending", False))

    def test_otherwise_a_copy_of_rules_yaml(self):
        def strip(data):
            rules = [{k: v for k, v in r.items() if k not in ("status", "enabled")} for r in data["rules"]]
            return {**{k: v for k, v in data.items() if k != "demo"}, "rules": rules}
        self.assertEqual(strip(self.demo), strip(self.real))
        self.assertIs(self.demo["demo"], True)
        self.assertIn("DEMO ONLY: rules not approved by the supervisor", demo.DEMO_CONFIG.read_text(encoding="utf-8"))

    def test_the_real_catalogue_is_not_a_demo(self):
        self.assertNotIn("demo", self.real)
        self.assertFalse(load_rules_config(CATALOGUE_PATH).demo)


class Marking(unittest.TestCase):
    def test_every_demo_report_says_demo_only(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario["id"]):
                document, _ = demo.run_scenario(scenario)
                if scenario["config"] == "demo":
                    self.assertEqual(document["demo_notice"], "DEMO ONLY: rules not approved by the supervisor")
                    self.assertIn("demo_only", document["overall"]["flags"])
                else:
                    self.assertIsNone(document["demo_notice"])
                    self.assertNotIn("demo_only", document["overall"]["flags"])

    def test_the_command_prints_the_tables_and_returns_0(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = demo.main(["--scenario", "gel_after_placement"])
        text = output.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("DEMO ONLY: rules not approved by the supervisor", text)
        self.assertIn("after_placement", text)
        self.assertIn("Overall: FAIL - R1 failed", text)
        self.assertIn("Matches the expected result.", text)

    def test_an_unknown_scenario_is_refused(self):
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(demo.main(["--scenario", "nope"]), 2)


def record():
    tags = [("Gel applied", 75), ("Gel applied", 125), ("first_paddle_taken", 150),
            ("first_paddle_firmly_on_the_chest", 250)]
    return {"schema_version": 1, "kind": RECORD_KIND, "canonical_task_id": "X01_LS", "participant_id": "X01",
            "camera_view": "LS", "annotation_source": "x", "archive": "a.zip", "task_path": ".", "media_name": "x.mp4",
            "fps": 25.0, "width": 1920, "height": 1080, "start_frame": 0, "stop_frame": 749, "duration_seconds": 30.0,
            "tags": [{"id": f"X01_LS_tag_{i:03d}", "label": label, "frame": frame, "timestamp_seconds": frame / 25.0}
                     for i, (label, frame) in enumerate(tags, start=1)],
            "zone_tracks": {"apical_placement_zone": 1, "sternal_placement_zone": 1},
            "zone_visibility": [{"label": z, "start_frame": 0, "end_frame": 749, "start_seconds": 0.0,
                                 "end_seconds": 29.96} for z in ("apical_placement_zone", "sternal_placement_zone")],
            "derived_events": []}


class InterimRecords(unittest.TestCase):
    def test_reports_go_only_under_data_rule_engine_and_are_development_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data_rule_engine"
            records = Path(tmp) / "records.jsonl"
            records.write_text(json.dumps(record()) + "\n", encoding="utf-8")
            with mock.patch.object(demo, "DEV_OUTPUT_ROOT", root):
                with self.assertRaisesRegex(ValueError, "refusing to write outside"):
                    demo.run_records(records, Path(tmp) / "elsewhere", out=lambda line: None)
                lines = []
                self.assertEqual(demo.run_records(records, root / "demo" / "run", out=lines.append), 1)
            report = json.loads((root / "demo" / "run" / "X01_LS.json").read_text(encoding="utf-8"))
            self.assertTrue(report["development_data"])
            self.assertEqual(report["demo_notice"], "DEMO ONLY: rules not approved by the supervisor")
            self.assertTrue(any("DEVELOPMENT DATA" in line for line in lines))

    def test_the_export_config_loads(self):   # run_records reads it for the adapter's gates
        self.assertIsNotNone(load_export_config().gel)


if __name__ == "__main__":
    unittest.main()
