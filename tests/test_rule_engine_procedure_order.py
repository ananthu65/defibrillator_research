"""The procedure order as a precedence graph (D-120, D-123, D-126, D-127). Config and loader only."""
import copy
from pathlib import Path
import tempfile
import unittest

import yaml

from pipeline.config import ROOT
from rules.config import RuleEngineConfig, load_rules_config
from rules.errors import ConfigError
from rules.procedure import load_procedure_order

CONFIG = load_rules_config()
ORDER = CONFIG.procedure_order
DATA = yaml.safe_load((ROOT / "configs/rule_engine/procedure_order.yaml").read_text(encoding="utf-8"))
RULES = yaml.safe_load((ROOT / "configs/rules.yaml").read_text(encoding="utf-8"))
RULE_IDS = [r.id for r in CONFIG.rules]


def load(**changes):
    data = copy.deepcopy(DATA)
    data.update(changes)
    return load_procedure_order(data, CONFIG.vocabulary)


def owner(a, b, order=ORDER):
    relation = order.relation(a, b)
    return None if relation is None else (relation.before, relation.after, relation.owner)


def owned(rule_id, order=ORDER):
    return {(r.before, r.after) for r in order.owned_by(rule_id)}


class RepositoryOrder(unittest.TestCase):
    """The interim order from the lecturer's ground-truth video (D-127), pending the supervisor (OQ-062)."""

    def test_it_is_not_clinically_approved_and_names_its_source(self):
        self.assertFalse(ORDER.approved)
        self.assertIn("NOT clinically approved", ORDER.note)
        self.assertIn("lecturer's ground-truth video", ORDER.source)
        self.assertEqual(ORDER.default_owner, "S1")

    def test_the_lecturers_order(self):
        sequence = ["A1", "A3", "A2", "CHARGE", "R1", "A4", "R2A", "PLACE", "R2B", "R3", "R4", "R5", "R6", "R7"]
        for a, b in zip(sequence, sequence[1:]):
            with self.subTest(pair=(a, b)):
                self.assertEqual(owner(a, b)[:2], (a, b))
        self.assertEqual(owner("A3", "A2")[:2], ("A3", "A2"))   # reverses the proposal's continue -> stand clear

    def test_the_gel_phase_is_interchangeable(self):
        """Gel on both zones (R1) and the spoken "applying gel" happen together: no order between them."""
        self.assertIn(("R1", "GELCMD"), ORDER.interchangeable)
        self.assertIsNone(ORDER.relation("R1", "GELCMD"))
        self.assertEqual(owner("CHARGE", "GELCMD"), ("CHARGE", "GELCMD", "A7"))
        self.assertEqual(owner("GELCMD", "A4"), ("GELCMD", "A4", "A7"))

    def test_charging_and_the_gel_announcement_are_optional(self):
        self.assertEqual({s.id for s in ORDER.steps if s.optional}, {"CHARGE", "GELCMD"})

    def test_a5_keeps_only_stop_before_it_and_before_the_buttons(self):
        """The lecturer said no shock command (OQ-075): A4 -> A5 -> R4 stays, A5 against the paddles is unknown."""
        relation = ORDER.relation("A5", "R4")
        self.assertEqual((relation.owner, relation.confirm, relation.direct), ("S1", True, True))
        self.assertEqual(owner("A4", "A5"), ("A4", "A5", "A7"))
        self.assertEqual(set(ORDER.unknown), {("A5", "R2A"), ("A5", "PLACE"), ("A5", "R2B"), ("A5", "R3")})
        for a, b in ORDER.unknown:
            with self.subTest(pair=(a, b)):
                self.assertIsNone(ORDER.relation(a, b))

    def test_existing_rules_keep_their_relations(self):
        self.assertEqual(owned("R4"), {("R3", "R4"), ("R4", "R5")})
        self.assertEqual(owned("A4"), {("A2", "A4"), ("A4", "R5")})
        self.assertEqual(owned("R2"), {("R2A", "PLACE"), ("PLACE", "R2B"), ("R2A", "R2B")})
        self.assertEqual(owned("A1"), {("A1", "R5")})

    def test_a7_owns_the_audio_pairs(self):
        for relation in ORDER.owned_by("A7"):
            self.assertEqual({ORDER.step(relation.before).modality, ORDER.step(relation.after).modality}, {"audio"})
        self.assertIn(("A3", "A2"), owned("A7"))

    def test_derived_steps_come_from_the_paddle_order(self):
        self.assertEqual({s.id: s.derived for s in ORDER.steps if s.derived},
                         {"R2A": "earliest_take", "PLACE": "earliest_placement", "R2B": "later_take"})
        self.assertEqual(ORDER.step("A4").modality, "audio")


