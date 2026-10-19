"""Step 9d: per-zone gel applications derived from the learner_hand and zone boxes (D-111, D-112)."""
from dataclasses import replace
from types import SimpleNamespace
import copy
import math
import unittest

import yaml

from annotation.build_yolo_video_dataset import Track
from annotation.derive_gel_applications import (
    AMBIGUOUS,
    GelReview,
    derive_gel,
    derived_gel_approved,
    gel_validation_markdown,
    gel_validation_summary,
    load_gel_settings,
)
from annotation.export_rule_engine_records import DEFAULT_CONFIG, VideoInfo, load_config

VIDEO = VideoInfo(25.0, 1920, 1080, None)
DIAGONAL = math.hypot(1920, 1080)                      # about 2203 px
EXPORT = load_config()
SETTINGS = EXPORT.gel                                   # gap 0.05 (about 110 px), dwell 10, ratio 2, exit 5, tags 30
APICAL, STERNAL = "apical_placement_zone", "sternal_placement_zone"
APICAL_BOX, STERNAL_BOX = (100, 100, 300, 300), (1200, 100, 1400, 300)
FAR = (900, 800, 960, 860)                              # the hand away from both zones
CONFIG_DATA = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))


def rect(frame, box, outside=False):
    return {"type": "rectangle", "frame": frame, "points": list(box), "outside": outside, "rotation": 0}


def beside_apical(gap_px):
    """A 60 x 60 hand box gap_px to the right of the apical zone."""
    x1 = 300 + gap_px
    return (x1, 150, x1 + 60, 210)


def hand(*visits, start=5, end=70, hidden=()):
    """The bottle hand from start to end: FAR, except (first, last, box) visits; hidden = (first, last) runs."""
    shapes = [rect(start, FAR)]
    for first, last, box in visits:
        shapes += [rect(first - 1, FAR), rect(first, box), rect(last, box), rect(last + 1, FAR)]
    for first, last in hidden:
        shapes += [rect(first - 1, FAR), rect(first, FAR, outside=True), rect(last + 1, FAR)]
    shapes += [rect(end, FAR), rect(end + 1, FAR, outside=True)]
    return Track("learner_hand", sorted(shapes, key=lambda s: s["frame"]))


def zones(apical=APICAL_BOX, sternal=STERNAL_BOX, sternal_from=0):
    tracks = [Track(APICAL, [rect(0, apical)])]
    if sternal is not None:
        tracks.append(Track(STERNAL, [rect(sternal_from, sternal)] if not sternal_from else
                            [rect(0, sternal, outside=True), rect(sternal_from, sternal)]))
    return tracks


def video(tracks, tags=(("first_paddle_firmly_on_the_chest", 80),), stop=99):
    return SimpleNamespace(canonical_task_id="P01_LS", camera_view="LS", archive="a.zip", task_path=".", start_frame=0,
                           stop_frame=stop, tags=[{"label": l, "frame": f} for l, f in tags], tracks=list(tracks),
                           standalone_shapes=[])


def run(source, settings=SETTINGS, placements=()):
    issues = []
    events, record, rows = derive_gel(source, VIDEO, settings, list(placements), issues)
    return events, {z["zone_label"]: z for z in record["zones"]}, {r["zone"]: r for r in rows}, issues, record


def frames(events, zone=None):
    return [e["frame"] for e in events if zone is None or e["metadata"]["zone_label"] == zone]


class Proximity(unittest.TestCase):
    def test_hand_touching_a_zone_is_an_application(self):
        events, status, _, _, _ = run(video([*zones(), hand((20, 35, beside_apical(0)))]))
        self.assertEqual(frames(events), [20])
        event = events[0]
        self.assertEqual((event["event_name"], event["flags"], event["method"]),
                         ("apical_gel_applied", ["derived_gel_application"], "hand_near_zone_v1"))
        self.assertEqual((event["metadata"]["zone_label"], event["metadata"]["dwell_frames"]), (APICAL, 16))
        self.assertEqual(event["metadata"]["settings_sha256"], SETTINGS.digest())
        self.assertEqual((status[APICAL]["status"], status[STERNAL]["status"]), ("gelled", "not_gelled"))

    def test_gap_at_the_threshold_counts_and_beyond_it_does_not(self):
        at = SETTINGS.max_gap * DIAGONAL - 0.01
        self.assertEqual(frames(run(video([*zones(), hand((20, 35, beside_apical(at)))]))[0]), [20])
        beyond = SETTINGS.max_gap * DIAGONAL + 1
        events, status, rows, _, _ = run(video([*zones(), hand((20, 35, beside_apical(beyond)))]))
        self.assertEqual(events, [])
        self.assertEqual(status[APICAL]["status"], "not_gelled")
        self.assertAlmostEqual(rows[APICAL]["smallest_gap"], round(beyond / DIAGONAL, 4))

    def test_overlap_is_not_required(self):
        """A-023, A-025: gel can be applied near the zone; proximity, not overlap."""
        events, _, _, _, _ = run(video([*zones(), hand((20, 35, beside_apical(60)))]))   # about 2.7% away
        self.assertEqual(frames(events, APICAL), [20])


