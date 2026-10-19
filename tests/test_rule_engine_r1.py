"""Increment 17: R1, gel applied twice, once to each zone, before the paddles are placed (P-038; D-109 to D-113)."""
import copy
from dataclasses import replace
import unittest

import yaml

from annotation.derive_gel_applications import GelReview
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
APPROVAL = {"approved_by": "Supervisor", "approved_on": "2026-10-17", "source": "test"}


def config(period=None):
    data = {**copy.deepcopy(CATALOGUE), "rules": [{"id": "R1", "status": "approved"}]}
    if period is not None:
        data["timing_limits"]["gel_application_period_seconds"] = period
    return RuleEngineConfig.from_dict(data)


R1 = config()
REGIONS = tuple(R1.engine.regions)
GAP = R1.engine.value("gel_minimum_gap_seconds")
ALL = ((0.0, 30.0),)


def ev(label, t, event_id=None, confidence=1.0, source="annotation", **metadata):
    return Event(label, t, t, source, confidence, event_id=event_id or f"{label}@{t}", camera_angle="LS",
                 metadata=metadata)


def header(apical=ALL, sternal=ALL, gel=None):
    """Zone visibility (None = no track); gel = {"apical": status, "sternal": status} past the 9d gate."""
    coverage, visibility = {}, {}
    for region, spans in (("apical_zone", apical), ("sternal_zone", sternal)):
        if spans is None:
            coverage[f"region:{region}"] = "unknown"
        else:
            visibility[f"region:{region}"] = [list(s) for s in spans]
            coverage[f"region:{region}"] = "covered" if spans == ALL else "unknown"
    for zone, status in (gel or {}).items():
        coverage[f"region:{zone}_gel"] = status
    return TimelineHeader.from_dict({"camera_angle": "LS", "duration_seconds": 30.0,
                                     "analyses_run": {"video": True, "audio": False},
                                     "coverage": coverage, "visibility": visibility}, regions=REGIONS)


PLACED = ev("first_paddle_firmly_on_the_chest", 10, "placed")   # the CVAT tag for first_paddle_placed


def gel(t, event_id=None, **kwargs):
    return ev("Gel applied", t, event_id or f"gel@{t}", **kwargs)


def zone_gel(zone, t):
    return ev(f"{zone}_gel_applied", t, f"{zone}_gel@{t}", derived_gel_application=True)


STERNAL_TAKEN = ev("second_paddle_taken", 11, "sternal_taken")   # after the first placement: the order is certain


def run(events, head=None, cfg=R1, apical_first=True):
    """apical_first adds the sternal take at 11 s (after the apical placement at 10 s), so the sternal
    paddle can't have been placed before it (D-118); tests about that uncertainty pass False."""
    if apical_first and not any(e.event_name == "second_paddle_taken" for e in events):
        events = [*events, STERNAL_TAKEN]
    return assess(events, cfg, header=head if head is not None else header(), registry=discover())


def r1(events, head=None, cfg=R1, apical_first=True):
    return run(events, head, cfg, apical_first).outcome("R1")


