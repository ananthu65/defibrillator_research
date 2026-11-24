"""D-128 for the video rules and the remaining timing Fails; D-129 for R3 and R4 against the shock inference.

A wrong-place (or wrong-time) Fail also claims the step was not done in the right place, so it needs clear
evidence over the window where a correctly placed occurrence would have had to be; otherwise Unable to Verify,
flagged correct_occurrence_unseen. D-129: with the shock confirmed on the screen (an inference source, D-102),
R3 placed_after_shock and R4 before_placement are Unable to Verify, flagged contradictory.

The full configs/rules.yaml with the rule under test approved (testing practice, methods.md); synthetic
timelines only.
"""
import copy
import unittest

import yaml

from pipeline.config import ROOT
from rules.config import RuleEngineConfig, load_rules_config
from rules.coverage import TimelineHeader
from rules.engine import assess
from rules.registry import discover
from schemas.event import Event

CATALOGUE = yaml.safe_load((ROOT / "configs/rules.yaml").read_text(encoding="utf-8"))
REGIONS = tuple(load_rules_config().engine.regions)
APPROVAL = {"approved_by": "Supervisor", "approved_on": "2026-11-24", "source": "test"}
ALL = ((0.0, 30.0),)
UNSEEN = "correct_occurrence_unseen"


def config(*approve, limits=None, parameters=None):
    data = copy.deepcopy(CATALOGUE)
    for entry in data["rules"]:
        if entry["id"] in approve:
            entry["status"] = "approved"
        if parameters and entry["id"] in parameters:
            entry["parameters"] = parameters[entry["id"]]
    data["timing_limits"].update(limits or {})
    return RuleEngineConfig.from_dict(data)


def tag(label, t, event_id=None, **metadata):
    return Event(label, t, t, "annotation", 1.0, event_id=event_id or f"{label}@{t:g}", camera_angle="LS",
                 metadata=metadata)


def said(name, start, end, event_id=None):
    return Event(name, start, end, "audio", 0.9, event_id=event_id or f"{name}@{start:g}",
                 metadata={"text": "x", "confidence_kind": "asr_proxy"})


def header(duration=30.0, gel=None, audio=None, **regions):
    """Visibility per region (seconds); gel = per-zone gel statuses past the 9d gate; audio = clear intervals."""
    visibility = {f"region:{name}": [list(s) for s in spans] for name, spans in regions.items()}
    coverage = {f"region:{zone}_gel": status for zone, status in (gel or {}).items()}
    if audio is not None:
        visibility["region:audio"] = [list(s) for s in audio]
    return TimelineHeader.from_dict({"camera_angle": "LS", "duration_seconds": duration,
                                     "analyses_run": {"video": True, "audio": audio is not None},
                                     "coverage": coverage, "visibility": visibility}, regions=REGIONS)


def outcome(rule_id, events, head, cfg):
    return assess(events, cfg, header=head, registry=discover()).outcome(rule_id)


class Check(unittest.TestCase):
    def fails(self, result, code):
        self.assertEqual((result.kind, result.failure_code), ("fail", code))
        self.assertIn("D-128", result.reason)

    def unseen(self, result):
        self.assertEqual(result.kind, "unable_to_verify")
        self.assertIn(UNSEEN, result.flags)
        self.assertIn("unseen_window_start", result.timestamps)


class R1Gel(Check):
    CFG = config("R1")
    EVENTS = [tag("first_paddle_firmly_on_the_chest", 10, "placed"), tag("second_paddle_taken", 11),
              tag("Gel applied", 12, "late")]

    def test_after_placement_needs_both_zones_in_view_before_the_placement(self):
        self.fails(outcome("R1", self.EVENTS, header(apical_zone=ALL, sternal_zone=ALL), self.CFG), "after_placement")
        self.unseen(outcome("R1", self.EVENTS, header(apical_zone=((5.0, 30.0),), sternal_zone=ALL), self.CFG))

    def test_outside_time_period_needs_the_zones_in_view_for_the_period(self):
        cfg = config("R1", limits={"gel_application_period_seconds": {"value": 2, **APPROVAL}})
        events = [tag("sternal_gel_applied", 2, derived_gel_application=True),
                  tag("apical_gel_applied", 7, derived_gel_application=True),
                  tag("first_paddle_firmly_on_the_chest", 10), tag("second_paddle_taken", 11)]
        gel = {"apical": "covered", "sternal": "covered"}
        result = outcome("R1", events, header(gel=gel, apical_zone=ALL, sternal_zone=ALL), cfg)
        self.fails(result, "outside_time_period")
        self.assertTrue(result.timing_checked)
        self.unseen(outcome("R1", events, header(gel=gel, apical_zone=((5.0, 30.0),), sternal_zone=ALL), cfg))


