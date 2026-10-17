"""Increment 11: R2, second paddle taken only after the first is placed (D-051, D-091, D-095)."""
import copy
from dataclasses import replace
import unittest

import yaml

from annotation.derive_paddle_placements import PlacementReview
from annotation.export_rule_engine_records import load_config as load_export_config
from pipeline.config import ROOT
from rules.adapters.annotation import RECORD_KIND, adapt_record
from rules.config import RuleEngineConfig
from rules.coverage import TimelineHeader
from rules.engine import assess
from rules.registry import discover
from schemas.event import Event

CATALOGUE = yaml.safe_load((ROOT / "configs/rules.yaml").read_text(encoding="utf-8"))
R2_APPROVED = RuleEngineConfig.from_dict({**copy.deepcopy(CATALOGUE), "rules": [{"id": "R2", "status": "approved"}]})
REGIONS = tuple(R2_APPROVED.engine.regions)
EXPORT = load_export_config()
FPS = 25.0


def ev(label, t, event_id=None, confidence=1.0, source="annotation"):
    return Event(label, t, t, source, confidence, event_id=event_id or f"{label}@{t}", camera_angle="LS")


def header(apical=((0.0, 20.0),), sternal=((0.0, 20.0),), duration=20.0):
    """Both placement zones visible throughout 0-20 s by default."""
    visibility = {}
    if apical is not None:
        visibility["region:apical_zone"] = [list(span) for span in apical]
    if sternal is not None:
        visibility["region:sternal_zone"] = [list(span) for span in sternal]
    return TimelineHeader.from_dict({"recording_id": None, "camera_angle": "LS", "duration_seconds": duration,
                                     "analyses_run": {"video": True, "audio": False},
                                     "coverage": {"region:apical_zone": "unknown", "region:sternal_zone": "unknown"},
                                     "visibility": visibility}, regions=REGIONS)


def r2(events, head=None, config=R2_APPROVED):
    return assess(events, config, header=head, registry=discover()).outcome("R2")


TAKEN = ev("first_paddle_taken", 5)


class Order(unittest.TestCase):
    def test_first_placed_before_the_second_is_taken_passes(self):
        outcome = r2([TAKEN, ev("first_paddle_firmly_on_the_chest", 7, "p1"), ev("second_paddle_taken", 9, "s2")])
        self.assertEqual((outcome.kind, outcome.evidence), ("pass_direct", ("p1", "s2")))
        self.assertEqual(outcome.timestamps, {"first_paddle_placed": 7, "second_paddle_taken": 9})

    def test_second_taken_before_the_first_is_placed(self):
        outcome = r2([TAKEN, ev("second_paddle_taken", 7), ev("first_paddle_firmly_on_the_chest", 9)])
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "taken_before_first_placed"))

    def test_at_the_same_time_is_simultaneous(self):
        outcome = r2([TAKEN, ev("first_paddle_firmly_on_the_chest", 7), ev("second_paddle_taken", 7.3)])
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "simultaneous"))

    def test_no_second_paddle_taken_cannot_be_checked(self):
        outcome = r2([TAKEN, ev("first_paddle_firmly_on_the_chest", 7)], header())
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("order cannot be checked", outcome.reason)

    def test_pending_in_the_catalogue_until_approved(self):
        result = assess([TAKEN], CATALOGUE, registry=discover())
        self.assertEqual(result.outcome("R2").kind, "pending")