class TagCountProxy(unittest.TestCase):
    """D-113: before the 9d gate, separate gel tags against the zones' visibility in the gel phase (A-026)."""

    def test_both_zones_visible_two_applications_pass_with_timing_not_checked(self):
        result = run([gel(3), gel(6), PLACED])
        outcome = result.outcome("R1")
        self.assertEqual((outcome.kind, outcome.evidence, outcome.flags),
                         ("pass_direct", ("gel@3", "gel@6"), ("timing_not_checked",)))
        self.assertIn("tag-count proxy", outcome.reason)
        self.assertEqual(result.overall.result, "incomplete")       # the period is unset (D-062)

    def test_both_zones_visible_one_application_is_applied_once(self):
        outcome = r1([gel(3), PLACED])
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "applied_once"))

    def test_tags_closer_than_the_minimum_gap_are_one_application(self):
        self.assertEqual(r1([gel(3), gel(3 + GAP - 0.1), PLACED]).failure_code, "applied_once")
        self.assertEqual(r1([gel(3), gel(3 + GAP + 0.05), PLACED]).kind, "pass_direct")

    def test_both_zones_visible_no_application_is_missing(self):
        self.assertEqual(r1([PLACED]).failure_code, "missing")

    def test_one_zone_visible(self):
        one = header(sternal=None)
        self.assertEqual(r1([PLACED], one).failure_code, "missing")
        self.assertEqual(r1([gel(3), PLACED], one).kind, "unable_to_verify")
        self.assertEqual(r1([gel(3), gel(6), PLACED], one).kind, "unable_to_verify")   # both may be on one zone

    def test_no_zone_visible_is_unable_to_verify(self):
        for head in (header(apical=None, sternal=None), header(apical=(), sternal=())):
            with self.subTest(head=head.coverage):
                self.assertEqual(r1([gel(3), gel(6), PLACED], head).kind, "unable_to_verify")
                self.assertEqual(r1([PLACED], head).kind, "unable_to_verify")

    def test_zone_visible_only_for_part_of_the_gel_phase_does_not_count(self):
        outcome = r1([PLACED], header(sternal=((5.0, 30.0),)))        # gel phase 0-10 s
        self.assertEqual(outcome.failure_code, "missing")              # the apical zone alone was visible
        self.assertIn("a zone was visible", outcome.reason)

    def test_gel_only_after_the_placement_is_after_placement(self):
        outcome = r1([PLACED, gel(12, "late")])
        self.assertEqual((outcome.kind, outcome.failure_code, outcome.evidence), ("fail", "after_placement",
                                                                                ("late", "placed")))

    def test_after_placement_needs_a_placement_time(self):
        outcome = r1([ev("first_paddle_taken", 8), gel(12)])          # phase ends at first paddle taken
        self.assertEqual(outcome.failure_code, "missing")

    def test_gel_before_and_after_the_placement_counts_the_applications_before(self):
        self.assertEqual(r1([gel(3), PLACED, gel(12)]).failure_code, "applied_once")

    def test_without_a_placement_the_phase_ends_at_first_paddle_taken(self):
        outcome = r1([gel(3), ev("first_paddle_taken", 8), gel(9)])
        self.assertEqual(outcome.failure_code, "applied_once")
        self.assertIn("before the first paddle was taken (8 s)", outcome.reason)

    def test_low_confidence_gel_is_never_a_fail(self):
        outcome = r1([gel(3), ev("gel_applied", 6, "weak", confidence=0.2, source="video"), PLACED])
        self.assertEqual((outcome.kind, outcome.evidence[0]), ("unable_to_verify", "weak"))

    def test_more_than_two_applications_pass(self):
        """OQ-021: repeats stay the supervisor's question."""
        self.assertEqual(r1([gel(2), gel(4), gel(6), PLACED]).kind, "pass_direct")

    def test_pending_in_the_catalogue(self):
        cfg = RuleEngineConfig.from_dict(CATALOGUE)
        self.assertEqual(run([gel(3), gel(6), PLACED], cfg=cfg).outcome("R1").kind, "pending")


class TimePeriod(unittest.TestCase):
    def test_an_approved_period_exceeded_is_outside_time_period(self):
        cfg = config({"value": 2, **APPROVAL})
        outcome = r1([gel(3), gel(6), PLACED], cfg=cfg)
        self.assertEqual((outcome.kind, outcome.failure_code, outcome.timing_checked), ("fail", "outside_time_period", True))
        within = r1([gel(3), gel(4.5), PLACED], cfg=cfg)
        self.assertEqual((within.kind, within.flags, within.timing_checked), ("pass_direct", (), True))

    def test_approved_no_limit_passes_fully(self):
        outcome = r1([gel(3), gel(6), PLACED], cfg=config({"value": None, "no_limit": True, **APPROVAL}))
        self.assertEqual((outcome.kind, outcome.flags, outcome.timing_checked), ("pass_direct", (), True))

    def test_the_period_applies_to_derived_applications_too(self):
        cfg = config({"value": 2, **APPROVAL})
        events = [zone_gel("sternal", 2), zone_gel("apical", 7), PLACED]
        head = header(gel={"apical": "covered", "sternal": "covered"})
        self.assertEqual(r1(events, head, cfg).failure_code, "outside_time_period")


class PerZone(unittest.TestCase):
    """D-110, D-113: past the 9d gate, each zone's gel status."""

    BOTH_SEEN = {"apical": "covered", "sternal": "covered"}

    def test_both_zones_gelled_pass_in_either_order(self):
        outcome = r1([zone_gel("sternal", 2), zone_gel("apical", 5), PLACED], header(gel=self.BOTH_SEEN))
        self.assertEqual((outcome.kind, outcome.evidence), ("pass_direct", ("apical_gel@5", "sternal_gel@2")))
        self.assertIn("derived_gel_application", outcome.flags)

    def test_one_gelled_and_the_other_not_gelled_is_applied_once(self):
        outcome = r1([zone_gel("apical", 5), gel(5), gel(7), PLACED], header(gel=self.BOTH_SEEN))
        self.assertEqual(outcome.failure_code, "applied_once")      # the per-zone status wins over the tag count
        self.assertIn("sternal zone", outcome.reason)

    def test_neither_gelled_is_missing(self):
        self.assertEqual(r1([PLACED], header(gel=self.BOTH_SEEN)).failure_code, "missing")

    def test_a_zone_unknown_is_unable_to_verify(self):
        outcome = r1([zone_gel("apical", 5), PLACED], header(gel={"apical": "covered", "sternal": "unknown"}))
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("sternal zone unknown", outcome.reason)

    def test_gel_only_after_the_placement_is_after_placement(self):
        self.assertEqual(r1([PLACED, gel(12)], header(gel=self.BOTH_SEEN)).failure_code, "after_placement")


