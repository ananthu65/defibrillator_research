"""Step 9b: the rule-engine annotation exporter and audit, on synthetic CVAT backups (D-074)."""
import copy
import contextlib
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import unittest.mock
import zipfile

import yaml

from annotation.audit_rule_engine_checks import audit_task, run_audit
from annotation.build_yolo_video_dataset import Track, frame_boxes, track_box_at
from annotation.export_rule_engine_records import (
    DEFAULT_CONFIG,
    DEFAULT_CONVERSION_REPORT,
    EXIT_REFUSED,
    TRAINING_DATA,
    VideoInfo,
    export,
    frame_runs,
    iter_tasks,
    load_config,
    load_conversion_report,
    main,
    unique_tasks,
    zone_visible_frames,
)

APICAL, STERNAL = "apical_placement_zone", "sternal_placement_zone"
CONFIG_DATA = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))
WIDTH, HEIGHT, FPS = 1920, 1080, 25.0


def rect(frame, x1=100, y1=100, x2=300, y2=300, outside=False):
    return {"type": "rectangle", "frame": frame, "points": [x1, y1, x2, y2], "outside": outside, "rotation": 0}


def track(label, *shapes):
    return {"label": label, "shapes": list(shapes)}


def tag(label, frame):
    return {"label": label, "frame": frame}


def task(name, stop=99, tags=(), tracks=(), shapes=(), jobs=None):
    return {"name": name, "stop": stop,
            "jobs": jobs if jobs is not None else [{"tags": list(tags), "tracks": list(tracks), "shapes": list(shapes)}]}


class Backups:
    """A temporary folder of synthetic CVAT backup ZIPs, a conversion report and a config."""

    def __init__(self, case):
        folder = tempfile.TemporaryDirectory()
        case.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.backups = self.root / "backups"
        self.backups.mkdir()
        self.videos = {}

    def add(self, archive, *tasks, fps=FPS, frames=None):
        path = self.backups / archive
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w") as stream:
            for index, item in enumerate(tasks):
                prefix = "" if len(tasks) == 1 else f"task_{index}/"
                stream.writestr(f"{prefix}task.json", json.dumps(
                    {"name": item["name"], "data": {"start_frame": 0, "stop_frame": item["stop"]}}))
                stream.writestr(f"{prefix}annotations.json", json.dumps(item["jobs"]))
                stream.writestr(f"{prefix}data/{item['name']}.mp4", b"\0")
                if fps is not None:
                    self.videos[item["name"]] = (fps, frames if frames is not None else item["stop"] + 1)
        return self

    def conversion(self):
        path = self.root / "video_conversion.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["canonical_task_id", "fps", "width", "height", "source_frame_count_cvat"])
            for name, (fps, frames) in sorted(self.videos.items()):
                writer.writerow([name, fps, WIDTH, HEIGHT, frames])
        return path

    def config(self, **changes):
        data = copy.deepcopy(CONFIG_DATA)
        data.update(changes)
        path = self.root / "annotation_export.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        return path

    def export(self, **config):
        output = self.root / "out"
        manifest = export(self.backups, output, self.conversion(), self.config(**config))
        records = [json.loads(line) for line in (output / "records.jsonl").read_text(encoding="utf-8").splitlines()]
        with (output / "export_issues.csv").open(encoding="utf-8") as stream:
            issues = list(csv.DictReader(stream))
        return manifest, {r["canonical_task_id"]: r for r in records}, issues


def codes(issues):
    return sorted(i["code"] if isinstance(i, dict) else i.code for i in issues)