class R2Order(Check):
    CFG = config("R2")
    EVENTS = [tag("first_paddle_taken", 5), tag("second_paddle_taken", 7), tag("first_paddle_firmly_on_the_chest", 9)]

    def test_the_first_paddles_zone_in_view_from_its_take_to_the_other_take(self):
        self.fails(outcome("R2", self.EVENTS, header(apical_zone=ALL, sternal_zone=ALL), self.CFG),
                   "taken_before_first_placed")
        self.unseen(outcome("R2", self.EVENTS, header(apical_zone=((6.0, 30.0),), sternal_zone=ALL), self.CFG))


class R3FirmPlacement(Check):
    EVENTS = [tag("first_paddle_taken", 5), tag("shock_delivered_on_screen", 15, "shock"),
              tag("paddles_firmly_on_chest", 17, "firm")]

    def test_with_the_shock_as_an_inference_source_it_is_contradictory(self):
        """D-129: the rules.yaml setting (inference_sources: [shock_delivered_on_screen])."""
        result = outcome("R3", self.EVENTS, header(apical_zone=ALL, sternal_zone=ALL), config("R3"))
        self.assertEqual((result.kind, result.flags), ("unable_to_verify", ("contradictory",)))

    def test_without_the_shock_inference_both_zones_in_view_from_the_first_take_to_the_shock(self):
        cfg = config("R3", parameters={"R3": {"inference_sources": []}})
        self.fails(outcome("R3", self.EVENTS, header(apical_zone=ALL, sternal_zone=ALL), cfg), "placed_after_shock")
        self.unseen(outcome("R3", self.EVENTS, header(apical_zone=ALL, sternal_zone=((10.0, 30.0),)), cfg))


class R4Press(Check):
    PRESS = tag("both_paddle_buttons_pressed", 8, "press")
    PLACED = tag("paddles_firmly_on_chest", 10, "placed")
    SHOCK = tag("shock_delivered_on_screen", 15, "shock")

    def test_with_the_shock_on_screen_it_is_contradictory(self):
        result = outcome("R4", [self.PRESS, self.PLACED, self.SHOCK], header(apical_paddle=ALL, sternal_paddle=ALL),
                         config("R4"))
        self.assertEqual((result.kind, result.flags, result.evidence),
                         ("unable_to_verify", ("contradictory",), ("press", "shock")))

    def test_without_a_shock_both_paddles_in_view_from_the_placement_to_the_end(self):
        cfg = config("R4")
        self.fails(outcome("R4", [self.PRESS, self.PLACED], header(apical_paddle=ALL, sternal_paddle=ALL), cfg),
                   "before_placement")
        self.unseen(outcome("R4", [self.PRESS, self.PLACED],
                            header(apical_paddle=ALL, sternal_paddle=((0.0, 20.0),)), cfg))

    def test_without_the_shock_inference_the_window_ends_at_the_shock(self):
        cfg = config("R4", parameters={"R4": {"inference_sources": []}})
        events = [self.PRESS, self.PLACED, self.SHOCK]
        self.fails(outcome("R4", events, header(apical_paddle=ALL, sternal_paddle=((0.0, 16.0),)), cfg),
                   "before_placement")
        self.unseen(outcome("R4", events, header(apical_paddle=ALL, sternal_paddle=((0.0, 12.0),)), cfg))


