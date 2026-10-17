"""Increment 12: R8, apical paddle placed before sternal (P-015; D-013, D-014, D-015, D-058, D-060, D-091, D-098, D-099)."""
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


def config(*rule_ids, **settings):
    data = {**copy.deepcopy(CATALOGUE), "rules": [{"id": r, "status": "approved"} for r in rule_ids]}
    loaded = RuleEngineConfig.from_dict(data)
    if settings:
        engine = loaded.engine
        values = {**engine.settings, **{k: Setting(k, v) for k, v in settings.items()}}
        loaded = replace(loaded, engine=replace(engine, settings=values))
    return loaded


R8 = config("R8")
REGIONS = tuple(R8.engine.regions)


def ev(label, t, event_id=None, confidence=1.0, source="annotation"):
    return Event(label, t, t, source, confidence, event_id=event_id or f"{label}@{t}", camera_angle="LS")


def header(apical=((0.0, 30.0),), sternal=((0.0, 30.0),)):
    """Zone visibility; None = no track (unknown), () = never visible."""
    coverage, visibility = {}, {}
    for region, spans in (("apical_zone", apical), ("sternal_zone", sternal)):
        if spans is None:
            coverage[f"region:{region}"] = "unknown"
        else:
            visibility[f"region:{region}"] = [list(s) for s in spans]
            coverage[f"region:{region}"] = "covered" if spans == ((0.0, 30.0),) else ("not_covered" if not spans else "unknown")
    return TimelineHeader.from_dict({"camera_angle": "LS", "duration_seconds": 30.0,
                                     "analyses_run": {"video": True, "audio": False},
                                     "coverage": coverage, "visibility": visibility}, regions=REGIONS)


ONE_ZONE = dict(apical=((0.0, 30.0),), sternal=None)        # an LL-like view: apical zone only
TAGS = [ev("first_paddle_taken", 5), ev("second_paddle_taken", 10), ev("paddles_firmly_on_chest", 14)]


def r8(events, head=None, cfg=R8):
    return assess(events, cfg, header=head, registry=discover()).outcome("R8")


class BothZonesVisible(unittest.TestCase):
    def test_apical_first_passes(self):
        outcome = r8([*TAGS, ev("apical_paddle_placed", 7, "a"), ev("sternal_paddle_placed", 12, "s")], header())
        self.assertEqual((outcome.kind, outcome.evidence), ("pass_direct", ("a", "s")))

    def test_sternal_first_is_wrong_order(self):
        outcome = r8([*TAGS, ev("apical_paddle_placed", 12), ev("sternal_paddle_placed", 7)], header())
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "wrong_order"))

    def test_same_time_is_simultaneous(self):
        outcome = r8([*TAGS, ev("apical_paddle_placed", 7), ev("sternal_paddle_placed", 7.3)], header())
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "simultaneous"))

    def test_one_placement_missing_is_placement_missing_not_wrong_order(self):
        outcome = r8([*TAGS, ev("first_paddle_firmly_on_the_chest", 7), ev("apical_paddle_placed", 7)], header())
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("placement_missing", outcome.flags)
        self.assertIn("no sternal placement", outcome.reason)

    def test_both_placements_missing_while_in_view(self):
        outcome = r8([*TAGS, ev("first_paddle_firmly_on_the_chest", 7)], header())
        self.assertEqual((outcome.kind, outcome.flags), ("unable_to_verify", ("placement_missing",)))

    def test_pending_in_the_catalogue(self):
        self.assertEqual(assess(TAGS, CATALOGUE, registry=discover()).outcome("R8").kind, "pending")