class ZoneVisibilityMatchesTrainingBoxes(unittest.TestCase):
    """D-079: visibility is computed with the training code itself; these tests pin its behaviour."""

    def test_track_box_at_behaviour_is_pinned(self):
        zone = Track(APICAL, [rect(10), rect(30, outside=True), rect(50)])
        self.assertIsNone(track_box_at(zone, 9))       # before the first keyframe: not visible
        self.assertIsNotNone(track_box_at(zone, 10))   # from a visible keyframe
        self.assertIsNotNone(track_box_at(zone, 29))   # interpolated up to the outside keyframe
        self.assertIsNone(track_box_at(zone, 30))      # hidden from the outside keyframe
        self.assertIsNone(track_box_at(zone, 49))
        self.assertIsNotNone(track_box_at(zone, 500))  # a last visible keyframe stays visible to the end

    def test_visible_frames_equal_frames_with_a_training_box(self):
        tracks = [Track(APICAL, [rect(5), rect(20, outside=True), rect(40, 1900, 100, 2500, 300)]),
                  Track(APICAL, [rect(18), rect(25, outside=True)]),
                  Track(STERNAL, [rect(60, outside=True)])]
        visible = set(zone_visible_frames([t for t in tracks if t.label == APICAL], 0, 99, WIDTH, HEIGHT))
        training = {f for f in range(100) if APICAL in {label for label, _ in frame_boxes(f, tracks, {}, WIDTH, HEIGHT)[0]}}
        self.assertEqual(visible, training)
        self.assertEqual(frame_runs(visible), [(5, 24), (40, 99)])

    def test_a_box_entirely_outside_the_image_is_not_visible(self):
        outside_image = Track(APICAL, [rect(0, 2000, 100, 2100, 200)])
        self.assertEqual(zone_visible_frames([outside_image], 0, 9, WIDTH, HEIGHT), [])