class R6Removal(Check):
    SHOCK = tag("shock_delivered_on_screen", 15, "shock")

    def test_a_derived_exit_needs_the_zone_in_view_from_the_exit_to_the_shock(self):
        cfg = config("R6")
        events = [tag("first_paddle_firmly_on_the_chest", 7), self.SHOCK,
                  Event("apical_paddle_placed", 7, 7, "video", 1.0, event_id="apical", camera_angle="LS",
                        metadata={"derived_placement": True, "end_seconds": 12.0, "ended_by_exit": True}),
                  Event("sternal_paddle_placed", 8, 8, "video", 1.0, event_id="sternal", camera_angle="LS",
                        metadata={"derived_placement": True, "end_seconds": 29.9, "ended_by_exit": False}),
                  tag("paddles_removed_after_shock", 20)]
        self.fails(outcome("R6", events, header(apical_zone=ALL, sternal_zone=ALL), cfg), "removed_before_shock")
        self.unseen(outcome("R6", events, header(apical_zone=((0.0, 13.0),), sternal_zone=ALL), cfg))

    def test_the_removal_tag_case_is_unchanged(self):
        """Nothing absent is claimed: the removal before the shock is seen directly."""
        events = [tag("paddles_firmly_on_chest", 10), self.SHOCK, tag("paddles_removed_after_shock", 12)]
        result = outcome("R6", events, header(), config("R6"))
        self.assertEqual((result.kind, result.failure_code), ("fail", "removed_before_shock"))

    def test_too_late_needs_the_zones_in_view_for_the_limit(self):
        cfg = config("R6", limits={"shock_to_removal_seconds": {"value": 3, **APPROVAL}})
        events = [tag("paddles_firmly_on_chest", 10), self.SHOCK, tag("paddles_removed_after_shock", 20)]
        result = outcome("R6", events, header(apical_zone=ALL, sternal_zone=ALL), cfg)
        self.fails(result, "too_late")
        self.assertTrue(result.timing_checked)
        self.unseen(outcome("R6", events, header(apical_zone=ALL, sternal_zone=((0.0, 16.0),)), cfg))


class R8Order(Check):
    EVENTS = [tag("first_paddle_taken", 5), tag("second_paddle_taken", 10), tag("paddles_firmly_on_chest", 14),
              tag("apical_paddle_placed", 12), tag("sternal_paddle_placed", 7)]

    def test_the_apical_zone_in_view_from_the_placement_phase_to_the_sternal_placement(self):
        self.fails(outcome("R8", self.EVENTS, header(apical_zone=ALL, sternal_zone=ALL), config("R8")), "wrong_order")
        self.unseen(outcome("R8", self.EVENTS, header(apical_zone=((6.0, 30.0),), sternal_zone=ALL), config("R8")))


class AudioTiming(Check):
    """A8 pre_shock_pause and R7/A6 too_late: an unheard command inside the window would change the time."""

    def test_a8_needs_clear_audio_over_the_pause(self):
        events = [said("stop_compressions_command", 10, 11, "stop"), tag("shock_delivered_on_screen", 14, "shock"),
                  said("start_compressions_command", 17, 18, "start")]
        for end_event, unclear in (("start", ((0.0, 15.0),)), ("shock", ((0.0, 12.0),))):
            cfg = config("A8", parameters={"A8": {"end_event": end_event}})
            with self.subTest(end_event=end_event):
                if end_event == "start":   # 6 to 8 s
                    result = outcome("A8", events, header(audio=((0.0, 30.0),)), cfg)
                    self.assertEqual((result.kind, result.failure_code), ("fail", "pre_shock_pause"))
                self.unseen(outcome("A8", [said("stop_compressions_command", 5, 6, "stop"), *events[1:]],
                                    header(audio=unclear), cfg))

    def test_r7_too_late_needs_clear_audio_from_the_shock_to_the_restart(self):
        cfg = config("R7", "A6", limits={"shock_to_compressions_seconds": {"value": 5, **APPROVAL}})
        events = [tag("shock_delivered_on_screen", 15, "shock"), said("start_compressions_command", 21, 22, "start")]
        result = outcome("R7", events, header(audio=((0.0, 30.0),)), cfg)
        self.assertEqual((result.kind, result.failure_code), ("fail", "too_late"))
        self.unseen(outcome("R7", events, header(audio=((0.0, 18.0),)), cfg))
        self.unseen(outcome("A6", events, header(audio=((0.0, 18.0),)), cfg))


if __name__ == "__main__":
    unittest.main()
