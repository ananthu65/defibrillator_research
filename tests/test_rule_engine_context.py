"""Procedure context tests. The shock time comes only from the screen; a paddle removal is never
taken as a shock or its time (D-093, D-115)."""
import copy
import unittest

import yaml

from pipeline.config import ROOT
from rules.config import EngineSettings, load_rules_config
from rules.context import build_context
from rules.coverage import TimelineHeader
from rules.errors import ConfigError
from rules.prepare import prepare_timeline
from schemas.event import Event

CONFIG = load_rules_config()  # simultaneous_window_seconds = 0.5 (placeholder)


def ev(name, t, source="annotation", confidence=1.0, event_id=None, end=None):
    return Event(name, t, t if end is None else end, source, confidence, event_id=event_id or f"{name}@{t}")


def cmd(name, t, event_id=None, confidence=0.9):
    return ev(name, t, "audio", confidence, event_id, end=t + 1)


def context(events, header=None, config=CONFIG):
    head = None if header is None else TimelineHeader.from_dict(header, regions=tuple(config.engine.regions))
    return build_context(prepare_timeline(events, config), config, head)


SHOCK = ev("shock_delivered_on_screen", 30, event_id="shock")
REMOVAL = ev("paddles_removed_after_shock", 33, event_id="removal")


class ShockTime(unittest.TestCase):
    def test_shock_on_screen_is_the_shock_time(self):
        shock = context([SHOCK, REMOVAL]).shock
        self.assertEqual((shock.time, shock.event_id, shock.event_name, shock.flags),
                         (30, "shock", "shock_delivered_on_screen", ()))

    def test_no_shock_at_all(self):
        ctx = context([ev("Gel applied", 1)])
        self.assertIsNone(ctx.shock.time)
        self.assertEqual(ctx.shock.flags, ("no_shock",))
        self.assertIsNone(ctx.phase_of(10))

    def test_multiple_shocks_give_no_shock_time(self):
        ctx = context([ev("shock_delivered_on_screen", 30, event_id="s1"),
                       ev("shock_delivered_on_screen", 60, event_id="s2"), REMOVAL])
        self.assertFalse(ctx.shock.present)  # not guessed, even though a removal exists
        self.assertEqual((ctx.shock.flags, ctx.shock.candidates), (("multiple_shocks",), ("s1", "s2")))
        self.assertIsNone(ctx.phase_of(45))
        elapsed = ctx.elapsed("shock", "first_placement")
        self.assertIsNone(elapsed.seconds)
        self.assertIn("multiple_shocks", elapsed.flags)

    def test_low_confidence_shock_is_not_the_shock_time(self):
        ctx = context([ev("shock_delivered_on_screen", 30, "video", 0.1), REMOVAL])
        self.assertFalse(ctx.shock.present)   # and the removal never stands in for it (D-115)

    def test_phases(self):
        ctx = context([SHOCK])
        self.assertEqual([ctx.phase_of(t) for t in (10, 30, 50)], ["before_shock", "at_shock", "after_shock"])


class ShockTimeOnlyFromTheScreen(unittest.TestCase):
    """D-093, D-115: the shock time is never inferred, and there is no setting to infer it."""

    def test_there_is_no_fallback_setting(self):
        data = copy.deepcopy(yaml.safe_load((ROOT / "configs/rule_engine/engine.yaml").read_text(encoding="utf-8")))
        self.assertNotIn("shock_time_fallback", data)
        data["shock_time_fallback"] = {"value": "removal"}
        with self.assertRaises(ConfigError):
            EngineSettings.from_dict(data)

    def test_no_shock_on_screen_means_no_shock_time_even_with_a_removal(self):
        ctx = context([REMOVAL, ev("Gel applied", 1)])
        self.assertFalse(ctx.shock.present)
        self.assertEqual(ctx.shock.flags, ("no_shock",))
        self.assertIn("never inferred", ctx.shock.reason)
        self.assertIsNone(ctx.phase_of(40))
        self.assertIsNone(ctx.elapsed("shock", "first_placement").seconds)

    def test_the_shock_on_screen_is_still_the_shock_time(self):
        self.assertEqual(context([SHOCK, REMOVAL]).shock.time, 30)

    def test_resume_commands_stay_unresolved_and_start_commands_are_ambiguous(self):
        ctx = context([REMOVAL, cmd("resume_compressions_command", 20, "r1"),
                       cmd("start_compressions_command", 40, "s1")])
        self.assertEqual([(r.event_id, r.resolved_to, r.flags) for r in ctx.resolutions], [("r1", None, ("no_shock_time",))])
        start = ctx.anchor("start_compressions")
        self.assertFalse(start.present)
        self.assertEqual(start.ambiguous, ("s1",))   # not a mistake (D-054)

    def test_a_low_confidence_shock_on_screen_does_not_become_the_removal(self):
        ctx = context([ev("shock_delivered_on_screen", 30, "video", 0.1), REMOVAL])
        self.assertFalse(ctx.shock.present)