class OneZoneVisible(unittest.TestCase):
    """D-013: only the apical zone in view; its placement against the first placement (window 0.5 s)."""

    def outcome(self, apical_at, first_at=7, cfg=R8, head=None):
        events = [*TAGS, ev("first_paddle_firmly_on_the_chest", first_at, "first")]
        if apical_at is not None:
            events.append(ev("apical_paddle_placed", apical_at, "a"))
        return r8(events, head or header(**ONE_ZONE), cfg)

    def test_visible_paddle_at_the_first_placement_time_was_first(self):
        outcome = self.outcome(7.2)
        self.assertEqual((outcome.kind, outcome.evidence), ("pass_inferred", ("a", "first")))

    def test_visible_paddle_clearly_later_means_the_other_was_first(self):
        outcome = self.outcome(11)   # the apical paddle was second, so the sternal was first: an inferred mistake
        self.assertEqual((outcome.kind, outcome.flags), ("unable_to_verify", ("inferred_fail_policy_undecided",)))
        self.assertIn("so the sternal paddle was first", outcome.reason)

    def test_inferred_mistake_follows_the_setting_once_decided(self):
        failing = self.outcome(11, cfg=config("R8", inferred_fail_outcome="fail"))
        self.assertEqual((failing.kind, failing.failure_code), ("fail", "wrong_order"))
        lenient = self.outcome(11, cfg=config("R8", inferred_fail_outcome="unable_to_verify"))
        self.assertEqual((lenient.kind, lenient.flags), ("unable_to_verify", ()))

    def test_visible_paddle_clearly_before_the_first_placement_is_contradictory(self):
        outcome = self.outcome(4)
        self.assertEqual((outcome.kind, outcome.flags), ("unable_to_verify", ("contradictory",)))

    def test_visible_zone_without_its_placement_is_placement_missing(self):
        outcome = self.outcome(None)
        self.assertEqual((outcome.kind, outcome.flags), ("unable_to_verify", ("placement_missing",)))

    def test_sternal_zone_only(self):
        events = [*TAGS, ev("first_paddle_firmly_on_the_chest", 7, "first"), ev("sternal_paddle_placed", 7.1, "s")]
        outcome = r8(events, header(apical=None, sternal=((0.0, 30.0),)))   # sternal first: inferred mistake
        self.assertEqual((outcome.kind, outcome.flags), ("unable_to_verify", ("inferred_fail_policy_undecided",)))

    def test_no_first_placement_is_not_determinable(self):
        events = [*TAGS, ev("apical_paddle_placed", 7)]
        outcome = r8(events, header(**ONE_ZONE))
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("no first placement time", outcome.reason)


class ZoneWindows(unittest.TestCase):
    """D-099: a zone counts as visible when it is covered over the placement phase (here 5-14 s)."""

    def test_zone_out_of_view_during_the_placement_phase_does_not_count(self):
        # The sternal zone is visible only after 20 s, so during placement only the apical zone was in view:
        # its missing sternal placement is not placement_missing; the one-zone inference applies.
        events = [*TAGS, ev("first_paddle_firmly_on_the_chest", 7, "first"), ev("apical_paddle_placed", 7.1, "a")]
        outcome = r8(events, header(apical=((0.0, 30.0),), sternal=((20.0, 30.0),)))
        self.assertEqual(outcome.kind, "pass_inferred")

    def test_zone_in_view_for_only_part_of_the_phase_does_not_count_as_visible(self):
        events = [*TAGS, ev("first_paddle_firmly_on_the_chest", 7, "first"), ev("apical_paddle_placed", 7.1, "a")]
        outcome = r8(events, header(apical=((0.0, 30.0),), sternal=((0.0, 9.0),)))
        self.assertEqual(outcome.kind, "pass_inferred")


class Fallback(unittest.TestCase):
    """D-014, D-060: the apical-first fallback is off by default."""

    EVENTS = [*TAGS, ev("first_paddle_firmly_on_the_chest", 7)]

    def test_off_by_default_not_determinable_is_unable_to_verify(self):
        self.assertFalse(R8.engine.value("assume_first_taken_is_apical"))
        outcome = r8(self.EVENTS, header(apical=None, sternal=None))
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("no placement zone was in view", outcome.reason)

    def test_on_gives_an_assumed_result_and_no_overall_pass(self):
        cfg = config("R8", assume_first_taken_is_apical=True)
        result = assess(self.EVENTS, cfg, header=header(apical=None, sternal=None), registry=discover())
        outcome = result.outcome("R8")
        self.assertEqual((outcome.kind, outcome.evidence), ("assumed", ("first_paddle_taken@5",)))
        self.assertIn("to be checked by the evaluator", outcome.reason)
        self.assertEqual(result.overall.result, "incomplete")

    def test_fallback_never_overrides_evidence(self):
        cfg = config("R8", assume_first_taken_is_apical=True)
        outcome = r8([*TAGS, ev("apical_paddle_placed", 12), ev("sternal_paddle_placed", 7)], header(), cfg)
        self.assertEqual(outcome.failure_code, "wrong_order")


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
                                "timestamp_seconds": frame / FPS, "evidence_type": "direct", "flags": list(flags),
                                "method": "paddle_in_zone_v1", "metadata": {"settings_sha256": EXPORT.placements.digest()}}
                               for i, (name, frame, flags) in enumerate(derived, start=1)]}


