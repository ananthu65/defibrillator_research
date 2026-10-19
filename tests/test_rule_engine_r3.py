"""Increment 15: R3, paddles placed firmly on the chest (P-035; D-057, D-093, D-106, D-115)."""
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
    rules = [{"id": "R3", "status": "approved", "parameters": {"inference_sources": sources}}]
    return RuleEngineConfig.from_dict({**copy.deepcopy(CATALOGUE), "rules": rules})


R3 = config()
NO_INFERENCE = config([])                         # reaches the coverage step
REGIONS = tuple(R3.engine.regions)
WINDOW = R3.engine.value("simultaneous_window_seconds")


def ev(label, t, event_id=None, confidence=1.0, source="annotation"):
    return Event(label, t, t, source, confidence, event_id=event_id or f"{label}@{t}", camera_angle="LS")


def header(apical=((0.0, 30.0),), sternal=((0.0, 30.0),)):
    """Zone visibility in seconds; None = no track (unknown)."""
    coverage, visibility = {}, {}
    for region, spans in (("apical_zone", apical), ("sternal_zone", sternal)):
        if spans is None:
            coverage[f"region:{region}"] = "unknown"
        else:
            visibility[f"region:{region}"] = [list(s) for s in spans]
            coverage[f"region:{region}"] = "covered" if spans == ((0.0, 30.0),) else "unknown"
    return TimelineHeader.from_dict({"camera_angle": "LS", "duration_seconds": 30.0,
                                     "analyses_run": {"video": True, "audio": False},
                                     "coverage": coverage, "visibility": visibility}, regions=REGIONS)


TAKEN = ev("first_paddle_taken", 5, "taken")
SHOCK = ev("shock_delivered_on_screen", 15, "shock")


def run(events, head=None, cfg=R3):
    return assess(events, cfg, header=head if head is not None else header(), registry=discover())


def r3(events, head=None, cfg=R3):
    return run(events, head, cfg).outcome("R3")


class DirectEvidence(unittest.TestCase):
    def test_firm_placement_before_the_shock_passes(self):
        result = run([TAKEN, ev("paddles_firmly_on_chest", 12, "firm"), SHOCK])
        outcome = result.outcome("R3")
        self.assertEqual((outcome.kind, outcome.evidence, outcome.flags), ("pass_direct", ("firm", "shock"), ()))
        self.assertEqual(result.overall.result, "pass")      # placement timing and presence only (D-106)

    def test_firm_placement_within_the_window_after_the_shock_counts_as_at_it(self):
        self.assertEqual(r3([ev("paddles_firmly_on_chest", 15 + WINDOW), SHOCK]).kind, "pass_direct")

    def test_firm_placement_only_after_the_shock_is_placed_after_shock(self):
        outcome = r3([ev("paddles_firmly_on_chest", 17, "firm"), SHOCK])
        self.assertEqual((outcome.kind, outcome.failure_code, outcome.evidence), ("fail", "placed_after_shock",
                                                                                ("firm", "shock")))

    def test_a_placement_before_the_shock_satisfies_the_rule_even_if_repeated_after(self):
        outcome = r3([ev("paddles_firmly_on_chest", 12, "early"), SHOCK, ev("paddles_firmly_on_chest", 18)])
        self.assertEqual((outcome.kind, outcome.evidence), ("pass_direct", ("early", "shock")))

    def test_placed_after_shock_beats_the_inference(self):
        """Direct evidence of the mistake is not overridden by the shock on screen."""
        outcome = r3([ev("paddles_firmly_on_chest", 17), SHOCK, ev("paddles_removed_after_shock", 20)])
        self.assertEqual(outcome.failure_code, "placed_after_shock")

    def test_not_in_zone_is_never_produced(self):
        """OQ-012: the chest regions are not approved, so only timing and presence are checked."""
        for events in ([ev("paddles_firmly_on_chest", 12), SHOCK], [ev("paddles_firmly_on_chest", 17), SHOCK]):
            self.assertNotEqual(r3(events).failure_code, "not_in_zone")

    def test_pending_in_the_catalogue(self):
        cfg = RuleEngineConfig.from_dict(CATALOGUE)
        self.assertEqual(run([ev("paddles_firmly_on_chest", 12), SHOCK], cfg=cfg).outcome("R3").kind, "pending")

    def test_invalid_inference_sources_is_an_engine_error(self):
        self.assertEqual(r3([SHOCK], cfg=config(["shock_given"])).kind, "engine_error")
        self.assertEqual(r3([SHOCK], cfg=config(None)).kind, "engine_error")


class Inference(unittest.TestCase):
    """D-057, D-115: when direct evidence is missing, the shock on screen gives Pass - Inferred. A paddle
    removal never does: it doesn't show that a shock was delivered."""

    def test_inferred_from_the_shock_on_screen(self):
        outcome = r3([TAKEN, SHOCK, ev("paddles_removed_after_shock", 20)])
        self.assertEqual((outcome.kind, outcome.evidence, outcome.flags), ("pass_inferred", ("shock",), ()))
        self.assertIn("inferred from shock_delivered_on_screen", outcome.reason)

    def test_a_removal_without_a_shock_on_screen_infers_nothing(self):
        outcome = r3([TAKEN, ev("paddles_removed_after_shock", 20, "removed")])
        self.assertEqual((outcome.kind, outcome.blocked_by), ("not_evaluable", "R5"))

    def test_the_removal_is_refused_as_an_inference_source(self):
        for sources in (["paddles_removed_after_shock"], ["shock_delivered_on_screen", "paddles_removed_after_shock"]):
            with self.subTest(sources=sources):
                outcome = r3([TAKEN, SHOCK], cfg=config(sources))
                self.assertEqual(outcome.kind, "engine_error")
                self.assertIn("doesn't show that a shock was delivered", outcome.reason)

    def test_the_catalogue_lists_only_the_shock(self):
        self.assertEqual(RuleEngineConfig.from_dict(CATALOGUE).rule("R3").parameters["inference_sources"],
                         ["shock_delivered_on_screen"])

    def test_a_tag_without_a_shock_time_cannot_be_checked_directly(self):
        """D-093: R3's direct check needs the shock time; a removal doesn't supply one."""
        removed = r3([ev("paddles_firmly_on_chest", 12), ev("paddles_removed_after_shock", 20, "removed")])
        self.assertEqual((removed.kind, removed.blocked_by), ("not_evaluable", "R5"))
        alone = r3([ev("paddles_firmly_on_chest", 12)])
        self.assertEqual((alone.kind, alone.blocked_by), ("not_evaluable", "R5"))

    def test_no_evidence_and_no_shock_time_is_not_evaluable_because_of_r5(self):
        outcome = r3([TAKEN])
        self.assertEqual((outcome.kind, outcome.blocked_by), ("not_evaluable", "R5"))