class FirstPlacementMissing(unittest.TestCase):
    """D-095: coverage of both placement zones from first paddle taken (5 s) to second paddle taken (9 s)."""

    EVENTS = [TAKEN, ev("second_paddle_taken", 9)]

    def test_zones_visible_throughout_is_first_placement_not_observed(self):
        outcome = r2(self.EVENTS, header())
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "first_placement_not_observed"))
        self.assertIn("either the paddles were placed in parallel, or the second paddle was taken before the first "
                      "was placed", outcome.reason)
        self.assertNotEqual(outcome.failure_code, "first_missing")   # D-097: never used for this case

    def test_first_placement_while_the_zones_were_out_of_view_is_unable_to_verify(self):
        outcome = r2(self.EVENTS, header(apical=((0.0, 4.0), (10.0, 20.0)), sternal=((0.0, 4.0), (10.0, 20.0))))
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("apical zone not_covered, sternal zone not_covered", outcome.reason)

    def test_one_zone_visible_for_only_part_of_the_window_is_unable_to_verify(self):
        outcome = r2(self.EVENTS, header(sternal=((0.0, 7.0),)))
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("sternal zone unknown", outcome.reason)

    def test_no_header_is_unable_to_verify(self):
        self.assertEqual(r2(self.EVENTS).kind, "unable_to_verify")

    def test_low_confidence_first_placement_is_unable_to_verify(self):
        weak = ev("first_paddle_placed", 7, "weak", confidence=0.2, source="video")
        self.assertEqual(r2([*self.EVENTS, weak], header()).kind, "unable_to_verify")

    def test_no_first_paddle_taken_gives_no_window(self):
        outcome = r2([ev("second_paddle_taken", 9)], header())
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("no window", outcome.reason)


def parallel_record():
    """Both paddles placed together at 0.8 s; no first-placement tag (A-019); zones visible throughout."""
    derived = [{"id": f"P01_LS_derived_00{i}", "event_name": name, "frame": frame, "timestamp_seconds": frame / FPS,
                "evidence_type": "direct", "flags": ["derived_placement", "possible_parallel_placement"],
                "method": "paddle_in_zone_v1", "metadata": {"settings_sha256": EXPORT.placements.digest()}}
               for i, (name, frame) in enumerate((("apical_paddle_placed", 20), ("sternal_paddle_placed", 22)), start=1)]
    tags = [("first_paddle_taken", 5), ("second_paddle_taken", 10), ("paddles_firmly_on_chest", 30)]
    return {"schema_version": 1, "kind": RECORD_KIND, "canonical_task_id": "P01_LS", "participant_id": "P01",
            "camera_view": "LS", "annotation_source": "x", "archive": "a.zip", "task_path": ".", "media_name": "x.mp4",
            "fps": FPS, "width": 1920, "height": 1080, "start_frame": 0, "stop_frame": 99, "duration_seconds": 4.0,
            "tags": [{"id": f"P01_LS_tag_00{i}", "label": label, "frame": frame, "timestamp_seconds": frame / FPS}
                     for i, (label, frame) in enumerate(tags, start=1)],
            "zone_tracks": {"apical_placement_zone": 1, "sternal_placement_zone": 1},
            "zone_visibility": [{"label": zone, "start_frame": 0, "end_frame": 99, "start_seconds": 0.0, "end_seconds": 3.96}
                                for zone in ("apical_placement_zone", "sternal_placement_zone")],
            "screen_tracks": 0, "screen_visibility": [], "derived_events": derived}


class ParallelPlacement(unittest.TestCase):
    """D-091: a possible parallel placement gives `simultaneous`, but only once the gate is approved (D-088)."""

    MANIFEST = {"export_id": "a" * 64, "placement_settings_sha256": EXPORT.placements.digest()}

    def run_r2(self, export_config):
        adapted = adapt_record(parallel_record(), R2_APPROVED, export_config, self.MANIFEST)
        return adapted, r2(adapted.events, adapted.header)

    def test_with_an_approved_gate_it_is_simultaneous(self):
        approved = replace(EXPORT, placements=replace(EXPORT.placements, review=PlacementReview(
            "Arnikan", "2026-10-17", "a" * 64, EXPORT.placements.digest())))
        adapted, outcome = self.run_r2(approved)
        self.assertEqual(adapted.derived_included, 2)
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "simultaneous"))
        self.assertEqual(outcome.evidence, ("P01_LS_derived_001", "P01_LS_derived_002"))

    def test_without_an_approved_gate_the_placements_are_not_used(self):
        adapted, outcome = self.run_r2(EXPORT)   # nothing reviewed
        self.assertEqual((adapted.derived_included, adapted.derived_withheld), (0, 2))
        # No first-placement tag (the annotators' convention for a parallel placement, A-019) and the zones were
        # visible throughout: the not-observed code covers both explanations; the gate would refine it (D-097).
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "first_placement_not_observed"))
        self.assertNotIn("possible_parallel_placement", outcome.reason)


if __name__ == "__main__":
    unittest.main()
