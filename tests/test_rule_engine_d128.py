"""D-128: a wrong-place (or wrong-time) Fail needs clear evidence over the window of the correct occurrence.

A wrong-order Fail claims the command was heard in a wrong place AND was not said in the right place. The
second claim is an absence, so it needs clear audio (D-122) over the window where a correctly placed one would
have had to be; otherwise Unable to Verify. One test per audio rule: the wrong-place command x that window clear
or unclear. The full configs/rules.yaml with the audio rules approved (testing practice, methods.md); synthetic
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
AUDIO_RULES = ("A1", "A2", "A3", "A4", "A5", "A7", "R7", "A6")


def config():
    data = copy.deepcopy(CATALOGUE)
    for entry in data["rules"]:
        if entry["id"] in AUDIO_RULES:
            entry["status"] = "approved"
    return RuleEngineConfig.from_dict(data)


CONFIG = config()


def screen(t=30):
    return Event("shock_delivered_on_screen", t, t, "annotation", 1.0, event_id="shock")


def said(name, start, event_id=None):
    return Event(name, start, start + 1.0, "audio", 0.9, event_id=event_id or f"{name}@{start:g}",
                 metadata={"text": "x", "confidence_kind": "asr_proxy"})


def header(*clear):
    return TimelineHeader.from_dict({"duration_seconds": 60.0, "analyses_run": {"video": True, "audio": True},
                                     "visibility": {"region:audio": [list(c) for c in clear]}}, regions=REGIONS)


def outcome(rule_id, events, *clear):
    return assess(events, CONFIG, header=header(*clear), registry=discover()).outcome(rule_id)


class AfterTheShock(unittest.TestCase):
    """A1, A3, A5 (`after_shock`) and A2 (`wrong_stage`): a correct command would have been before the shock, so
    the audio must be clear from the start of the recording to the shock (30 s)."""

    CASES = {"A1": ("oxygen_away_command", "after_shock"), "A3": ("stand_clear_command", "after_shock"),
             "A5": ("shock_command", "after_shock"), "A2": ("continue_compressions_command", "wrong_stage")}

    def test_clear_before_the_shock_fails_and_unclear_is_unable(self):
        for rule_id, (name, code) in self.CASES.items():
            events = [screen(30), said(name, 40)]
            with self.subTest(rule_id, window="clear"):
                result = outcome(rule_id, events, (0.0, 60.0))
                self.assertEqual((result.kind, result.failure_code), ("fail", code))
                self.assertIn("D-128", result.reason)
            for clear in ((10.0, 60.0), (30.0, 60.0)):   # unclear for part of, or all of, the window
                with self.subTest(rule_id, clear=clear):
                    result = outcome(rule_id, events, clear)
                    self.assertEqual((result.kind, result.failure_code), ("unable_to_verify", None))
                    self.assertIn("may have been said and not heard", result.reason)

    def test_unclear_audio_after_the_shock_does_not_matter(self):
        self.assertEqual(outcome("A1", [screen(30), said("oxygen_away_command", 40)], (0.0, 30.0)).failure_code,
                         "after_shock")


class StopCompressions(unittest.TestCase):
    def test_after_shock_needs_clear_audio_from_the_first_continue_to_the_shock(self):
        events = [said("continue_compressions_command", 10), screen(30), said("stop_compressions_command", 40)]
        self.assertEqual(outcome("A4", events, (0.0, 60.0)).failure_code, "after_shock")
        self.assertEqual(outcome("A4", events, (10.0, 30.0)).failure_code, "after_shock")   # the window only
        self.assertEqual(outcome("A4", events, (20.0, 60.0)).kind, "unable_to_verify")

    def test_after_shock_without_continue_uses_the_recording_start(self):
        events = [screen(30), said("stop_compressions_command", 40)]
        self.assertEqual(outcome("A4", events, (0.0, 60.0)).failure_code, "after_shock")
        self.assertEqual(outcome("A4", events, (10.0, 60.0)).kind, "unable_to_verify")

    def test_stop_before_continue_needs_clear_audio_from_continue_to_the_shock(self):
        events = [said("stop_compressions_command", 5), said("continue_compressions_command", 10), screen(30)]
        self.assertEqual(outcome("A4", events, (0.0, 60.0)).failure_code, "wrong_order")
        self.assertEqual(outcome("A4", events, (10.0, 30.0)).failure_code, "wrong_order")
        result = outcome("A4", events, (0.0, 20.0))
        self.assertEqual((result.kind, result.failure_code), ("unable_to_verify", None))

    def test_stop_before_continue_without_a_shock_time_uses_the_recording_end(self):
        events = [said("stop_compressions_command", 5), said("continue_compressions_command", 10)]
        self.assertEqual(outcome("A4", events, (0.0, 60.0)).failure_code, "wrong_order")
        self.assertEqual(outcome("A4", events, (0.0, 40.0)).kind, "unable_to_verify")


class Restart(unittest.TestCase):
    """R7/A6 `before_shock`: the first case of D-128 (the Increment 24 review fix)."""

    def test_before_shock_needs_clear_audio_from_the_shock_to_the_end(self):
        events = [said("start_compressions_command", 10), screen(30)]
        self.assertEqual(outcome("R7", events, (0.0, 60.0)).failure_code, "before_shock")
        self.assertEqual(outcome("A6", events, (30.0, 60.0)).failure_code, "before_shock")
        self.assertEqual(outcome("R7", events, (0.0, 45.0)).kind, "unable_to_verify")


class CommandOrder(unittest.TestCase):
    """A7: for each command reported, the window runs from its latest observed required predecessor to its
    earliest observed required successor (the recording start or end where none)."""

    # stand clear 2 s and oxygen away 4 s swapped; continue 6 s, stop 12 s, the shock 30 s, start 34 s
    SWAPPED = [said("stand_clear_command", 2), said("oxygen_away_command", 4),
               said("continue_compressions_command", 6), said("stop_compressions_command", 12), screen(30),
               said("start_compressions_command", 34)]

    def test_the_windows_of_the_reported_commands(self):
        # A1: from the start to stand clear's end (0-3 s); A3: from oxygen away (4 s) to continue's end (7 s)
        self.assertEqual(outcome("A7", self.SWAPPED, (0.0, 8.0)).failure_code, "wrong_order")
        self.assertEqual(outcome("A7", self.SWAPPED, (0.0, 20.0)).failure_code, "wrong_order")   # later audio unclear

    def test_an_unclear_window_is_unable_to_verify(self):
        for clear in ((1.0, 60.0), (0.0, 5.0)):   # A1's window, then A3's, partly unclear
            with self.subTest(clear=clear):
                result = outcome("A7", self.SWAPPED, clear)
                self.assertEqual((result.kind, result.flags), ("unable_to_verify", ("order_partially_checked",)))
                self.assertIn("D-128", result.reason)

    def test_a_misplaced_command_with_no_successor_runs_to_the_recording_end(self):
        """Start said first (start is the last step): its window runs from stop (12 s) to the end (60 s)."""
        events = [said("start_compressions_command", 0.5), said("oxygen_away_command", 2),
                  said("stand_clear_command", 4), said("continue_compressions_command", 6),
                  said("stop_compressions_command", 12), screen(30)]
        self.assertEqual(outcome("A7", events, (0.0, 60.0)).failure_code, "wrong_order")
        self.assertEqual(outcome("A7", events, (0.0, 50.0)).kind, "unable_to_verify")


if __name__ == "__main__":
    unittest.main()
