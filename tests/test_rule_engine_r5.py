"""Increment 13: R5, shock confirmed on screen (P-033; D-093, D-094, D-101). Since Increment 26 R5 judges only the
shock indication: its preceding_steps is retired (D-123)."""
import copy
import unittest

import yaml

from pipeline.config import ROOT
from rules.config import RuleEngineConfig
from rules.coverage import TimelineHeader
from rules.engine import assess
from rules.registry import discover
from schemas.event import Event

CATALOGUE = yaml.safe_load((ROOT / "configs/rules.yaml").read_text(encoding="utf-8"))


def config(*also, parameters=None):
    rules = [{"id": "R5", "status": "approved", "parameters": parameters or {}}]
    rules += [{"id": r, "status": "approved"} for r in also]
    return RuleEngineConfig.from_dict({**copy.deepcopy(CATALOGUE), "rules": rules})


UNSET = config()
REGIONS = tuple(UNSET.engine.regions)


def ev(label, t, event_id=None, confidence=1.0, source="annotation"):
    return Event(label, t, t, source, confidence, event_id=event_id or f"{label}@{t}", camera_angle="LS")


def header(screen=((0.0, 30.0),), coverage="covered"):
    """Screen visibility in seconds; None = no screen track (unknown)."""
    data = {"camera_angle": "LS", "duration_seconds": 30.0, "analyses_run": {"video": True, "audio": False},
            "coverage": {"region:screen": "unknown" if screen is None else coverage}}
    if screen is not None:
        data["visibility"] = {"region:screen": [list(s) for s in screen]}
    return TimelineHeader.from_dict(data, regions=REGIONS)


WINDOW_TAGS = [ev("paddles_firmly_on_chest", 10, "placed"), ev("paddles_removed_after_shock", 20, "removed")]


def run(events, head=None, cfg=UNSET):
    return assess(events, cfg, header=head, registry=discover())


def r5(events, head=None, cfg=UNSET):
    return run(events, head, cfg).outcome("R5")


class ShockSeen(unittest.TestCase):
    def test_a_shock_on_screen_is_a_clean_pass(self):
        """D-123: no order_not_checked any more; the relations before the shock are owned by their own rules."""
        result = run([*WINDOW_TAGS, ev("shock_delivered_on_screen", 15, "shock")], header())
        outcome = result.outcome("R5")
        self.assertEqual((outcome.kind, outcome.evidence, outcome.flags), ("pass_direct", ("shock",), ()))
        self.assertEqual(result.overall.result, "pass")

    def test_r5_never_judges_the_order_of_the_steps_before_the_shock(self):
        """The buttons pressed after the shock are R4's relation (R4 -> R5), not R5's."""
        events = [*WINDOW_TAGS, ev("both_paddle_buttons_pressed", 16, "buttons"), ev("shock_delivered_on_screen", 15)]
        self.assertEqual(r5(events, header()).kind, "pass_direct")

    def test_a_leftover_preceding_steps_is_an_engine_error(self):
        for value in (None, ["both_paddle_buttons_pressed"]):
            with self.subTest(value=value):
                outcome = r5([ev("shock_delivered_on_screen", 15)], header(),
                             config(parameters={"preceding_steps": value}))
                self.assertEqual(outcome.kind, "engine_error")

    def test_multiple_shocks_is_unable_to_verify(self):
        outcome = r5([*WINDOW_TAGS, ev("shock_delivered_on_screen", 14, "s1"), ev("shock_delivered_on_screen", 16, "s2")],
                     header())
        self.assertEqual((outcome.kind, outcome.evidence), ("unable_to_verify", ("s1", "s2")))
        self.assertIn("multiple_shocks", outcome.flags)

    def test_pending_in_the_catalogue(self):
        self.assertEqual(run([ev("shock_delivered_on_screen", 15)], cfg=CATALOGUE).outcome("R5").kind, "pending")


class ShockMissing(unittest.TestCase):
    """D-101: the screen must be visible throughout paddles firmly on chest (10 s) -> paddles removed (20 s)."""

    def test_screen_visible_throughout_the_window_is_missing(self):
        outcome = r5(WINDOW_TAGS, header(screen=((5.0, 25.0),), coverage="unknown"))
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "missing"))
        self.assertIn("between paddles firmly on chest (10 s) and paddles removed (20 s)", outcome.reason)

    def test_screen_out_of_view_in_the_window_is_unable_to_verify(self):
        outcome = r5(WINDOW_TAGS, header(screen=((0.0, 8.0), (22.0, 30.0)), coverage="unknown"))
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("coverage not_covered", outcome.reason)

    def test_screen_in_view_for_part_of_the_window_is_unable_to_verify(self):
        outcome = r5(WINDOW_TAGS, header(screen=((0.0, 15.0),), coverage="unknown"))
        self.assertEqual(outcome.kind, "unable_to_verify")
        self.assertIn("coverage unknown", outcome.reason)

    def test_no_screen_track_is_unable_to_verify(self):
        self.assertEqual(r5(WINDOW_TAGS, header(screen=None)).kind, "unable_to_verify")

    def test_missing_window_tags_use_the_whole_recording(self):
        events = [ev("paddles_removed_after_shock", 20)]     # no paddles_firmly_on_chest
        throughout = r5(events, header(screen=((0.0, 30.0),), coverage="covered"))
        self.assertEqual((throughout.kind, throughout.failure_code), ("fail", "missing"))
        self.assertIn("in the recording", throughout.reason)
        partly = r5(events, header(screen=((5.0, 25.0),), coverage="unknown"))   # visible for part of it
        self.assertEqual(partly.kind, "unable_to_verify")

    def test_low_confidence_shock_is_never_a_fail(self):
        weak = ev("shock_delivered_on_screen", 15, "weak", confidence=0.2, source="video")
        outcome = r5([*WINDOW_TAGS, weak], header())
        self.assertEqual((outcome.kind, outcome.evidence), ("unable_to_verify", ("weak",)))


if __name__ == "__main__":
    unittest.main()