class Records(unittest.TestCase):
    def test_record_keeps_every_tag_and_times_it(self):
        backups = Backups(self).add("kartheepan/P01_LL.zip", task(
            "P01_LL", stop=99,
            tags=[tag("paddles_removed_after_shock", 80), tag("Gel applied", 10),
                  tag("first_paddle_firmly_on_the_chest", 40), tag("Not a known tag", 50)],
            tracks=[track(APICAL, rect(20))]))
        manifest, records, issues = backups.export()
        record = records["P01_LL"]
        self.assertEqual([(t["label"], t["frame"]) for t in record["tags"]],
                         [("Gel applied", 10), ("first_paddle_firmly_on_the_chest", 40), ("Not a known tag", 50),
                          ("paddles_removed_after_shock", 80)])
        self.assertEqual(record["tags"][1], {"id": "P01_LL_tag_002", "label": "first_paddle_firmly_on_the_chest",
                                             "frame": 40, "timestamp_seconds": 1.6})
        self.assertEqual((record["participant_id"], record["camera_view"], record["annotation_source"]),
                         ("P01", "LL", "kartheepan"))
        self.assertEqual((record["fps"], record["stop_frame"], record["duration_seconds"]), (25.0, 99, 4.0))
        self.assertEqual(record["zone_tracks"], {APICAL: 1, STERNAL: 0})
        self.assertEqual(record["zone_visibility"], [{"label": APICAL, "start_frame": 20, "end_frame": 99,
                                                      "start_seconds": 0.8, "end_seconds": 3.96}])
        self.assertEqual(record["derived_events"], [])
        self.assertEqual(issues, [])
        self.assertEqual(manifest["counts"], {"tasks": 1, "records": 1, "tags": 4, "zone_intervals": 1, "screen_intervals": 0,
                                              "paddle_intervals": 0, "derived_events": 0})
        self.assertEqual(manifest["backups"][0]["archive"], "kartheepan/P01_LL.zip")

    def test_zone_intervals_close_at_outside_keyframes_and_merge_across_tracks_and_jobs(self):
        jobs = [{"tags": [], "shapes": [], "tracks": [track(APICAL, rect(10), rect(30, outside=True))]},
                {"tags": [], "shapes": [], "tracks": [track(APICAL, rect(30), rect(50, outside=True)),
                                                      track(STERNAL, rect(60), rect(70, outside=True))]}]
        _, records, _ = Backups(self).add("P02_LS.zip", task("P02_LS", jobs=jobs)).export()
        zones = [(z["label"], z["start_frame"], z["end_frame"]) for z in records["P02_LS"]["zone_visibility"]]
        self.assertEqual(zones, [(APICAL, 10, 49), (STERNAL, 60, 69)])
        self.assertEqual(records["P02_LS"]["zone_tracks"], {APICAL: 2, STERNAL: 1})

    def test_missing_and_never_visible_tracks_are_reported_as_facts_only(self):
        _, records, _ = Backups(self).add("P03_T.zip", task("P03_T", tracks=[
            track(STERNAL, rect(0, outside=True), rect(50, outside=True))])).export()
        self.assertEqual(records["P03_T"]["zone_tracks"], {APICAL: 0, STERNAL: 1})
        self.assertEqual(records["P03_T"]["zone_visibility"], [])  # coverage is decided by the adapter (P-030)

    def test_screen_visibility_is_exported_like_the_zones(self):
        backups = (Backups(self)
                   .add("P23_LS.zip", task("P23_LS", tracks=[track("defibrillator_screen", rect(10), rect(40, outside=True))]))
                   .add("P23_LL.zip", task("P23_LL", tracks=[track(APICAL, rect(0))])))
        _, records, _ = backups.export()
        self.assertEqual(records["P23_LS"]["screen_tracks"], 1)
        self.assertEqual(records["P23_LS"]["screen_visibility"], [{"label": "defibrillator_screen", "start_frame": 10,
                                                                  "end_frame": 39, "start_seconds": 0.4,
                                                                  "end_seconds": 1.56}])
        self.assertEqual((records["P23_LL"]["screen_tracks"], records["P23_LL"]["screen_visibility"]), (0, []))

    def test_paddle_visibility_is_exported_like_the_zones(self):
        """D-108: R4's coverage of the button press."""
        backups = Backups(self).add("P24_LS.zip", task("P24_LS", tracks=[
            track("paddle_apical", rect(5), rect(30, outside=True)), track("paddle_sternal", rect(0))]))
        _, records, _ = backups.export()
        record = records["P24_LS"]
        self.assertEqual(record["paddle_tracks"], {"paddle_apical": 1, "paddle_sternal": 1})
        self.assertEqual([(p["label"], p["start_frame"], p["end_frame"]) for p in record["paddle_visibility"]],
                         [("paddle_apical", 5, 29), ("paddle_sternal", 0, 99)])

    def test_a_single_frame_zone_shape_is_reported_not_converted(self):
        _, records, issues = Backups(self).add("P04_T.zip", task("P04_T", shapes=[
            {"type": "rectangle", "frame": 12, "label": APICAL, "points": [1, 1, 50, 50]}])).export()
        self.assertEqual(records["P04_T"]["zone_visibility"], [])
        self.assertEqual(codes(issues), ["zone_shape_without_track"])
        self.assertEqual(issues[0]["frame"], "12")

    def test_video_missing_from_the_conversion_report_is_an_export_issue(self):
        backups = Backups(self).add("P05_LL.zip", task("P05_LL"), fps=None).add("P06_LL.zip", task("P06_LL"))
        _, records, issues = backups.export()
        self.assertEqual(sorted(records), ["P06_LL"])
        self.assertEqual([(i["code"], i["severity"], i["canonical_task_id"]) for i in issues],
                         [("fps_missing", "error", "P05_LL")])

    def test_frame_count_disagreeing_with_the_conversion_report_is_a_warning(self):
        _, records, issues = Backups(self).add("P07_LL.zip", task("P07_LL", stop=99), frames=120).export()
        self.assertIn("P07_LL", records)
        self.assertEqual(codes(issues), ["frame_count_mismatch"])

    def test_tag_outside_the_frame_range_is_kept_and_reported(self):
        _, records, issues = Backups(self).add("P08_LL.zip", task("P08_LL", stop=99, tags=[tag("Gel applied", 150)])).export()
        self.assertEqual(len(records["P08_LL"]["tags"]), 1)
        self.assertEqual(codes(issues), ["tag_outside_frames"])

    def test_project_backup_with_several_tasks_and_duplicates(self):
        backups = Backups(self).add("defib.zip", task("P09_LL"), task("P09_LS")).add("zz/P09_LL.zip", task("P09_LL"))
        _, records, issues = backups.export()
        self.assertEqual(sorted(records), ["P09_LL", "P09_LS"])
        self.assertEqual(records["P09_LL"]["archive"], "defib.zip")  # the first in archive order is kept
        self.assertEqual(codes(issues), ["duplicate_task"])

    def test_unrecognised_task_name_is_an_error(self):
        backups = Backups(self).add("odd.zip", {"name": "rehearsal", "stop": 9, "jobs": []})
        issues = []
        self.assertEqual(list(iter_tasks(backups.backups, issues)), [])
        self.assertEqual(codes(issues), ["unrecognized_task_name"])

    def test_derived_placements_reach_the_record_and_the_manifest_identifies_the_export(self):
        placed = lambda frame: [rect(0, 1000, 800, 1100, 900), rect(frame - 1, 1000, 800, 1100, 900), rect(frame, 150, 150, 250, 250)]
        backups = Backups(self).add("P22_LL.zip", task("P22_LL", tags=[tag("first_paddle_firmly_on_the_chest", 21)],
                                                       tracks=[track(APICAL, rect(0)), track("paddle_apical", *placed(20))]))
        manifest, records, _ = backups.export()
        derived = records["P22_LL"]["derived_events"]
        self.assertEqual([(e["event_name"], e["frame"], e["flags"]) for e in derived],
                         [("apical_paddle_placed", 20, ["derived_placement"])])
        records_bytes = (backups.root / "out/records.jsonl").read_bytes()
        self.assertEqual(manifest["export_id"], hashlib.sha256(records_bytes).hexdigest())   # the file as sent
        self.assertNotIn(b"\r\n", records_bytes)
        self.assertEqual(manifest["placement_settings_sha256"], load_config().placements.digest())
        self.assertEqual(manifest["placement_validation"]["videos"], 1)
        self.assertTrue((backups.root / "out/placement_validation.md").read_text(encoding="utf-8").startswith("# Derived"))

    def test_export_is_deterministic(self):
        backups = Backups(self).add("P10_T.zip", task("P10_T", tags=[tag("Gel applied", 3), tag("Gel applied", 3)],
                                                       tracks=[track(APICAL, rect(5)), track(STERNAL, rect(8))]))
        first = export(backups.backups, backups.root / "a", backups.conversion(), backups.config())
        second = export(backups.backups, backups.root / "b", backups.conversion(), backups.config())
        self.assertEqual((backups.root / "a/records.jsonl").read_bytes(), (backups.root / "b/records.jsonl").read_bytes())
        self.assertEqual(first["backups"], second["backups"])


