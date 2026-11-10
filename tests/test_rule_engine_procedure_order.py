"""Increment 20: the procedure order as a precedence graph (D-120, D-123). Config and loader only."""
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


class RepositoryOrder(unittest.TestCase):
    def test_it_is_a_draft_not_clinically_approved(self):
        self.assertFalse(ORDER.approved)
        self.assertIn("NOT clinically approved", ORDER.note)
        self.assertEqual(ORDER.default_owner, "S1")

    def test_the_proposal_chains(self):
        self.assertEqual(owner("R1", "PLACE"), ("R1", "PLACE", "R1"))
        self.assertEqual(owner("R5", "R7"), ("R5", "R7", "R7"))
        self.assertEqual(owner("A1", "A5"), ("A1", "A5", "A7"))   # the audio command sequence
        self.assertEqual(owner("R6", "R7"), ("R6", "R7", "S1"))   # Figure 2: removal before the restart

    def test_a5_before_r4_awaits_confirmation(self):
        relation = ORDER.relation("A5", "R4")
        self.assertEqual((relation.owner, relation.confirm, relation.direct), ("S1", True, True))

    def test_every_relation_has_exactly_one_owner(self):
        pairs = [(r.before, r.after) for r in ORDER.relations]
        self.assertEqual(len(pairs), len(set(pairs)))
        self.assertTrue(all(r.owner for r in ORDER.relations))

    def test_existing_rules_keep_their_relations(self):
        self.assertEqual({(r.before, r.after) for r in ORDER.owned_by("R4")}, {("R3", "R4"), ("R4", "R5")})
        self.assertEqual({(r.before, r.after) for r in ORDER.owned_by("A4")}, {("A2", "A4"), ("A4", "R5")})
        self.assertEqual({(r.before, r.after) for r in ORDER.owned_by("R2")},
                         {("R2A", "PLACE"), ("PLACE", "R2B"), ("R2A", "R2B")})

    def test_a7_owns_the_remaining_audio_pairs_and_s1_the_rest(self):
        for relation in ORDER.owned_by("A7"):
            self.assertEqual({ORDER.step(relation.before).modality, ORDER.step(relation.after).modality}, {"audio"})
        cross_modal = [r for r in ORDER.owned_by("S1")
                       if ORDER.step(r.before).modality != ORDER.step(r.after).modality]
        self.assertIn(("A5", "R4"), [(r.before, r.after) for r in cross_modal])

    def test_unknown_pairs_are_not_ordered(self):
        """The proposal doesn't place A1-A5 relative to gel, the paddles and firm placement (OQ-062)."""
        self.assertIn(("A1", "R1"), ORDER.unknown)
        for a, b in ORDER.unknown:
            with self.subTest(pair=(a, b)):
                self.assertIsNone(ORDER.relation(a, b))

    def test_derived_steps_come_from_the_paddle_order(self):
        self.assertEqual({s.id: s.derived for s in ORDER.steps if s.derived},
                         {"R2A": "earliest_take", "PLACE": "earliest_placement", "R2B": "later_take"})
        self.assertEqual(ORDER.step("A4").modality, "audio")


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

    def test_an_unknown_derived_kind_is_refused(self):
        steps = copy.deepcopy(DATA["steps"])
        steps["R2A"]["derived"] = "first_take_by_name"
        with self.assertRaisesRegex(ConfigError, "derived"):
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
        owners = {r.owner for r in ORDER.relations}
        self.assertEqual(owners - set(RULE_IDS), {"S1"})   # S1 is added to rules.yaml in Increment 27

    def test_an_unknown_pair_ordered_by_the_chains_is_refused(self):
        chains = [*DATA["chains"], {"chain": ["A1", "R1"], "source": "test"}]
        with self.assertRaisesRegex(ConfigError, "marked unknown"):
            load(chains=chains)

    def test_an_interchangeable_group_removes_the_order_inside_it(self):
        order = load(interchangeable=[["A1", "A2"]])
        self.assertIsNone(order.relation("A1", "A2"))
        self.assertEqual(owner("A1", "A3", order), ("A1", "A3", "A7"))   # outside the group: kept

    def test_the_keys_are_exact(self):
        data = copy.deepcopy(DATA)
        data["extra"] = 1
        with self.assertRaisesRegex(ConfigError, "exactly the keys"):
            load_procedure_order(data, CONFIG.vocabulary)


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