class S1OwnsOnlyUnimpliedRelations(unittest.TestCase):
    """D-126 (OQ-071, option B): S1 owns only relations not implied by any other relation, so each mistake is
    judged by exactly one rule. An implied relation has no owner; it is judged through the relations implying it."""

    def test_s1_keeps_six_relations(self):
        self.assertEqual(owned("S1"), {("CHARGE", "R1"), ("R1", "A4"), ("A4", "R2A"), ("R2B", "R3"), ("A5", "R4"),
                                       ("R6", "R7")})

    def test_no_s1_relation_has_an_intermediate_step(self):
        pairs = {(r.before, r.after) for r in ORDER.relations}
        steps = [s.id for s in ORDER.steps]
        for a, b in owned("S1"):
            with self.subTest(pair=(a, b)):
                self.assertFalse(any((a, c) in pairs and (c, b) in pairs for c in steps))

    def test_an_implied_relation_has_no_owner(self):
        """O2 away before removal follows from O2 away before the shock (A1) and the shock before removal (R6)."""
        relation = ORDER.relation("A1", "R6")
        self.assertEqual((relation.owner, relation.implied), (None, True))
        self.assertEqual(owner("PLACE", "R3"), ("PLACE", "R3", None))   # through PLACE -> R2B -> R3

    def test_every_relation_has_at_most_one_owner(self):
        pairs = [(r.before, r.after) for r in ORDER.relations]
        self.assertEqual(len(pairs), len(set(pairs)))
        unowned = [r for r in ORDER.relations if r.owner is None]
        self.assertTrue(unowned)
        self.assertTrue(all(r.implied for r in unowned))

    def test_explicit_owners_keep_implied_relations(self):
        """Only the default owner is reduced: R3 keeps R3 -> R5 although R3 -> R4 -> R5 implies it."""
        self.assertEqual(owner("R3", "R5"), ("R3", "R5", "R3"))


class Validation(unittest.TestCase):
    def test_a_cycle_is_refused_and_named(self):
        chains = [*DATA["chains"], {"chain": ["R7", "A1"], "source": "test"}]
        with self.assertRaisesRegex(ConfigError, r"circular order: .*R7 -> A1"):
            load(chains=chains)

    def test_an_unknown_step_in_a_chain_is_refused(self):
        with self.assertRaisesRegex(ConfigError, "two or more known steps"):
            load(chains=[*DATA["chains"], {"chain": ["R1", "R9"], "source": "test"}])

    def test_a_step_needs_canonical_events_of_one_modality(self):
        for events, message in ((["gel_aplied"], "canonical events"),
                                (["gel_applied", "stand_clear_command"], "one modality")):
            with self.subTest(events=events):
                steps = copy.deepcopy(DATA["steps"])
                steps["R1"]["events"] = events
                with self.assertRaisesRegex(ConfigError, message):
                    load(steps=steps)

    def test_an_unknown_derived_kind_or_optional_value_is_refused(self):
        for key, value in (("derived", "first_take_by_name"), ("optional", "yes")):
            with self.subTest(key=key):
                steps = copy.deepcopy(DATA["steps"])
                steps["R2A"][key] = value
                with self.assertRaisesRegex(ConfigError, key):
                    load(steps=steps)

    def test_two_owners_for_one_relation_are_refused(self):
        owners = {**copy.deepcopy(DATA["owners"]), "R3": [["R3", "R5"], ["R3", "R4"]]}
        with self.assertRaisesRegex(ConfigError, "already owned by R4|one owner per relation"):
            load(owners=owners)

    def test_an_owned_pair_must_be_a_relation(self):
        owners = {**copy.deepcopy(DATA["owners"]), "R3": [["R5", "R3"]]}
        with self.assertRaisesRegex(ConfigError, "not a relation"):
            load(owners=owners)

    def test_an_owner_must_look_like_a_rule_id(self):
        with self.assertRaisesRegex(ConfigError, "expected a rule ID"):
            load(owners={**copy.deepcopy(DATA["owners"]), "gel rule": [["R3", "R5"]]})

    def test_every_owner_is_a_rule_in_the_catalogue_or_the_planned_default(self):
        owners = {r.owner for r in ORDER.relations} - {None}
        self.assertEqual(owners - set(RULE_IDS), {"S1"})   # S1 is added to rules.yaml in Increment 27

    def test_an_unknown_pair_ordered_by_the_chains_is_refused(self):
        chains = [*DATA["chains"], {"chain": ["A5", "R3"], "source": "test"}]
        with self.assertRaisesRegex(ConfigError, "marked unknown"):
            load(chains=chains)

    def test_an_interchangeable_group_removes_the_order_inside_it(self):
        order = load(interchangeable=[["R1", "GELCMD"], ["A1", "A3"]])
        self.assertIsNone(order.relation("A1", "A3"))
        self.assertEqual(owner("A1", "A2", order), ("A1", "A2", "A7"))   # outside the group: kept

    def test_the_keys_are_exact(self):
        data = copy.deepcopy(DATA)
        data["extra"] = 1
        with self.assertRaisesRegex(ConfigError, "exactly the keys"):
            load_procedure_order(data, CONFIG.vocabulary)


