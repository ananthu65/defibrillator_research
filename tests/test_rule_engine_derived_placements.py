"""Step 9c: per-paddle placements derived from the annotated boxes (D-081, D-086 to D-089)."""
from dataclasses import replace
from types import SimpleNamespace
import copy
from pathlib import Path
import tempfile
import unittest

import yaml

from annotation.build_yolo_video_dataset import Track
from annotation.derive_paddle_placements import (
    PARALLEL,
    PlacementReview,
    derive_placements,
    derived_placements_approved,
    load_placement_settings,
    validation_markdown,
    validation_summary,
)
from annotation.export_rule_engine_records import DEFAULT_CONFIG, VideoInfo, load_config, simultaneous_window_seconds

VIDEO = VideoInfo(25.0, 1920, 1080, None)          # diagonal about 2203 px: 2% is about 44 px
SETTINGS = load_config().placements
APICAL_ZONE, STERNAL_ZONE = (100, 100, 300, 300), (600, 100, 800, 300)
FAR = (1000, 800, 1100, 900)
CONFIG_DATA = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))


def rect(frame, box, outside=False):
    return {"type": "rectangle", "frame": frame, "points": list(box), "outside": outside, "rotation": 0}


def inside(zone, dx=0):
    """A 100 x 100 paddle box centred in the zone, shifted by dx."""
    x1, y1, x2, y2 = zone
    cx, cy = (x1 + x2) / 2 + dx, (y1 + y2) / 2
    return (cx - 50, cy - 50, cx + 50, cy + 50)


def paddle(label, zone, placed, leave=None, back=None, box=None):
    """A paddle away from the zone, placed at `placed`, optionally leaving at `leave` and back at `back`."""
    box = box or inside(zone)
    shapes = [rect(0, FAR), rect(placed - 1, FAR), rect(placed, box)]
    if leave is not None:
        shapes += [rect(leave - 1, box), rect(leave, FAR)]
    if back is not None:
        shapes += [rect(back - 1, FAR), rect(back, box)]
    return Track(label, shapes)


def zone_track(label, box):
    return Track(label, [rect(0, box)])


def video(tracks, tags=(), view="LS", stop=99, shapes=()):
    return SimpleNamespace(canonical_task_id=f"P01_{view}", camera_view=view, archive="a.zip", task_path=".",
                           start_frame=0, stop_frame=stop, tags=[{"label": l, "frame": f} for l, f in tags],
                           tracks=list(tracks), standalone_shapes=list(shapes))


def two_zone(apical_at, sternal_at, t1=None, t2=None, **apical):
    tags = ([("first_paddle_firmly_on_the_chest", t1)] if t1 is not None else []) + \
           ([("paddles_firmly_on_chest", t2)] if t2 is not None else [])
    return video([zone_track("apical_placement_zone", APICAL_ZONE), zone_track("sternal_placement_zone", STERNAL_ZONE),
                  paddle("paddle_apical", APICAL_ZONE, apical_at, **apical),
                  paddle("paddle_sternal", STERNAL_ZONE, sternal_at)], tags)


def run(source, settings=SETTINGS):
    issues = []
    events, rows = derive_placements(source, VIDEO, settings, issues)
    return events, {r["paddle"]: r for r in rows}, issues


def frames(events, name=None):
    return [e["frame"] for e in events if name is None or e["event_name"] == name]


