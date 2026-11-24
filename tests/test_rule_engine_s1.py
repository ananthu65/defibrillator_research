"""Increment 27: S1, the procedure order (P-046; D-120, D-123, D-126, D-128; OQ-078).

The full configs/rules.yaml with S1 (and, where stated, the other built rules) approved (testing practice,
methods.md). The order is the interim one in procedure_order.yaml (NOT clinically approved, OQ-062). Synthetic
timelines only.
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
ALL = ((0.0, 30.0),)
HELD = ("A5", "A8")   # pending here as in the demo: no shock command is said (OQ-075); A8's end event (OQ-076)


def config(*approve):
    data = copy.deepcopy(CATALOGUE)
    for entry in data["rules"]:
        if entry["id"] in approve:
            entry["status"] = "approved"
    return RuleEngineConfig.from_dict(data)


S1_ONLY = config("S1")
ALL_BUILT = config(*[r["id"] for r in CATALOGUE["rules"] if r["id"] not in HELD])


def said(name, start, end=None, event_id=None):
    return Event(name, start, end if end is not None else start + 1.0, "audio", 0.9,
                 event_id=event_id or f"{name}@{start:g}", metadata={"text": "x", "confidence_kind": "asr_proxy"})


def tag(label, t, event_id=None):
    return Event(label, t, t, "annotation", 1.0, event_id=event_id or f"{label}@{t:g}", camera_angle="LS")


def procedure(**times):
    """A lecturer-like procedure (D-127): oxygen away, stand clear, continue, charging, the gel phase with "applying
    gel", stop, the paddles, the shock, removal, start (no shock command). Override a step's time by its key, or
    drop it with None."""
    plan = {"A1": 2, "A3": 4, "A2": 6, "CHARGE": 8, "GEL": 10, "GEL2": 11.5, "GELCMD": 10, "A4": 13, "TAKE1": 15,
            "PLACE": 16, "TAKE2": 17, "FIRM": 18, "PRESS": 19, "SHOCK": 20, "REMOVE": 21, "START": 23, **times}
    audio = {"A1": "oxygen_away_command", "A3": "stand_clear_command", "A2": "continue_compressions_command",
             "CHARGE": "charging_command", "GELCMD": "gel_announcement_command", "A4": "stop_compressions_command",
             "START": "start_compressions_command", "A5": "shock_command"}
    video = {"GEL": "Gel applied", "GEL2": "Gel applied", "TAKE1": "first_paddle_taken",
             "PLACE": "first_paddle_firmly_on_the_chest", "TAKE2": "second_paddle_taken", "FIRM": "paddles_firmly_on_chest",
             "PRESS": "both_paddle_buttons_pressed", "SHOCK": "shock_delivered_on_screen",
             "REMOVE": "paddles_removed_after_shock"}
    events = []
    for key, t in plan.items():
        if t is None:
            continue
        events.append(said(audio[key], t, event_id=key) if key in audio else tag(video[key], t, event_id=key))
    return events


def header(audio=ALL, zones=ALL, paddles=ALL, screen=ALL):
    visibility = {"region:apical_zone": zones, "region:sternal_zone": zones, "region:apical_paddle": paddles,
                  "region:sternal_paddle": paddles, "region:screen": screen, "region:audio": audio}
    return TimelineHeader.from_dict({"camera_angle": "LS", "duration_seconds": 30.0,
                                     "analyses_run": {"video": True, "audio": True},
                                     "visibility": {k: [list(s) for s in v] for k, v in visibility.items()}},
                                    regions=REGIONS)


def run(events, head=None, cfg=S1_ONLY):
    return assess(events, cfg, header=head if head is not None else header(), registry=discover())


def s1(events, head=None, cfg=S1_ONLY):
    return run(events, head, cfg).outcome("S1")


def failing(result):
    return {o.rule_id for o in result.outcomes if o.kind == "fail"}


class Order(unittest.TestCase):
    def test_the_lecturer_like_procedure_passes_cleanly(self):
        result = s1(procedure())
        self.assertEqual((result.kind, result.flags), ("pass_direct", ()))
        for relation in ("CHARGE->R1", "R1->A4", "A4->R2A", "R2B->R3", "R6->R7"):   # D-126 option B
            self.assertIn(relation, result.reason)

    def test_stop_after_the_first_paddle_is_taken_is_s1s_mistake_alone(self):
        events = procedure(A4=16.5, PLACE=18, TAKE2=19, FIRM=20, PRESS=21, SHOCK=22, REMOVE=23, START=25)
        result = run(events, cfg=ALL_BUILT)
        s1_result = result.outcome("S1")
        self.assertEqual((s1_result.kind, s1_result.failure_code), ("fail", "wrong_order"))
        self.assertIn("A4 (stop_compressions_command at 16.5 s) and R2A (first_paddle_taken at 15 s) are in the wrong "
                      "order (one mistake)", s1_result.reason)
        self.assertEqual(failing(result), {"S1"})   # no other rule reports it (D-123)

    def test_a_tie_within_the_cross_modal_tolerance_is_not_ordered(self):
        self.assertEqual(s1(procedure(A4=14.2)).kind, "pass_direct")   # stop 14.2-15.2 s, take at 15 s

    def test_the_gel_phase_is_interchangeable_and_optional_steps_need_not_be_said(self):
        self.assertEqual(s1(procedure(GELCMD=12)).kind, "pass_direct")                    # "applying gel" after the gel
        self.assertEqual(s1(procedure(CHARGE=None, GELCMD=None)).kind, "pass_direct")

    def test_the_shock_command_against_the_shocking_actions_stays_unordered(self):
        """OQ-075: A5 between the take and the placement is not S1's to judge."""
        self.assertEqual(s1([*procedure(), said("shock_command", 15.2, 15.4, "A5")]).kind, "pass_direct")