class ApplyingTheCompleteOrder(unittest.TestCase):
    """When the supervisor's order arrives (OQ-062), applying it is a change to procedure_order.yaml only: move pairs
    from "unknown" to chains; new relations get owners automatically (A7 between audio steps, else S1 unless
    another relation implies them)."""

    def test_every_unknown_pair_resolved_loads_and_gets_owners(self):
        # an example placement for the test only, NOT a clinical answer: the shock command before the first take
        order = load(chains=[*DATA["chains"], {"chain": ["A5", "R2A"], "source": "test"}], unknown=[])
        self.assertEqual(order.unknown, ())
        for a, b in ORDER.unknown:   # every pair left open is now ordered
            with self.subTest(pair=(a, b)):
                self.assertIsNotNone(order.relation(a, b))
        self.assertEqual(owner("A5", "R2A", order), ("A5", "R2A", "S1"))   # no owner entry needed
        steps = len(order.steps)
        self.assertEqual(len(order.relations), steps * (steps - 1) // 2 - 1)   # total, except the gel phase pair
        self.assertEqual(owner("R4", "R5", order), ("R4", "R5", "R4"))   # explicit owners kept

    def test_a_single_pair_can_be_resolved_on_its_own(self):
        unknown = [{"pairs": [[a, b] for a, b in ORDER.unknown if (a, b) != ("A5", "R3")], "question": "OQ-075"}]
        order = load(chains=[*DATA["chains"], {"chain": ["A5", "R3"], "source": "test"}], unknown=unknown)
        self.assertEqual(owner("A5", "R3", order), ("A5", "R3", "S1"))
        self.assertEqual(len(order.unknown), len(ORDER.unknown) - 1)

    def test_a_pair_implied_by_a_new_relation_must_leave_unknown_too(self):
        """R2B before A5 also orders R2A and PLACE before A5 (R2A -> PLACE -> R2B)."""
        with self.assertRaisesRegex(ConfigError, "through other relations"):
            load(chains=[*DATA["chains"], {"chain": ["R2B", "A5"], "source": "test"}],
                 unknown=[{"pairs": [["A5", "R2A"], ["A5", "PLACE"], ["A5", "R3"]], "question": "OQ-075"}])


class LoadedWithTheCatalogue(unittest.TestCase):
    def test_a_bad_order_stops_the_catalogue_from_loading(self):
        data = copy.deepcopy(DATA)
        data["chains"].append({"chain": ["R7", "A1"], "source": "test"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "procedure_order.yaml"
            path.write_text(yaml.safe_dump(data), encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "circular order"):
                RuleEngineConfig.from_dict({**RULES, "procedure_order": str(path)})

    def test_no_rule_reads_it_yet(self):
        """S1 and A7 come in Increments 26-27; the order changes no result today."""
        self.assertNotIn("S1", RULE_IDS)


if __name__ == "__main__":
    unittest.main()