class MediaIsNeverRead(unittest.TestCase):
    """D-085: the backups may contain the videos; only task.json and annotations.json are opened."""

    def test_export_and_audit_open_only_the_annotation_json(self):
        backups = Backups(self).add("P20_LL.zip", task("P20_LL", tags=[tag("Gel applied", 5)],
                                                       tracks=[track(APICAL, rect(0))]))
        opened = []
        original = zipfile.ZipFile.open

        def spy(archive, name, *args, **kwargs):
            opened.append(name if isinstance(name, str) else name.filename)
            return original(archive, name, *args, **kwargs)

        with unittest.mock.patch.object(zipfile.ZipFile, "open", spy):
            export(backups.backups, backups.root / "export", backups.conversion(), backups.config())
            run_audit(backups.backups, backups.root / "audit", backups.conversion(), backups.config())
        self.assertTrue(opened)
        self.assertEqual({Path(name).name for name in opened}, {"task.json", "annotations.json"})

    def test_manifest_digest_covers_annotations_not_media(self):
        first = Backups(self).add("P21_LL.zip", task("P21_LL", tags=[tag("Gel applied", 5)]))
        second = Backups(self).add("P21_LL.zip", task("P21_LL", tags=[tag("Gel applied", 5)]))
        with zipfile.ZipFile(second.backups / "P21_LL.zip", "a") as stream:
            stream.writestr("data/extra_frame.jpg", b"different media bytes")
        third = Backups(self).add("P21_LL.zip", task("P21_LL", tags=[tag("Gel applied", 6)]))
        digests = [b.export()[0]["backups"][0]["annotation_sha256"] for b in (first, second, third)]
        self.assertEqual(digests[0], digests[1])     # media changed: same digest
        self.assertNotEqual(digests[0], digests[2])  # annotation changed: new digest


