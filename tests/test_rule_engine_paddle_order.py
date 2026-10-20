"""D-118: paddle time order comes from event times; the tag names give identity only (A-027).

Sternal-first learners, under the team's labelling: first_paddle_* is the apical paddle, second_paddle_*
the sternal one, so a sternal-first learner produces second_paddle_taken before first_paddle_taken.
"""
import copy
from types import SimpleNamespace
import unittest

import yaml

from annotation.derive_gel_applications import gel_phase
from annotation.export_rule_engine_records import load_config as load_export_config
from pipeline.config import ROOT
from rules.config import RuleEngineConfig
from rules.context import paddle_order
from rules.coverage import TimelineHeader
from rules.engine import assess
from rules.registry import discover
from schemas.event import Event

CATALOGUE = yaml.safe_load((ROOT / "configs/rules.yaml").read_text(encoding="utf-8"))
CONFIG = RuleEngineConfig.from_dict({**copy.deepcopy(CATALOGUE),
                                     "rules": [{"id": r, "status": "approved"} for r in ("R1", "R2", "R8")]})
REGIONS = tuple(CONFIG.engine.regions)
WINDOW = CONFIG.engine.value("simultaneous_window_seconds")


def ev(label, t, event_id=None, flags=()):
    return Event(label, t, t, "annotation", 1.0, event_id=event_id or f"{label}@{t}", camera_angle="LS",
                 metadata={"flags": list(flags)} if flags else {})


def header():
    return TimelineHeader.from_dict({
        "camera_angle": "LS", "duration_seconds": 30.0, "analyses_run": {"video": True, "audio": False},
        "coverage": {"region:apical_zone": "covered", "region:sternal_zone": "covered"},
        "visibility": {"region:apical_zone": [[0.0, 30.0]], "region:sternal_zone": [[0.0, 30.0]]}}, regions=REGIONS)


def run(events):
    result = assess(events, CONFIG, header=header(), registry=discover())
    return {rule: result.outcome(rule) for rule in ("R1", "R2", "R8")}


# a sternal-first learner handling one paddle at a time
STERNAL_TAKEN = ev("second_paddle_taken", 3, "sternal_taken")
STERNAL_PLACED = ev("sternal_paddle_placed", 5, "sternal_placed")
APICAL_TAKEN = ev("first_paddle_taken", 6, "apical_taken")
APICAL_FIRM = ev("first_paddle_firmly_on_the_chest", 9, "apical_firm")
APICAL_PLACED = ev("apical_paddle_placed", 9, "apical_placed")
BOTH_FIRM = ev("paddles_firmly_on_chest", 10, "both_firm")
STERNAL_FIRST = [STERNAL_TAKEN, STERNAL_PLACED, APICAL_TAKEN, APICAL_FIRM, APICAL_PLACED, BOTH_FIRM]
APICAL_PLACED_CANONICAL = ev("first_paddle_placed", 9, "apical_firm")   # the canonical name of the CVAT tag


def gel(t):
    return ev("Gel applied", t, f"gel@{t}")


