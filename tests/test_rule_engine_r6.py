"""Increment 14: R6, paddles removed after the shock (P-034; D-093, D-103, D-104)."""
import copy
from dataclasses import replace
import unittest

import yaml

from annotation.derive_paddle_placements import PlacementReview
from annotation.export_rule_engine_records import load_config as load_export_config
from pipeline.config import ROOT
from rules.adapters.annotation import RECORD_KIND, adapt_record
from rules.config import RuleEngineConfig, Setting
from rules.coverage import TimelineHeader
from rules.engine import assess
from rules.registry import discover
from schemas.event import Event

CATALOGUE = yaml.safe_load((ROOT / "configs/rules.yaml").read_text(encoding="utf-8"))
EXPORT = load_export_config()
FPS = 25.0
APPROVAL = {"approved_by": "Supervisor", "approved_on": "2026-10-17", "source": "test"}


def config(limit=None, **settings):
    data = {**copy.deepcopy(CATALOGUE), "rules": [{"id": "R6", "status": "approved"}]}
    if limit is not None:
        data["timing_limits"]["shock_to_removal_seconds"] = limit
    loaded = RuleEngineConfig.from_dict(data)
    if settings:
        engine = loaded.engine
        values = {**engine.settings, **{k: Setting(k, v) for k, v in settings.items()}}
        loaded = replace(loaded, engine=replace(engine, settings=values))
    return loaded


R6 = config()
REGIONS = tuple(R6.engine.regions)
WINDOW = R6.engine.value("simultaneous_window_seconds")


def ev(label, t, event_id=None, confidence=1.0, source="annotation"):
    return Event(label, t, t, source, confidence, event_id=event_id or f"{label}@{t}", camera_angle="LS")


def header(zones=((0.0, 30.0),)):
    """Both placement zones visible over `zones` (seconds); None = no zone tracks (unknown)."""
    coverage, visibility = {}, {}
    for region in ("apical_zone", "sternal_zone"):
        if zones is None:
            coverage[f"region:{region}"] = "unknown"
        else:
            visibility[f"region:{region}"] = [list(s) for s in zones]
            coverage[f"region:{region}"] = "covered" if zones == ((0.0, 30.0),) else "unknown"
    return TimelineHeader.from_dict({"camera_angle": "LS", "duration_seconds": 30.0,
                                     "analyses_run": {"video": True, "audio": False},
                                     "coverage": coverage, "visibility": visibility}, regions=REGIONS)


SHOCK = ev("shock_delivered_on_screen", 15, "shock")


def run(events, head=None, cfg=R6):
    return assess(events, cfg, header=head if head is not None else header(), registry=discover())


def r6(events, head=None, cfg=R6):
    return run(events, head, cfg).outcome("R6")


class WithShockTime(unittest.TestCase):
    def test_removal_after_the_shock_passes_with_timing_not_checked(self):
        result = run([SHOCK, ev("paddles_removed_after_shock", 20, "removed")])
        outcome = result.outcome("R6")
        self.assertEqual((outcome.kind, outcome.evidence, outcome.flags),
                         ("pass_direct", ("removed", "shock"), ("timing_not_checked",)))
        self.assertFalse(outcome.timing_checked)
        self.assertEqual(outcome.timestamps["seconds"], 5)
        self.assertEqual(result.overall.result, "incomplete")      # an unset limit keeps the overall result from Pass

    def test_removal_just_before_the_shock_is_treated_as_at_the_shock(self):
        outcome = r6([SHOCK, ev("paddles_removed_after_shock", 15 - WINDOW, "removed")])
        self.assertEqual(outcome.kind, "pass_direct")
        self.assertEqual(outcome.timestamps["seconds"], 0)

    def test_removal_clearly_before_the_shock_is_removed_before_shock(self):
        outcome = r6([SHOCK, ev("paddles_removed_after_shock", 15 - WINDOW - 0.1, "removed")])
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "removed_before_shock"))
        self.assertEqual(outcome.evidence, ("removed", "shock"))

    def test_approved_limit_exceeded_is_too_late(self):
        cfg = config({"value": 3, **APPROVAL})
        outcome = r6([SHOCK, ev("paddles_removed_after_shock", 20)], cfg=cfg)
        self.assertEqual((outcome.kind, outcome.failure_code, outcome.timing_checked), ("fail", "too_late", True))
        within = r6([SHOCK, ev("paddles_removed_after_shock", 17)], cfg=cfg)
        self.assertEqual((within.kind, within.flags, within.timing_checked), ("pass_direct", (), True))

    def test_approved_no_limit_passes_fully(self):
        """D-103: "no limit" is a decision, so timing is not left unchecked."""
        result = run([SHOCK, ev("paddles_removed_after_shock", 25)], cfg=config({"value": None, "no_limit": True, **APPROVAL}))
        outcome = result.outcome("R6")
        self.assertEqual((outcome.kind, outcome.flags, outcome.timing_checked), ("pass_direct", (), True))
        self.assertIn("no time limit applies", outcome.reason)
        self.assertEqual(result.overall.result, "pass")

    def test_unapproved_no_limit_leaves_timing_unchecked(self):
        cfg = config({"value": None, "no_limit": True, "source": "proposal"})
        outcome = r6([SHOCK, ev("paddles_removed_after_shock", 20)], cfg=cfg)
        self.assertEqual(outcome.flags, ("timing_not_checked", "limit_not_approved"))

    def test_pending_in_the_catalogue(self):
        cfg = RuleEngineConfig.from_dict(CATALOGUE)
        self.assertEqual(run([SHOCK, ev("paddles_removed_after_shock", 20)], cfg=cfg).outcome("R6").kind, "pending")


