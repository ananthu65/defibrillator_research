"""Increment 18: the shared context for the audio rules and the combined flow (D-120 to D-125).

Segment-timed audio comparisons, the cross-modal tolerance, time limits on bounds, the audio region
(D-122), the D-121 helper, the new flags and the command anchors. Synthetic timelines only.
"""
import copy
from dataclasses import replace
from types import SimpleNamespace
import unittest

import yaml

from pipeline.config import ROOT
from rules import checks
from rules.config import ClinicalValue, EngineSettings, load_rules_config
from rules.context import build_context
from rules.coverage import TimelineHeader
from rules.outcome import passed
from rules.policy import decide
from rules.prepare import prepare_timeline
from schemas.event import Event

CONFIG = load_rules_config()
REGIONS = tuple(CONFIG.engine.regions)
FIVE = ClinicalValue("pre_shock_pause_seconds", 5, approved_by="Supervisor", approved_on="2026-10-10")


def video(name, t, event_id=None):
    return Event(name, t, t, "annotation", 1.0, event_id=event_id or f"{name}@{t}")


def audio(name, start, end, event_id=None, **metadata):
    """A command event as detect_commands emits it: the Whisper segment's start and end (D-125)."""
    return Event(name, start, end, "audio", 0.9, event_id=event_id or f"{name}@{start}",
                 metadata={"text": "x", "confidence_kind": "asr_proxy", **metadata})


def ctx_for(events, header=None, config=CONFIG):
    head = TimelineHeader.from_dict(header, regions=REGIONS) if header is not None else None
    return build_context(prepare_timeline(events, config), config, head)


CTX = ctx_for([])


class Windows(unittest.TestCase):
    def test_cross_modal_pairs_use_the_cross_modal_tolerance(self):
        self.assertEqual(checks.window_between(CTX, video("R", 1), audio("c", 1, 1)), 1.0)
        self.assertEqual(checks.window_between(CTX, video("R", 1), video("S", 2)), 0.5)
        self.assertEqual(checks.window_between(CTX, audio("a", 1, 1), audio("b", 2, 2)), 0.5)

    def test_timing_noise_near_the_tolerance(self):
        """An audio command 0.9 s after a video step is a tie; 1.1 s after, it is certainly after (scenario 8)."""
        press = video("both_paddle_buttons_pressed", 10)
        near = audio("stand_clear_command", 10.9, 10.9, time_basis="word")
        far = audio("stand_clear_command", 11.1, 11.1, time_basis="word")
        self.assertEqual(checks.relation_between(CTX, near, press), checks.SIMULTANEOUS)
        self.assertEqual(checks.relation_between(CTX, far, press), checks.AFTER)
        self.assertEqual(checks.relation_between(CTX, press, far), checks.BEFORE)

    def test_point_events_match_relation(self):
        for a, b in ((1, 3), (3, 1), (2, 2.4)):
            with self.subTest(a=a, b=b):
                self.assertEqual(checks.relation_between(CTX, video("x", a), video("y", b)), checks.relation(a, b, 0.5))


class SegmentTimedAudio(unittest.TestCase):
    """D-125: an audio command lies somewhere in its Whisper segment."""

    def test_a_segment_is_an_interval_and_a_word_timed_event_a_point(self):
        self.assertEqual(checks.time_bounds(audio("c", 4, 7)), (4, 7))
        self.assertEqual(checks.time_bounds(audio("c", 4, 7, time_basis="word")), (4, 4))
        self.assertEqual(checks.time_bounds(video("x", 4)), (4, 4))
        self.assertTrue(checks.segment_timed(audio("c", 4, 7)))

    def test_an_order_is_broken_only_when_certainly_after(self):
        stop = audio("stop_compressions_command", 10, 14)
        self.assertEqual(checks.relation_between(CTX, stop, video("shock_delivered_on_screen", 14.5)),
                         checks.SIMULTANEOUS)   # the command may be at 14 s: a tie, never a Fail
        self.assertEqual(checks.relation_between(CTX, stop, video("shock_delivered_on_screen", 16)), checks.BEFORE)
        self.assertEqual(checks.relation_between(CTX, stop, video("shock_delivered_on_screen", 8.5)), checks.AFTER)

    def test_commands_in_one_segment_are_not_ordered(self):
        """Scenario 12: "stop compressions, all stand clear" in one segment."""
        stop = audio("stop_compressions_command", 10, 13, "stop")
        clear = audio("stand_clear_command", 10, 13, "clear")
        self.assertTrue(checks.same_segment(stop, clear))
        self.assertEqual(checks.relation_between(CTX, stop, clear), checks.SIMULTANEOUS)
        self.assertFalse(checks.same_segment(stop, audio("stand_clear_command", 13, 15)))