class SternalFirst(unittest.TestCase):
    def test_one_paddle_at_a_time_with_gel_before_both(self):
        """R2 passes (the paddle taken first was placed before the other was taken); only R8 reports the order."""
        outcome = run([gel(1), gel(2), *STERNAL_FIRST])
        self.assertEqual((outcome["R2"].kind, outcome["R2"].evidence), ("pass_direct", ("sternal_placed", "apical_taken")))
        self.assertIn("the sternal paddle (taken first) placed at 5 s", outcome["R2"].reason)
        self.assertEqual((outcome["R8"].kind, outcome["R8"].failure_code), ("fail", "wrong_order"))
        self.assertEqual(outcome["R1"].kind, "pass_direct")
        self.assertIn("before the first placement (5 s)", outcome["R1"].reason)   # the sternal one, not the apical

    def test_gel_after_the_sternal_placement_but_before_the_apical_is_after_placement(self):
        outcome = run([gel(6.5), gel(7.5), *STERNAL_FIRST])
        self.assertEqual((outcome["R1"].kind, outcome["R1"].failure_code), ("fail", "after_placement"))
        self.assertIn("after the first paddle was placed (5 s)", outcome["R1"].reason)

    def test_sternal_placement_time_unknown(self):
        """No event marks the sternal placement (no tag exists for it; derived ones only past the gate)."""
        events = [gel(1), gel(4), STERNAL_TAKEN, APICAL_TAKEN, APICAL_FIRM, BOTH_FIRM]
        outcome = run(events)
        self.assertEqual((outcome["R2"].kind, outcome["R2"].flags), ("unable_to_verify", ("placement_time_unknown",)))
        self.assertIn("the sternal paddle was taken first (3 s)", outcome["R2"].reason)
        # gel at 4 s may have come after the sternal placement (any time after 3 s), never Pass
        self.assertEqual((outcome["R1"].kind, outcome["R1"].flags), ("unable_to_verify", ("placement_time_unknown",)))
        self.assertEqual(outcome["R1"].evidence, ("gel@4",))

    def test_gel_before_the_sternal_take_is_certain(self):
        outcome = run([gel(1), gel(2), STERNAL_TAKEN, APICAL_TAKEN, APICAL_FIRM, BOTH_FIRM])
        self.assertEqual(outcome["R1"].kind, "pass_direct")

    def test_parallel_placement_still_fails_both(self):
        """OQ-059 unchanged: one parallel placement fails R2 and R8 (D-098)."""
        flags = ("derived_placement", "possible_parallel_placement")
        events = [gel(1), gel(2), ev("first_paddle_taken", 3), ev("second_paddle_taken", 3.3),
                  ev("apical_paddle_placed", 5, "a", flags), ev("sternal_paddle_placed", 5.2, "s", flags), BOTH_FIRM]
        outcome = run(events)
        for rule in ("R2", "R8"):
            with self.subTest(rule):
                self.assertEqual((outcome[rule].kind, outcome[rule].failure_code), ("fail", "simultaneous"))
                self.assertIn("possible_parallel_placement", outcome[rule].flags)


class Helper(unittest.TestCase):
    """The helper works on canonical names (after preparation): first_paddle_placed, not the CVAT label."""
    def test_first_taken_comes_from_times_not_names(self):
        self.assertEqual(paddle_order(STERNAL_FIRST, WINDOW).first_taken, "sternal")
        self.assertEqual(paddle_order([ev("first_paddle_taken", 3), ev("second_paddle_taken", 6)], WINDOW).first_taken,
                         "apical")

    def test_an_exact_tie_counts_as_apical(self):
        self.assertEqual(paddle_order([ev("first_paddle_taken", 3), ev("second_paddle_taken", 3)], WINDOW).first_taken,
                         "apical")

    def test_a_paddle_placed_before_the_other_was_taken_was_taken_first(self):
        order = paddle_order([APICAL_PLACED_CANONICAL, ev("second_paddle_taken", 12)], WINDOW)
        self.assertEqual((order.first_taken, order.take_deduced), ("apical", True))   # its take isn't tagged
        self.assertIsNone(paddle_order([ev("second_paddle_taken", 12)], WINDOW).first_taken)
        self.assertFalse(paddle_order(STERNAL_FIRST, WINDOW).take_deduced)

    def test_earliest_placement_and_whether_it_is_certain(self):
        both = paddle_order(STERNAL_FIRST, WINDOW)
        self.assertEqual((both.earliest_placement.event_id, both.earliest_certain), ("sternal_placed", True))
        later = paddle_order([APICAL_PLACED_CANONICAL, ev("second_paddle_taken", 11)], WINDOW)
        self.assertTrue(later.earliest_certain)               # the sternal paddle was taken after the placement
        unknown = paddle_order([STERNAL_TAKEN, APICAL_PLACED_CANONICAL], WINDOW)
        self.assertEqual((unknown.earliest_certain, unknown.unknown_from), (False, 3))
        untaken = paddle_order([APICAL_PLACED_CANONICAL], WINDOW)
        self.assertEqual((untaken.earliest_certain, untaken.unknown_from), (False, 0.0))


