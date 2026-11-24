"""Increment 23: A5, the verbal shock command (P-042).

The full configs/rules.yaml with A5 approved (testing practice, methods.md). Synthetic timelines only; command
events carry their Whisper segment (D-125). A5 stays pending in rules.yaml and is held back in the demo (OQ-075).
"""
import copy
import unittest

import yaml

from pipeline.config import ROOT
from rules import demo
from rules.config import RuleEngineConfig, load_rules_config
from rules.coverage import TimelineHeader
from rules.engine import assess
from rules.registry import discover
from schemas.event import Event

CATALOGUE = yaml.safe_load((ROOT / "configs/rules.yaml").read_text(encoding="utf-8"))
REGIONS = tuple(load_rules_config().engine.regions)
APPROVAL = {"approved_by": "Supervisor", "approved_on": "2026-11-24", "source": "test"}


def config(approve=("A5",), **limits):
    data = copy.deepcopy(CATALOGUE)
    for entry in data["rules"]:
        if entry["id"] in approve:
            entry["status"] = "approved"
    data["timing_limits"].update(limits)
    return RuleEngineConfig.from_dict(data)


CONFIG = config()


def screen(t, event_id="shock"):
    return Event("shock_delivered_on_screen", t, t, "annotation", 1.0, event_id=event_id)


def command(start, end=None, event_id="cmd", confidence=0.9):
    return Event("shock_command", start, end if end is not None else start + 1.0, "audio", confidence,
                 event_id=event_id, metadata={"text": "x", "confidence_kind": "asr_proxy"})


def header(audio=True, clear=((0.0, 30.0),), screen_seen=True):
    data = {"duration_seconds": 30.0, "analyses_run": {"video": True, "audio": audio}}
    visibility = {}
    if clear is not None:
        visibility["region:audio"] = [list(c) for c in clear]
    if screen_seen:
        visibility["region:screen"] = [[0.0, 30.0]]
    data["visibility"] = visibility
    return TimelineHeader.from_dict(data, regions=REGIONS)


def run(events, head=None, cfg=CONFIG):
    return assess(events, cfg, header=head if head is not None else header(), registry=discover())


def a5(events, head=None, cfg=CONFIG):
    return run(events, head, cfg).outcome("A5")


class WithShockTime(unittest.TestCase):
    def test_before_the_shock_passes_with_timing_not_checked(self):
        result = a5([command(10), screen(15)])
        self.assertEqual((result.kind, result.timing_checked), ("pass_direct", False))
        self.assertIn("timing_not_checked", result.flags)
        self.assertIn("before the shock on the screen at 15 s", result.reason)

    def test_at_the_shock_is_a_tie(self):
        """A segment overlapping the shock, or within the cross-modal tolerance, is "at" the shock."""
        for cmd in (command(14, 16), command(15.5, 15.6)):
            with self.subTest(segment=(cmd.start, cmd.end)):
                result = a5([cmd, screen(15)])
                self.assertEqual(result.kind, "pass_direct")
                self.assertIn("at (within the tolerance of) the shock", result.reason)
                self.assertNotIn("timing_not_checked", result.flags)

    def test_only_certainly_after_the_shock_is_after_shock(self):
        """An order mistake on A5's own relation (A5 -> R5), like A1 and A3, not a time-limit question."""
        result = a5([screen(15), command(20)])
        self.assertEqual((result.kind, result.failure_code), ("fail", "after_shock"))
        self.assertIn("said only at 20 s, after the shock", result.reason)

    def test_any_occurrence_before_or_at_the_shock_satisfies_a5(self):
        self.assertEqual(a5([command(5, 6, "early"), screen(15), command(20, 21, "late")]).kind, "pass_direct")
        result = a5([command(5, 6, "early"), command(15, 16, "at"), screen(15)])
        self.assertEqual(result.evidence[0], "at")   # at the shock preferred

    def test_how_long_before_is_timing_not_checked(self):
        result = a5([command(5, 6, "far"), command(10, 11, "near"), screen(15)])
        self.assertEqual((result.kind, result.evidence[0]), ("pass_direct", "near"))
        self.assertIn("how long before: timing not checked", result.reason)

    def test_missing_while_the_audio_was_clear_is_missing(self):
        result = a5([screen(15)])
        self.assertEqual((result.kind, result.failure_code), ("fail", "missing"))

    def test_missing_without_clear_audio_is_unable_to_verify(self):
        for head in (header(clear=None), header(audio=False, clear=None), header(clear=((0.0, 10.0),))):
            with self.subTest(head=head.visibility.get("region:audio")):
                self.assertEqual(a5([screen(15)], head).kind, "unable_to_verify")

    def test_a_low_confidence_command_is_never_a_fail(self):
        result = a5([command(10, confidence=0.2), screen(15)])
        self.assertEqual((result.kind, result.evidence), ("unable_to_verify", ("cmd",)))


