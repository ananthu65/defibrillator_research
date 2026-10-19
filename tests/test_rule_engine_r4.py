"""Increment 16: R4, both discharge buttons pressed (P-036; D-057, D-093, D-108, D-115)."""
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
EXPORT = load_export_config()
FPS = 25.0
SHOCK_ONLY = ["shock_delivered_on_screen"]   # D-115: the removal is never an inference source


def config(sources=SHOCK_ONLY):
    rules = [{"id": "R4", "status": "approved", "parameters": {"inference_sources": sources}}]
    return RuleEngineConfig.from_dict({**copy.deepcopy(CATALOGUE), "rules": rules})


R4 = config()
NO_INFERENCE = config([])                         # reaches the coverage step
REGIONS = tuple(R4.engine.regions)
WINDOW = R4.engine.value("simultaneous_window_seconds")
ALL = ((0.0, 30.0),)


def ev(label, t, event_id=None, confidence=1.0, source="annotation"):
    return Event(label, t, t, source, confidence, event_id=event_id or f"{label}@{t}", camera_angle="LS")


def header(apical=ALL, sternal=ALL):
    """Paddle visibility in seconds; None = no paddle track (unknown)."""
    coverage, visibility = {}, {}
    for region, spans in (("apical_paddle", apical), ("sternal_paddle", sternal)):
        if spans is None:
            coverage[f"region:{region}"] = "unknown"
        else:
            visibility[f"region:{region}"] = [list(s) for s in spans]
            coverage[f"region:{region}"] = "covered" if spans == ALL else "unknown"
    return TimelineHeader.from_dict({"camera_angle": "LS", "duration_seconds": 30.0,
                                     "analyses_run": {"video": True, "audio": False},
                                     "coverage": coverage, "visibility": visibility}, regions=REGIONS)


PLACED = ev("paddles_firmly_on_chest", 10, "placed")
SHOCK = ev("shock_delivered_on_screen", 15, "shock")
REMOVED = ev("paddles_removed_after_shock", 20, "removed")


def press(t, event_id="press", **kwargs):
    return ev("both_paddle_buttons_pressed", t, event_id, **kwargs)


def run(events, head=None, cfg=R4):
    return assess(events, cfg, header=head if head is not None else header(), registry=discover())


def r4(events, head=None, cfg=R4):
    return run(events, head, cfg).outcome("R4")


class DirectEvidence(unittest.TestCase):
    def test_press_after_placement_and_before_the_shock_passes(self):
        result = run([PLACED, press(13), SHOCK])
        outcome = result.outcome("R4")
        self.assertEqual((outcome.kind, outcome.evidence, outcome.flags), ("pass_direct", ("press", "placed", "shock"), ()))
        self.assertEqual(result.overall.result, "pass")

    def test_press_within_the_window_after_the_shock_counts_as_at_it(self):
        self.assertEqual(r4([PLACED, SHOCK, press(15 + WINDOW)]).kind, "pass_direct")

    def test_press_within_the_window_before_the_placement_counts_as_after_it(self):
        self.assertEqual(r4([press(10 - WINDOW), PLACED, SHOCK]).kind, "pass_direct")

    def test_press_before_the_placement_is_before_placement(self):
        outcome = r4([press(8), PLACED, SHOCK])
        self.assertEqual((outcome.kind, outcome.failure_code, outcome.evidence),
                         ("fail", "before_placement", ("press", "placed")))

    def test_before_placement_beats_the_inference(self):
        self.assertEqual(r4([press(8), PLACED, SHOCK, REMOVED]).failure_code, "before_placement")

    def test_a_valid_press_satisfies_the_rule_even_after_an_early_one(self):
        """Repeated presses stay the supervisor's question (OQ-023); any valid one counts (D-012)."""
        outcome = r4([press(8, "early"), PLACED, press(13, "valid"), SHOCK])
        self.assertEqual((outcome.kind, outcome.evidence[0]), ("pass_direct", "valid"))

    def test_press_only_after_the_shock_is_contradictory(self):
        outcome = r4([PLACED, SHOCK, press(17)])
        self.assertEqual((outcome.kind, outcome.flags), ("unable_to_verify", ("contradictory",)))

    def test_no_placement_observed_leaves_the_order_unchecked(self):
        result = run([press(13), SHOCK])
        outcome = result.outcome("R4")
        self.assertEqual((outcome.kind, outcome.flags), ("pass_direct", ("order_not_checked",)))
        self.assertEqual(result.overall.result, "incomplete")

    def test_repeated_presses_count_stays_undecided(self):
        self.assertIsNone(R4.engine.expected_counts["both_paddle_buttons_pressed"].value)
        self.assertTrue(R4.engine.expected_counts["both_paddle_buttons_pressed"].undecided)

    def test_pending_in_the_catalogue(self):
        cfg = RuleEngineConfig.from_dict(CATALOGUE)
        self.assertEqual(run([PLACED, press(13), SHOCK], cfg=cfg).outcome("R4").kind, "pending")

    def test_invalid_inference_sources_is_an_engine_error(self):
        self.assertEqual(r4([SHOCK], cfg=config(["button_press"])).kind, "engine_error")