class Placement(unittest.TestCase):
    def test_both_paddles_placed_in_order(self):
        events, rows, issues = run(two_zone(20, 40, t1=21, t2=45))
        self.assertEqual([(e["event_name"], e["frame"]) for e in events],
                         [("apical_paddle_placed", 20), ("sternal_paddle_placed", 40)])
        event = events[0]
        self.assertEqual((event["id"], event["evidence_type"], event["flags"], event["method"], event["timestamp_seconds"]),
                         ("P01_LS_derived_001", "direct", ["derived_placement"], "paddle_in_zone_v2", 0.8))
        self.assertEqual(event["metadata"]["paddle_label"], "paddle_apical")
        self.assertEqual(event["metadata"]["settings_sha256"], SETTINGS.digest())
        self.assertEqual(issues, [])
        self.assertEqual(rows["paddle_apical"]["outcome"], "event")

    def test_overlap_boundary(self):
        half = (200, 150, 400, 250)    # 100 of its 200 px width inside the zone: exactly 0.5
        less = (202, 150, 402, 250)    # 98 of 200: 0.49
        for box, expected in ((half, [20]), (less, [])):
            with self.subTest(box=box):
                events, _, _ = run(two_zone(20, 25, t1=21, box=box))
                self.assertEqual(frames(events, "apical_paddle_placed"), expected)

    def test_steady_frames_boundary(self):
        for leave, expected in ((25, [20]), (24, [])):   # in on frames 20-24 (5) or 20-23 (4)
            with self.subTest(leave=leave):
                events, rows, _ = run(two_zone(20, 30, t1=21, leave=leave))
                self.assertEqual(frames(events, "apical_paddle_placed"), expected)
        self.assertIn("never settled", rows["paddle_apical"]["reason"])

    def test_centre_motion_boundary(self):
        # The paddle drifts by dx between frames 20 and 24, then stays: within 2% of the diagonal it is placed
        # at frame 20; beyond it, the first steady start is later.
        for dx, expected in ((43, [20]), (45, [21])):
            with self.subTest(dx=dx):
                source = two_zone(20, 30, t1=21)
                source.tracks[2] = Track("paddle_apical", [rect(0, FAR), rect(19, FAR), rect(20, inside(APICAL_ZONE)),
                                                           rect(24, inside(APICAL_ZONE, dx))])
                events, _, _ = run(source)
                self.assertEqual(frames(events, "apical_paddle_placed"), expected)

    def test_zone_not_visible_on_those_frames(self):
        source = two_zone(20, 30, t1=21)
        source.tracks[0] = Track("apical_placement_zone", [rect(0, APICAL_ZONE), rect(10, APICAL_ZONE, outside=True)])
        events, rows, _ = run(source)
        self.assertEqual(frames(events, "apical_paddle_placed"), [])
        self.assertGreater(rows["paddle_apical"]["frames_zone_not_visible"], 0)


class RePlacement(unittest.TestCase):
    def test_out_for_exit_frames_then_back_is_a_second_placement(self):
        events, _, _ = run(two_zone(20, 30, t1=21, leave=41, back=47))     # out on frames 41-46 (6)
        self.assertEqual(frames(events, "apical_paddle_placed"), [20, 47])
        self.assertEqual([e["metadata"]["placement"] for e in events if e["event_name"] == "apical_paddle_placed"], [1, 2])

    def test_episode_end_is_recorded_for_r6(self):
        """D-104: each placement records its last frame in the zone and whether a real exit ended it."""
        events, _, _ = run(two_zone(20, 30, t1=21, leave=41, back=47))
        apical = [e["metadata"] for e in events if e["event_name"] == "apical_paddle_placed"]
        self.assertEqual([(m["end_frame"], m["end_seconds"], m["ended_by_exit"]) for m in apical],
                         [(40, 1.6, True), (99, 3.96, False)])                  # the second runs to the end of the video
        sternal = [e["metadata"] for e in events if e["event_name"] == "sternal_paddle_placed"]
        self.assertEqual([(m["end_frame"], m["ended_by_exit"]) for m in sternal], [(99, False)])

    def test_a_short_dip_is_the_same_placement(self):
        events, _, _ = run(two_zone(20, 30, t1=21, leave=41, back=45))     # out on frames 41-44 (4)
        self.assertEqual(frames(events, "apical_paddle_placed"), [20])

    def test_exit_frames_is_its_own_setting(self):
        settings = replace(SETTINGS, exit_frames=3)
        events, _, _ = run(two_zone(20, 30, t1=21, leave=41, back=45), settings)
        self.assertEqual(frames(events, "apical_paddle_placed"), [20, 45])
        self.assertEqual(settings.steady_frames, 5)


