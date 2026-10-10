import csv
import json
from pathlib import Path
import tempfile
import unittest
import types
from unittest.mock import patch

from annotation.to_timeline import convert
from audio.benchmark_whisper import word_errors
from audio.commands.detect import detect_commands
from experiments.record import record_experiment
from pipeline.config import ROOT, load_yaml
from pipeline.merge_timeline import merge_timeline
from pipeline.registry import create_model
from pipeline.run import assess
from schemas.event import Event
from schemas.transcript import TranscriptSegment
from schemas.rule_result import RuleResult, RuleStatus
from rules.engine import evaluate
from feedback.generate import generate
from experiments.summarize import rebuild
from video.postprocess import merge_observations


class PipelineContracts(unittest.TestCase):
    def test_invalid_evidence_is_rejected(self):
        for overrides in ({"start": -1}, {"end": 0}, {"confidence": 1.2}, {"confidence": float("nan")},
                          {"source": "unknown"}, {"evidence_type": "inferred"}):
            data = dict(event_name="test", start=1, end=2, source="video", confidence=0.8)
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                Event(**(data | overrides))

    def test_roundtrip_and_offsets_do_not_mutate_input(self):
        event = Event("command", 2, 3, "audio", 0.8)
        self.assertEqual(Event.from_dict(event.to_dict()), event)
        self.assertEqual(merge_timeline([event], offsets={"audio": 1})[0].start, 3)
        self.assertEqual(event.start, 2)

    def test_observations_merge_by_label_without_inventing_actions(self):
        events = [Event("object_visible:paddle", 1, 2, "video", 0.7),
                  Event("object_visible:paddle", 2, 3, "video", 0.9),
                  Event("object_visible:paddle", 5, 6, "video", 0.8)]
        merged = merge_observations(events)
        self.assertEqual([(e.start, e.end) for e in merged], [(1, 3), (5, 6)])
        self.assertEqual(merged[0].confidence, 0.9)
        self.assertEqual(merged[0].event_name, "object_visible:paddle")

    def test_fixture_pipeline_has_no_assumed_clinical_passes(self):
        events = [Event.from_dict(e) for e in json.loads((ROOT / "tests/fixtures/sample_timeline.json").read_text())]
        result = assess(load_yaml(ROOT / "configs/pipeline.yaml"), events=events)
        self.assertEqual([e["start"] for e in result["events"]], [1, 2, 4])
        self.assertEqual(len(result["rules"]), 16)  # update when rules are added or removed (rule engine owner)
        self.assertTrue(all(r["status"] == "unable_to_assess" for r in result["rules"]))
        self.assertEqual(len(result["feedback"]), 16)

    def test_enabled_branch_requires_its_input(self):
        config = load_yaml(ROOT / "configs/pipeline.yaml")
        config["video"]["enabled"] = True
        with self.assertRaisesRegex(ValueError, "input file"):
            assess(config)

    def test_no_inputs_does_not_create_a_fake_assessment(self):
        with self.assertRaisesRegex(ValueError, "Supply --events"):
            assess(load_yaml(ROOT / "configs/pipeline.yaml"))

    def test_unknown_model_fails_before_import(self):
        with self.assertRaisesRegex(ValueError, "Unknown video model"):
            create_model("video", {"model": "typo"})

    def test_detector_family_is_configurable(self):
        with tempfile.TemporaryDirectory() as directory:
            weights = Path(directory) / "local.pt"
            weights.touch()
            yolo = create_model("video", {"model": "yolo", "options": {"weights": str(weights)}})
            rtdetr = create_model("video", {"model": "rtdetr", "options": {"weights": str(weights)}})
            self.assertEqual(yolo.backend, "YOLO")
            self.assertEqual(rtdetr.backend, "RTDETR")

    def test_phrase_matching_has_word_boundaries(self):
        segments = [TranscriptSegment(0, 1, "We stand clearly", 0.9), TranscriptSegment(2, 3, "ALL, stand clear!", 0.8)]
        events = detect_commands(segments, {"stand_clear_command": ["stand clear"]})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].start, 2)

    def test_annotation_point_keeps_provenance(self):
        events = convert({"participant_id": "P01", "canonical_task_id": "P01_T",
                          "events": [{"label": "gel_applied", "timestamp_seconds": 2, "frame": 50}]})
        self.assertEqual(events[0].start, events[0].end)
        self.assertEqual(events[0].metadata["task_id"], "P01_T")

    def test_wer_counts_insertions_deletions_and_substitutions(self):
        self.assertEqual(word_errors("all stand clear", "stand clear now"), (2, 3))
        self.assertEqual(word_errors("", "noise"), (1, 0))

    def test_new_rule_can_be_added_without_engine_changes(self):
        module = types.ModuleType("research_test_rules")
        module.custom_rule = lambda timeline, config: RuleResult(config["id"], RuleStatus.PASS_DIRECT,
            "Synthetic contract test", [timeline[0].event_id], {"observed": timeline[0].start})
        timeline = merge_timeline([Event("example", 2, 3, "video", 1)])
        config = {"schema_version": 1, "rules": [{"id": "NEW_RESEARCH_RULE", "status": "approved",
                   "implementation": "research_test_rules:custom_rule", "parameters": {}}]}
        with patch.dict("sys.modules", research_test_rules=module):
            results = evaluate(timeline, config)
        self.assertEqual(results[0].rule_id, "NEW_RESEARCH_RULE")
        self.assertEqual(results[0].supporting_events, [timeline[0].event_id])

    def test_rule_cannot_cite_nonexistent_evidence(self):
        module = types.ModuleType("research_test_rules")
        module.custom_rule = lambda timeline, config: RuleResult("X", RuleStatus.PASS_INFERRED,
                                                                "Synthetic test", ["missing"])
        config = {"schema_version": 1, "rules": [{"id": "X", "status": "approved",
                   "implementation": "research_test_rules:custom_rule"}]}
        with patch.dict("sys.modules", research_test_rules=module), self.assertRaisesRegex(ValueError, "outside"):
            evaluate([], config)

    def test_model_catalog_accepts_another_developers_adapter(self):
        module = types.ModuleType("research_test_models")
        class CustomDetector:
            def __init__(self, threshold):
                self.threshold = threshold
            def detect(self, video):
                return []
        module.CustomDetector = CustomDetector
        catalog = {"schema_version": 1, "video": {"new_model": {
            "implementation": "research_test_models:CustomDetector", "defaults": {"threshold": 0.6}}}}
        with patch.dict("sys.modules", research_test_models=module):
            model = create_model("video", {"model": "new_model"}, catalog=catalog)
        self.assertEqual(model.threshold, 0.6)

    def test_ui_results_work_without_models(self):
        fixture = json.loads((ROOT / "tests/fixtures/sample_rule_results.json").read_text())
        results = [RuleResult.from_dict(row) for row in fixture]
        self.assertEqual(len(generate(results)), 5)
        self.assertEqual(results[1].status, RuleStatus.PASS_INFERRED)

    def test_schema_version_and_duplicate_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            Event("x", 0, 1, "video", 1, schema_version=2)
        event = Event("x", 0, 1, "video", 1, event_id="same")
        with self.assertRaisesRegex(ValueError, "Duplicate event"):
            merge_timeline([event, event])

    def test_record_preserves_other_runs_and_blocks_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record_experiment("a", "video", {"model": "yolo"}, {}, root=root)
            record_experiment("b", "audio", {"model": "whisper"}, {}, root=root)
            with self.assertRaises(FileExistsError):
                record_experiment("a", "video", {}, {}, root=root)
            record_experiment("a", "video", {"model": "yolo"}, {"map": 0.5}, root=root, update=True)
            with (root / "results_summary.csv").open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([r["run_id"] for r in rows], ["a", "b"])
            self.assertEqual(json.loads(rows[0]["metrics_json"]), {"map": 0.5})
            rebuild(root)
            with (root / "results_summary.csv").open(newline="") as stream:
                rebuilt = list(csv.DictReader(stream))
            self.assertEqual(rebuilt, rows)
            with self.assertRaises(ValueError):
                record_experiment("../escape", "video", {}, {}, root=root)


if __name__ == "__main__":
    unittest.main()