class NearestZone(unittest.TestCase):
    NEAR_STERNAL = (420, 100, 620, 300)    # a second zone 120 px to the right of the apical zone

    def test_the_clearly_nearer_zone_gets_the_application(self):
        events, _, _, _, _ = run(video([*zones(sternal=self.NEAR_STERNAL), hand((20, 35, beside_apical(5)))]))
        self.assertEqual([e["event_name"] for e in events], ["apical_gel_applied"])   # 5 px against 55 px

    def test_about_as_near_to_both_is_ambiguous_and_no_application(self):
        source = video([*zones(sternal=self.NEAR_STERNAL), hand((20, 35, beside_apical(30)))])   # 30 px each
        events, status, rows, _, _ = run(source)
        self.assertEqual(events, [])
        self.assertEqual(rows[APICAL]["ambiguous_frames"], 16)
        self.assertEqual((status[APICAL]["status"], status[STERNAL]["status"]), ("not_gelled", "not_gelled"))

    def test_ratio_decides_clearly_nearer(self):
        source = video([*zones(sternal=self.NEAR_STERNAL), hand((20, 35, beside_apical(20)))])   # 20 px against 40 px
        self.assertEqual(frames(run(source)[0]), [20])                                   # exactly 2x: clearly nearer
        self.assertEqual(run(source, replace(SETTINGS, nearer_ratio=2.5))[0], [])        # not 2.5x: ambiguous

    def test_the_other_zone_not_visible_does_not_block_the_match(self):
        events, status, _, _, _ = run(video([*zones(sternal=None), hand((20, 35, beside_apical(0)))]))
        self.assertEqual(frames(events, APICAL), [20])
        self.assertEqual(status[STERNAL]["status"], "unknown")


class Visits(unittest.TestCase):
    def test_a_short_dip_stays_in_one_visit(self):
        events, _, _, _, _ = run(video([*zones(), hand((20, 29, beside_apical(0)), (35, 44, beside_apical(0)))]))
        self.assertEqual(frames(events), [20])                    # out on frames 30-34 (5 = exit frames)
        self.assertEqual(events[0]["metadata"]["dwell_frames"], 20)

    def test_a_longer_dip_starts_a_new_visit_and_each_counts(self):
        events, _, _, _, _ = run(video([*zones(), hand((20, 29, beside_apical(0)), (36, 45, beside_apical(0)))]))
        self.assertEqual(frames(events), [20, 36])                # out on frames 30-35 (6)
        self.assertEqual([e["metadata"]["application"] for e in events], [1, 2])

    def test_too_short_a_visit_is_not_an_application(self):
        events, _, rows, _, _ = run(video([*zones(), hand((20, 28, beside_apical(0)))]))   # 9 frames < 10
        self.assertEqual(events, [])
        self.assertEqual(rows[APICAL]["dwell_frames"], 9)

    def test_both_zones_in_either_order(self):
        source = video([*zones(), hand((20, 35, (1400, 150, 1460, 210)), (45, 60, beside_apical(0)))])
        events, status, _, _, _ = run(source)
        self.assertEqual([(e["event_name"], e["frame"]) for e in events],
                         [("sternal_gel_applied", 20), ("apical_gel_applied", 45)])
        self.assertEqual({z["status"] for z in status.values()}, {"gelled"})


