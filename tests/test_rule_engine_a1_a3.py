"""Increment 21: A1 (oxygen away) and A3 (all stand clear), each a command before the shock (P-040).

The full configs/rules.yaml with A1 and A3 approved (testing practice, methods.md). Synthetic timelines
only; command events as detect_commands emits them: the Whisper segment's start and end (D-125).
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
RULES = {"A1": "oxygen_away_command", "A3": "stand_clear_command"}


def config(**limits):
    """The full catalogue, A1 and A3 approved; limits replace timing_limits entries."""
    data = copy.deepcopy(CATALOGUE)
    for entry in data["rules"]:
        if entry["id"] in RULES:
            entry["status"] = "approved"
    data["timing_limits"].update(limits)
    return RuleEngineConfig.from_dict(data)


CONFIG = config()
APPROVAL = {"approved_by": "Supervisor", "approved_on": "2026-11-10", "source": "test"}


def screen(t, event_id="shock"):
    return Event("shock_delivered_on_screen", t, t, "annotation", 1.0, event_id=event_id)


def said(name, start, end=None, event_id=None, confidence=0.9):
    return Event(name, start, end if end is not None else start + 1.0, "audio", confidence,
                 event_id=event_id or f"{name}@{start}", metadata={"text": "x", "confidence_kind": "asr_proxy"})


def header(audio=True, clear=((0.0, 30.0),)):
    """analyses_run.audio and the clear-audio intervals (None: not stated, D-122)."""
    data = {"duration_seconds": 30.0, "analyses_run": {"video": True, "audio": audio}}
    if clear is not None:
        data["visibility"] = {"region:audio": [list(c) for c in clear]}
    return TimelineHeader.from_dict(data, regions=REGIONS)


def run(events, head=None, cfg=CONFIG):
    return assess(events, cfg, header=head if head is not None else header(), registry=discover())


class Each(unittest.TestCase):
    """Every case for both rules."""

    def check(self, make_events, expect, head=None, cfg=CONFIG):
        for rule_id, name in RULES.items():
            with self.subTest(rule=rule_id):
                outcome = run(make_events(name), head, cfg).outcome(rule_id)
                expect(outcome)


class WithShockTime(Each):
    def test_before_the_shock_passes_with_timing_not_checked(self):
        def expect(o):
            self.assertEqual((o.kind, o.timing_checked), ("pass_direct", False))
            self.assertIn("timing_not_checked", o.flags)
            self.assertIn("before the shock on the screen at 15 s", o.reason)
        self.check(lambda n: [said(n, 5, 6, "cmd"), screen(15)], expect)

    def test_the_overall_result_cannot_be_pass(self):
        result = run([said("oxygen_away_command", 5), said("stand_clear_command", 8), screen(15)])
        self.assertEqual(result.overall.result, "incomplete")

    def test_a_segment_overlapping_the_shock_is_a_tie_never_after(self):
        """D-125: the command may lie anywhere in its segment; overlapping the shock is a tie, so it counts."""
        def expect(o):
            self.assertEqual(o.kind, "pass_direct")
            self.assertIn("at (within the tolerance of) the shock", o.reason)
        self.check(lambda n: [said(n, 14, 16.5), screen(15)], expect)

    def test_within_the_cross_modal_tolerance_after_the_shock_is_a_tie(self):
        self.check(lambda n: [said(n, 15.8, 15.9), screen(15)], lambda o: self.assertEqual(o.kind, "pass_direct"))

    def test_only_after_the_shock_is_after_shock(self):
        def expect(o):
            self.assertEqual((o.kind, o.failure_code), ("fail", "after_shock"))
            self.assertIn("said only at 18 s, after the shock on the screen at 15 s", o.reason)
        self.check(lambda n: [screen(15), said(n, 18, 19)], expect)

    def test_any_occurrence_before_the_shock_counts(self):
        self.check(lambda n: [said(n, 5, 6, "early"), screen(15), said(n, 18, 19, "late")],
                   lambda o: self.assertEqual((o.kind, o.evidence[0]), ("pass_direct", "early")))

    def test_missing_while_the_audio_was_clear_is_missing(self):
        def expect(o):
            self.assertEqual((o.kind, o.failure_code), ("fail", "missing"))
            self.assertIn("although the audio was clear throughout (D-122)", o.reason)
        self.check(lambda n: [screen(15)], expect, header(clear=((0.0, 20.0),)))

    def test_missing_without_clear_audio_intervals_is_unable_to_verify(self):
        """D-122: the audio analysed doesn't say a command would have been recognised."""
        self.check(lambda n: [screen(15)], lambda o: self.assertEqual(o.kind, "unable_to_verify"), header(clear=None))

    def test_missing_with_unclear_audio_before_the_shock_is_unable_to_verify(self):
        self.check(lambda n: [screen(15)], lambda o: self.assertEqual(o.kind, "unable_to_verify"),
                   header(clear=((0.0, 5.0), (10.0, 30.0))))

    def test_missing_with_no_audio_analysed_is_unable_to_verify(self):
        self.check(lambda n: [screen(15)], lambda o: self.assertEqual(o.kind, "unable_to_verify"),
                   header(audio=False, clear=None))

    def test_a_low_confidence_command_is_never_a_fail(self):
        def expect(o):
            self.assertEqual((o.kind, o.evidence), ("unable_to_verify", ("weak",)))
            self.assertIn("low confidence", o.reason)
        self.check(lambda n: [said(n, 5, 6, "weak", confidence=0.2), screen(15)], expect)


