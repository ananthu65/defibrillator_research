from dataclasses import replace
import json
import unittest

from pipeline.config import ROOT
from pipeline.merge_timeline import merge_timeline
from rules.config import Setting, load_rules_config
from rules.errors import TimelineError
from rules.prepare import prepare_timeline
from schemas.event import Event

CONFIG = load_rules_config()  # thresholds: annotation 1.0, video 0.5, audio 0.5 (placeholders)


def event(name, t, source="annotation", confidence=1.0, event_id=None, **fields):
    return Event(name, t, t, source, confidence, event_id=event_id or f"{name}@{t}", **fields)


def with_thresholds(**values):
    thresholds = {s: Setting(f"confidence_thresholds.{s}", v) for s, v in values.items()}
    return replace(CONFIG, engine=replace(CONFIG.engine, confidence_thresholds=thresholds))


class Mapping(unittest.TestCase):
    def test_labels_become_canonical_and_keep_their_original(self):
        prepared = prepare_timeline([event("Gel applied", 3)], CONFIG)
        self.assertEqual(prepared.events[0].event_name, "gel_applied")
        self.assertEqual(prepared.events[0].metadata["source_label"], "Gel applied")

    def test_unknown_unused_and_unresolved_labels_are_reported_not_dropped(self):
        prepared = prepare_timeline([event("gel applied", 1), event("charging_sound", 2, "audio", 0.9),
                                     event("resume_compressions_command", 3, "audio", 0.9)], CONFIG)
        self.assertEqual([i.label for i in prepared.unknown_labels], ["gel applied"])
        self.assertEqual([i.label for i in prepared.unused_labels], ["charging_sound"])
        self.assertEqual([i.label for i in prepared.unresolved_labels], ["resume_compressions_command"])
        self.assertEqual(len(prepared.events), 3)

    def test_events_are_returned_in_time_order(self):
        prepared = prepare_timeline([event("shock_delivered_on_screen", 9), event("Gel applied", 2)], CONFIG)
        self.assertEqual([e.start for e in prepared.events], [2, 9])

    def test_repeated_events_are_all_kept_in_time_order(self):
        timeline = [event("Gel applied", 9, event_id="g3"), event("first_paddle_taken", 12, event_id="f2"),
                    event("Gel applied", 2, event_id="g1"), event("first_paddle_taken", 11, event_id="f1"),
                    event("Gel applied", 5, event_id="g2"),
                    event("stand_clear_command", 20, "audio", 0.9, event_id="c1"),
                    event("stand_clear_command", 21, "audio", 0.9, event_id="c2")]
        prepared = prepare_timeline(timeline, CONFIG)
        self.assertEqual([e.event_id for e in prepared.named("gel_applied")], ["g1", "g2", "g3"])
        self.assertEqual([e.event_id for e in prepared.named("first_paddle_taken")], ["f1", "f2"])
        self.assertEqual([e.event_id for e in prepared.named("stand_clear_command")], ["c1", "c2"])
        self.assertEqual(len(prepared.events), len(timeline))  # none merged or dropped

    def test_order_uses_start_time(self):
        long = Event("Gel applied", 1, 10, "annotation", 1.0, event_id="long")
        short = Event("Gel applied", 2, 3, "annotation", 1.0, event_id="short")
        self.assertEqual([e.event_id for e in prepare_timeline([short, long], CONFIG).events], ["long", "short"])

    def test_input_is_not_modified(self):
        original = [event("Gel applied", 3)]
        prepare_timeline(original, CONFIG)
        self.assertEqual(original[0].event_name, "Gel applied")