def record(tags, gel_events=(), statuses=("gelled", "not_gelled")):
    return {"schema_version": 1, "kind": RECORD_KIND, "canonical_task_id": "P02_LS", "participant_id": "P02",
            "camera_view": "LS", "annotation_source": "x", "archive": "a.zip", "task_path": ".", "media_name": "x.mp4",
            "fps": FPS, "width": 1920, "height": 1080, "start_frame": 0, "stop_frame": 749, "duration_seconds": 30.0,
            "tags": [{"id": f"P02_LS_tag_{i:03d}", "label": label, "frame": frame, "timestamp_seconds": frame / FPS}
                     for i, (label, frame) in enumerate(tags, start=1)],
            "zone_tracks": {"apical_placement_zone": 1, "sternal_placement_zone": 1},
            "zone_visibility": [{"label": z, "start_frame": 0, "end_frame": 749, "start_seconds": 0.0,
                                 "end_seconds": 29.96} for z in ("apical_placement_zone", "sternal_placement_zone")],
            "screen_tracks": 0, "screen_visibility": [], "derived_events": [],
            "derived_gel_events": [{"id": f"P02_LS_gel_{i:03d}", "event_name": name, "frame": frame,
                                    "timestamp_seconds": frame / FPS, "evidence_type": "direct",
                                    "flags": ["derived_gel_application"], "method": "hand_near_zone_v1",
                                    "metadata": {"zone_label": zone, "settings_sha256": EXPORT.gel.digest()}}
                                   for i, (name, zone, frame) in enumerate(gel_events, start=1)],
            "gel": {"phase": {"end_frame": 250, "end_seconds": 10.0, "ended_by": "first_paddle_firmly_on_the_chest"},
                    "bottle": {"start_frame": 25, "end_frame": 200, "start_seconds": 1.0, "end_seconds": 8.0,
                               "hidden_frames": 0},
                    "zones": [{"zone_label": z, "event": f"{n}_gel_applied", "region": f"{n}_gel", "status": s,
                               "reason": "", "applications": int(s == "gelled")}
                              for z, n, s in zip(("apical_placement_zone", "sternal_placement_zone"),
                                                 ("apical", "sternal"), statuses)]}}


APPROVED = replace(EXPORT, gel=replace(EXPORT.gel, review=GelReview("Arnikan", "2026-10-17", "a" * 64, EXPORT.gel.digest())))
MANIFEST = {"export_id": "a" * 64, "gel_settings_sha256": EXPORT.gel.digest()}
TAGS = [("Gel applied", 75), ("Gel applied", 125), ("first_paddle_firmly_on_the_chest", 250),
        ("second_paddle_taken", 275)]   # two tags: the proxy passes; the sternal take after the placement


class Gate(unittest.TestCase):
    """D-112: derived gel applications and gel statuses reach R1 only for the reviewed export and settings."""

    def test_approved_gate_uses_each_zones_status(self):
        adapted = adapt_record(record(TAGS, [("apical_gel_applied", "apical_placement_zone", 75)]), R1, APPROVED, MANIFEST)
        self.assertEqual((adapted.gel_included, adapted.gel_gate), (1, "approved"))
        self.assertEqual((adapted.header.coverage["region:apical_gel"], adapted.header.coverage["region:sternal_gel"]),
                         ("covered", "covered"))
        self.assertEqual(r1(adapted.events, adapted.header).failure_code, "applied_once")

    def test_unknown_gel_status_is_unknown_coverage(self):
        adapted = adapt_record(record(TAGS, [("apical_gel_applied", "apical_placement_zone", 75)],
                                      ("gelled", "unknown")), R1, APPROVED, MANIFEST)
        self.assertEqual(adapted.header.coverage["region:sternal_gel"], "unknown")
        self.assertEqual(r1(adapted.events, adapted.header).kind, "unable_to_verify")

    def test_gate_not_approved_uses_the_tag_count_proxy(self):
        adapted = adapt_record(record(TAGS, [("apical_gel_applied", "apical_placement_zone", 75)]), R1, EXPORT, MANIFEST)
        self.assertEqual((adapted.gel_withheld, adapted.gel_gate[:12]), (1, "not approved"))
        self.assertNotIn("region:apical_gel", adapted.header.coverage)
        outcome = r1(adapted.events, adapted.header)
        self.assertEqual(outcome.kind, "pass_direct")                    # two separate tags, both zones visible
        self.assertIn("tag-count proxy", outcome.reason)

    def test_an_export_without_gel_is_the_proxy(self):
        data = record(TAGS)
        del data["gel"], data["derived_gel_events"]
        adapted = adapt_record(data, R1, APPROVED, MANIFEST)
        self.assertIn("exporter version 3", adapted.gel_gate)
        self.assertIn("tag-count proxy", r1(adapted.events, adapted.header).reason)


if __name__ == "__main__":
    unittest.main()