APPROVED = replace(EXPORT, placements=replace(EXPORT.placements, review=PlacementReview(
    "Arnikan", "2026-10-17", "a" * 64, EXPORT.placements.digest())))
MANIFEST = {"export_id": "a" * 64, "placement_settings_sha256": EXPORT.placements.digest()}
ORDERED = [("apical_paddle_placed", 175, ("derived_placement",)), ("sternal_paddle_placed", 300, ("derived_placement",))]
ORDERED_TAGS = [("first_paddle_taken", 125), ("first_paddle_firmly_on_the_chest", 176), ("second_paddle_taken", 250),
                ("paddles_firmly_on_chest", 350)]


class Gate(unittest.TestCase):
    """D-088: derived placements reach R8 only for the reviewed export and settings."""

    def test_approved_gate_derived_placements_are_used_and_flagged(self):
        adapted = adapt_record(record(ORDERED, ORDERED_TAGS), R8, APPROVED, MANIFEST)
        outcome = r8(adapted.events, adapted.header)   # annotation data: also annotation_coverage_assumed (D-066)
        self.assertEqual((outcome.kind, outcome.flags), ("pass_direct", ("derived_placement", "annotation_coverage_assumed")))

    def test_gate_not_approved_the_placements_never_reach_r8(self):
        adapted = adapt_record(record(ORDERED, ORDERED_TAGS), R8, EXPORT, MANIFEST)
        self.assertEqual(adapted.derived_withheld, 2)
        outcome = r8(adapted.events, adapted.header)   # both zones in view, no placement observed (D-058)
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("placement_missing", outcome.flags)
        self.assertNotIn("derived_placement", outcome.flags)


class ParallelPlacement(unittest.TestCase):
    """D-098: one parallel placement fails both R2 and R8 with `simultaneous`, sharing the cause flag."""

    PARALLEL = [("apical_paddle_placed", 175, ("derived_placement", "possible_parallel_placement")),
                ("sternal_paddle_placed", 177, ("derived_placement", "possible_parallel_placement"))]
    TAGS = [("first_paddle_taken", 125), ("second_paddle_taken", 150), ("paddles_firmly_on_chest", 250)]   # no T1 (A-019)

    def test_approved_gate_fails_both_rules_with_the_shared_cause_flag(self):
        both = config("R2", "R8")
        adapted = adapt_record(record(self.PARALLEL, self.TAGS), both, APPROVED, MANIFEST)
        result = assess(adapted.events, both, header=adapted.header, registry=discover())
        for rule_id in ("R2", "R8"):
            with self.subTest(rule_id):
                outcome = result.outcome(rule_id)
                self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "simultaneous"))
                self.assertIn("possible_parallel_placement", outcome.flags)
                self.assertIn("derived_placement", outcome.flags)
        self.assertEqual([m.rule_ids for m in result.overall.mistakes], [("R2",), ("R8",)])   # two mistakes, D-098
        self.assertEqual(result.overall.result, "fail")

    def test_gate_not_approved_neither_rule_sees_the_parallel_placement(self):
        both = config("R2", "R8")
        adapted = adapt_record(record(self.PARALLEL, self.TAGS), both, EXPORT, MANIFEST)
        result = assess(adapted.events, both, header=adapted.header, registry=discover())
        self.assertEqual(result.outcome("R2").failure_code, "first_placement_not_observed")   # D-097
        r8_outcome = result.outcome("R8")
        self.assertEqual(r8_outcome.kind, "unable_to_verify")
        self.assertIn("placement_missing", r8_outcome.flags)
        self.assertTrue(all("possible_parallel_placement" not in result.outcome(r).flags for r in ("R2", "R8")))


if __name__ == "__main__":
    unittest.main()