class BridgingRelations(unittest.TestCase):
    """OQ-078: S1 derives its relations from the observed steps, so a relation across a missing or unseen step is
    judged once, by S1 unless another rule owns it."""

    def test_charging_after_the_first_take_with_the_gel_phase_and_stop_unseen_is_s1s(self):
        events = procedure(CHARGE=16.5, GEL=None, GEL2=None, GELCMD=None, A4=None)
        head = header(zones=((14.0, 30.0),))   # the gel phase out of view
        result = run(events, head, ALL_BUILT)
        s1_result = result.outcome("S1")
        self.assertEqual((s1_result.kind, s1_result.failure_code), ("fail", "wrong_order"))
        self.assertIn("CHARGE (charging_command at 16.5 s) and R2A", s1_result.reason)
        self.assertIn("order_partially_checked", s1_result.flags)   # the gel phase unseen
        self.assertNotIn("A7", failing(result))

    def test_charging_after_stop_with_the_gel_phase_unseen_is_a7s_not_s1s(self):
        """Both are audio commands: charging -> stop is A7's relation (its audio scope), so A7 reports it, once."""
        events = procedure(CHARGE=14, GEL=None, GEL2=None, GELCMD=None, A4=11, TAKE1=16, PLACE=17, TAKE2=18,
                           FIRM=19, PRESS=20, SHOCK=21, REMOVE=22, START=24)
        result = run(events, header(zones=((16.5, 30.0),)), ALL_BUILT)
        self.assertEqual(result.outcome("A7").failure_code, "wrong_order")
        self.assertNotEqual(result.outcome("S1").kind, "fail")

    def test_a_step_misplaced_on_another_rules_relation_is_left_to_that_rule(self):
        """Gel only after the placement breaks R1 -> PLACE (R1's); S1 doesn't also fail it for R1 -> stop."""
        events = procedure(GEL=17.2, GEL2=18.4)   # beyond the annotation-lag window after the placement (16 s)
        result = run(events, cfg=ALL_BUILT)
        self.assertEqual(result.outcome("R1").failure_code, "after_placement")
        self.assertEqual(result.outcome("S1").kind, "pass_direct")
        self.assertIn("reported by their own rule: R1 (R1)", result.outcome("S1").reason)
        self.assertEqual(failing(result), {"R1"})


class Evidence(unittest.TestCase):
    def test_a_misplaced_step_whose_window_was_not_clear_is_unable_to_verify(self):
        """D-128: stop's correct place (after the gel, 10 s, before the take, 15 s) was not clearly heard."""
        events = procedure(A4=16.5, PLACE=18, TAKE2=19, FIRM=20, PRESS=21, SHOCK=22, REMOVE=23, START=25)
        result = s1(events, header(audio=((0.0, 12.0), (16.0, 30.0))))
        self.assertEqual(result.kind, "unable_to_verify")
        self.assertIn("correct_occurrence_unseen", result.flags)
        self.assertIn("A4 from 10 s to 15 s", result.reason)

    def test_unseen_steps_never_give_a_clean_pass(self):
        result = s1(procedure(A2=None), header(audio=((0.0, 5.0), (7.0, 30.0))))   # continue not heard, audio unclear
        self.assertEqual((result.kind, result.flags), ("pass_direct", ("order_partially_checked",)))

    def test_fewer_than_two_observed_steps_is_unable_to_verify(self):
        self.assertEqual(s1([said("oxygen_away_command", 2)]).kind, "unable_to_verify")


class Catalogue(unittest.TestCase):
    def test_pending_in_rules_yaml_and_held_back_in_the_demo(self):
        self.assertEqual(run(procedure(), cfg=load_rules_config()).outcome("S1").kind, "pending")
        entry = next(r for r in demo.load_rules_config(demo.DEMO_CONFIG).rules if r.id == "S1")
        self.assertEqual(entry.status, "pending")

    def test_s1_owns_no_relation_another_rule_owns(self):
        order = S1_ONLY.procedure_order
        self.assertEqual({r.owner for r in order.relations} - {None, "S1"},
                         {"R1", "R2", "R3", "R4", "R6", "A1", "A2", "A3", "A4", "A5", "R7", "A7"})


if __name__ == "__main__":
    unittest.main()