class CouldHaveBeenMissed(unittest.TestCase):
    def test_hidden_hand_frames_make_a_zone_without_an_application_unknown(self):
        source = video([*zones(), hand((20, 35, beside_apical(0)), hidden=((50, 55),))])
        _, status, rows, _, record = run(source)
        self.assertEqual((status[APICAL]["status"], status[STERNAL]["status"]), ("gelled", "unknown"))
        self.assertIn("hand hidden on 6 frames", status[STERNAL]["reason"])
        self.assertEqual((record["bottle"]["start_frame"], record["bottle"]["end_frame"], record["bottle"]["hidden_frames"]),
                         (5, 70, 6))

    def test_a_zone_not_visible_throughout_the_bottle_period_is_unknown(self):
        _, status, _, _, _ = run(video([*zones(sternal_from=30), hand((40, 55, beside_apical(0)))]))
        self.assertEqual(status[STERNAL]["status"], "unknown")
        self.assertIn("zone not visible throughout", status[STERNAL]["reason"])

    def test_no_hand_track_in_the_gel_phase_is_unknown_and_a_review_issue(self):
        source = video([*zones(), Track("learner_hand", [rect(85, FAR)])])   # only after the gel phase (ends at 80)
        events, status, rows, issues, record = run(source)
        self.assertEqual(events, [])
        self.assertEqual({z["status"] for z in status.values()}, {"unknown"})
        self.assertEqual([i.code for i in issues], ["gel_hand_not_tracked"])
        self.assertIsNone(record["bottle"])
        self.assertEqual(rows[APICAL]["bottle_start_frame"], "")


class GelPhase(unittest.TestCase):
    def test_ends_at_the_first_placement_tag(self):
        _, _, _, _, record = run(video([*zones(), hand((20, 35, beside_apical(0)))]))
        self.assertEqual((record["phase"]["end_frame"], record["phase"]["ended_by"]), (80, "first_paddle_firmly_on_the_chest"))

    def test_else_at_the_derived_placement_else_at_first_paddle_taken(self):
        tracks = [*zones(), hand((20, 35, beside_apical(0)))]
        _, _, _, _, record = run(video(tracks, tags=[("first_paddle_taken", 75)]),
                                 placements=[{"frame": 60, "event_name": "sternal_paddle_placed"}])
        self.assertEqual((record["phase"]["end_frame"], record["phase"]["ended_by"]), (60, "derived placement"))
        _, _, _, _, record = run(video(tracks, tags=[("first_paddle_taken", 75)]))
        self.assertEqual((record["phase"]["end_frame"], record["phase"]["ended_by"]), (75, "first_paddle_taken"))
        _, _, _, _, record = run(video(tracks, tags=[]))
        self.assertEqual(record["phase"]["ended_by"], "end of recording")

    def test_the_earliest_placement_of_either_paddle_ends_it(self):
        """D-118: a sternal placement before the apical tag ends the phase; the apical tag wins over the
        derived apical placement; with only takes, the earliest take of either paddle ends it."""
        tracks = [*zones(), hand((20, 35, beside_apical(0)))]
        sternal_first = [{"frame": 50, "event_name": "sternal_paddle_placed"}, {"frame": 78, "event_name": "apical_paddle_placed"}]
        _, _, _, _, record = run(video(tracks), placements=sternal_first)          # T1 at 80
        self.assertEqual((record["phase"]["end_frame"], record["phase"]["ended_by"]), (50, "derived placement"))
        _, _, _, _, record = run(video(tracks), placements=[{"frame": 70, "event_name": "apical_paddle_placed"}])
        self.assertEqual(record["phase"]["end_frame"], 80)                          # the tag, not the derived 70
        _, _, _, _, record = run(video(tracks, tags=[("first_paddle_taken", 75), ("second_paddle_taken", 65)]))
        self.assertEqual((record["phase"]["end_frame"], record["phase"]["ended_by"]), (65, "second_paddle_taken"))

    def test_an_application_after_the_gel_phase_is_not_derived(self):
        events, _, _, _, _ = run(video([*zones(), hand((20, 35, beside_apical(0)), end=90)],
                                       tags=[("first_paddle_firmly_on_the_chest", 18)]))
        self.assertEqual(events, [])