class OutputIsSeparateFromTraining(unittest.TestCase):
    def run_main(self, *args):
        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            return main(list(args)), stderr.getvalue()

    def test_refuses_to_write_inside_the_training_data(self):
        backups = Backups(self).add("P11_LL.zip", task("P11_LL"))
        code, message = self.run_main("--backup-root", str(backups.backups), "--output", str(TRAINING_DATA / "x"),
                                      "--conversion-report", str(backups.conversion()))
        self.assertEqual(code, EXIT_REFUSED)
        self.assertIn("training pipeline", message)
        self.assertFalse((TRAINING_DATA / "x").exists())

    def test_refuses_a_non_empty_output_folder(self):
        backups = Backups(self).add("P12_LL.zip", task("P12_LL"))
        (backups.root / "used").mkdir()
        (backups.root / "used" / "old.txt").write_text("x")
        code, message = self.run_main("--backup-root", str(backups.backups), "--output", str(backups.root / "used"),
                                      "--conversion-report", str(backups.conversion()))
        self.assertEqual(code, EXIT_REFUSED)
        self.assertIn("not empty", message)

    def test_command_line_writes_the_five_files(self):
        backups = Backups(self).add("P13_LL.zip", task("P13_LL"))
        code, _ = self.run_main("--backup-root", str(backups.backups), "--output", str(backups.root / "run"),
                                "--conversion-report", str(backups.conversion()), "--config", str(backups.config()))
        self.assertEqual(code, 0)
        self.assertEqual(sorted(p.name for p in (backups.root / "run").iterdir()),
                         ["export_issues.csv", "export_manifest.json", "placement_validation.csv",
                          "placement_validation.md", "records.jsonl"])


class Configuration(unittest.TestCase):
    def test_repository_config(self):
        config = load_config()
        self.assertEqual(config.usual_zone_pattern, {"LL": (APICAL,), "LS": (APICAL, STERNAL), "T": (APICAL, STERNAL)})
        self.assertEqual(config.reviewed_zone_exceptions, ())
        self.assertEqual((config.zone_motion_fraction_of_diagonal, config.repeated_tag_window_frames), (0.05, 15))

    def test_reviewed_exception_is_loaded(self):
        backups = Backups(self)
        config = load_config(backups.config(reviewed_zone_exceptions=[
            {"task": "P07_T", "zone": APICAL, "confirmed_by": "Annotator A", "confirmed_on": "2026-10-16"}]))
        self.assertEqual(config.confirmed_not_visible("P07_T"), {APICAL})
        self.assertEqual(config.confirmed_not_visible("P07_LL"), set())

    def test_invalid_exceptions_are_rejected(self):
        good = {"task": "P07_T", "zone": APICAL, "confirmed_by": "A", "confirmed_on": "2026-10-16"}
        for bad, message in (({**good, "task": "P7_T"}, "canonical task ID"), ({**good, "zone": "apical_zone"}, "zone"),
                             ({**good, "confirmed_by": " "}, "confirmed_by"), ({**good, "confirmed_on": "16/10/2026"}, "date"),
                             ({**good, "reason": "x"}, "expected only")):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, message):
                load_config(Backups(self).config(reviewed_zone_exceptions=[bad]))
        with self.assertRaisesRegex(ValueError, "listed twice"):
            load_config(Backups(self).config(reviewed_zone_exceptions=[good, good]))

    def test_invalid_patterns_and_settings_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "usual_zone_pattern.LL"):
            load_config(Backups(self).config(usual_zone_pattern={"LL": ["apical_zone"]}))
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            load_config(Backups(self).config(audit={"zone_motion_fraction_of_diagonal": 5,
                                                    "repeated_tag_window_frames": 15}))
        with self.assertRaisesRegex(ValueError, "exactly the keys"):
            load_config(Backups(self).config(extra=1))

    def test_repository_conversion_report(self):
        videos = load_conversion_report(DEFAULT_CONVERSION_REPORT)
        self.assertEqual(len(videos), 144)
        self.assertEqual(videos["P01_LL"], VideoInfo(24.91, 1920, 1080, 473))


