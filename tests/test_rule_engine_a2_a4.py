"""Increment 22: A2 continue compressions and A4 stop CPR (P-041).

The full configs/rules.yaml with A2 and A4 approved (testing practice, methods.md). Synthetic timelines only;
command events carry their Whisper segment (D-125).
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


def config(**limits):
    data = copy.deepcopy(CATALOGUE)
    for entry in data["rules"]:
        if entry["id"] in ("A2", "A4"):
            entry["status"] = "approved"
    data["timing_limits"].update(limits)
    return RuleEngineConfig.from_dict(data)


CONFIG = config()


def screen(t, event_id="shock"):
    return Event("shock_delivered_on_screen", t, t, "annotation", 1.0, event_id=event_id)


def said(name, start, end=None, event_id=None, confidence=0.9):
    return Event(name, start, end if end is not None else start + 1.0, "audio", confidence,
                 event_id=event_id or f"{name}@{start}", metadata={"text": "x", "confidence_kind": "asr_proxy"})


def cont(start, end=None, event_id="cont", **kw):
    return said("continue_compressions_command", start, end, event_id, **kw)


def resume(start, end=None, event_id="resume"):
    return said("resume_compressions_command", start, end, event_id)


def stop(start, end=None, event_id="stop", **kw):
    return said("stop_compressions_command", start, end, event_id, **kw)


def header(audio=True, clear=((0.0, 30.0),)):
    data = {"duration_seconds": 30.0, "analyses_run": {"video": True, "audio": audio}}
    if clear is not None:
        data["visibility"] = {"region:audio": [list(c) for c in clear]}
    return TimelineHeader.from_dict(data, regions=REGIONS)


def outcome(rule_id, events, head=None, cfg=CONFIG):
    return assess(events, cfg, header=head if head is not None else header(), registry=discover()).outcome(rule_id)


class A2WithShockTime(unittest.TestCase):
    def test_continue_before_the_shock_passes(self):
        result = outcome("A2", [cont(4), screen(15)])
        self.assertEqual((result.kind, result.evidence), ("pass_direct", ("cont", "shock")))

    def test_a_resume_phrase_before_the_shock_is_continue(self):
        """P-011: resolved by its segment's position relative to the shock."""
        self.assertEqual(outcome("A2", [resume(4), screen(15)]).kind, "pass_direct")

    def test_a_resume_segment_overlapping_the_shock_is_unable_to_verify(self):
        """D-125: continue (before) or start (after) can't be told: never wrong_stage, never missing."""
        result = outcome("A2", [resume(14, 16), screen(15)])
        self.assertEqual(result.kind, "unable_to_verify")
        self.assertIn("continue (before) or start (after) can't be told", result.reason)

    def test_an_unambiguous_continue_only_after_the_shock_is_wrong_stage(self):
        result = outcome("A2", [screen(15), cont(20)])
        self.assertEqual((result.kind, result.failure_code), ("fail", "wrong_stage"))

    def test_a_resume_after_the_shock_is_the_restart_not_continue(self):
        """It resolves to start (R7), so A2 has no continue: missing while the audio was clear."""
        result = outcome("A2", [screen(15), resume(20)])
        self.assertEqual((result.kind, result.failure_code), ("fail", "missing"))

    def test_missing_without_clear_audio_is_unable_to_verify(self):
        for head in (header(clear=None), header(audio=False, clear=None)):
            with self.subTest(head=head.analyses_run):
                self.assertEqual(outcome("A2", [screen(15)], head).kind, "unable_to_verify")

    def test_a_low_confidence_continue_is_never_a_fail(self):
        result = outcome("A2", [cont(4, confidence=0.2), screen(15)])
        self.assertEqual((result.kind, result.evidence), ("unable_to_verify", ("cont",)))


class A2WithoutShockTime(unittest.TestCase):
    def test_continue_seen_is_not_evaluable_because_of_r5(self):
        result = outcome("A2", [cont(4)])
        self.assertEqual((result.kind, result.blocked_by, result.evidence), ("not_evaluable", "R5", ("cont",)))

    def test_an_unresolved_resume_is_named_too(self):
        result = outcome("A2", [resume(4)])
        self.assertEqual((result.kind, result.blocked_by), ("not_evaluable", "R5"))
        self.assertIn("continue or start: no shock time", result.reason)

    def test_missing_with_clear_audio_is_missing_and_otherwise_not_evaluable(self):
        self.assertEqual(outcome("A2", [stop(8)]).failure_code, "missing")
        self.assertEqual(outcome("A2", [stop(8)], header(clear=None)).blocked_by, "R5")