class WithoutShockTime(unittest.TestCase):
    def test_no_shock_on_screen_is_not_evaluable_because_of_r5_even_with_a_removal(self):
        outcome = r6([ev("paddles_removed_after_shock", 20)])
        self.assertEqual((outcome.kind, outcome.blocked_by), ("not_evaluable", "R5"))

    def test_multiple_shocks_is_not_evaluable_because_of_r5(self):
        events = [ev("shock_delivered_on_screen", 14, "s1"), ev("shock_delivered_on_screen", 16, "s2"),
                  ev("paddles_removed_after_shock", 20)]
        self.assertEqual(r6(events).blocked_by, "R5")

    def test_shock_time_taken_from_the_removal_is_unable_to_verify(self):
        """shock_time_fallback removal: the removal can't be judged against its own time."""
        outcome = r6([ev("paddles_removed_after_shock", 20)], cfg=config(shock_time_fallback="removal"))
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("shock_time_from_removal", outcome.flags)


class RemovalMissing(unittest.TestCase):
    """D-104: missing only if both placement zones were visible from the shock (15 s) to the end (30 s)."""

    def test_zones_visible_to_the_end_is_missing(self):
        outcome = r6([SHOCK], header(((5.0, 30.0),)))
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "missing"))
        self.assertIn("from the shock (15 s) to the end of the recording (30 s)", outcome.reason)

    def test_zones_out_of_view_before_the_end_is_unable_to_verify(self):
        outcome = r6([SHOCK], header(((0.0, 22.0),)))
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("apical zone unknown, sternal zone unknown", outcome.reason)

    def test_no_zone_tracks_is_unable_to_verify(self):
        self.assertEqual(r6([SHOCK], header(None)).kind, "unable_to_verify")

    def test_low_confidence_removal_is_never_a_fail(self):
        weak = ev("paddles_removed_after_shock", 20, "weak", confidence=0.2, source="video")
        outcome = r6([SHOCK, weak])
        self.assertEqual((outcome.kind, outcome.evidence), ("unable_to_verify", ("weak",)))


def record(derived, tags):
    """derived: (event name, frame, end frame, ended by exit)."""
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
                                "method": "paddle_in_zone_v1",
                                "metadata": {"settings_sha256": EXPORT.placements.digest(), "end_frame": end,
                                             "end_seconds": end / FPS, "ended_by_exit": exited}}
                               for i, (name, frame, end, exited) in enumerate(derived, start=1)]}


APPROVED = replace(EXPORT, placements=replace(EXPORT.placements, review=PlacementReview(
    "Arnikan", "2026-10-17", "a" * 64, EXPORT.placements.digest())))
MANIFEST = {"export_id": "a" * 64, "placement_settings_sha256": EXPORT.placements.digest()}
TAGS = [("shock_delivered_on_screen", 375), ("paddles_removed_after_shock", 500)]   # 15 s and 20 s
APICAL_OFF_EARLY = [("apical_paddle_placed", 175, 300, True),       # on 7 s -> off at 12 s by a real exit
                    ("sternal_paddle_placed", 200, 749, False)]


class DerivedPlacements(unittest.TestCase):
    """Past the gate, a placement episode ending before the shock is evidence of removed_before_shock."""

    def adapted(self, derived, export=APPROVED):
        return adapt_record(record(derived, TAGS), R6, export, MANIFEST)

    def test_approved_gate_episode_ending_before_the_shock_is_removed_before_shock(self):
        adapted = self.adapted(APICAL_OFF_EARLY)
        outcome = r6(adapted.events, adapted.header)
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "removed_before_shock"))
        self.assertEqual(outcome.evidence, ("P02_LS_derived_001", "P02_LS_tag_001"))
        self.assertIn("apical paddle off its zone at 12 s", outcome.reason)
        self.assertIn("derived_placement", outcome.flags)

    def test_gate_not_approved_the_episode_never_reaches_r6(self):
        adapted = self.adapted(APICAL_OFF_EARLY, EXPORT)
        self.assertEqual(adapted.derived_withheld, 2)
        outcome = r6(adapted.events, adapted.header)
        self.assertEqual(outcome.kind, "pass_direct")                       # the removal tag at 20 s
        self.assertNotIn("derived_placement", outcome.flags)

    def test_paddle_placed_again_before_the_shock_is_not_removed_early(self):
        derived = [*APICAL_OFF_EARLY, ("apical_paddle_placed", 320, 749, False)]   # back on at 12.8 s
        adapted = self.adapted(derived)
        self.assertEqual(r6(adapted.events, adapted.header).kind, "pass_direct")

    def test_episode_ending_within_the_window_of_the_shock_is_at_the_shock(self):
        adapted = self.adapted([("apical_paddle_placed", 175, 370, True), ("sternal_paddle_placed", 200, 749, False)])
        self.assertEqual(r6(adapted.events, adapted.header).kind, "pass_direct")   # off at 14.8 s


if __name__ == "__main__":
    unittest.main()
