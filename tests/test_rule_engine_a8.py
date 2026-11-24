"""Increment 25: A8, the pre-shock pause (P-044), with its end event as a config value (OQ-076).

The full configs/rules.yaml with A8 approved (testing practice, methods.md); the 5 s limit is the approved one.
Synthetic timelines only; command events carry their Whisper segment unless marked word-timed (D-125). The
shock time comes only from the screen (D-093).
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


def config(end_event="start", approve=("A8",)):
    data = copy.deepcopy(CATALOGUE)
    for entry in data["rules"]:
        if entry["id"] in approve:
            entry["status"] = "approved"
        if entry["id"] == "A8" and end_event is not None:
            entry["parameters"] = {"end_event": end_event}
    return RuleEngineConfig.from_dict(data)


START_END, SHOCK_END = config("start"), config("shock")


def screen(t, event_id="shock"):
    return Event("shock_delivered_on_screen", t, t, "annotation", 1.0, event_id=event_id)


def said(name, start, end=None, event_id=None, word=False, confidence=0.9):
    metadata = {"text": "x", "confidence_kind": "asr_proxy", **({"time_basis": "word"} if word else {})}
    return Event(name, start, end if end is not None else (start if word else start + 1.0), "audio", confidence,
                 event_id=event_id or name, metadata=metadata)


def stop(t, end=None, event_id="stop", **kw):
    return said("stop_compressions_command", t, end, event_id, **kw)


def start(t, end=None, event_id="start", **kw):
    return said("start_compressions_command", t, end, event_id, **kw)


def resume(t, end=None, event_id="resume"):
    return said("resume_compressions_command", t, end, event_id)


def header():
    return TimelineHeader.from_dict({"duration_seconds": 60.0, "analyses_run": {"video": True, "audio": True},
                                     "visibility": {"region:audio": [[0.0, 60.0]]}}, regions=REGIONS)


def run(events, cfg=START_END):
    return assess(events, cfg, header=header(), registry=discover())


def a8(events, cfg=START_END):
    return run(events, cfg).outcome("A8")


class Limit(unittest.TestCase):
    """5 s, approved. Word-timed commands are points; segment-timed ones are judged on bounds (D-125)."""

    def test_4_9_5_0_and_5_1_seconds(self):
        for pause, kind in ((4.9, "pass_direct"), (5.0, "pass_direct"), (5.1, "fail")):
            with self.subTest(pause=pause):
                result = a8([stop(10, word=True), screen(12), start(10 + pause, word=True)])
                self.assertEqual((result.kind, result.timing_checked), (kind, True))
                if kind == "fail":
                    self.assertEqual(result.failure_code, "pre_shock_pause")

    def test_segments_within_over_and_uncertain(self):
        within = a8([stop(10, 11), screen(12), start(13, 14)])          # 2 to 4 s
        over = a8([stop(10, 11), screen(14), start(17, 18)])            # 6 to 8 s
        uncertain = a8([stop(10, 11), screen(12), start(15, 16)])       # 4 to 6 s
        self.assertEqual((within.kind, within.timing_checked), ("pass_direct", True))
        self.assertEqual((over.kind, over.failure_code), ("fail", "pre_shock_pause"))
        self.assertEqual((uncertain.kind, uncertain.flags), ("unable_to_verify", ("timing_uncertain",)))
        self.assertEqual(uncertain.timestamps, {"shortest_seconds": 4.0, "longest_seconds": 6.0})


class EndEvent(unittest.TestCase):
    """OQ-076: the same lecturer-like timeline under each end event."""

    # stop -> shocking actions (paddles taken, placed, buttons, shock, removal) -> start
    LECTURER = [stop(10, 11),
                Event("first_paddle_taken", 11.5, 11.5, "annotation", 1.0, event_id="taken1"),
                Event("second_paddle_taken", 12, 12, "annotation", 1.0, event_id="taken2"),
                Event("paddles_firmly_on_chest", 13, 13, "annotation", 1.0, event_id="firm"),
                screen(14),
                Event("paddles_removed_after_shock", 15, 15, "annotation", 1.0, event_id="removal"),
                start(17, 18)]

    def test_lecturer_like_timeline_under_each_end_event(self):
        to_start, to_shock = a8(self.LECTURER, START_END), a8(self.LECTURER, SHOCK_END)
        self.assertEqual((to_start.kind, to_start.failure_code), ("fail", "pre_shock_pause"))   # 6 to 8 s
        self.assertEqual(to_start.evidence, ("stop", "start"))
        self.assertEqual((to_shock.kind, to_shock.timing_checked), ("pass_direct", True))     # 3 to 4 s
        self.assertEqual(to_shock.evidence, ("stop", "shock"))

    def test_start_is_the_default_and_in_rules_yaml(self):
        self.assertEqual(load_rules_config().rule("A8").parameters, {"end_event": "start"})
        self.assertEqual(a8(self.LECTURER, config(end_event=None)).failure_code, "pre_shock_pause")

    def test_an_unknown_end_event_is_refused_loudly(self):
        self.assertEqual(a8(self.LECTURER, config("removal")).kind, "engine_error")

    def test_with_end_event_shock_the_restart_is_not_needed(self):
        self.assertEqual(a8([stop(10, 11), screen(14)], SHOCK_END).kind, "pass_direct")


class MissingReferences(unittest.TestCase):
    """D-121: A8 never fails for a missing reference; it names what blocks it."""

    def test_no_shock_time_is_not_evaluable_because_of_r5_under_both_end_events(self):
        for cfg in (START_END, SHOCK_END):
            with self.subTest(cfg=cfg.rule("A8").parameters):
                result = a8([stop(10, 11), start(17, 18)], cfg)
                self.assertEqual((result.kind, result.blocked_by, result.evidence), ("not_evaluable", "R5", ("stop",)))
        removal = Event("paddles_removed_after_shock", 15, 15, "annotation", 1.0, event_id="removal")
        self.assertEqual(a8([stop(10, 11), removal, start(17, 18)], SHOCK_END).blocked_by, "R5")   # never the removal

    def test_no_stop_is_not_evaluable_because_of_a4(self):
        cases = {"not heard": [screen(14), start(17, 18)],
                 "only after the shock": [screen(14), stop(16, 17), start(18, 19)],
                 "resumed after it": [stop(5, 6), said("continue_compressions_command", 8, 9, "cont"), screen(14),
                                      start(17, 18)],
                 "low confidence": [stop(10, 11, confidence=0.2), screen(14), start(17, 18)]}
        for case, events in cases.items():
            with self.subTest(case):
                self.assertEqual(a8(events).blocked_by, "A4")
        self.assertIn("missing too (R7)", a8([screen(14)]).reason)

    def test_no_restart_is_not_evaluable_because_of_r7(self):
        cases = {"not heard": ([stop(10, 11), screen(14)], "no restart command heard"),
                 "start only before the shock": ([stop(10, 11), start(12, 12.5), screen(14)], "only before the shock"),
                 "unresolved resume": ([stop(10, 11), screen(14), resume(13.5, 14.5)], "likely cause")}
        for case, (events, why) in cases.items():
            with self.subTest(case):
                result = a8(events)
                self.assertEqual((result.kind, result.blocked_by, result.evidence), ("not_evaluable", "R7", ("stop",)))
                self.assertIn(why, result.reason)


class SharedRestart(unittest.TestCase):
    """A8 and R7/A6 always judge the same restart: the context's start anchor (D-025, D-125)."""

    CFG = config(approve=("A8", "R7", "A6"))

    def test_the_same_restart_as_r7(self):
        timelines = {"early start ineligible": [stop(8, 9), start(5, 6, "early"), screen(14), start(17, 18, "late")],
                     "a tie at the shock": [stop(10, 11), screen(14), start(13.5, 14.5, "tie"), start(17, 18, "late")],
                     "resolved resume": [stop(10, 11), screen(14), resume(16, 17)]}
        for case, events in timelines.items():
            with self.subTest(case):
                result = run(events, self.CFG)
                self.assertEqual(result.outcome("A8").evidence[1], result.outcome("R7").evidence[0])

    def test_the_stop_after_the_last_continue_starts_the_pause(self):
        events = [stop(2, 3, "first"), said("continue_compressions_command", 5, 6, "cont"), stop(9, 10, "second"),
                  screen(12), start(13, 14)]
        self.assertEqual(a8(events).evidence, ("second", "start"))

    def test_a_stop_and_continue_in_one_segment_still_starts_the_pause(self):
        events = [said("continue_compressions_command", 9, 10, "cont"), stop(9, 10), screen(12), start(13, 14)]
        self.assertEqual(a8(events).evidence, ("stop", "start"))


class Catalogue(unittest.TestCase):
    def test_pending_until_approved(self):
        result = assess(EndEvent.LECTURER, load_rules_config(), header=header(), registry=discover())
        self.assertEqual(result.outcome("A8").kind, "pending")


if __name__ == "__main__":
    unittest.main()