class ConfidenceThreshold(unittest.TestCase):
    def test_below_threshold_is_excluded_and_logged(self):
        low = event("stand_clear_command", 4, "audio", 0.3, event_id="a1")
        prepared = prepare_timeline([low], CONFIG)
        self.assertEqual(prepared.events, ())
        excluded = prepared.excluded[0]
        self.assertEqual((excluded.event_id, excluded.event_name, excluded.confidence, excluded.threshold,
                          excluded.reason), ("a1", "stand_clear_command", 0.3, 0.5, "below_confidence_threshold"))

    def test_exactly_at_threshold_is_kept(self):
        self.assertEqual(len(prepare_timeline([event("stand_clear_command", 4, "audio", 0.5)], CONFIG).events), 1)

    def test_threshold_is_per_source(self):
        prepared = prepare_timeline([event("Gel applied", 1, "annotation", 0.9),     # below annotation 1.0
                                     event("stand_clear_command", 2, "audio", 0.9)], CONFIG)  # above audio 0.5
        self.assertEqual([e.event_name for e in prepared.events], ["stand_clear_command"])
        self.assertEqual([e.source for e in prepared.excluded], ["annotation"])

    def test_threshold_zero_disables_the_check(self):
        config = with_thresholds(annotation=0, video=0, audio=0)
        prepared = prepare_timeline([event("Gel applied", 1, "annotation", 0.0),
                                     event("stand_clear_command", 2, "audio", 0.01)], config)
        self.assertEqual(len(prepared.events), 2)
        self.assertEqual(prepared.excluded, ())

    def test_source_without_threshold_is_a_clear_error(self):
        config = with_thresholds(annotation=1.0, audio=0.5)  # no video threshold
        with self.assertRaisesRegex(TimelineError, "source 'video', which has no confidence threshold") as caught:
            prepare_timeline([event("shock_delivered_on_screen", 5, "video", 0.9)], config)
        self.assertEqual(caught.exception.code, "no_confidence_threshold")

    def test_excluded_events_can_be_looked_up_by_canonical_name(self):
        prepared = prepare_timeline([event("Gel applied", 7, "annotation", 0.4, event_id="late"),
                                     event("Gel applied", 3, "annotation", 0.6, event_id="early"),
                                     event("stand_clear_command", 4, "audio", 0.1)], CONFIG)
        self.assertEqual(prepared.named("gel_applied"), [])
        low = prepared.excluded_named("gel_applied")
        self.assertEqual([(e.event_id, e.start) for e in low], [("early", 3), ("late", 7)])

    def test_excluded_events_do_not_count_towards_anomalies(self):
        prepared = prepare_timeline([event("shock_delivered_on_screen", 5, "video", 0.9, event_id="s1"),
                                     event("shock_delivered_on_screen", 8, "video", 0.2, event_id="s2")], CONFIG)
        self.assertFalse(prepared.has_anomaly("multiple_shocks"))
        self.assertEqual([e.event_id for e in prepared.named("shock_delivered_on_screen")], ["s1"])


class Anomalies(unittest.TestCase):
    def test_one_shock_is_normal(self):
        self.assertEqual(prepare_timeline([event("shock_delivered_on_screen", 5)], CONFIG).anomalies, ())

    def test_more_than_one_shock_is_flagged_with_both_events(self):
        prepared = prepare_timeline([event("shock_delivered_on_screen", 5, event_id="s1"),
                                     event("shock_delivered_on_screen", 30, event_id="s2")], CONFIG)
        anomaly = prepared.anomalies[0]
        self.assertEqual((anomaly.code, anomaly.event_ids), ("multiple_shocks", ("s1", "s2")))
        self.assertFalse(anomaly.details["within_simultaneous_window"])
        self.assertNotIn("possibly the same shock", anomaly.message)

    def test_close_shocks_are_kept_but_marked_possibly_the_same(self):
        prepared = prepare_timeline([event("shock_delivered_on_screen", 5.0, event_id="s1"),
                                     event("shock_delivered_on_screen", 5.3, event_id="s2")], CONFIG)
        anomaly = prepared.anomaly("multiple_shocks")
        self.assertEqual(anomaly.event_ids, ("s1", "s2"))  # not merged
        self.assertEqual(len(prepared.named("shock_delivered_on_screen")), 2)
        self.assertTrue(anomaly.details["within_simultaneous_window"])
        self.assertAlmostEqual(anomaly.details["smallest_gap_seconds"], 0.3)
        self.assertIn("possibly the same shock detected twice", anomaly.message)

    def test_no_shock_is_not_an_anomaly(self):
        # A missing shock is R5's finding, not a data anomaly.
        self.assertEqual(prepare_timeline([event("Gel applied", 1)], CONFIG).anomalies, ())

    def test_human_and_model_evidence_for_one_event_is_flagged(self):
        prepared = prepare_timeline([event("shock_delivered_on_screen", 5, "annotation", event_id="h"),
                                     Event("shock_delivered_on_screen", 5.1, 5.1, "video", 0.9, event_id="m")],
                                    CONFIG)
        self.assertTrue(prepared.has_anomaly("mixed_evidence_sources"))

    def test_unknown_labels_raise_a_warning_anomaly(self):
        prepared = prepare_timeline([event("gel applied", 1, event_id="u1"),
                                     event("stop_cpr", 2, "audio", 0.9, event_id="u2"),
                                     event("Gel applied", 3)], CONFIG)
        anomaly = prepared.anomaly("unknown_labels_present")
        self.assertEqual(anomaly.event_ids, ("u1", "u2"))
        self.assertEqual(anomaly.details["labels"], ["annotation:gel applied", "audio:stop_cpr"])

    def test_known_labels_raise_no_warning(self):
        self.assertFalse(prepare_timeline([event("Gel applied", 1)], CONFIG).has_anomaly("unknown_labels_present"))

    def test_empty_timeline_is_valid(self):
        prepared = prepare_timeline([], CONFIG)
        self.assertEqual((prepared.events, prepared.anomalies, prepared.sources), ((), (), frozenset()))

    def test_sources_present_are_recorded(self):
        prepared = prepare_timeline([event("Gel applied", 1), event("stand_clear_command", 2, "audio", 0.2)], CONFIG)
        self.assertEqual(prepared.sources, {"annotation", "audio"})  # includes sources of excluded events