class TagAgreement(unittest.TestCase):
    def test_a_tag_within_the_window_agrees(self):
        source = video([*zones(), hand((20, 35, beside_apical(0)))],
                       tags=[("Gel applied", 40), ("first_paddle_firmly_on_the_chest", 80)])
        events, _, rows, _, _ = run(source)
        self.assertEqual(events[0]["metadata"]["tag_frames"], [40])
        self.assertEqual((rows[APICAL]["tags_agreeing"], rows[APICAL]["disagreements"]), (1, ""))

    def test_disagreements_are_reported_both_ways_and_never_drop_an_event(self):
        source = video([*zones(), hand((20, 35, beside_apical(0)))],
                       tags=[("Gel applied", 75), ("first_paddle_firmly_on_the_chest", 80)])   # 40 frames after the visit
        events, _, rows, _, _ = run(source)
        self.assertEqual(frames(events), [20])
        self.assertIn("application at frame 20 has no Gel applied tag within 30 frames", rows[APICAL]["disagreements"])
        self.assertIn("Gel applied tags with no derived application: [75]", rows[STERNAL]["disagreements"])


class SettingsAndGate(unittest.TestCase):
    def test_repository_settings(self):
        self.assertEqual((SETTINGS.hand_label, SETTINGS.max_gap, SETTINGS.dwell_frames, SETTINGS.nearer_ratio,
                          SETTINGS.exit_frames, SETTINGS.tag_agreement_frames), ("learner_hand", 0.05, 10, 2.0, 5, 30))
        self.assertEqual([(z.zone, z.event, z.region) for z in SETTINGS.zones],
                         [(APICAL, "apical_gel_applied", "apical_gel"), (STERNAL, "sternal_gel_applied", "sternal_gel")])

    def test_digest_covers_the_settings_and_the_9c_settings_but_not_the_review(self):
        self.assertNotEqual(SETTINGS.digest(), replace(SETTINGS, dwell_frames=11).digest())
        self.assertNotEqual(SETTINGS.digest(), replace(SETTINGS, placement_settings_sha256="b" * 64).digest())
        self.assertEqual(SETTINGS.digest(), replace(SETTINGS, review=GelReview("A", "2026-10-17", "a" * 64, "b" * 64)).digest())

    def test_gate_only_for_the_reviewed_export_and_settings(self):
        manifest = {"export_id": "a" * 64, "gel_settings_sha256": SETTINGS.digest()}
        self.assertFalse(derived_gel_approved(SETTINGS, manifest))
        reviewed = replace(SETTINGS, review=GelReview("Arnikan", "2026-10-17", "a" * 64, SETTINGS.digest()))
        self.assertTrue(derived_gel_approved(reviewed, manifest))
        self.assertFalse(derived_gel_approved(reviewed, {**manifest, "export_id": "c" * 64}))
        self.assertFalse(derived_gel_approved(reviewed, {**manifest, "gel_settings_sha256": "c" * 64}))

    def test_invalid_settings_are_rejected(self):
        def rejected(message, change):
            data = copy.deepcopy(CONFIG_DATA["derived_gel"])
            change(data)
            with self.assertRaisesRegex(ValueError, message):
                load_gel_settings(data, (APICAL, STERNAL), EXPORT.placements, "derived_gel")
        rejected("exactly the keys", lambda d: d.pop("gel_dwell_frames"))
        rejected("greater than 0", lambda d: d.update(gel_hand_zone_max_gap={"value": 0}))
        rejected("at least 1", lambda d: d.update(gel_zone_nearer_ratio=0.5))
        rejected("own event and region", lambda d: d["zones"][STERNAL].update(region="apical_gel"))
        rejected("fill all of", lambda d: d["reviewed_for_r1"].update(reviewed_by="Arnikan"))


class ValidationReport(unittest.TestCase):
    def test_summary_and_markdown(self):
        source = video([*zones(), hand((20, 35, beside_apical(0)))],
                       tags=[("Gel applied", 25), ("Gel applied", 70), ("first_paddle_firmly_on_the_chest", 80)])
        _, _, rows, _, _ = run(source)
        summary = gel_validation_summary(list(rows.values()), SETTINGS, {"export_id": "x"})
        self.assertEqual((summary["videos"], summary["zones_gelled"], summary["zones_not_gelled"], summary["applications"],
                          summary["gel_tags_in_phase"], summary["gel_tags_agreeing"], summary["videos_with_disagreements"]),
                         (1, 1, 1, 1, 2, 1, 1))
        self.assertTrue(summary["smallest_gap"].startswith("min 0.0"))
        markdown = gel_validation_markdown(summary, list(rows.values()), SETTINGS)
        self.assertIn("# Derived gel application validation (Step 9d)", markdown)
        self.assertIn("Gel applied tags with no derived application: [70]", markdown)


if __name__ == "__main__":
    unittest.main()
