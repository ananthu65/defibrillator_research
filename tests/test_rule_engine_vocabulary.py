import copy
import json
import unittest

from annotation.audit_cvat_backups import EVENT_LABELS
from annotation.to_timeline import convert
from pipeline.config import ROOT, load_yaml
from rules.errors import ConfigError
from rules.vocabulary import DEFAULT_PATH, SOURCE_LABEL_KEY, Vocabulary, load_vocabulary
from schemas.event import Event

MINIMAL = {"schema_version": 1,
           "events": {"gel_applied": {"modality": "video"}, "stand_clear_command": {"modality": "audio"}},
           "labels": {"annotation": [{"label": "Gel applied", "event": "gel_applied"}],
                      "audio": [{"label": "stand_clear_command", "event": "stand_clear_command"}]},
           "unused": {"video": [{"prefix": "object_visible:"}], "audio": ["charging_sound"]}}


def config(**changes):
    value = copy.deepcopy(MINIMAL)
    value.update(changes)
    return value


class RepositoryVocabulary(unittest.TestCase):
    """The shipped vocabulary stays in sync with the labels other modules actually emit."""

    def setUp(self):
        self.vocabulary = load_vocabulary(DEFAULT_PATH)

    def test_every_cvat_event_tag_is_mapped(self):
        missing = [label for label in EVENT_LABELS if self.vocabulary.canonical("annotation", label) is None]
        self.assertEqual(missing, [])
        self.assertEqual(self.vocabulary.canonical("annotation", "Gel applied"), "gel_applied")

    def test_every_configured_audio_command_is_mapped(self):
        commands = load_yaml(ROOT / "configs/pipeline.yaml")["commands"]
        missing = [name for name in commands if self.vocabulary.canonical("audio", name) is None]
        self.assertEqual(missing, [])

    def test_placeholders_are_listed_until_real_names_arrive(self):
        self.assertTrue({("annotation", "first_paddle_placed"), ("annotation", "apical_paddle_placed"),
                         ("annotation", "sternal_paddle_placed"), ("audio", "stop_compressions_command"),
                         ("audio", "shock_command")} <= self.vocabulary.placeholder_labels)
        self.assertNotIn(("annotation", "Gel applied"), self.vocabulary.placeholder_labels)

    def test_modality_belongs_to_the_event_not_the_source(self):
        self.assertEqual(self.vocabulary.modality("gel_applied"), "video")
        self.assertEqual(self.vocabulary.modality("compressions_command"), "audio")

    def test_fixture_timeline_has_no_unknown_labels(self):
        events = [Event.from_dict(e) for e in json.loads(
            (ROOT / "tests/fixtures/sample_timeline.json").read_text())]
        result = self.vocabulary.map_events(events)
        self.assertEqual(result.unknown, [])
        self.assertEqual({i.label for i in result.unused}, {"object_visible:paddle_sternal", "charging_sound"})


class Mapping(unittest.TestCase):
    def setUp(self):
        self.vocabulary = Vocabulary.from_dict(MINIMAL)

    def test_label_is_renamed_and_everything_else_is_kept(self):
        event = Event("Gel applied", 2, 2, "annotation", 1.0, metadata={"frame": 50}, event_id="e1",
                      camera_angle="T")
        mapped = self.vocabulary.map_events([event]).events[0]
        self.assertEqual(mapped.event_name, "gel_applied")
        self.assertEqual(mapped.metadata, {"frame": 50, SOURCE_LABEL_KEY: "Gel applied"})
        self.assertEqual((mapped.event_id, mapped.start, mapped.source, mapped.camera_angle),
                         ("e1", 2, "annotation", "T"))
        self.assertEqual(event.event_name, "Gel applied")  # input is not modified
        self.assertNotIn(SOURCE_LABEL_KEY, event.metadata)

    def test_mapping_is_per_source(self):
        result = self.vocabulary.map_events([Event("Gel applied", 2, 2, "video", 0.9, event_id="v1")])
        self.assertEqual(result.events[0].event_name, "Gel applied")
        self.assertEqual([(i.event_id, i.source, i.label) for i in result.unknown], [("v1", "video", "Gel applied")])

    def test_unknown_label_is_kept_and_flagged(self):
        result = self.vocabulary.map_events([Event("gel applied", 1, 1, "annotation", 1, event_id="x"),
                                             Event("Gel applied", 3, 3, "annotation", 1, event_id="y")])
        self.assertEqual([e.event_name for e in result.events], ["gel applied", "gel_applied"])
        self.assertEqual([i.event_id for i in result.unknown], ["x"])

    def test_unused_labels_are_kept_but_not_flagged_as_unknown(self):
        result = self.vocabulary.map_events([Event("object_visible:paddle", 1, 2, "video", 0.8, event_id="a"),
                                             Event("charging_sound", 3, 4, "audio", 0.9, event_id="b")])
        self.assertEqual(result.unknown, [])
        self.assertEqual([i.event_id for i in result.unused], ["a", "b"])
        self.assertEqual(len(result.events), 2)

    def test_mapping_twice_changes_nothing(self):
        once = self.vocabulary.map_events([Event("Gel applied", 2, 2, "annotation", 1, event_id="e1")])
        twice = self.vocabulary.map_events(once.events)
        self.assertEqual(twice.events, once.events)
        self.assertEqual(twice.unknown, [])

    def test_order_and_missing_ids_are_preserved(self):
        events = convert({"participant_id": "P01", "canonical_task_id": "P01_T", "events": [
            {"label": "Gel applied", "timestamp_seconds": 5, "frame": 125},
            {"label": "Gel applied", "timestamp_seconds": 1, "frame": 25}]})
        mapped = self.vocabulary.map_events(events).events
        self.assertEqual([e.start for e in mapped], [5, 1])
        self.assertTrue(all(e.event_id is None and e.event_name == "gel_applied" for e in mapped))


class InvalidVocabulary(unittest.TestCase):
    def assertRejected(self, data, message):
        with self.assertRaisesRegex(ConfigError, message):
            Vocabulary.from_dict(data)

    def test_wrong_schema_version(self):
        self.assertRejected(config(schema_version=2), "schema_version")

    def test_no_events(self):
        self.assertRejected(config(events={}), "events")

    def test_bad_modality(self):
        self.assertRejected(config(events={"gel_applied": {"modality": "smell"}}), r"events\.gel_applied")

    def test_label_to_undeclared_event(self):
        self.assertRejected(config(labels={"annotation": [{"label": "Gel applied", "event": "gel_aplied"}]}),
                            r"labels\.annotation\[0\]: unknown canonical event 'gel_aplied'")

    def test_duplicate_label(self):
        entry = {"label": "Gel applied", "event": "gel_applied"}
        self.assertRejected(config(labels={"annotation": [entry, entry]}), r"\[1\].*mapped twice")

    def test_unknown_source(self):
        self.assertRejected(config(labels={"camera": []}), "unknown source 'camera'")

    def test_typo_in_entry_key(self):
        self.assertRejected(config(labels={"annotation": [{"label": "Gel applied", "evnt": "gel_applied"}]}),
                            "expected only")

    def test_empty_label(self):
        self.assertRejected(config(labels={"annotation": [{"label": "", "event": "gel_applied"}]}), "nonempty")

    def test_label_both_mapped_and_unused(self):
        self.assertRejected(config(unused={"annotation": ["Gel applied"]}), "both mapped and unused")

    def test_bad_unused_entry(self):
        self.assertRejected(config(unused={"video": [{"startswith": "x"}]}), r"unused\.video\[0\]")


if __name__ == "__main__":
    unittest.main()
