"""D-132 (extends D-130): a Pass that also claims something did NOT happen needs that window in view; otherwise
Unable to Verify, flagged correct_occurrence_unseen. R5 is the exception: a second shock is a data anomaly, so its
Pass stays, flagged second_shock_not_ruled_out, which never blocks an overall Pass on its own.

The full configs/rules.yaml with the rule under test approved (testing practice, methods.md); synthetic timelines.
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
UNSEEN = "correct_occurrence_unseen"


def config(*approve):
    data = copy.deepcopy(CATALOGUE)
    for entry in data["rules"]:
        if entry["id"] in approve:
            entry["status"] = "approved"
    return RuleEngineConfig.from_dict(data)


def tag(label, t, event_id=None, **metadata):
    return Event(label, t, t, "annotation", 1.0, event_id=event_id or f"{label}@{t:g}", camera_angle="LS",
                 metadata=metadata)


def header(gel=None, **regions):
    visibility = {f"region:{name}": [list(s) for s in spans] for name, spans in regions.items()}
    coverage = {f"region:{zone}_gel": status for zone, status in (gel or {}).items()}
    return TimelineHeader.from_dict({"camera_angle": "LS", "duration_seconds": 30.0,
                                     "analyses_run": {"video": True, "audio": False},
                                     "coverage": coverage, "visibility": visibility}, regions=REGIONS)


def run(rule_id, events, head):
    return assess(events, config(rule_id), header=head, registry=discover())


class Check(unittest.TestCase):
    def passes(self, result):
        self.assertEqual(result.kind, "pass_direct")
        self.assertNotIn(UNSEEN, result.flags)

    def unseen(self, result):
        self.assertEqual(result.kind, "unable_to_verify")
        self.assertIn(UNSEEN, result.flags)
        self.assertIn("D-132", result.reason)


class R1(Check):
    """The paddle placed first was not placed earlier, from the last counted gel to its placement."""
    GEL = {"apical": "covered", "sternal": "covered"}   # per-zone gel status (past the 9d gate)
    EVENTS = [tag("sternal_gel_applied", 2, derived_gel_application=True),
              tag("apical_gel_applied", 4, derived_gel_application=True),
              tag("first_paddle_firmly_on_the_chest", 10, "placed"), tag("second_paddle_taken", 11)]

    def test_the_zone_in_view_from_the_last_gel_to_the_placement(self):
        self.passes(run("R1", self.EVENTS, header(gel=self.GEL, apical_zone=ALL, sternal_zone=ALL)).outcome("R1"))
        self.unseen(run("R1", self.EVENTS, header(gel=self.GEL, apical_zone=((0.0, 5.0),), sternal_zone=ALL))
                    .outcome("R1"))


class R2(Check):
    """The other paddle was not taken earlier, from the first take to the first placement."""
    EVENTS = [tag("first_paddle_taken", 5), tag("first_paddle_firmly_on_the_chest", 7), tag("second_paddle_taken", 9)]

    def test_the_other_paddle_in_view_from_the_first_take_to_the_placement(self):
        self.passes(run("R2", self.EVENTS, header(apical_zone=ALL, sternal_zone=ALL, apical_paddle=ALL,
                                                  sternal_paddle=ALL)).outcome("R2"))
        self.unseen(run("R2", self.EVENTS, header(apical_zone=ALL, sternal_zone=ALL, apical_paddle=ALL,
                                                  sternal_paddle=((6.0, 30.0),))).outcome("R2"))


class R6(Check):
    """The paddles were not removed before the shock, from the firm placement to the shock."""
    EVENTS = [tag("paddles_firmly_on_chest", 10), tag("shock_delivered_on_screen", 15, "shock"),
              tag("paddles_removed_after_shock", 20, "removed")]

    def test_both_zones_in_view_from_the_firm_placement_to_the_shock(self):
        self.passes(run("R6", self.EVENTS, header(apical_zone=ALL, sternal_zone=ALL)).outcome("R6"))
        self.unseen(run("R6", self.EVENTS, header(apical_zone=ALL, sternal_zone=((0.0, 12.0), (16.0, 30.0))))
                    .outcome("R6"))


class R8(Check):
    """The sternal paddle was not placed earlier, from the start of the placement phase to the apical placement."""
    EVENTS = [tag("first_paddle_taken", 5), tag("second_paddle_taken", 10), tag("paddles_firmly_on_chest", 14),
              tag("apical_paddle_placed", 7), tag("sternal_paddle_placed", 12)]

    def test_the_sternal_zone_in_view_from_the_placement_phase_to_the_apical_placement(self):
        self.passes(run("R8", self.EVENTS, header(apical_zone=ALL, sternal_zone=ALL)).outcome("R8"))
        self.unseen(run("R8", self.EVENTS, header(apical_zone=ALL, sternal_zone=((6.0, 30.0),))).outcome("R8"))


class R5SecondShock(unittest.TestCase):
    """The exception: the Pass stays; the flag is information, not an obstacle to an overall Pass."""
    EVENTS = [tag("paddles_firmly_on_chest", 10), tag("shock_delivered_on_screen", 15, "shock"),
              tag("paddles_removed_after_shock", 20)]

    def test_the_screen_in_view_from_placement_to_removal_gives_a_plain_pass(self):
        result = run("R5", self.EVENTS, header(screen=ALL)).outcome("R5")
        self.assertEqual((result.kind, result.flags), ("pass_direct", ()))

    def test_otherwise_the_pass_is_flagged_and_does_not_block_an_overall_pass(self):
        assessed = run("R5", self.EVENTS, header(screen=((12.0, 30.0),)))
        result = assessed.outcome("R5")
        self.assertEqual((result.kind, result.flags), ("pass_direct", ("second_shock_not_ruled_out",)))
        self.assertIn("second shock can't be ruled out", result.reason)
        self.assertEqual([c for c in assessed.overall.incomplete if "R5" in c.rule_ids], [])


if __name__ == "__main__":
    unittest.main()