class WithoutShockTime(Each):
    """D-121: "before the shock" can't be judged; whether the command was said still can."""

    def test_a_command_seen_is_not_evaluable_because_of_r5_naming_it(self):
        def expect(o):
            self.assertEqual((o.kind, o.blocked_by, o.evidence), ("not_evaluable", "R5", ("cmd",)))
            self.assertIn("said at 5 s; whether before the shock can't be judged", o.reason)
        self.check(lambda n: [said(n, 5, 6, "cmd")], expect)

    def test_missing_while_the_audio_was_clear_throughout_is_missing(self):
        def expect(o):
            self.assertEqual((o.kind, o.failure_code), ("fail", "missing"))
            self.assertIn("no shock time is needed to judge this (D-121)", o.reason)
        self.check(lambda n: [Event("Gel applied", 2, 2, "annotation", 1.0, event_id="gel")], expect)

    def test_missing_without_clear_audio_is_not_evaluable_because_of_r5(self):
        def expect(o):
            self.assertEqual((o.kind, o.blocked_by), ("not_evaluable", "R5"))
            self.assertIn("whether it was said is unknown too", o.reason)
        self.check(lambda n: [Event("Gel applied", 2, 2, "annotation", 1.0, event_id="gel")], expect, header(clear=None))

    def test_two_shocks_give_no_shock_time(self):
        self.check(lambda n: [said(n, 5, 6), screen(14, "s1"), screen(16, "s2")],
                   lambda o: self.assertEqual((o.kind, o.blocked_by), ("not_evaluable", "R5")))


class TimeLimit(unittest.TestCase):
    def test_an_approved_no_limit_passes_fully(self):
        cfg = config(oxygen_away_before_shock_seconds={"value": None, "no_limit": True, **APPROVAL})
        outcome = run([said("oxygen_away_command", 5), screen(15)], cfg=cfg).outcome("A1")
        self.assertEqual((outcome.kind, outcome.timing_checked), ("pass_direct", True))
        self.assertNotIn("timing_not_checked", outcome.flags)

    def test_an_approved_numeric_limit_is_refused_loudly(self):
        """No failure code is defined for it, so it is never guessed: engine_error (D-063)."""
        cfg = config(stand_clear_before_shock_seconds={"value": 10, **APPROVAL})
        outcome = run([said("stand_clear_command", 5), screen(15)], cfg=cfg).outcome("A3")
        self.assertEqual(outcome.kind, "engine_error")
        self.assertIn("not implemented", outcome.reason)


class Catalogue(unittest.TestCase):
    def test_pending_until_approved(self):
        result = assess([said("oxygen_away_command", 5), screen(15)], load_rules_config(), header=header(),
                        registry=discover())
        self.assertEqual({result.outcome(r).kind for r in RULES}, {"pending"})

    def test_a1_and_a3_own_command_before_the_shock(self):
        order = CONFIG.procedure_order
        self.assertEqual((order.relation("A1", "R5").owner, order.relation("A3", "R5").owner), ("A1", "A3"))


if __name__ == "__main__":
    unittest.main()
