"""Increment 26: A7, the order of the audio commands (P-045; D-120 to D-127).

The full configs/rules.yaml with A7 approved (testing practice, methods.md); the order is the interim one in
procedure_order.yaml (the lecturer's ground-truth video, NOT clinically approved, OQ-062). Synthetic timelines
only; command events carry their Whisper segment (D-125).
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


def config(approve=("A7",)):
    data = copy.deepcopy(CATALOGUE)
    for entry in data["rules"]:
        if entry["id"] in approve:
            entry["status"] = "approved"
    return RuleEngineConfig.from_dict(data)


CONFIG = config()
NAMES = {"A1": "oxygen_away_command", "A3": "stand_clear_command", "A2": "continue_compressions_command",
         "CHARGE": "charging_command", "GELCMD": "gel_announcement_command", "A4": "stop_compressions_command",
         "A5": "shock_command", "R7": "start_compressions_command"}


def said(step, start, end=None, event_id=None, confidence=0.9):
    return Event(NAMES.get(step, step), start, end if end is not None else start + 1.0, "audio", confidence,
                 event_id=event_id or f"{step}@{start:g}", metadata={"text": "x", "confidence_kind": "asr_proxy"})


def screen(t=30):
    return Event("shock_delivered_on_screen", t, t, "annotation", 1.0, event_id="shock")


def header(clear=((0.0, 60.0),)):
    data = {"duration_seconds": 60.0, "analyses_run": {"video": True, "audio": True}}
    if clear is not None:
        data["visibility"] = {"region:audio": [list(c) for c in clear]}
    return TimelineHeader.from_dict(data, regions=REGIONS)


def run(events, head=None, cfg=CONFIG):
    return assess(events, cfg, header=head if head is not None else header(), registry=discover())


def a7(events, head=None, cfg=CONFIG):
    return run(events, head, cfg).outcome("A7")


# The lecturer-like command sequence: oxygen away, stand clear, continue, charging, "applying gel", stop, (no
# shock command), the shock, start.
LECTURER = [said("A1", 2), said("A3", 4), said("A2", 6), said("CHARGE", 8), said("GELCMD", 10), said("A4", 12),
            screen(30), said("R7", 34)]


class Order(unittest.TestCase):
    def test_the_lecturer_like_sequence_passes_cleanly(self):
        """A5 is not said: a missing step is left out (its own rule reports it), so no flag."""
        result = a7(LECTURER)
        self.assertEqual((result.kind, result.flags), ("pass_direct", ()))
        self.assertEqual(result.evidence, ("A1@2", "A3@4", "A2@6", "CHARGE@8", "GELCMD@10", "A4@12", "R7@34"))

    def test_one_swapped_pair_is_one_mistake_naming_both(self):
        events = [said("A3", 2), said("A1", 4)] + LECTURER[2:]
        result = a7(events)
        self.assertEqual((result.kind, result.failure_code), ("fail", "wrong_order"))
        self.assertIn("A1 (oxygen_away_command at 4 s) and A3 (stand_clear_command at 2 s) are in the wrong order "
                      "(one mistake)", result.reason)
        self.assertEqual(result.evidence, ("A1@4", "A3@2"))

    def test_a_repeated_command_in_the_right_place_counts(self):
        events = [said("A3", 0), said("A1", 2), said("A3", 4, event_id="A3 again")] + LECTURER[2:]
        result = a7(events)
        self.assertEqual(result.kind, "pass_direct")
        self.assertIn("A3 again", result.evidence)

    def test_an_optional_step_out_of_place_is_misplaced(self):
        """Charging said after stop: dropping charging (1) beats dropping stop and "applying gel" (2)."""
        events = [said("A1", 2), said("A3", 4), said("A2", 6), said("GELCMD", 10), said("A4", 12),
                  said("CHARGE", 14), screen(30), said("R7", 34)]
        result = a7(events)
        self.assertEqual((result.kind, result.failure_code, result.evidence), ("fail", "wrong_order", ("CHARGE@14",)))
        self.assertIn("CHARGE (charging_command at 14 s) is out of order", result.reason)

    def test_optional_steps_not_said_are_never_missing(self):
        events = [e for e in LECTURER if not e.event_id.startswith(("CHARGE", "GELCMD"))]
        self.assertEqual((a7(events).kind, a7(events).flags), ("pass_direct", ()))

    def test_a_missing_required_step_is_left_out(self):
        events = [e for e in LECTURER if not e.event_id.startswith("A3")]
        result = a7(events)
        self.assertEqual((result.kind, result.flags), ("pass_direct", ()))
        self.assertNotIn("A3", result.reason)

    def test_a_misplaced_step_among_many_is_named_alone(self):
        """Stand clear after stop: one step misplaced, not a mistake between it and every later step."""
        events = [said("A1", 2), said("A2", 6), said("CHARGE", 8), said("A4", 12), said("A3", 14), screen(30),
                  said("R7", 34)]
        result = a7(events)
        self.assertEqual((result.failure_code, result.evidence), ("wrong_order", ("A3@14",)))

    def test_a_tie_satisfies_either_order(self):
        events = [said("A1", 2), said("A3", 1.5, 2.5)] + LECTURER[2:]   # overlapping segments
        self.assertEqual(a7(events).kind, "pass_direct")


class Ownership(unittest.TestCase):
    def test_a7_judges_only_the_audio_relations_it_owns(self):
        order = CONFIG.procedure_order
        owned = {(r.before, r.after) for r in order.owned_by("A7")}
        self.assertNotIn(("A2", "A4"), owned)   # A4's (D-027)
        self.assertIn(("A4", "A5"), owned)
        for before, after in owned:
            self.assertEqual({order.step(before).modality, order.step(after).modality}, {"audio"})

    def test_stop_before_continue_is_judged_once_by_a4_not_by_a7(self):
        events = [said("A1", 2), said("A3", 4), said("A4", 6), said("A2", 8), screen(30), said("R7", 34)]
        result = run(events, cfg=config(approve=("A7", "A4")))
        self.assertEqual(result.outcome("A7").kind, "pass_direct")
        self.assertEqual(result.outcome("A4").failure_code, "wrong_order")

    def test_no_depends_on(self):
        self.assertEqual(load_rules_config().rule("A7").depends_on, ())


class PartialEvidence(unittest.TestCase):
    def test_fewer_than_two_commands_is_unable_to_verify(self):
        for events in ([screen(30)], [said("A1", 2), screen(30)]):
            with self.subTest(n=len(events) - 1):
                self.assertEqual((a7(events).kind, a7(events).flags), ("unable_to_verify", ()))

    def test_commands_in_one_segment_are_not_ordered(self):
        """"stop compressions, shock" in one Whisper segment: their mutual order isn't checked, never a Fail."""
        events = [said("A1", 2), said("A3", 4), said("A2", 6), said("A4", 8, 9), said("A5", 8, 9), screen(30),
                  said("R7", 34)]
        result = a7(events)
        self.assertEqual((result.kind, result.flags), ("pass_direct", ("order_partially_checked",)))
        self.assertIn("in one segment, so not ordered: A4 and A5", result.reason)

    def test_unclear_audio_never_gives_a_clean_pass(self):
        head = header(clear=((0.0, 20.0),))
        self.assertEqual((a7(LECTURER, head).kind, a7(LECTURER, head).flags),
                         ("pass_direct", ("order_partially_checked",)))

    def test_a_misplacement_needs_clear_audio_where_the_correct_occurrence_would_be(self):
        """D-128: the swap at 2-4 s is judged on the audio there (0-7 s), not on the whole recording."""
        swapped = [said("A3", 2), said("A1", 4)] + LECTURER[2:]
        clear_there = a7(swapped, header(clear=((0.0, 20.0),)))
        self.assertEqual((clear_there.kind, clear_there.failure_code), ("fail", "wrong_order"))
        unclear_there = a7(swapped, header(clear=((10.0, 60.0),)))
        self.assertEqual((unclear_there.kind, unclear_there.flags), ("unable_to_verify", ("order_partially_checked",)))
        self.assertIn("said and not heard", unclear_there.reason)

    def test_a_low_confidence_command_in_the_right_place_blocks_the_fail(self):
        events = [said("A1", 1, event_id="weak", confidence=0.2), said("A3", 2), said("A1", 4)] + LECTURER[2:]
        result = a7(events)
        self.assertEqual((result.kind, result.flags), ("unable_to_verify", ("order_partially_checked",)))
        self.assertIn("low-confidence or unresolved", result.reason)

    def test_an_unresolved_resume_that_could_be_continue_blocks_the_fail(self):
        events = [said("A2", 1, event_id="early continue"), said("A1", 3), said("A3", 5), said("A4", 12), screen(30),
                  Event("resume_compressions_command", 29.5, 30.5, "audio", 0.9, event_id="resume",
                        metadata={"text": "x", "confidence_kind": "asr_proxy"}), said("R7", 35)]
        self.assertEqual(a7(events).kind, "unable_to_verify")
        without = [e for e in events if e.event_id != "resume"]
        self.assertEqual((a7(without).failure_code, a7(without).evidence), ("wrong_order", ("early continue",)))

    def test_an_unresolved_command_flags_a_pass(self):
        events = LECTURER + [Event("resume_compressions_command", 29.5, 30.5, "audio", 0.9, event_id="resume",
                                   metadata={"text": "x", "confidence_kind": "asr_proxy"})]
        self.assertEqual(a7(events).flags, ("order_partially_checked",))


class Catalogue(unittest.TestCase):
    def test_pending_until_approved(self):
        result = assess(LECTURER, load_rules_config(), header=header(), registry=discover())
        self.assertEqual(result.outcome("A7").kind, "pending")


if __name__ == "__main__":
    unittest.main()