def with_counts(**values):
    counts = {**CONFIG.engine.expected_counts,
              **{name: Setting(f"expected_counts.{name}", value) for name, value in values.items()}}
    return replace(CONFIG, engine=replace(CONFIG.engine, expected_counts=counts))


def counts(prepared):
    return [a for a in prepared.anomalies if a.code == "count_violation"]


class ExpectedCounts(unittest.TestCase):
    """P-005, D-071: confident events per canonical event against engine.yaml expected_counts."""

    def test_exactly_one_met_raises_nothing(self):
        self.assertEqual(counts(prepare_timeline([event("first_paddle_taken", 5)], CONFIG)), [])

    def test_exactly_one_found_twice_names_the_event_counts_and_ids(self):
        prepared = prepare_timeline([event("first_paddle_taken", 5, event_id="t1"),
                                     event("first_paddle_taken", 20, event_id="t2")], CONFIG)
        anomaly, = counts(prepared)
        self.assertEqual(anomaly.event_ids, ("t1", "t2"))
        self.assertEqual({k: anomaly.details[k] for k in ("event", "expected", "found", "possible_duplicates")},
                         {"event": "first_paddle_taken", "expected": {"exactly": 1}, "found": 2,
                          "possible_duplicates": []})
        self.assertIn("first_paddle_taken: expected exactly 1, found 2 confident events", anomaly.message)
        self.assertNotIn("possibly the same", anomaly.message)
        self.assertEqual(len(prepared.named("first_paddle_taken")), 2)  # kept, not merged

    def test_no_events_is_missing_not_a_count_violation(self):
        # A-018: a missing event is decided by the coverage step and the rules.
        self.assertEqual(counts(prepare_timeline([event("Gel applied", 1)], CONFIG)), [])

    def test_only_confident_events_are_counted(self):
        prepared = prepare_timeline([event("second_paddle_taken", 5, "video", 0.9, event_id="v1"),
                                     event("second_paddle_taken", 9, "video", 0.2, event_id="v2")], CONFIG)
        self.assertEqual(counts(prepared), [])

    def test_unlimited_is_never_a_violation(self):
        commands = [event("stand_clear_command", t, "audio", 0.9) for t in (1, 2, 3, 4)]
        self.assertEqual(counts(prepare_timeline(commands, CONFIG)), [])

    def test_undecided_count_is_not_checked(self):
        gel = [event("Gel applied", t) for t in (1, 2, 3, 4, 5)]
        self.assertIsNone(CONFIG.engine.expected_counts["gel_applied"].value)
        self.assertEqual(counts(prepare_timeline(gel, CONFIG)), [])

    def test_at_least(self):
        config = with_counts(gel_applied={"at_least": 2})
        self.assertEqual(counts(prepare_timeline([event("Gel applied", 1), event("Gel applied", 5)], config)), [])
        anomaly, = counts(prepare_timeline([event("Gel applied", 1)], config))
        self.assertEqual((anomaly.details["expected"], anomaly.details["found"]), ({"at_least": 2}, 1))
        self.assertNotIn("possible_duplicates", anomaly.details)  # only for events limited to one

    def test_at_most(self):
        config = with_counts(gel_applied={"at_most": 2})
        self.assertEqual(counts(prepare_timeline([event("Gel applied", 1), event("Gel applied", 1.1)], config)), [])
        anomaly, = counts(prepare_timeline([event("Gel applied", t) for t in (1, 1.1, 1.2)], config))
        self.assertEqual((anomaly.details["expected"], anomaly.details["found"]), ({"at_most": 2}, 3))
        self.assertNotIn("possible_duplicates", anomaly.details)

    def test_exactly_more_than_one(self):
        config = with_counts(gel_applied={"exactly": 2})
        self.assertEqual(counts(prepare_timeline([event("Gel applied", 1), event("Gel applied", 5)], config)), [])
        for times in ((1,), (1, 5, 9)):
            with self.subTest(times=times):
                anomaly, = counts(prepare_timeline([event("Gel applied", t) for t in times], config))
                self.assertEqual(anomaly.details["found"], len(times))

    def test_every_violation_is_reported_separately_in_name_order(self):
        prepared = prepare_timeline([event("second_paddle_taken", t, event_id=f"s{t}") for t in (5, 9)]
                                    + [event("first_paddle_taken", t, event_id=f"f{t}") for t in (1, 3)], CONFIG)
        self.assertEqual([a.details["event"] for a in counts(prepared)], ["first_paddle_taken", "second_paddle_taken"])

    def test_two_shocks_raise_both_the_shock_anomaly_and_the_count(self):
        prepared = prepare_timeline([event("shock_delivered_on_screen", t, event_id=f"s{t}") for t in (30, 60)],
                                    CONFIG)
        self.assertEqual([a.code for a in prepared.anomalies], ["multiple_shocks", "count_violation"])