class A4WithShockTime(unittest.TestCase):
    def test_after_continue_and_before_the_shock_passes_with_timing_not_checked(self):
        result = outcome("A4", [cont(4), stop(8), screen(15)])
        self.assertEqual((result.kind, result.timing_checked), ("pass_direct", False))
        self.assertIn("timing_not_checked", result.flags)
        self.assertEqual(result.evidence, ("stop", "cont", "shock"))

    def test_stop_before_continue_is_wrong_order(self):
        """D-027: A4 owns stop-before-continue; A2 doesn't fail for it."""
        events = [stop(4), cont(8), screen(15)]
        result = outcome("A4", events)
        self.assertEqual((result.kind, result.failure_code), ("fail", "wrong_order"))
        self.assertEqual(outcome("A2", events, cfg=CONFIG).kind, "pass_direct")

    def test_stop_only_after_the_shock_is_after_shock(self):
        result = outcome("A4", [cont(4), screen(15), stop(20)])
        self.assertEqual((result.kind, result.failure_code), ("fail", "after_shock"))

    def test_no_continue_and_a_stop_only_after_the_shock_is_after_shock(self):
        """D-121: a judgeable part shows a mistake (stop after the shock), so Fail, not Not evaluable because of A2."""
        result = outcome("A4", [screen(15), stop(20)])
        self.assertEqual((result.kind, result.failure_code), ("fail", "after_shock"))

    def test_stop_overlapping_the_shock_is_a_tie(self):
        self.assertEqual(outcome("A4", [cont(4), stop(14, 16), screen(15)]).kind, "pass_direct")

    def test_stop_and_continue_in_one_segment_are_not_ordered(self):
        events = [cont(6, 9, "c"), stop(6, 9, "s"), screen(15)]
        result = outcome("A4", events)
        self.assertEqual(result.kind, "pass_direct")
        self.assertIn("order_partially_checked", result.flags)
        self.assertIn("not ordered", result.reason)

    def test_no_continue_observed_is_not_evaluable_because_of_a2(self):
        result = outcome("A4", [stop(8), screen(15)])
        self.assertEqual((result.kind, result.blocked_by, result.evidence), ("not_evaluable", "A2", ("stop", "shock")))
        self.assertIn("checked: stop said at 8 s, before the shock", result.reason)

    def test_only_an_unresolved_resume_is_not_evaluable_because_of_a2(self):
        result = outcome("A4", [stop(8), resume(14, 16), screen(15)])
        self.assertEqual((result.kind, result.blocked_by), ("not_evaluable", "A2"))
        self.assertIn("couldn't be resolved", result.reason)

    def test_missing_stop(self):
        self.assertEqual(outcome("A4", [cont(4), screen(15)]).failure_code, "missing")
        self.assertEqual(outcome("A4", [cont(4), screen(15)], header(clear=None)).kind, "unable_to_verify")


class A4WithoutShockTime(unittest.TestCase):
    def test_stop_after_continue_is_not_evaluable_because_of_r5_naming_both(self):
        result = outcome("A4", [cont(4), stop(8)])
        self.assertEqual((result.kind, result.blocked_by), ("not_evaluable", "R5"))
        self.assertIn("stop said at 8 s, after continue (4 s)", result.reason)

    def test_stop_before_continue_is_wrong_order_without_a_shock_time(self):
        """D-121: the order against continue is A4's own evidence; no shock time is needed."""
        self.assertEqual(outcome("A4", [stop(4), cont(8)]).failure_code, "wrong_order")

    def test_missing_with_clear_audio_is_missing(self):
        self.assertEqual(outcome("A4", [cont(4)]).failure_code, "missing")


class Limits(unittest.TestCase):
    def test_an_approved_no_limit_passes_fully(self):
        cfg = config(stop_to_shock_seconds={"value": None, "no_limit": True, **APPROVAL})
        result = outcome("A4", [cont(4), stop(8), screen(15)], cfg=cfg)
        self.assertEqual((result.kind, result.timing_checked), ("pass_direct", True))

    def test_an_approved_number_is_refused_loudly(self):
        cfg = config(stop_to_shock_seconds={"value": 10, **APPROVAL})
        self.assertEqual(outcome("A4", [cont(4), stop(8), screen(15)], cfg=cfg).kind, "engine_error")


class Ownership(unittest.TestCase):
    def test_the_relations_a2_and_a4_own(self):
        order = CONFIG.procedure_order
        self.assertEqual({(r.before, r.after) for r in order.owned_by("A2")}, {("A2", "R5")})
        self.assertEqual({(r.before, r.after) for r in order.owned_by("A4")}, {("A2", "A4"), ("A4", "R5")})

    def test_pending_until_approved(self):
        result = assess([cont(4), stop(8), screen(15)], load_rules_config(), header=header(), registry=discover())
        self.assertEqual({result.outcome(r).kind for r in ("A2", "A4")}, {"pending"})


if __name__ == "__main__":
    unittest.main()
