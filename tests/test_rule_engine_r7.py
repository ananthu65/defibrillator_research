"""Increment 24: R7/A6, compressions restarted after the shock: one check reported under both IDs (P-043, D-044).

The full configs/rules.yaml with R7 and A6 approved (testing practice, methods.md). Synthetic timelines only;
command events carry their Whisper segment (D-125). The shock time comes only from the screen (D-093).
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
        if entry["id"] in ("R7", "A6"):
            entry["status"] = "approved"
    data["timing_limits"].update(limits)
    return RuleEngineConfig.from_dict(data)


CONFIG = config()


def screen(t, event_id="shock"):
    return Event("shock_delivered_on_screen", t, t, "annotation", 1.0, event_id=event_id)


def said(name, start, end=None, event_id=None, confidence=0.9):
    return Event(name, start, end if end is not None else start + 1.0, "audio", confidence,
                 event_id=event_id or f"{name}@{start}", metadata={"text": "x", "confidence_kind": "asr_proxy"})


def start(t, end=None, event_id="start", **kw):
    return said("start_compressions_command", t, end, event_id, **kw)


def resume(t, end=None, event_id="resume"):
    return said("resume_compressions_command", t, end, event_id)


def header(audio=True, clear=((0.0, 30.0),)):
    data = {"duration_seconds": 30.0, "analyses_run": {"video": True, "audio": audio}}
    if clear is not None:
        data["visibility"] = {"region:audio": [list(c) for c in clear]}
    return TimelineHeader.from_dict(data, regions=REGIONS)


def both(events, head=None, cfg=CONFIG):
    """(R7, A6): one check reported under both IDs (D-044)."""
    result = assess(events, cfg, header=head if head is not None else header(), registry=discover())
    return result.outcome("R7"), result.outcome("A6")


def r7(events, head=None, cfg=CONFIG):
    return both(events, head, cfg)[0]


class WithShockTime(unittest.TestCase):
    def test_a_restart_after_the_shock_passes_with_timing_not_checked_under_both_ids(self):
        r7_result, a6_result = both([screen(15), start(18)])
        for result in (r7_result, a6_result):
            self.assertEqual((result.kind, result.timing_checked), ("pass_direct", False))
            self.assertIn("timing_not_checked", result.flags)
        self.assertEqual(a6_result.reason, r7_result.reason)

    def test_a_resume_phrase_after_the_shock_is_the_restart(self):
        self.assertEqual(r7([screen(15), resume(18)]).kind, "pass_direct")

    def test_a_start_overlapping_the_shock_is_a_tie(self):
        self.assertEqual(r7([screen(15), start(14.5, 16)]).kind, "pass_direct")

    def test_an_unresolved_resume_near_the_shock_is_unable_to_verify_naming_the_cause(self):
        result = r7([screen(15), resume(14.5, 15.5)])
        self.assertEqual(result.kind, "unable_to_verify")
        self.assertIn("likely cause", result.reason)
        self.assertIn("resume_compressions_command", result.reason)
        self.assertIn("word time", result.reason)

    def test_start_only_before_the_shock_is_before_shock(self):
        result = r7([start(5), screen(15)])
        self.assertEqual((result.kind, result.failure_code), ("fail", "before_shock"))

    def test_before_shock_needs_clear_audio_from_the_shock_to_the_end(self):
        """D-122: a start heard only before the shock fails only if a restart could not have been missed."""
        self.assertEqual(r7([start(5), screen(15)], header(clear=((0.0, 30.0),))).failure_code, "before_shock")
        for head in (header(clear=((0.0, 15.0),)), header(clear=((0.0, 20.0),)), header(clear=None)):
            with self.subTest(clear=head.visibility.get("region:audio")):
                result = r7([start(5), screen(15)], head)
                self.assertEqual((result.kind, result.failure_code), ("unable_to_verify", None))
                self.assertIn("may have been said", result.reason)

    def test_an_early_start_and_a_low_confidence_restart_is_unable(self):
        result = r7([start(5), screen(15), start(18, event_id="low", confidence=0.2)])
        self.assertEqual((result.kind, result.evidence), ("unable_to_verify", ("start", "low")))

    def test_a_restart_after_the_shock_counts_even_after_an_early_start(self):
        self.assertEqual(r7([start(5, 6, "early"), screen(15), start(18, 19, "late")]).evidence[0], "late")

    def test_an_early_start_and_an_unresolved_resume_is_unable_never_before_shock(self):
        """The unresolved command may have been the restart: a Fail needs certainty."""
        self.assertEqual(r7([start(5), screen(15), resume(14.5, 15.5)]).kind, "unable_to_verify")

    def test_missing(self):
        self.assertEqual(r7([screen(15)]).failure_code, "missing")   # clear from the shock to the end
        for head in (header(clear=((0.0, 15.0),)), header(clear=None), header(audio=False, clear=None)):
            with self.subTest(clear=head.visibility.get("region:audio")):
                self.assertEqual(r7([screen(15)], head).kind, "unable_to_verify")

    def test_a_low_confidence_restart_is_never_a_fail(self):
        result = r7([screen(15), start(18, confidence=0.2)])
        self.assertEqual((result.kind, result.evidence), ("unable_to_verify", ("start",)))


class TimeLimit(unittest.TestCase):
    """shock_to_compressions_seconds, judged on the shortest and longest possible durations (D-125)."""

    FIVE = config(shock_to_compressions_seconds={"value": 5, **APPROVAL})

    def test_within_too_late_and_uncertain(self):
        self.assertEqual(r7([screen(15), start(17, 18)], cfg=self.FIVE).timing_checked, True)
        late = r7([screen(15), start(21, 22)], cfg=self.FIVE)
        self.assertEqual((late.kind, late.failure_code), ("fail", "too_late"))
        uncertain = r7([screen(15), start(18, 22)], cfg=self.FIVE)   # 3 to 7 s
        self.assertEqual((uncertain.kind, uncertain.flags), ("unable_to_verify", ("timing_uncertain",)))

    def test_an_approved_no_limit_passes_fully(self):
        cfg = config(shock_to_compressions_seconds={"value": None, "no_limit": True, **APPROVAL})
        self.assertEqual(r7([screen(15), start(25)], cfg=cfg).timing_checked, True)


class WithoutShockTime(unittest.TestCase):
    def test_a_start_or_resume_seen_is_not_evaluable_because_of_r5(self):
        for events in ([start(18)], [resume(18)]):
            with self.subTest(events=[e.event_name for e in events]):
                result = r7(events)
                self.assertEqual((result.kind, result.blocked_by), ("not_evaluable", "R5"))

    def test_a_removal_never_gives_the_shock_time(self):
        """D-093, D-115: no removal fallback."""
        removal = Event("paddles_removed_after_shock", 16, 16, "annotation", 1.0, event_id="removal")
        self.assertEqual(r7([removal, start(18)]).blocked_by, "R5")

    def test_missing_with_clear_audio_is_missing(self):
        gel = Event("Gel applied", 2, 2, "annotation", 1.0, event_id="gel")
        self.assertEqual(r7([gel]).failure_code, "missing")
        self.assertEqual(r7([gel], header(clear=None)).blocked_by, "R5")


class Catalogue(unittest.TestCase):
    def test_r7_owns_only_shock_before_the_restart(self):
        order = CONFIG.procedure_order
        self.assertEqual({(r.before, r.after) for r in order.owned_by("R7")}, {("R5", "R7")})
        self.assertEqual(order.relation("R6", "R7").owner, "S1")

    def test_pending_until_approved(self):
        result = assess([screen(15), start(18)], load_rules_config(), header=header(), registry=discover())
        self.assertEqual({result.outcome(r).kind for r in ("R7", "A6")}, {"pending"})


if __name__ == "__main__":
    unittest.main()