class PossibleDuplicates(unittest.TestCase):
    def test_extra_event_within_the_window_is_marked(self):
        prepared = prepare_timeline([event("paddles_removed_after_shock", 40.0, event_id="r1"),
                                     event("paddles_removed_after_shock", 40.3, event_id="r2")], CONFIG)
        anomaly, = counts(prepared)
        self.assertEqual(anomaly.details["possible_duplicates"], [["r1", "r2"]])
        self.assertEqual(anomaly.details["simultaneous_window_seconds"], 0.5)
        self.assertIn("possibly the same incident detected twice", anomaly.message)

    def test_only_the_close_pair_is_marked(self):
        prepared = prepare_timeline([event("first_paddle_taken", t, event_id=f"t{t}") for t in (5.0, 5.4, 20.0)],
                                    CONFIG)
        self.assertEqual(counts(prepared)[0].details["possible_duplicates"], [["t5.0", "t5.4"]])

    def test_exactly_at_the_window_counts_as_close(self):
        prepared = prepare_timeline([event("first_paddle_taken", t, event_id=f"t{t}") for t in (5.0, 5.5)], CONFIG)
        self.assertEqual(counts(prepared)[0].details["possible_duplicates"], [["t5.0", "t5.5"]])

    def test_at_most_one_is_also_limited_to_one(self):
        config = with_counts(gel_applied={"at_most": 1})
        prepared = prepare_timeline([event("Gel applied", 1.0, event_id="g1"),
                                     event("Gel applied", 1.2, event_id="g2")], config)
        self.assertEqual(counts(prepared)[0].details["possible_duplicates"], [["g1", "g2"]])