class ZoneNotVisible(unittest.TestCase):
    """A-020, D-090: a frame where the zone isn't visible is unknown, neither in nor out of the zone."""

    def occluded(self, hidden_from, visible_again):
        source = two_zone(20, 30, t1=21)
        source.tracks[0] = Track("apical_placement_zone", [rect(0, APICAL_ZONE), rect(hidden_from, APICAL_ZONE, outside=True),
                                                           rect(visible_again, APICAL_ZONE)])
        return source

    def test_a_six_frame_occlusion_during_a_placement_is_one_placement(self):
        events, rows, _ = run(self.occluded(41, 47))      # zone hidden on frames 41-46; the paddle stays put
        self.assertEqual(frames(events, "apical_paddle_placed"), [20])
        self.assertEqual(rows["paddle_apical"]["frames_zone_not_visible"], 6)   # still counted for the report

    def test_a_real_six_frame_exit_with_the_zone_visible_is_two_placements(self):
        events, rows, _ = run(two_zone(20, 30, t1=21, leave=41, back=47))       # out on frames 41-46
        self.assertEqual(frames(events, "apical_paddle_placed"), [20, 47])
        self.assertEqual(rows["paddle_apical"]["frames_zone_not_visible"], 0)

    def test_unknown_frames_do_not_start_a_placement(self):
        # The paddle settles while the zone is hidden (frames 10-29); the placement starts only once the
        # zone is visible again and the paddle has been in for 5 frames.
        source = two_zone(15, 40, t1=31)
        source.tracks[0] = Track("apical_placement_zone", [rect(0, APICAL_ZONE), rect(10, APICAL_ZONE, outside=True),
                                                           rect(30, APICAL_ZONE)])
        events, _, _ = run(source)
        self.assertEqual(frames(events, "apical_paddle_placed"), [30])

    def test_out_frames_on_both_sides_of_an_occlusion_add_up_to_an_exit(self):
        # Out on frames 41-43, zone hidden on 44-49, out again on 50-51: 5 out frames with no in frame between
        # them is an exit, so the return at frame 60 is a re-placement.
        source = two_zone(20, 30, t1=21, leave=41, back=60)
        source.tracks[0] = Track("apical_placement_zone", [rect(0, APICAL_ZONE), rect(44, APICAL_ZONE, outside=True),
                                                           rect(50, APICAL_ZONE)])
        events, _, _ = run(source)
        self.assertEqual(frames(events, "apical_paddle_placed"), [20, 60])


class TracksPerLabel(unittest.TestCase):
    """D-087: placements are derived per paddle label across all its tracks, never per track."""

    def test_a_track_split_mid_placement_is_not_a_re_placement(self):
        source = two_zone(20, 30, t1=21)
        box = inside(APICAL_ZONE)
        source.tracks[2] = Track("paddle_apical", [rect(0, FAR), rect(19, FAR), rect(20, box), rect(50, box, outside=True)])
        source.tracks.append(Track("paddle_apical", [rect(50, box)]))     # a new track ID continues from frame 50
        events, _, issues = run(source)
        self.assertEqual(frames(events, "apical_paddle_placed"), [20])
        self.assertEqual(issues, [])

    def test_overlapping_tracks_of_one_paddle_give_no_event(self):
        source = two_zone(20, 30, t1=21)
        source.tracks.append(Track("paddle_apical", [rect(18, (500, 500, 600, 600)), rect(60, FAR, outside=True)]))
        events, rows, issues = run(source)
        self.assertEqual(frames(events, "apical_paddle_placed"), [])
        self.assertEqual([i.code for i in issues], ["placement_duplicate_paddle_box"])
        self.assertIn("training labels", issues[0].details)
        self.assertGreater(rows["paddle_apical"]["frames_overlapping_boxes"], 0)
        self.assertEqual(frames(events, "sternal_paddle_placed"), [30])   # the other paddle is unaffected