class TakenTogether(unittest.TestCase):
    """Both paddles taken within the simultaneous window fail R2 `simultaneous`, whichever is named first:
    the apical tie-break (Helper) never decides it."""
    def test_takes_within_the_window_are_simultaneous_whichever_is_named_first(self):
        cases = {
            "apical named first": [ev("first_paddle_taken", 3), ev("second_paddle_taken", 3.3), APICAL_FIRM],
            "sternal named first": [ev("second_paddle_taken", 3), ev("first_paddle_taken", 3.3),
                                    ev("sternal_paddle_placed", 5, "sternal_placed"), APICAL_FIRM],
            "an exact tie": [ev("first_paddle_taken", 3), ev("second_paddle_taken", 3), APICAL_FIRM],
            "no placement seen": [ev("second_paddle_taken", 3), ev("first_paddle_taken", 3.4)],
        }
        for name, events in cases.items():
            with self.subTest(name):
                outcome = run([gel(1), gel(2), *events, BOTH_FIRM])["R2"]
                self.assertEqual((outcome.kind, outcome.failure_code), ("fail", "simultaneous"))
                self.assertIn("both paddles taken together", outcome.reason)

    def test_takes_just_outside_the_window_are_ordered(self):
        events = [ev("second_paddle_taken", 3), ev("sternal_paddle_placed", 3.5, "sternal_placed"),
                  ev("first_paddle_taken", 3 + WINDOW + 0.6), APICAL_FIRM, BOTH_FIRM]
        self.assertEqual(run([gel(1), gel(2), *events])["R2"].kind, "pass_direct")


class TakeDeducedFromPlacement(unittest.TestCase):
    """A paddle placed before the other was taken was taken first; the report shows it was deduced."""
    def test_r2_carries_the_flag(self):
        outcome = run([gel(1), gel(2), APICAL_FIRM, ev("second_paddle_taken", 11), BOTH_FIRM])["R2"]
        self.assertEqual((outcome.kind, outcome.flags), ("pass_direct", ("take_order_from_placement",)))
        self.assertIn("its take isn't tagged", outcome.reason)

    def test_no_flag_when_both_takes_are_tagged(self):
        self.assertNotIn("take_order_from_placement", run([gel(1), gel(2), *STERNAL_FIRST])["R2"].flags)


class StepNineDAgreesWithTheHelper(unittest.TestCase):
    """Step 9d (frames, CVAT labels) and paddle_order (seconds, canonical names) give the same gel-phase end
    on the same timelines. In the pipeline 9d also sees the 9c placements while the 9c gate is closed."""
    FPS = 25.0
    SETTINGS = load_export_config().gel
    CANONICAL = {"first_paddle_taken": "first_paddle_taken", "second_paddle_taken": "second_paddle_taken",
                 "first_paddle_firmly_on_the_chest": "first_paddle_placed"}   # vocabulary.yaml (D-047)
    TIMELINES = {   # (CVAT tags, 9c placements), in frames
        "apical first": ([("first_paddle_taken", 50), ("first_paddle_firmly_on_the_chest", 75),
                          ("second_paddle_taken", 100)],
                         [("apical_paddle_placed", 76), ("sternal_paddle_placed", 125)]),
        "sternal first": ([("second_paddle_taken", 50), ("first_paddle_taken", 100),
                           ("first_paddle_firmly_on_the_chest", 125)],
                          [("sternal_paddle_placed", 75), ("apical_paddle_placed", 126)]),
        "sternal placement unknown": ([("second_paddle_taken", 50), ("first_paddle_taken", 100),
                                       ("first_paddle_firmly_on_the_chest", 125)], []),
        "the apical tag wins over its 9c placement": ([("first_paddle_taken", 50),
                                                      ("first_paddle_firmly_on_the_chest", 80)],
                                                     [("apical_paddle_placed", 70)]),
        "no placement, takes only": ([("second_paddle_taken", 50), ("first_paddle_taken", 100)], []),
        "nothing": ([], []),
    }

    def test_same_gel_phase_end(self):
        for name, (tags, placements) in self.TIMELINES.items():
            with self.subTest(name):
                source = SimpleNamespace(tags=[{"label": label, "frame": frame} for label, frame in tags],
                                         stop_frame=199)
                end, _ = gel_phase(source, self.SETTINGS,
                                   [{"event_name": event, "frame": frame} for event, frame in placements])
                events = [ev(self.CANONICAL[label], frame / self.FPS, f"{label}@{frame}") for label, frame in tags]
                events += [ev(event, frame / self.FPS, f"{event}@{frame}") for event, frame in placements]
                helper = paddle_order(events, WINDOW).gel_phase_end
                self.assertEqual(None if helper is None else round(helper.start * self.FPS),
                                 None if end == source.stop_frame + 1 else end)


if __name__ == "__main__":
    unittest.main()