class PaddleIdentity(unittest.TestCase):
    def identity(self, *timeline):
        return prepare_timeline(list(timeline), CONFIG).anomaly("paddle_identity_conflict")

    def test_two_apical_and_no_sternal(self):
        anomaly = self.identity(event("apical_paddle_placed", 10, event_id="a1"),
                                event("apical_paddle_placed", 14, event_id="a2"))
        self.assertEqual(anomaly.event_ids, ("a1", "a2"))
        self.assertEqual(anomaly.details, {"apical_paddle_placed": 2, "sternal_paddle_placed": 0})
        self.assertIn("2 apical_paddle_placed and no sternal_paddle_placed", anomaly.message)

    def test_two_sternal_and_no_apical(self):
        anomaly = self.identity(event("sternal_paddle_placed", 10), event("sternal_paddle_placed", 14),
                                event("sternal_paddle_placed", 18))
        self.assertEqual(anomaly.details, {"apical_paddle_placed": 0, "sternal_paddle_placed": 3})

    def test_one_of_each_or_one_alone_is_no_conflict(self):
        for timeline in ([event("apical_paddle_placed", 10), event("sternal_paddle_placed", 14)],
                         [event("apical_paddle_placed", 10)], []):
            with self.subTest(timeline=[e.event_name for e in timeline]):
                self.assertIsNone(self.identity(*timeline))

    def test_two_apical_and_one_sternal_is_a_count_problem_not_identity(self):
        prepared = prepare_timeline([event("apical_paddle_placed", 10), event("apical_paddle_placed", 14),
                                     event("sternal_paddle_placed", 12)], CONFIG)
        self.assertFalse(prepared.has_anomaly("paddle_identity_conflict"))
        self.assertEqual([a.details["event"] for a in counts(prepared)], ["apical_paddle_placed"])

    def test_low_confidence_placements_do_not_count(self):
        self.assertIsNone(self.identity(Event("apical_paddle_placed", 10, 10, "video", 0.9, event_id="a1"),
                                        Event("apical_paddle_placed", 14, 14, "video", 0.1, event_id="a2")))

    def test_conflict_is_never_a_fail_by_itself(self):
        prepared = prepare_timeline([event("apical_paddle_placed", 10), event("apical_paddle_placed", 14)], CONFIG)
        self.assertEqual({a.code for a in prepared.anomalies}, {"count_violation", "paddle_identity_conflict"})
        self.assertEqual(len(prepared.named("apical_paddle_placed")), 2)  # nothing removed or judged


class MalformedInput(unittest.TestCase):
    def assertRejected(self, timeline, message, code):
        with self.assertRaisesRegex(TimelineError, message) as caught:
            prepare_timeline(timeline, CONFIG)
        self.assertEqual(caught.exception.code, code)

    def test_not_a_list(self):
        self.assertRejected(42, "list of events", "not_a_list")
        self.assertRejected({"events": []}, "list of events", "not_a_list")

    def test_raw_dict_instead_of_event(self):
        self.assertRejected([{"event_name": "Gel applied", "start": 1}], r"timeline\[0\] is dict", "not_an_event")

    def test_missing_event_id(self):
        self.assertRejected([Event("Gel applied", 1, 1, "annotation", 1.0)], "has no event_id", "missing_event_id")

    def test_duplicate_event_id(self):
        self.assertRejected([event("Gel applied", 1, event_id="x"), event("Gel applied", 5, event_id="x")],
                            "duplicate event_id 'x'", "duplicate_event_id")

    def test_two_camera_angles(self):
        self.assertRejected([event("Gel applied", 1, camera_angle="T"), event("Gel applied", 5, camera_angle="LS")],
                            r"mixes camera angles \['LS', 'T'\]", "multiple_camera_angles")

    def test_audio_without_camera_angle_is_not_a_second_angle(self):
        timeline = [Event("shock_delivered_on_screen", 5, 5, "video", 0.9, camera_angle="LS", event_id="v1"),
                    Event("paddles_removed_after_shock", 7, 7, "video", 0.9, camera_angle="LS", event_id="v2"),
                    Event("stand_clear_command", 3, 3.5, "audio", 0.9, event_id="a1"),
                    Event("oxygen_away_command", 1, 1.5, "audio", 0.9, event_id="a2")]
        prepared = prepare_timeline(timeline, CONFIG)
        self.assertEqual(len(prepared.events), 4)

    def test_two_recordings(self):
        self.assertRejected([event("Gel applied", 1, metadata={"task_id": "P01_T"}),
                             event("Gel applied", 5, metadata={"task_id": "P02_T"})], "mixes recordings", "multiple_recordings")

    def test_invalid_event_values_are_already_rejected_by_the_shared_schema(self):
        with self.assertRaises(ValueError):
            Event("Gel applied", 5, 1, "annotation", 1.0, event_id="x")  # end before start


class PipelineTimeline(unittest.TestCase):
    def test_sample_fixture_after_merge_prepares_cleanly(self):
        raw = [Event.from_dict(e) for e in json.loads((ROOT / "tests/fixtures/sample_timeline.json").read_text())]
        prepared = prepare_timeline(merge_timeline(raw), CONFIG)
        self.assertEqual(prepared.unknown_labels, ())
        self.assertEqual(prepared.anomalies, ())
        self.assertEqual({e.event_name for e in prepared.events},
                         {"stand_clear_command", "object_visible:paddle_sternal", "charging_sound"})


if __name__ == "__main__":
    unittest.main()