class TagChecks(unittest.TestCase):
    def test_t1_cross_checks_only_the_apical_placement(self):
        """D-118: T1 marks the apical placement (A-027); the sternal placement is never checked against it."""
        for t1, expected in ((35, [20, 40]), (36, [40])):     # the apical 15 frames from T1, then 16
            with self.subTest(t1=t1):
                events, rows, issues = run(two_zone(20, 40, t1=t1))
                self.assertEqual(frames(events), expected)
        self.assertEqual([(i.code, i.label) for i in issues], [("placement_disagrees_with_tag", "paddle_apical")])
        self.assertIn("16 frames from first_paddle_firmly_on_the_chest", rows["paddle_apical"]["reason"])
        self.assertEqual(rows["paddle_sternal"]["outcome"], "event")

    def test_sternal_first_keeps_both_placements(self):
        """D-118: a sternal-first video (sternal at frame 30, apical and T1 at 60) used to lose both."""
        events, rows, issues = run(two_zone(60, 30, t1=60))
        self.assertEqual([(e["event_name"], e["frame"]) for e in events],
                         [("sternal_paddle_placed", 30), ("apical_paddle_placed", 60)])
        self.assertEqual(issues, [])

    def test_one_zone_apical_placement_must_match_t1(self):
        def one_zone(placed, t1):
            return video([zone_track("apical_placement_zone", APICAL_ZONE), paddle("paddle_apical", APICAL_ZONE, placed),
                          paddle("paddle_sternal", STERNAL_ZONE, 30)],
                         [("first_paddle_firmly_on_the_chest", t1)], view="LL")
        for placed, t1, expected in ((20, 35, [20]), (20, 36, []), (50, 30, [])):   # T1 is the apical's own tag (A-027)
            with self.subTest(placed=placed, t1=t1):
                events, rows, _ = run(one_zone(placed, t1))
                self.assertEqual(frames(events), expected)
                self.assertIn("zone unknown", rows["paddle_sternal"]["reason"])

    def test_t1_missing_and_simultaneous_is_a_possible_parallel_placement(self):
        events, rows, issues = run(two_zone(20, 30))    # 10 frames = 0.4 s, within 0.5 s
        self.assertEqual(frames(events), [20, 30])
        self.assertTrue(all(e["flags"] == ["derived_placement", PARALLEL] for e in events))
        self.assertEqual(rows["paddle_apical"]["flags"], PARALLEL)
        self.assertEqual(issues, [])

    def test_t1_missing_otherwise_gives_no_events(self):
        for source in (two_zone(20, 33),                                   # 13 frames = 0.52 s apart
                       video([zone_track("apical_placement_zone", APICAL_ZONE),
                              paddle("paddle_apical", APICAL_ZONE, 20)], view="LL")):   # only one paddle derivable
            with self.subTest(view=source.camera_view):
                events, rows, issues = run(source)
                self.assertEqual(events, [])
                self.assertIn("is not tagged", rows["paddle_apical"]["reason"])
                self.assertEqual(issues, [])    # expected when only the parallel case is untagged: not a review item

    def test_t2_used_only_when_present(self):
        events, rows, issues = run(two_zone(20, 70, t1=21, t2=45))         # sternal 25 frames after T2
        self.assertEqual(frames(events), [20])
        self.assertIn("after paddles_firmly_on_chest", rows["paddle_sternal"]["reason"])
        events, _, _ = run(two_zone(20, 70, t1=21))                        # no T2: not checked
        self.assertEqual(frames(events), [20, 70])

    def test_parallel_placement_failing_t2_drops_both(self):
        source = two_zone(60, 65, t2=40)
        events, _, _ = run(source)
        self.assertEqual(events, [])


class ValidationReport(unittest.TestCase):
    def test_rows_report_what_was_reached_for_tuning(self):
        _, rows, _ = run(two_zone(20, 40, t1=21, box=(202, 150, 402, 250)))   # apical never reaches 0.5
        apical = rows["paddle_apical"]
        self.assertEqual((apical["outcome"], apical["highest_overlap"], apical["steady_frames_achieved"]),
                         ("no_event", 0.49, 0))
        sternal = rows["paddle_sternal"]
        self.assertEqual((sternal["highest_overlap"], sternal["steady_frames_achieved"], sternal["centre_motion_of_diagonal"]),
                         (1.0, 50, 0.0))     # steady frames are reported up to 50

    def test_summary_counts_and_distributions(self):
        rows = []
        for source in (two_zone(20, 40, t1=21), two_zone(20, 30), two_zone(20, 40, t1=50)):
            source.canonical_task_id = f"P0{len(rows) // 2 + 1}_LS"
            rows += list(run(source)[1].values())
        summary = validation_summary(rows, SETTINGS, {"export_id": "x" * 64})
        self.assertEqual((summary["videos"], summary["videos_both_paddles"], summary["videos_no_paddle"]), (3, 2, 0))
        self.assertEqual(summary["videos_possible_parallel_placement"], 1)
        self.assertEqual((summary["two_zone_videos_checkable_against_t1"], summary["two_zone_videos_agreeing_with_t1"]), (2, 1))
        self.assertIn("median", summary["highest_overlap"])
        text = validation_markdown(summary, rows, SETTINGS)
        self.assertIn("## Disagreements with the tags (1)", text)   # only the apical placement is checked
        self.assertIn("## Possible parallel placements (1 videos)", text)
        self.assertIn(SETTINGS.digest(), text)