def audited(case, archive, item, **config):
    backups = Backups(case).add(archive, item)
    issues, info = [], []
    source, = unique_tasks(iter_tasks(backups.backups, issues), issues)
    pattern = audit_task(source, VideoInfo(FPS, WIDTH, HEIGHT, None), load_config(backups.config(**config)), issues, info)
    return pattern, issues, info


class AuditChecks(unittest.TestCase):
    def test_two_boxes_of_one_paddle_on_the_same_frames(self):
        _, issues, _ = audited(self, "P01_LL.zip", task("P01_LL", tracks=[
            track(APICAL, rect(0)),
            track("paddle_apical", rect(10), rect(21, outside=True)),
            track("paddle_apical", rect(15, 400, 400, 500, 500), rect(31, outside=True))]))
        found = [i for i in issues if i.code == "duplicate_paddle_box"]
        self.assertEqual([(i.label, i.frame) for i in found], [("paddle_apical", 15)])
        self.assertIn("frames 15-20", found[0].details)

    def test_one_box_per_paddle_is_fine_and_a_standalone_shape_counts(self):
        _, issues, _ = audited(self, "P02_LL.zip", task("P02_LL", tracks=[
            track(APICAL, rect(0)), track("paddle_apical", rect(10)), track("paddle_sternal", rect(10))]))
        self.assertNotIn("duplicate_paddle_box", codes(issues))
        _, issues, _ = audited(self, "P03_LL.zip", task("P03_LL", tracks=[track(APICAL, rect(0)), track("paddle_sternal", rect(10))],
                                                         shapes=[{"type": "rectangle", "frame": 40, "label": "paddle_sternal",
                                                                  "points": [5, 5, 50, 50]}]))
        self.assertEqual([(i.code, i.frame) for i in issues if i.code == "duplicate_paddle_box"],
                         [("duplicate_paddle_box", 40)])

    def test_zone_moving_more_than_five_percent_of_the_diagonal(self):
        # diagonal of 1920x1080 is about 2203 px: 200 px is 9.1%, 50 px is 2.3%
        _, issues, _ = audited(self, "P04_LL.zip", task("P04_LL", tracks=[
            track(APICAL, rect(0), rect(50, 300, 100, 500, 300)),
            track("paddle_apical", rect(50, 300, 100, 500, 300))]))
        moving, = [i for i in issues if i.code == "zone_moves_like_paddle"]
        self.assertIn("moved 9.1% of the frame diagonal between frames 0 and 50", moving.details)
        self.assertIn("overlaps paddle_apical (IoU 1.00)", moving.details)
        _, issues, _ = audited(self, "P05_LL.zip", task("P05_LL", tracks=[track(APICAL, rect(0), rect(50, 150, 100, 350, 300))]))
        self.assertNotIn("zone_moves_like_paddle", codes(issues))

    def test_same_tag_within_fifteen_frames_is_possibly_one_incident(self):
        _, issues, info = audited(self, "P06_LL.zip", task("P06_LL", tracks=[track(APICAL, rect(0))], tags=[
            tag("paddles_firmly_on_chest", 30), tag("paddles_firmly_on_chest", 45),
            tag("Gel applied", 10), tag("Gel applied", 26)]))
        repeated = [i for i in issues if i.code == "repeated_incident_tag"]
        self.assertEqual([(i.label, i.frame) for i in repeated], [("paddles_firmly_on_chest", 30)])
        self.assertIn("possibly the same incident tagged twice", repeated[0].details)
        self.assertEqual([(i.label, i.frame) for i in info if i.code == "repeated_tag"], [("Gel applied", 10)])

    def test_learner_order_is_information_only(self):
        _, issues, info = audited(self, "P07_LL.zip", task("P07_LL", tracks=[track(APICAL, rect(0))], tags=[
            tag("paddles_removed_after_shock", 5), tag("Gel applied", 60)]))
        self.assertEqual(issues, [])
        sequence, = [i for i in info if i.code == "tag_sequence"]
        self.assertEqual(sequence.details, "paddles_removed_after_shock@5; Gel applied@60")
        self.assertIn("first_placement_tag_missing", codes(info))

    def test_zone_patterns_per_view(self):
        cases = (("P08_LL", [APICAL], False, "none", "none"),
                 ("P09_LL", [], True, APICAL, "none"),
                 ("P10_LL", [STERNAL], True, APICAL, STERNAL),
                 ("P11_LS", [APICAL], True, STERNAL, "none"),
                 ("P12_T", [APICAL, STERNAL], False, "none", "none"))
        for name, zones, off, missing, unexpected in cases:
            with self.subTest(name=name):
                pattern, issues, _ = audited(self, f"{name}.zip", task(name, tracks=[track(z, rect(0)) for z in zones]))
                self.assertEqual((pattern.on_review_list, pattern.missing, pattern.unexpected), (off, missing, unexpected))
                self.assertEqual("zone_pattern_off" in codes(issues), off)

    def test_never_visible_track_is_information_and_counts_as_present(self):
        pattern, issues, info = audited(self, "P13_LL.zip", task("P13_LL", tracks=[track(APICAL, rect(0, outside=True))]))
        self.assertFalse(pattern.on_review_list)
        self.assertEqual((pattern.present, pattern.visible, pattern.never_visible), (APICAL, "none", APICAL))
        self.assertIn("zone_track_never_visible", codes(info))
        self.assertEqual(issues, [])

    def test_reviewed_exception_removes_the_video_from_the_review_list(self):
        exception = [{"task": "P14_T", "zone": APICAL, "confirmed_by": "Annotator A", "confirmed_on": "2026-10-16"}]
        pattern, issues, info = audited(self, "P14_T.zip", task("P14_T", tracks=[track(STERNAL, rect(0))]),
                                        reviewed_zone_exceptions=exception)
        self.assertFalse(pattern.on_review_list)
        self.assertEqual(pattern.confirmed_not_visible, APICAL)
        self.assertEqual(issues, [])
        self.assertIn("zone_exception_confirmed", codes(info))

    def test_exception_contradicted_by_a_visible_zone_is_reviewed(self):
        exception = [{"task": "P15_T", "zone": APICAL, "confirmed_by": "Annotator A", "confirmed_on": "2026-10-16"}]
        _, issues, _ = audited(self, "P15_T.zip", task("P15_T", tracks=[track(APICAL, rect(0)), track(STERNAL, rect(0))]),
                               reviewed_zone_exceptions=exception)
        self.assertEqual(codes(issues), ["zone_exception_contradicted"])


class AuditOutput(unittest.TestCase):
    def test_reports_with_the_usual_pattern_beside_the_actual_distribution(self):
        backups = (Backups(self).add("P01_LL.zip", task("P01_LL", tracks=[track(APICAL, rect(0))]))
                   .add("P02_LL.zip", task("P02_LL")).add("P03_LS.zip", task("P03_LS", tracks=[track(APICAL, rect(0))])))
        output = backups.root / "audit"
        manifest = run_audit(backups.backups, output, backups.conversion(), backups.config())
        self.assertEqual(sorted(p.name for p in output.iterdir()),
                         ["README.md", "audit_manifest.json", "info.csv", "issues.csv", "zone_patterns.csv"])
        self.assertEqual(manifest["zone_distribution"]["LL"], {"usual": APICAL, "actual": {APICAL: 1, "none": 1}})
        self.assertEqual(manifest["counts"]["off_pattern_videos"], 2)
        with (output / "issues.csv").open(encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual({r["severity"] for r in rows}, {"review"})
        readme = (output / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"| LL | {APICAL} | {APICAL}: 1, none: 1 |", readme)
        self.assertIn("## Off-pattern videos (2)", readme)


if __name__ == "__main__":
    unittest.main()