class CommandResolution(unittest.TestCase):
    def resolution(self, ctx, event_id):
        return next(r for r in ctx.resolutions if r.event_id == event_id)

    def test_before_shock_is_continue_and_after_is_start(self):
        ctx = context([SHOCK, cmd("resume_compressions_command", 10, "r1"), cmd("resume_compressions_command", 35, "r2")])
        self.assertEqual(self.resolution(ctx, "r1").resolved_to, "continue_compressions_command")
        self.assertEqual(self.resolution(ctx, "r2").resolved_to, "start_compressions_command")
        self.assertEqual([e.event_id for e in ctx.named("continue_compressions_command")], ["r1"])
        self.assertEqual(ctx.anchor("start_compressions").event_id, "r2")
        resolved = ctx.named("start_compressions_command")[0]
        self.assertEqual(resolved.metadata["source_label"], "resume_compressions_command")  # original kept
        self.assertEqual(resolved.metadata["shock_time"], 30)

    def test_command_within_the_window_of_the_shock_is_left_unresolved(self):
        for t in (29.5, 30.0, 30.4):
            with self.subTest(t=t):
                ctx = context([SHOCK, cmd("resume_compressions_command", t, "r")])
                resolution = self.resolution(ctx, "r")
                self.assertIsNone(resolution.resolved_to)
                self.assertEqual(resolution.flags, ("command_near_shock",))
                self.assertEqual(ctx.named("resume_compressions_command")[0].event_id, "r")
                self.assertEqual(ctx.named("start_compressions_command"), [])

    def test_command_just_outside_the_window_is_resolved(self):
        ctx = context([SHOCK, cmd("resume_compressions_command", 30.6, "r")])
        self.assertEqual(self.resolution(ctx, "r").resolved_to, "start_compressions_command")

    def test_no_shock_leaves_commands_unresolved_and_flagged(self):
        ctx = context([cmd("resume_compressions_command", 10, "r")])
        self.assertIsNone(self.resolution(ctx, "r").resolved_to)
        self.assertEqual(self.resolution(ctx, "r").flags, ("no_shock_time",))

    def test_multiple_shocks_leave_commands_unresolved(self):
        ctx = context([ev("shock_delivered_on_screen", 30, event_id="s1"), ev("shock_delivered_on_screen", 60, event_id="s2"),
                       cmd("resume_compressions_command", 45, "r")])
        self.assertEqual(self.resolution(ctx, "r").flags, ("no_shock_time",))

    def test_unresolved_commands_flag_the_continue_and_start_anchors(self):
        ctx = context([SHOCK, cmd("resume_compressions_command", 30.2, "r"), cmd("start_compressions_command", 40, "s")])
        self.assertEqual(ctx.anchor("start_compressions").event_id, "s")  # explicit command still used
        self.assertIn("unresolved_commands", ctx.anchor("start_compressions").flags)
        self.assertIn("unresolved_commands", ctx.anchor("continue_compressions").flags)
        self.assertNotIn("unresolved_commands", ctx.anchor("stop_compressions").flags)

    def test_with_a_real_shock_commands_before_it_are_still_continue(self):
        ctx = context([SHOCK, REMOVAL, cmd("resume_compressions_command", 25, "r")])
        self.assertEqual(self.resolution(ctx, "r").resolved_to, "continue_compressions_command")

    def test_explicit_command_names_are_not_reclassified(self):
        ctx = context([SHOCK, cmd("start_compressions_command", 10, "s")])  # said before the shock: a rule's problem
        self.assertEqual(ctx.named("start_compressions_command")[0].event_id, "s")
        self.assertEqual(ctx.resolutions, ())


