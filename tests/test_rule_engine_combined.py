"""Increment 28: the combined scenario matrix (audio_integration_plan.md section 8, scenarios 1-14, plus the
cross-modal OQ-078 case and a late gel).

Merged audio and video synthetic timelines, on the full configs/rules.yaml with every built rule approved except
A5 (OQ-075: the lecturer gave no shock command) and A8 (OQ-076: its end event), as in the demo; scenarios about A8
approve it too. For each scenario the exact set of failing rules is checked, so every mistake is reported by
exactly one rule (D-119, D-123).
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
ALL = ((0.0, 30.0),)


def config(held=("A5", "A8")):
    data = copy.deepcopy(CATALOGUE)
    for entry in data["rules"]:
        if entry["id"] not in held:
            entry["status"] = "approved"
    return RuleEngineConfig.from_dict(data)


CFG = config()
WITH_A8 = config(held=("A5",))

AUDIO = {"A1": "oxygen_away_command", "A3": "stand_clear_command", "A2": "continue_compressions_command",
         "CHARGE": "charging_command", "GELCMD": "gel_announcement_command", "A4": "stop_compressions_command",
         "A5": "shock_command", "START": "start_compressions_command", "RESUME": "resume_compressions_command"}
VIDEO = {"GEL": "Gel applied", "GEL2": "Gel applied", "TAKE1": "first_paddle_taken",
         "PLACE": "first_paddle_firmly_on_the_chest", "APICAL": "apical_paddle_placed", "TAKE2": "second_paddle_taken",
         "STERNAL": "sternal_paddle_placed", "FIRM": "paddles_firmly_on_chest", "PRESS": "both_paddle_buttons_pressed",
         "SHOCK": "shock_delivered_on_screen", "REMOVE": "paddles_removed_after_shock"}
LECTURER = {"A1": 2, "A3": 4, "A2": 6, "CHARGE": 8, "GEL": 10, "GEL2": 11.5, "GELCMD": 10, "A4": 13, "TAKE1": 15,
            "PLACE": 16, "APICAL": 16, "TAKE2": 17, "STERNAL": 17.5, "FIRM": 18, "PRESS": 19, "SHOCK": 20,
            "REMOVE": 21, "START": 23}


def event(key, t, end=None, confidence=0.9, event_id=None):
    name = key.split("#")[0]
    if name in AUDIO:
        return Event(AUDIO[name], t, end if end is not None else t + 1.0, "audio", confidence,
                     event_id=event_id or key, metadata={"text": "x", "confidence_kind": "asr_proxy"})
    return Event(VIDEO[name], t, t, "annotation", 1.0 if confidence == 0.9 else confidence, event_id=event_id or key,
                 camera_angle="LS")


def timeline(extra=(), **times):
    """The lecturer-like procedure (D-127; no shock command), a step moved by its key or dropped with None, plus
    extra events."""
    plan = {**LECTURER, **times}
    return [event(k, t) for k, t in plan.items() if t is not None] + list(extra)


def header(audio=ALL, video=ALL, screen=ALL, audio_run=True, zones=None):
    """Visibility in seconds: `video` for the zones and the paddles (`zones` overrides the placement zones)."""
    visibility = {f"region:{r}": video for r in ("apical_zone", "sternal_zone", "apical_paddle", "sternal_paddle")}
    if zones is not None:
        visibility.update({"region:apical_zone": zones, "region:sternal_zone": zones})
    visibility["region:screen"] = screen
    if audio is not None:
        visibility["region:audio"] = audio
    return TimelineHeader.from_dict({"camera_angle": "LS", "duration_seconds": 30.0,
                                     "analyses_run": {"video": True, "audio": audio_run},
                                     "visibility": {k: [list(s) for s in v] for k, v in visibility.items()}},
                                    regions=REGIONS)


def run(events, head=None, cfg=CFG):
    return assess(events, cfg, header=head if head is not None else header(), registry=discover())


def failing(result):
    return {o.rule_id for o in result.outcomes if o.kind == "fail"}


class Matrix(unittest.TestCase):
    def assertFails(self, result, expected):
        """Every mistake is reported by exactly one rule: the failing rules are exactly the expected ones."""
        self.assertEqual(failing(result), set(expected), {o.rule_id: (o.kind, o.reason[:90]) for o in result.outcomes
                                                          if o.kind == "fail"})

    # 1
    def test_01_the_lecturer_like_correct_procedure(self):
        result = run(timeline())
        self.assertFails(result, ())
        self.assertEqual(result.overall.result, "incomplete")   # timing not checked (unset limits), never a Fail
        for rule_id in ("R1", "R2", "R8", "R3", "R4", "R5", "R6", "A1", "A2", "A3", "A4", "R7", "A6", "A7", "S1"):
            self.assertEqual(result.outcome(rule_id).kind, "pass_direct", rule_id)

    # 2
    def test_02_one_misplaced_step_stand_clear_after_the_press(self):
        """Stand clear after the button press, still before the shock: A3 passes (before the shock); in the
        lecturer's order it comes before continue, so A7 (its audio relations) reports it, once."""
        result = run(timeline(A3=19.2))
        self.assertFails(result, {"A7"})
        self.assertIn("A3 (stand_clear_command at 19.2 s) is out of order", result.outcome("A7").reason)
        self.assertEqual(result.outcome("A3").kind, "pass_direct")

    # 3
    def test_03_two_steps_swapped(self):
        result = run(timeline(A1=4, A3=2))
        self.assertFails(result, {"A7"})
        self.assertIn("(one mistake)", result.outcome("A7").reason)

    def test_03b_a_cross_modal_swap_is_s1s(self):
        result = run(timeline(A4=16.5, TAKE1=15, PLACE=18, APICAL=18, TAKE2=19, STERNAL=19.5, FIRM=20, PRESS=21,
                              SHOCK=22, REMOVE=23, START=25))
        self.assertFails(result, {"S1"})
        self.assertIn("A4 (stop_compressions_command at 16.5 s) and R2A", result.outcome("S1").reason)

    # 4
    def test_04_a_missing_step(self):
        """No stop, the audio clear: A4 fails missing; A8 is not evaluable because of A4; S1 doesn't fail."""
        result = run(timeline(A4=None), cfg=WITH_A8)
        self.assertFails(result, {"A4"})
        self.assertEqual(result.outcome("A4").failure_code, "missing")
        self.assertEqual((result.outcome("A8").kind, result.outcome("A8").blocked_by), ("not_evaluable", "A4"))

    # 5
    def test_05_an_unseen_step(self):
        """Stop said outside the clear-audio intervals: A4 Unable to Verify; S1 and A7 flagged partial."""
        result = run(timeline(A4=None), header(audio=((0.0, 12.0), (14.5, 30.0))))
        self.assertFails(result, ())
        self.assertEqual(result.outcome("A4").kind, "unable_to_verify")
        for rule_id in ("S1", "A7"):
            self.assertIn("order_partially_checked", result.outcome(rule_id).flags, rule_id)

    # 6
    def test_06_no_audio(self):
        video_only = [e for e in timeline() if e.source != "audio"]
        result = run(video_only, header(audio=None, audio_run=False))
        self.assertFails(result, ())
        for rule_id in ("A1", "A2", "A3", "A4", "R7", "A7"):
            self.assertEqual(result.outcome(rule_id).kind, "unable_to_verify", rule_id)
        self.assertEqual(result.outcome("S1").flags, ("order_partially_checked",))   # the video steps only

    def test_06b_audio_without_clear_intervals(self):
        result = run(timeline(), header(audio=None))
        self.assertFails(result, ())
        self.assertIn("order_partially_checked", result.outcome("S1").flags)

    # 7
    def test_07_no_shock_seen(self):
        """A1 and A3 are not evaluable because of R5 with presence still checked; resume commands stay unresolved."""
        events = timeline(SHOCK=None, START=None, extra=[event("RESUME", 23)])
        result = run(events, header(screen=()))
        self.assertFails(result, ())
        for rule_id in ("A1", "A3", "R7"):
            self.assertEqual((result.outcome(rule_id).kind, result.outcome(rule_id).blocked_by), ("not_evaluable", "R5"))
        self.assertEqual(result.outcome("R5").kind, "unable_to_verify")

    # 8
    def test_08_timing_noise_near_the_cross_modal_tolerance(self):
        """Stop 0.9 s and 1.1 s after the first paddle taken (tolerance 1.0 s): first a tie, then misplaced."""
        tie = run(timeline(A4=15.9, PLACE=18, APICAL=18, TAKE2=19, STERNAL=19.5, FIRM=20, PRESS=21, SHOCK=22,
                           REMOVE=23, START=25))
        late = run(timeline(A4=16.1, PLACE=18, APICAL=18, TAKE2=19, STERNAL=19.5, FIRM=20, PRESS=21, SHOCK=22,
                            REMOVE=23, START=25))
        self.assertFails(tie, ())
        self.assertFails(late, {"S1"})

    # 9
    def test_09_repeated_commands(self):
        result = run(timeline(extra=[event("A3#late", 19.2, event_id="A3 late")]))
        self.assertFails(result, ())

    # 10
    def test_10_low_confidence_commands(self):
        """A low-confidence stop is excluded: unseen, never a Fail."""
        result = run(timeline(A4=None, extra=[event("A4", 13, confidence=0.1, event_id="weak stop")]))
        self.assertFails(result, ())
        self.assertEqual(result.outcome("A4").kind, "unable_to_verify")
        self.assertIn("order_partially_checked", result.outcome("S1").flags)

    # 11
    def test_11_two_commands_in_one_segment(self):
        """"Stop compressions, shocking" in one Whisper segment: their mutual order isn't checked, never a Fail."""
        result = run(timeline(A4=None, extra=[event("A4", 13, 14), event("A5", 13, 14)]))
        self.assertFails(result, ())
        self.assertIn("order_partially_checked", result.outcome("A7").flags)

    # 12
    def test_12_segment_timing_near_a_limit(self):
        """A8 (5 s, approved, end event start): a pause of 4 to 6 s is Unable to Verify, timing_uncertain."""
        events = timeline(A4=None, START=None, extra=[event("A4", 13.5, 14.5), event("START", 18.5, 19.5)],
                          PRESS=None, SHOCK=16, REMOVE=17, FIRM=15.5, TAKE1=14, PLACE=14.5, APICAL=14.5, TAKE2=14.8,
                          STERNAL=15)
        result = run(events, cfg=WITH_A8)
        a8 = result.outcome("A8")
        self.assertEqual((a8.kind, a8.flags), ("unable_to_verify", ("timing_uncertain",)))

    # 13: the cross-modal OQ-078 case
    BRIDGE = dict(CHARGE=16.5, GEL=None, GEL2=None, GELCMD=None, A4=None)   # charging after the first take (15 s)

    def test_13_stop_missing_charging_after_the_first_take(self):
        """The audio clear and no stop: A4 fails missing (its own mistake); S1 judges charging -> first take."""
        result = run(timeline(**self.BRIDGE), header(zones=((14.0, 30.0),)))   # the gel phase out of view
        self.assertFails(result, {"S1", "A4"})
        self.assertEqual(result.outcome("A4").failure_code, "missing")

    def test_13a_stop_unseen_low_confidence_only_s1_fails(self):
        """The OQ-078 case with the stop unseen (heard only with low confidence, the audio clear): A4 is Unable
        to Verify; the relation bridging the unseen gel phase and stop is S1's, and only S1 fails."""
        weak = event("A4", 13, confidence=0.1, event_id="weak stop")
        result = run(timeline(extra=[weak], **self.BRIDGE), header(zones=((14.0, 30.0),)))
        self.assertFails(result, {"S1"})
        self.assertEqual(result.outcome("A4").kind, "unable_to_verify")
        self.assertIn("CHARGE (charging_command at 16.5 s) and R2A", result.outcome("S1").reason)

    def test_13b_stop_unseen_in_unclear_audio_is_unable_everywhere(self):
        """The stop unseen because the audio was unclear around it (12-14.5 s): A4 is Unable to Verify (D-122).
        That gap lies where a correct "charging" would have been (continue 6 s -> first take 15 s), so S1 can't
        fail either (D-128): no rule fails."""
        result = run(timeline(**self.BRIDGE), header(audio=((0.0, 12.0), (14.5, 30.0)), zones=((14.0, 30.0),)))
        self.assertFails(result, ())
        self.assertEqual(result.outcome("A4").kind, "unable_to_verify")
        self.assertEqual(result.outcome("S1").kind, "unable_to_verify")
        self.assertIn("correct_occurrence_unseen", result.outcome("S1").flags)

    def test_13c_charging_after_stop_is_a7s(self):
        events = timeline(CHARGE=14, GEL=None, GEL2=None, GELCMD=None, A4=11, TAKE1=16, PLACE=17, APICAL=17,
                          TAKE2=18, STERNAL=18.5, FIRM=19, PRESS=20, SHOCK=21, REMOVE=22, START=24)
        result = run(events, header(zones=((16.5, 30.0),)))
        self.assertIn("A7", failing(result))
        self.assertNotIn("S1", failing(result))

    # 14
    def test_14_a_late_gel_fails_only_r1(self):
        result = run(timeline(GEL=17.2, GEL2=18.4))
        self.assertFails(result, {"R1"})
        self.assertEqual(result.outcome("R1").failure_code, "after_placement")
        self.assertIn("reported by their own rule: R1", result.outcome("S1").reason)


if __name__ == "__main__":
    unittest.main()