class Inference(unittest.TestCase):
    """D-057, D-115: the shock on screen infers the press; a paddle removal never does."""

    def test_inferred_from_the_shock(self):
        outcome = r4([PLACED, SHOCK, REMOVED])
        self.assertEqual((outcome.kind, outcome.evidence, outcome.flags), ("pass_inferred", ("shock",), ()))

    def test_a_removal_without_a_shock_on_screen_infers_nothing(self):
        """A view without the screen: no shock time, and the removal doesn't show a shock (D-115)."""
        outcome = r4([PLACED, REMOVED])
        self.assertEqual((outcome.kind, outcome.blocked_by), ("not_evaluable", "R5"))

    def test_the_removal_is_refused_as_an_inference_source(self):
        outcome = r4([PLACED, SHOCK], cfg=config(["shock_delivered_on_screen", "paddles_removed_after_shock"]))
        self.assertEqual(outcome.kind, "engine_error")

    def test_a_press_without_a_shock_time_is_not_evaluable(self):
        for events in ([PLACED, press(13), REMOVED], [PLACED, press(13)]):
            with self.subTest(events=[e.event_name for e in events]):
                outcome = r4(events)
                self.assertEqual((outcome.kind, outcome.blocked_by), ("not_evaluable", "R5"))

    def test_without_a_shock_time_an_early_press_fails_only_if_no_later_press(self):
        self.assertEqual(r4([press(8), PLACED], cfg=NO_INFERENCE).failure_code, "before_placement")
        later = r4([press(8, "early"), PLACED, press(13, "late")], cfg=NO_INFERENCE)
        self.assertEqual((later.kind, later.blocked_by), ("not_evaluable", "R5"))

    def test_no_inference_source_is_coverage(self):
        outcome = r4([PLACED, SHOCK], cfg=NO_INFERENCE)
        self.assertEqual(outcome.failure_code, "not_pressed")        # both paddles visible throughout

    def test_nothing_and_no_shock_time_is_not_evaluable_because_of_r5(self):
        self.assertEqual(r4([PLACED]).blocked_by, "R5")

    def test_with_the_shock_as_a_source_not_pressed_is_unreachable(self):
        """With a shock time there's a shock on screen, which infers; without one, Not evaluable because of R5."""
        self.assertEqual(r4([PLACED, SHOCK]).kind, "pass_inferred")
        self.assertEqual(r4([PLACED]).kind, "not_evaluable")


class Coverage(unittest.TestCase):
    """D-108: with no inference, not_pressed only if both paddles were visible from the placement (10 s) to the shock (15 s)."""

    def test_both_paddles_visible_throughout_is_not_pressed(self):
        outcome = r4([PLACED, SHOCK], header(apical=((8.0, 30.0),), sternal=((9.0, 16.0),)), NO_INFERENCE)
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "not_pressed"))
        self.assertIn("between the placement (10 s) and the shock (15 s)", outcome.reason)

    def test_a_paddle_partly_visible_is_unable_to_verify(self):
        outcome = r4([PLACED, SHOCK], header(sternal=((0.0, 12.0),)), NO_INFERENCE)
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("apical paddle covered, sternal paddle unknown", outcome.reason)

    def test_a_paddle_out_of_view_is_unable_to_verify(self):
        outcome = r4([PLACED, SHOCK], header(apical=((20.0, 30.0),)), NO_INFERENCE)
        self.assertIn("apical paddle not_covered", outcome.reason)

    def test_no_paddle_tracks_is_unable_to_verify(self):
        self.assertEqual(r4([PLACED, SHOCK], header(apical=None, sternal=None), NO_INFERENCE).kind, "unable_to_verify")

    def test_no_placement_uses_the_recording_start(self):
        partly = r4([SHOCK], header(apical=((5.0, 30.0),)), NO_INFERENCE)
        self.assertEqual(partly.kind, "unable_to_verify")
        throughout = r4([SHOCK], header(), NO_INFERENCE)
        self.assertEqual(throughout.failure_code, "not_pressed")
        self.assertIn("before the shock (15 s)", throughout.reason)

    def test_low_confidence_press_is_never_a_fail(self):
        outcome = r4([PLACED, press(13, "weak", confidence=0.2, source="video"), SHOCK], cfg=NO_INFERENCE)
        self.assertEqual((outcome.kind, outcome.evidence), ("unable_to_verify", ("weak",)))