class LimitsOnBounds(unittest.TestCase):
    """Time limits on the shortest and longest possible durations (scenario 13: A8's 5 s)."""

    def judge(self, stop, start, limit=FIVE):
        return checks.timed_between("A8", audio("stop_compressions_command", *stop, "stop"),
                                    audio("start_compressions_command", *start, "start"), limit,
                                    code="pre_shock_pause", what="stop to start", evidence=("stop", "start"))

    def test_within_whatever_the_word_times(self):
        outcome = self.judge((10, 11), (14, 15))   # 3 to 5 s
        self.assertEqual((outcome.kind, outcome.timing_checked), ("pass_direct", True))
        self.assertEqual(outcome.timestamps, {"shortest_seconds": 3, "longest_seconds": 5})

    def test_beyond_whatever_the_word_times(self):
        outcome = self.judge((10, 11), (17, 18))   # 6 to 8 s
        self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "pre_shock_pause"))

    def test_straddling_the_limit_is_timing_uncertain(self):
        outcome = self.judge((10, 11), (15, 17))   # 4 to 7 s
        self.assertEqual((outcome.kind, outcome.flags), ("unable_to_verify", ("timing_uncertain",)))
        self.assertIn("timing uncertain: 4–7 s", outcome.reason)

    def test_no_approved_limit_is_timing_not_checked(self):
        outcome = self.judge((10, 11), (15, 17), ClinicalValue("x"))
        self.assertEqual((outcome.kind, outcome.flags), ("pass_direct", ("timing_not_checked",)))

    def test_point_events_are_an_ordinary_limit(self):
        check = checks.bounded_time_limit(4, 4, FIVE)
        self.assertEqual((check.checked, check.within, check.flags), (True, True, ()))


class AudioRegion(unittest.TestCase):
    """D-122: a missing command can Fail only within clear-audio intervals."""

    def missing(self, header, window=None):
        return ctx_for([video("shock_delivered_on_screen", 30)], header).missing("stop_compressions_command", window)

    def test_audio_analysed_without_clear_intervals_is_unknown(self):
        result = self.missing({"analyses_run": {"video": True, "audio": True}})
        self.assertEqual((result.outcome, result.coverage.status), ("unable_to_verify", "unknown"))

    def test_audio_not_analysed_is_not_covered(self):
        result = self.missing({"analyses_run": {"video": True, "audio": False}})
        self.assertEqual((result.outcome, result.coverage.status), ("unable_to_verify", "not_covered"))

    def test_within_a_clear_interval_a_missing_command_fails(self):
        head = {"analyses_run": {"audio": True, "video": True}, "duration_seconds": 60,
                "visibility": {"region:audio": [[0, 40]]}}
        self.assertEqual(self.missing(head, (10, 30)).outcome, "fail")
        self.assertEqual(self.missing(head, (30, 50)).outcome, "unable_to_verify")   # partly unclear

    def test_the_audio_region_is_reported_in_the_context(self):
        ctx = ctx_for([], {"analyses_run": {"video": True, "audio": True}})
        self.assertEqual(ctx.zone_visibility["audio"].status, "unknown")


class PartlyEvaluable(unittest.TestCase):
    def test_not_evaluable_names_the_checked_part_and_its_evidence(self):
        anchor = SimpleNamespace(reason="no shock seen on the screen", flags=("no_shock",))
        outcome = checks.partly_evaluable("A1", anchor, "R5", "oxygen away said at 4 s", evidence=("o2",),
                                          timestamps={"oxygen_away_command": 4})
        self.assertEqual((outcome.kind, outcome.blocked_by, outcome.evidence), ("not_evaluable", "R5", ("o2",)))
        self.assertEqual(outcome.reason, "not evaluable because of R5: no shock seen on the screen; checked: oxygen "
                                         "away said at 4 s")
        self.assertIn("no_shock", outcome.flags)


class Flags(unittest.TestCase):
    def test_order_partially_checked_never_gives_an_overall_pass(self):
        overall = decide([passed("R1", "ok", ("e",)), passed("R2", "ok", ("e",), flags=("order_partially_checked",))],
                         CONFIG)
        self.assertEqual(overall.result, "incomplete")
        self.assertEqual([c.category for c in overall.incomplete], ["order partially checked"])

    def test_the_new_flags_are_shared_flags(self):
        self.assertIn("order_partially_checked", checks.FLAGS)
        self.assertIn("timing_uncertain", checks.FLAGS)


class CommandAnchors(unittest.TestCase):
    def test_every_command_has_an_anchor(self):
        events = [audio("oxygen_away_command", 2, 3, "o2"), audio("stand_clear_command", 5, 6, "clear"),
                  audio("shock_command", 8, 9, "shock")]
        ctx = ctx_for(events, {"analyses_run": {"video": True, "audio": True}})
        self.assertEqual({name: ctx.anchor(name).event_id for name in ("oxygen_away", "stand_clear", "shock_command")},
                         {"oxygen_away": "o2", "stand_clear": "clear", "shock_command": "shock"})
        self.assertFalse(ctx.anchor("stop_compressions").present)


class Config(unittest.TestCase):
    ENGINE = yaml.safe_load((ROOT / "configs/rule_engine/engine.yaml").read_text(encoding="utf-8"))

    def test_the_cross_modal_tolerance_is_required(self):
        data = copy.deepcopy(self.ENGINE)
        del data["cross_modal_tolerance_seconds"]
        with self.assertRaises(Exception):
            EngineSettings.from_dict(data)

    def test_the_audio_region_can_be_switched_off(self):
        data = copy.deepcopy(self.ENGINE)
        data["coverage_policy"]["stated_only_regions"] = []
        config = replace(CONFIG, engine=EngineSettings.from_dict(data))
        result = ctx_for([], {"analyses_run": {"video": True, "audio": True}}, config).missing("stop_compressions_command")
        self.assertEqual(result.coverage.status, "covered")   # analyses_run alone, the old behaviour


if __name__ == "__main__":
    unittest.main()
