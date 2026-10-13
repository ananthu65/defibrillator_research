import unittest

from rules.config import load_rules_config
from rules.context import build_context
from rules.coverage import TimelineHeader
from rules.prepare import prepare_timeline
from schemas.event import Event

CONFIG = load_rules_config()  # simultaneous_window_seconds = 0.5 (placeholder)


def ev(name, t, source="annotation", confidence=1.0, event_id=None, end=None):
    return Event(name, t, t if end is None else end, source, confidence, event_id=event_id or f"{name}@{t}")


def cmd(name, t, event_id=None, confidence=0.9):
    return ev(name, t, "audio", confidence, event_id, end=t + 1)


def context(events, header=None):
    head = None if header is None else TimelineHeader.from_dict(header, regions=tuple(CONFIG.engine.regions))
    return build_context(prepare_timeline(events, CONFIG), CONFIG, head)


SHOCK = ev("shock_delivered_on_screen", 30, event_id="shock")
REMOVAL = ev("paddles_removed_after_shock", 33, event_id="removal")


class ShockTime(unittest.TestCase):
    def test_shock_on_screen_is_the_shock_time(self):
        shock = context([SHOCK, REMOVAL]).shock
        self.assertEqual((shock.time, shock.event_id, shock.event_name, shock.flags),
                         (30, "shock", "shock_delivered_on_screen", ()))

    def test_fallback_to_removal_is_recorded_and_flagged(self):
        shock = context([REMOVAL]).shock
        self.assertEqual((shock.time, shock.event_id, shock.event_name), (33, "removal", "paddles_removed_after_shock"))
        self.assertEqual(shock.flags, ("shock_time_from_removal",))
        self.assertIn("after the shock", shock.reason)

    def test_every_timing_result_using_the_fallback_is_flagged(self):
        ctx = context([REMOVAL, cmd("start_compressions_command", 35, "start"), cmd("stop_compressions_command", 25, "stop")])
        to_start = ctx.elapsed("shock", "start_compressions")
        self.assertEqual(to_start.seconds, 2)
        self.assertIn("shock_time_from_removal", to_start.flags)
        self.assertIn("shock_time_from_removal", ctx.elapsed("stop_compressions", "shock").flags)
        # D-059: no start or resume before the removal, so the restart is certain; stop -> start (A8)
        # does not depend on the shock time and carries no fallback flag
        self.assertNotIn("shock_time_from_removal", ctx.elapsed("stop_compressions", "start_compressions").flags)
        self.assertNotIn("shock_time_from_removal", ctx.elapsed("first_placement", "stop_compressions").flags)

    def test_multiple_removals_without_shock_use_the_earliest(self):
        shock = context([ev("paddles_removed_after_shock", 40, event_id="r2"), REMOVAL]).shock
        self.assertEqual((shock.time, shock.candidates), (33, ("removal", "r2")))
        self.assertEqual(shock.flags, ("shock_time_from_removal", "multiple_candidates"))

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
        self.assertEqual(ctx.shock.event_id, "removal")

    def test_phases(self):
        ctx = context([SHOCK])
        self.assertEqual([ctx.phase_of(t) for t in (10, 30, 50)], ["before_shock", "at_shock", "after_shock"])


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

    def test_resolution_against_removal_time_carries_the_fallback_flag(self):
        ctx = context([REMOVAL, cmd("resume_compressions_command", 40, "r")])
        self.assertEqual(self.resolution(ctx, "r").resolved_to, "start_compressions_command")
        self.assertEqual(self.resolution(ctx, "r").flags, ("shock_time_from_removal",))

    def test_under_the_removal_fallback_commands_before_removal_stay_unresolved(self):
        # D-024 (OQ-029): the real shock was before the removal, so "before removal" is not "before the shock"
        for t in (10, 25, 32.9):
            with self.subTest(t=t):
                ctx = context([REMOVAL, cmd("resume_compressions_command", t, "r")])
                resolution = self.resolution(ctx, "r")
                self.assertIsNone(resolution.resolved_to)
                self.assertEqual(resolution.flags, ("command_before_removal", "shock_time_from_removal"))
                self.assertEqual(ctx.named("continue_compressions_command"), [])

    def test_under_the_removal_fallback_commands_just_after_removal_are_near_the_shock(self):
        ctx = context([REMOVAL, cmd("resume_compressions_command", 33.3, "r")])
        self.assertEqual(self.resolution(ctx, "r").flags, ("command_near_shock", "shock_time_from_removal"))

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

    def test_under_the_fallback_an_unambiguous_restart_carries_no_fallback_flag(self):
        # D-059: a start after the removal, with none before it, is definitely the restart
        ctx = context([REMOVAL, cmd("start_compressions_command", 36, "s")])
        anchor = ctx.anchor("start_compressions")
        self.assertEqual((anchor.event_id, anchor.flags), ("s", ()))
        self.assertEqual((anchor.ambiguous, anchor.ineligible), ((), ()))
        # R7/A6 still measure from the removal-based shock time, so their delay stays flagged
        self.assertIn("shock_time_from_removal", ctx.elapsed("shock", "start_compressions").flags)

    def test_each_start_command_is_checked_on_its_own(self):
        # (e2): the later start after the shock is still the restart when an earlier one does not count
        anchor = context([SHOCK, cmd("start_compressions_command", 20, "pre"), cmd("start_compressions_command", 31, "post"),
                          cmd("start_compressions_command", 40, "late")]).anchor("start_compressions")
        self.assertEqual((anchor.event_id, anchor.candidates, anchor.ineligible), ("post", ("post", "late"), ("pre",)))

    def test_under_the_fallback_a_start_before_removal_is_ambiguous_not_a_mistake(self):
        # D-053 (OQ-039): the real shock was at an unknown time before the removal (33 s)
        for t in (20, 32, 33):
            with self.subTest(t=t):
                anchor = context([REMOVAL, cmd("start_compressions_command", t, "early")]).anchor("start_compressions")
                self.assertFalse(anchor.present)  # not counted as the restart
                self.assertEqual(anchor.ambiguous, ("early",))
                self.assertEqual(anchor.ineligible, ())  # not a sequence mistake for A7
                self.assertEqual(anchor.flags, ("shock_time_from_removal", "command_before_removal"))
                self.assertNotIn("start_command_before_shock", anchor.flags)

    def test_under_the_fallback_an_unresolved_resume_before_removal_makes_the_restart_ambiguous(self):
        # D-059 (OQ-041): "resume" at 30 s, before the removal at 33 s, may have been the restart
        ctx = context([REMOVAL, cmd("resume_compressions_command", 30, "r"), cmd("start_compressions_command", 40, "s")])
        anchor = ctx.anchor("start_compressions")
        self.assertEqual((anchor.event_id, anchor.ambiguous), ("s", ("r",)))  # later start still used, but...
        self.assertEqual(anchor.flags[:2], ("shock_time_from_removal", "command_before_removal"))
        self.assertIn("command_before_removal", ctx.elapsed("stop_compressions", "start_compressions").flags)
        self.assertEqual(anchor.ineligible, ())  # never a sequence mistake

    def test_under_the_fallback_only_a_resume_before_removal_leaves_no_restart(self):
        anchor = context([REMOVAL, cmd("resume_compressions_command", 30, "r")]).anchor("start_compressions")
        self.assertEqual((anchor.present, anchor.ambiguous), (False, ("r",)))
        self.assertIn("command_before_removal", anchor.flags)

    def test_with_a_shock_on_screen_a_resume_before_it_is_continue_not_ambiguous(self):
        anchor = context([SHOCK, cmd("resume_compressions_command", 20, "r"),
                          cmd("start_compressions_command", 35, "s")]).anchor("start_compressions")
        self.assertEqual((anchor.event_id, anchor.ambiguous, anchor.flags), ("s", (), ()))

    def test_under_the_fallback_a_later_start_is_used_but_the_ambiguity_is_flagged(self):
        anchor = context([REMOVAL, cmd("start_compressions_command", 31, "early"),
                          cmd("start_compressions_command", 40, "late")]).anchor("start_compressions")
        self.assertEqual((anchor.event_id, anchor.ambiguous), ("late", ("early",)))
        # the early one may have been the real restart, so a delay measured to "late" is uncertain
        self.assertIn("command_before_removal", anchor.flags)
        self.assertIn("command_before_removal", context([REMOVAL, cmd("stop_compressions_command", 25),
                                                         cmd("start_compressions_command", 31, "early"),
                                                         cmd("start_compressions_command", 40, "late")])
                      .elapsed("stop_compressions", "start_compressions").flags)

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
                         {"apical_zone": "unknown", "sternal_zone": "unknown"})

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