class WithoutShockTime(unittest.TestCase):
    def test_a_command_seen_is_not_evaluable_because_of_r5(self):
        result = a5([command(10)])
        self.assertEqual((result.kind, result.blocked_by, result.evidence), ("not_evaluable", "R5", ("cmd",)))

    def test_missing_with_clear_audio_is_missing_and_otherwise_not_evaluable(self):
        gel = Event("Gel applied", 2, 2, "annotation", 1.0, event_id="gel")
        self.assertEqual(a5([gel]).failure_code, "missing")
        self.assertEqual(a5([gel], header(clear=None)).blocked_by, "R5")


class Limits(unittest.TestCase):
    def test_an_approved_no_limit_passes_fully(self):
        cfg = config(shock_command_tolerance_seconds={"value": None, "no_limit": True, **APPROVAL})
        result = a5([command(10), screen(15)], cfg=cfg)
        self.assertEqual((result.kind, result.timing_checked), ("pass_direct", True))

    def test_an_approved_number_is_refused_loudly(self):
        cfg = config(shock_command_tolerance_seconds={"value": 3, **APPROVAL})
        self.assertEqual(a5([command(10), screen(15)], cfg=cfg).kind, "engine_error")


class NeverAffectsR5(unittest.TestCase):
    """The proposal: the shock is judged visually. A5's result, Pass or Fail, never changes R5's."""

    CFG = config(approve=("A5", "R5"))

    def test_r5_is_the_same_with_or_without_a_shock_command(self):
        with_command = run([command(10), screen(15)], cfg=self.CFG)
        without = run([screen(15)], cfg=self.CFG)
        self.assertEqual(without.outcome("A5").failure_code, "missing")
        self.assertEqual((with_command.outcome("R5").kind, with_command.outcome("R5").failure_code),
                         (without.outcome("R5").kind, without.outcome("R5").failure_code))
        self.assertEqual(without.outcome("R5").kind, "pass_direct")


class Catalogue(unittest.TestCase):
    def test_pending_in_rules_yaml(self):
        result = assess([command(10), screen(15)], load_rules_config(), header=header(), registry=discover())
        self.assertEqual(result.outcome("A5").kind, "pending")

    def test_held_back_in_the_demo(self):
        """OQ-075: a lecturer-like demo without a shock command must not fail."""
        entry = next(r for r in demo.load_rules_config(demo.DEMO_CONFIG).rules if r.id == "A5")
        self.assertEqual(entry.status, "pending")

    def test_a5_owns_only_command_before_the_shock(self):
        order = CONFIG.procedure_order
        self.assertEqual({(r.before, r.after) for r in order.owned_by("A5")}, {("A5", "R5")})
        self.assertEqual(order.relation("A4", "A5").owner, "A7")
        for step in ("R2A", "PLACE", "R2B", "R3", "R4"):
            self.assertIn(("A5", step), order.unknown)


if __name__ == "__main__":
    unittest.main()