def record(derived, tags, paddles=None):
    data = {"schema_version": 1, "kind": RECORD_KIND, "canonical_task_id": "P02_LS", "participant_id": "P02",
            "camera_view": "LS", "annotation_source": "x", "archive": "a.zip", "task_path": ".", "media_name": "x.mp4",
            "fps": FPS, "width": 1920, "height": 1080, "start_frame": 0, "stop_frame": 749, "duration_seconds": 30.0,
            "tags": [{"id": f"P02_LS_tag_{i:03d}", "label": label, "frame": frame, "timestamp_seconds": frame / FPS}
                     for i, (label, frame) in enumerate(tags, start=1)],
            "zone_tracks": {"apical_placement_zone": 1, "sternal_placement_zone": 1},
            "zone_visibility": [{"label": z, "start_frame": 0, "end_frame": 749, "start_seconds": 0.0,
                                 "end_seconds": 29.96} for z in ("apical_placement_zone", "sternal_placement_zone")],
            "screen_tracks": 0, "screen_visibility": [],
            "derived_events": [{"id": f"P02_LS_derived_{i:03d}", "event_name": name, "frame": frame,
                                "timestamp_seconds": frame / FPS, "evidence_type": "direct", "flags": ["derived_placement"],
                                "method": "paddle_in_zone_v1", "metadata": {"settings_sha256": EXPORT.placements.digest()}}
                               for i, (name, frame) in enumerate(derived, start=1)]}
    if paddles is not None:   # (start frame, end frame) for each paddle
        data["paddle_tracks"] = {"paddle_apical": 1, "paddle_sternal": 1}
        data["paddle_visibility"] = [{"label": label, "start_frame": a, "end_frame": b, "start_seconds": a / FPS,
                                      "end_seconds": b / FPS} for label, (a, b) in zip(("paddle_apical", "paddle_sternal"),
                                                                                     paddles)]
    return data


APPROVED = replace(EXPORT, placements=replace(EXPORT.placements, review=PlacementReview(
    "Arnikan", "2026-10-17", "a" * 64, EXPORT.placements.digest())))
MANIFEST = {"export_id": "a" * 64, "placement_settings_sha256": EXPORT.placements.digest()}
BOTH = [("apical_paddle_placed", 175), ("sternal_paddle_placed", 300)]            # 7 s and 12 s; no firm tag


class DerivedPlacementsAndPaddleVisibility(unittest.TestCase):
    """Past the gate, the later derived placement marks the placement (D-088)."""

    def outcome(self, tags, export=APPROVED, cfg=R4, paddles=None):
        adapted = adapt_record(record(BOTH, tags, paddles), cfg, export, MANIFEST)
        return r4(adapted.events, adapted.header, cfg)

    def test_approved_gate_press_after_the_later_derived_placement_passes(self):
        outcome = self.outcome([("both_paddle_buttons_pressed", 325), ("shock_delivered_on_screen", 375)])
        self.assertEqual((outcome.kind, outcome.evidence),
                         ("pass_direct", ("P02_LS_tag_001", "P02_LS_derived_002", "P02_LS_tag_002")))
        self.assertIn("derived_placement", outcome.flags)

    def test_approved_gate_press_between_the_two_placements_is_before_placement(self):
        outcome = self.outcome([("both_paddle_buttons_pressed", 250), ("shock_delivered_on_screen", 375)])
        self.assertEqual(outcome.failure_code, "before_placement")              # 10 s, before the sternal at 12 s

    def test_gate_not_approved_no_placement_is_known(self):
        outcome = self.outcome([("both_paddle_buttons_pressed", 250), ("shock_delivered_on_screen", 375)], EXPORT)
        self.assertEqual((outcome.kind, outcome.flags[0]), ("pass_direct", "order_not_checked"))

    def test_exported_paddle_visibility_reaches_r4(self):
        tags = [("shock_delivered_on_screen", 375)]
        throughout = self.outcome(tags, cfg=NO_INFERENCE, paddles=((0, 749), (0, 749)))
        self.assertEqual(throughout.failure_code, "not_pressed")
        partly = self.outcome(tags, cfg=NO_INFERENCE, paddles=((0, 749), (0, 320)))   # sternal leaves view at 12.8 s
        self.assertEqual(partly.kind, "unable_to_verify")
        missing = self.outcome(tags, cfg=NO_INFERENCE)                        # an export without paddle visibility
        self.assertEqual(missing.kind, "unable_to_verify")


if __name__ == "__main__":
    unittest.main()