class Gate(unittest.TestCase):
    """D-088: an approval applies only to the reviewed export and the reviewed settings."""

    def test_approved_only_for_the_reviewed_export_and_settings(self):
        manifest = {"export_id": "a" * 64, "placement_settings_sha256": SETTINGS.digest()}
        self.assertFalse(derived_placements_approved(SETTINGS, manifest))    # nothing reviewed yet
        reviewed = replace(SETTINGS, review=PlacementReview("Arnikan", "2026-10-16", "a" * 64, SETTINGS.digest()))
        self.assertTrue(derived_placements_approved(reviewed, manifest))
        self.assertFalse(derived_placements_approved(reviewed, {**manifest, "export_id": "b" * 64}))
        changed = replace(reviewed, steady_frames=6)
        self.assertFalse(derived_placements_approved(changed, {**manifest, "placement_settings_sha256": changed.digest()}))

    def test_settings_digest_ignores_the_review_record(self):
        self.assertEqual(SETTINGS.digest(), replace(SETTINGS, review=PlacementReview("A", "2026-10-16", "a" * 64, "b" * 64)).digest())
        self.assertNotEqual(SETTINGS.digest(), replace(SETTINGS, exit_frames=6).digest())

    def test_review_record_must_be_complete(self):
        data = copy.deepcopy(CONFIG_DATA["derived_placements"])
        data["reviewed_for_r8"]["reviewed_by"] = "Arnikan"
        with self.assertRaisesRegex(ValueError, "fill all of"):
            load_placement_settings(data, ("apical_placement_zone", "sternal_placement_zone"),
                                    ("paddle_apical", "paddle_sternal"), 0.5, "test")


class Configuration(unittest.TestCase):
    def test_repository_settings(self):
        self.assertEqual((SETTINGS.min_overlap_of_paddle, SETTINGS.steady_frames, SETTINGS.max_centre_motion_of_diagonal,
                          SETTINGS.exit_frames, SETTINGS.tag_agreement_window_frames), (0.5, 5, 0.02, 5, 15))
        self.assertEqual([(p.paddle, p.zone, p.event) for p in SETTINGS.paddles],
                         [("paddle_apical", "apical_placement_zone", "apical_paddle_placed"),
                          ("paddle_sternal", "sternal_placement_zone", "sternal_paddle_placed")])
        self.assertEqual(SETTINGS.review, PlacementReview())

    def test_parallel_window_comes_from_engine_yaml(self):
        self.assertEqual(SETTINGS.simultaneous_window_seconds, simultaneous_window_seconds())
        with tempfile.TemporaryDirectory() as folder:
            engine = Path(folder) / "engine.yaml"
            engine.write_text("simultaneous_window_seconds: {value: 0.3}\n", encoding="utf-8")
            self.assertEqual(load_config(DEFAULT_CONFIG, engine).placements.simultaneous_window_seconds, 0.3)

    def test_invalid_settings_are_rejected(self):
        for key, value, message in (("steady_frames", {"value": 0}, "whole number"),
                                    ("min_overlap_of_paddle", {"value": 1.5}, "at most 1"),
                                    ("paddles", {"paddle_apical": {"zone": "apical_zone", "event": "x"}}, "paddles")):
            with self.subTest(key=key):
                data = copy.deepcopy(CONFIG_DATA["derived_placements"])
                data[key] = value
                with self.assertRaisesRegex(ValueError, message):
                    load_placement_settings(data, ("apical_placement_zone", "sternal_placement_zone"),
                                            ("paddle_apical", "paddle_sternal"), 0.5, "test")


if __name__ == "__main__":
    unittest.main()