class Coverage(unittest.TestCase):
    """D-106: with no inference, a missing tag fails only if both zones were visible over first paddle taken -> shock."""

    def test_both_zones_visible_throughout_the_placement_phase_is_missing(self):
        outcome = r3([TAKEN, SHOCK], header(apical=((2.0, 30.0),), sternal=((4.0, 30.0),)), NO_INFERENCE)
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "missing"))
        self.assertIn("between taking the first paddle (5 s) and the shock (15 s)", outcome.reason)

    def test_one_paddle_visible_is_unable_to_verify(self):
        """The tag is not made when only one paddle is visible (A-019)."""
        outcome = r3([TAKEN, SHOCK], header(sternal=None), NO_INFERENCE)
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("apical zone covered, sternal zone unknown", outcome.reason)

    def test_a_zone_visible_for_part_of_the_phase_is_unable_to_verify(self):
        outcome = r3([TAKEN, SHOCK], header(sternal=((10.0, 30.0),)), NO_INFERENCE)
        self.assertEqual(outcome.kind, "unable_to_verify")

    def test_without_first_paddle_taken_the_phase_starts_at_the_recording_start(self):
        visible_from_2 = header(apical=((2.0, 30.0),), sternal=((2.0, 30.0),))
        self.assertEqual(r3([SHOCK], visible_from_2, NO_INFERENCE).kind, "unable_to_verify")
        outcome = r3([SHOCK], header(), NO_INFERENCE)
        self.assertEqual(outcome.failure_code, "missing")
        self.assertIn("before the shock (15 s)", outcome.reason)

    def test_low_confidence_firm_placement_is_never_a_fail(self):
        weak = ev("paddles_firmly_on_chest", 12, "weak", confidence=0.2, source="video")
        outcome = r3([TAKEN, weak, SHOCK], cfg=NO_INFERENCE)
        self.assertEqual((outcome.kind, outcome.evidence), ("unable_to_verify", ("weak",)))

    def test_with_the_shock_as_a_source_a_shock_on_screen_always_infers(self):
        """With a shock time, the shock on screen is itself an inference source, so coverage is not reached."""
        self.assertEqual(r3([TAKEN, SHOCK], header(sternal=None)).kind, "pass_inferred")


def record(derived, tags):
    return {"schema_version": 1, "kind": RECORD_KIND, "canonical_task_id": "P02_LS", "participant_id": "P02",
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


APPROVED = replace(EXPORT, placements=replace(EXPORT.placements, review=PlacementReview(
    "Arnikan", "2026-10-17", "a" * 64, EXPORT.placements.digest())))
MANIFEST = {"export_id": "a" * 64, "placement_settings_sha256": EXPORT.placements.digest()}
TAGS = [("first_paddle_taken", 125), ("shock_delivered_on_screen", 375)]          # no paddles_firmly_on_chest
BOTH = [("apical_paddle_placed", 175), ("sternal_paddle_placed", 300)]            # 7 s and 12 s


class DerivedPlacements(unittest.TestCase):
    """Past the gate, both derived placements before the shock are direct evidence (D-088, D-106)."""

    def outcome(self, derived, export=APPROVED, cfg=R3):
        adapted = adapt_record(record(derived, TAGS), cfg, export, MANIFEST)
        return adapted, r3(adapted.events, adapted.header, cfg)

    def test_approved_gate_both_placements_before_the_shock_pass_directly(self):
        _, outcome = self.outcome(BOTH)
        self.assertEqual((outcome.kind, outcome.evidence),
                         ("pass_direct", ("P02_LS_derived_001", "P02_LS_derived_002", "P02_LS_tag_002")))
        self.assertIn("derived_placement", outcome.flags)

    def test_gate_not_approved_the_placements_never_reach_r3(self):
        adapted, outcome = self.outcome(BOTH, EXPORT)
        self.assertEqual(adapted.derived_withheld, 2)
        self.assertEqual(outcome.kind, "pass_inferred")                       # from the shock on screen
        self.assertNotIn("derived_placement", outcome.flags)

    def test_one_derived_placement_is_not_direct_evidence(self):
        _, outcome = self.outcome(BOTH[:1], cfg=NO_INFERENCE)
        self.assertEqual(outcome.failure_code, "missing")                     # both zones visible, no firm tag

    def test_a_placement_after_the_shock_is_not_direct_evidence(self):
        _, outcome = self.outcome([("apical_paddle_placed", 175), ("sternal_paddle_placed", 450)], cfg=NO_INFERENCE)
        self.assertNotEqual(outcome.kind, "pass_direct")


if __name__ == "__main__":
    unittest.main()