class Anchors(unittest.TestCase):
    def test_multiple_candidates_use_the_earliest_and_record_all(self):
        ctx = context([ev("first_paddle_firmly_on_the_chest", 14, event_id="p2"),
                       ev("first_paddle_firmly_on_the_chest", 12, event_id="p1"),
                       ev("first_paddle_firmly_on_the_chest", 16, event_id="p3")])
        anchor = ctx.anchor("first_placement")
        self.assertEqual((anchor.time, anchor.event_id, anchor.candidates), (12, "p1", ("p1", "p2", "p3")))
        self.assertEqual(anchor.flags, ("multiple_candidates",))

    def test_single_candidate_has_no_flag(self):
        anchor = context([ev("first_paddle_firmly_on_the_chest", 12, event_id="p1")]).anchor("first_placement")
        self.assertEqual((anchor.candidates, anchor.flags), (("p1",), ()))

    def test_per_paddle_placement_anchors(self):
        ctx = context([ev("apical_paddle_placed", 12, event_id="a"), ev("sternal_paddle_placed", 15, event_id="s")])
        self.assertEqual((ctx.anchor("apical_placement").time, ctx.anchor("sternal_placement").time), (12, 15))

    def test_absent_anchor_explains_itself(self):
        anchor = context([SHOCK]).anchor("stop_compressions")
        self.assertFalse(anchor.present)
        self.assertEqual(anchor.reason, "no confident stop_compressions_command event")

    def test_absent_anchor_with_low_confidence_evidence_is_flagged(self):
        anchor = context([SHOCK, cmd("stop_compressions_command", 20, confidence=0.1)]).anchor("stop_compressions")
        self.assertEqual((anchor.present, anchor.flags), (False, ("low_confidence_evidence",)))

    def test_stop_to_start_elapsed(self):
        ctx = context([SHOCK, cmd("stop_compressions_command", 27), cmd("start_compressions_command", 31)])
        self.assertEqual(ctx.elapsed("stop_compressions", "start_compressions").seconds, 4)


class StartAnchor(unittest.TestCase):
    """D-025 (OQ-030): the restart is the earliest start command after the shock."""

    def test_earliest_start_after_the_shock(self):
        anchor = context([SHOCK, cmd("start_compressions_command", 36, "late"),
                          cmd("start_compressions_command", 33, "early")]).anchor("start_compressions")
        self.assertEqual((anchor.event_id, anchor.candidates), ("early", ("early", "late")))
        self.assertIn("multiple_candidates", anchor.flags)

    def test_start_before_the_shock_does_not_count(self):
        anchor = context([SHOCK, cmd("start_compressions_command", 10, "pre"),
                          cmd("start_compressions_command", 35, "post")]).anchor("start_compressions")
        self.assertEqual((anchor.event_id, anchor.ineligible), ("post", ("pre",)))
        self.assertEqual(anchor.flags, ("start_command_before_shock",))  # for A7 to report as a sequence problem

    def test_start_only_before_the_shock_leaves_the_anchor_absent(self):
        ctx = context([SHOCK, cmd("start_compressions_command", 10, "pre")])
        anchor = ctx.anchor("start_compressions")
        self.assertFalse(anchor.present)
        self.assertEqual((anchor.ineligible, anchor.flags), (("pre",), ("start_command_before_shock",)))
        self.assertEqual([e.event_id for e in ctx.named("start_compressions_command")], ["pre"])  # still visible

    def test_start_exactly_at_the_shock_does_not_count(self):
        anchor = context([SHOCK, cmd("start_compressions_command", 30, "at")]).anchor("start_compressions")
        self.assertEqual((anchor.present, anchor.ineligible), (False, ("at",)))

    def test_no_shock_time_means_no_start_anchor(self):
        for timeline, shock_flag in (([cmd("start_compressions_command", 35, "s")], "no_shock"),
                                     ([ev("shock_delivered_on_screen", 30, event_id="s1"),
                                       ev("shock_delivered_on_screen", 60, event_id="s2"),
                                       cmd("start_compressions_command", 35, "s")], "multiple_shocks")):
            with self.subTest(shock_flag=shock_flag):
                anchor = context(timeline).anchor("start_compressions")
                self.assertFalse(anchor.present)
                self.assertEqual(anchor.flags, ("no_shock_time", shock_flag))
                # D-054: timing unknown, so ambiguous, not a sequence mistake for A7
                self.assertEqual((anchor.ambiguous, anchor.ineligible), (("s",), ()))

    def test_each_start_command_is_checked_on_its_own(self):
        # (e2): the later start after the shock is still the restart when an earlier one does not count
        anchor = context([SHOCK, cmd("start_compressions_command", 20, "pre"), cmd("start_compressions_command", 31, "post"),
                          cmd("start_compressions_command", 40, "late")]).anchor("start_compressions")
        self.assertEqual((anchor.event_id, anchor.candidates, anchor.ineligible), ("post", ("post", "late"), ("pre",)))

    def test_with_a_shock_on_screen_a_resume_before_it_is_continue_not_ambiguous(self):
        anchor = context([SHOCK, cmd("resume_compressions_command", 20, "r"),
                          cmd("start_compressions_command", 35, "s")]).anchor("start_compressions")
        self.assertEqual((anchor.event_id, anchor.ambiguous, anchor.flags), ("s", (), ()))

    def test_with_a_shock_on_screen_a_start_before_it_is_still_a_mistake(self):
        anchor = context([SHOCK, REMOVAL, cmd("start_compressions_command", 25, "pre")]).anchor("start_compressions")
        self.assertEqual((anchor.ineligible, anchor.ambiguous), (("pre",), ()))
        self.assertEqual(anchor.flags, ("start_command_before_shock",))

    def test_weak_start_after_the_shock_is_flagged_low_confidence(self):
        anchor = context([SHOCK, cmd("start_compressions_command", 35, confidence=0.1)]).anchor("start_compressions")
        self.assertEqual((anchor.present, anchor.flags), (False, ("low_confidence_evidence",)))


class ZoneVisibility(unittest.TestCase):
    def test_no_header_means_unknown(self):
        self.assertEqual({r: s.status for r, s in context([SHOCK]).zone_visibility.items()},
                         {"apical_zone": "unknown", "sternal_zone": "unknown", "screen": "unknown", "apical_paddle": "unknown", "sternal_paddle": "unknown",
                          "apical_gel": "unknown", "sternal_gel": "unknown"})

    def test_header_region_coverage(self):
        ctx = context([SHOCK], {"analyses_run": {"video": True}, "coverage": {"region:sternal_zone": "not_covered"}})
        self.assertEqual(ctx.zone_visibility["sternal_zone"].status, "not_covered")
        self.assertEqual(ctx.zone_visibility["apical_zone"].status, "covered")


class LowConfidenceResumeCommands(unittest.TestCase):
    HEADER = {"analyses_run": {"video": True, "audio": True}}

    def test_weak_resume_after_shock_makes_missing_start_unverifiable(self):
        ctx = context([SHOCK, cmd("resume_compressions_command", 35, "weak", confidence=0.2)], self.HEADER)
        result = ctx.missing("start_compressions_command")
        self.assertEqual((result.outcome, result.flags, result.low_confidence_event_ids),
                         ("unable_to_verify", ("low_confidence_evidence",), ("weak",)))
        self.assertEqual(ctx.coverage.missing("start_compressions_command").outcome, "fail")  # why the context wraps it

    def test_weak_resume_before_shock_does_not_count_for_start(self):
        ctx = context([SHOCK, cmd("resume_compressions_command", 10, "weak", confidence=0.2)], self.HEADER)
        self.assertEqual(ctx.missing("start_compressions_command").outcome, "fail")
        self.assertEqual(ctx.missing("continue_compressions_command").outcome, "unable_to_verify")

    def test_weak_resume_near_shock_could_be_either(self):
        ctx = context([SHOCK, cmd("resume_compressions_command", 30.2, "weak", confidence=0.2)], self.HEADER)
        for name in ("start_compressions_command", "continue_compressions_command"):
            with self.subTest(name=name):
                self.assertEqual(ctx.missing(name).outcome, "unable_to_verify")

    def test_unrelated_events_are_unaffected(self):
        ctx = context([SHOCK, cmd("resume_compressions_command", 35, "weak", confidence=0.2)], self.HEADER)
        self.assertEqual(ctx.missing("stand_clear_command").outcome, "fail")


class RepeatedAndOrdered(unittest.TestCase):
    def test_context_events_keep_every_event_in_time_order(self):
        timeline = [SHOCK, cmd("resume_compressions_command", 35, "r2"), ev("Gel applied", 2, event_id="g1"),
                    ev("Gel applied", 5, event_id="g2"), cmd("resume_compressions_command", 10, "r1")]
        ctx = context(timeline)
        self.assertEqual([e.event_id for e in ctx.events], ["g1", "g2", "r1", "shock", "r2"])


if __name__ == "__main__":
    unittest.main()
