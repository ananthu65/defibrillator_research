"""Increment 10: the annotation adapter (P-001, P-030), windowed zone coverage (D-092) and the 9c gate (D-088)."""
import contextlib
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest

from annotation.derive_paddle_placements import PlacementReview
from annotation.export_rule_engine_records import ZoneException, load_config as load_export_config
from rules.adapters.annotation import RECORD_KIND, adapt_record, main
from rules.config import load_rules_config
from rules.context import build_context
from rules.coverage import ANNOTATION_COVERAGE_ASSUMED, Coverage, TimelineHeader
from rules.engine import assess
from rules.errors import TimelineError
from rules.prepare import prepare_timeline
from rules.run import main as run_main

RULES = load_rules_config()
EXPORT = load_export_config()
APICAL, STERNAL = "apical_placement_zone", "sternal_placement_zone"
FPS = 25.0
DIGEST = EXPORT.placements.digest()
EXPORT_ID = "a" * 64


def record(task="P01_LS", view="LS", stop=99, tags=(), tracks=None, zones=(), derived=(), screen_tracks=0,
           screen=()):
    data = _record(task, view, stop, tags, tracks, zones, derived)
    if screen_tracks is not None:   # None: an export made before the screen was added
        data["screen_tracks"] = screen_tracks
        data["screen_visibility"] = [{"label": "defibrillator_screen", "start_frame": a, "end_frame": b,
                                      "start_seconds": round(a / FPS, 6), "end_seconds": round(b / FPS, 6)}
                                     for a, b in screen]
    return data


def _record(task, view, stop, tags, tracks, zones, derived):
    return {"schema_version": 1, "kind": RECORD_KIND, "canonical_task_id": task, "participant_id": task[:3],
            "camera_view": view, "annotation_source": "x", "archive": "a.zip", "task_path": ".",
            "media_name": f"{task}.mp4", "fps": FPS, "width": 1920, "height": 1080, "start_frame": 0,
            "stop_frame": stop, "duration_seconds": round((stop + 1) / FPS, 6),
            "tags": [{"id": f"{task}_tag_{i:03d}", "label": label, "frame": frame,
                      "timestamp_seconds": round(frame / FPS, 6)} for i, (label, frame) in enumerate(tags, start=1)],
            "zone_tracks": tracks if tracks is not None else {APICAL: 0, STERNAL: 0},
            "zone_visibility": [{"label": zone, "start_frame": a, "end_frame": b, "start_seconds": round(a / FPS, 6),
                                 "end_seconds": round(b / FPS, 6)} for zone, a, b in zones],
            "derived_events": list(derived)}


def derived_event(task="P01_LS", frame=20, settings=DIGEST, flags=("derived_placement",)):
    return {"id": f"{task}_derived_001", "event_name": "apical_paddle_placed", "frame": frame,
            "timestamp_seconds": frame / FPS, "evidence_type": "direct", "flags": list(flags),
            "method": "paddle_in_zone_v1", "metadata": {"paddle_label": "paddle_apical", "placement": 1,
                                                        "settings_sha256": settings}}


def reviewed(export_id=EXPORT_ID, settings=DIGEST):
    return replace(EXPORT, placements=replace(EXPORT.placements,
                                              review=PlacementReview("Arnikan", "2026-10-17", export_id, settings)))


def zone_status(adapted):
    return {z.region: z.status for z in adapted.zones}


class EventsAndHeader(unittest.TestCase):
    def test_tags_become_annotation_events_under_their_cvat_names(self):
        adapted = adapt_record(record(tags=[("Gel applied", 10), ("first_paddle_firmly_on_the_chest", 40)]), RULES, EXPORT)
        event = adapted.events[1]
        self.assertEqual((event.event_name, event.start, event.source, event.confidence, event.camera_angle, event.event_id),
                         ("first_paddle_firmly_on_the_chest", 1.6, "annotation", 1.0, "LS", "P01_LS_tag_002"))
        self.assertEqual(event.metadata, {"task_id": "P01_LS", "participant_id": "P01", "frame": 40,
                                          "confidence_kind": "human_annotation"})
        prepared = prepare_timeline(adapted.events, RULES)    # the vocabulary maps; CVAT labels are never renamed
        self.assertEqual([e.event_name for e in prepared.events], ["gel_applied", "first_paddle_placed"])

    def test_header_comes_from_the_record_and_is_flagged(self):
        header = adapt_record(record(task="P07_T", view="T", stop=249), RULES, EXPORT).header
        self.assertEqual((header.recording_id, header.camera_angle, header.duration_seconds), ("P07_T", "T", 10.0))
        self.assertEqual(header.analyses_run, {"video": True, "audio": False})
        self.assertEqual(header.flags, (ANNOTATION_COVERAGE_ASSUMED,))

    def test_not_a_record_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not a rule-engine annotation record"):
            adapt_record({"kind": "something else"}, RULES, EXPORT)


class ZoneCoverageRules(unittest.TestCase):
    """P-030: exception -> not covered; visible throughout -> covered; part -> unknown; never -> not covered; none -> unknown."""

    def test_each_case(self):
        adapted = adapt_record(record(tracks={APICAL: 1, STERNAL: 0}, zones=[(APICAL, 0, 99)]), RULES, EXPORT)
        self.assertEqual(zone_status(adapted), {"apical_zone": "covered", "sternal_zone": "unknown", "screen": "unknown"})
        self.assertEqual(adapted.header.visibility, {"region:apical_zone": ((0.0, 3.96),)})

        adapted = adapt_record(record(tracks={APICAL: 1, STERNAL: 2}, zones=[(APICAL, 0, 39), (APICAL, 60, 99)]),
                               RULES, EXPORT)
        self.assertEqual(zone_status(adapted), {"apical_zone": "unknown", "sternal_zone": "not_covered", "screen": "unknown"})
        self.assertEqual(adapted.header.visibility, {"region:apical_zone": ((0.0, 1.56), (2.4, 3.96)),
                                                     "region:sternal_zone": ()})
        self.assertIn("80 of 100 frames", adapted.zones[0].reason)
        self.assertIn("never visible", adapted.zones[1].reason)

    def test_reviewed_exception_is_not_covered_even_if_a_track_shows_it(self):
        config = replace(EXPORT, reviewed_zone_exceptions=(ZoneException("P01_LS", APICAL, "Annotator A", "2026-10-17"),))
        adapted = adapt_record(record(tracks={APICAL: 1, STERNAL: 0}, zones=[(APICAL, 0, 99)]), RULES, config)
        self.assertEqual(zone_status(adapted)["apical_zone"], "not_covered")
        self.assertNotIn("region:apical_zone", adapted.header.visibility)
        self.assertIn("reviewed exception", adapted.zones[0].reason)


class WindowedCoverage(unittest.TestCase):
    """D-092: apical zone visible 0-1.56 s and 2.4-3.96 s; out of view 1.6-2.36 s."""

    def setUp(self):
        self.adapted = adapt_record(record(tracks={APICAL: 1, STERNAL: 0}, zones=[(APICAL, 0, 39), (APICAL, 60, 99)]),
                                    RULES, EXPORT)
        self.coverage = Coverage(prepare_timeline(self.adapted.events, RULES), RULES, self.adapted.header)

    def status(self, window=None):
        return self.coverage.status("apical_paddle_placed", window).status

    def test_visible_throughout_the_window_is_covered(self):
        self.assertEqual(self.status((0.2, 1.0)), "covered")
        self.assertEqual(self.status((0.0, 1.56)), "covered")    # exactly the interval

    def test_visible_for_part_of_the_window_is_unknown(self):
        self.assertEqual(self.status((1.0, 2.0)), "unknown")

    def test_never_visible_in_the_window_is_not_covered(self):
        self.assertEqual(self.status((1.7, 2.2)), "not_covered")

    def test_without_a_window_partial_visibility_is_unknown(self):
        self.assertEqual(self.status(), "unknown")

    def test_a_placement_expected_while_the_zone_was_out_of_view_is_never_a_fail(self):
        gap = self.coverage.missing("apical_paddle_placed", (1.7, 2.2))
        self.assertEqual((gap.outcome, gap.coverage.status), ("unable_to_verify", "not_covered"))
        self.assertIn("never visible", gap.coverage.basis)
        visible = self.coverage.missing("apical_paddle_placed", (0.2, 1.0))
        self.assertEqual((visible.outcome, visible.coverage.status), ("fail", "covered"))
        context = build_context(prepare_timeline(self.adapted.events, RULES), RULES, self.adapted.header)
        self.assertEqual(context.missing("apical_paddle_placed", (1.7, 2.2)).outcome, "unable_to_verify")

    def test_other_events_ignore_the_window(self):
        self.assertEqual(self.coverage.status("gel_applied", (1.7, 2.2)).status, "covered")   # analyses_run video


class ScreenCoverage(unittest.TestCase):
    """D-094: the defibrillator screen's coverage, exactly as for the zones; R5's missing shock on screen."""

    def missing_shock(self, data, window=None):
        adapted = adapt_record(data, RULES, EXPORT)
        coverage = Coverage(prepare_timeline(adapted.events, RULES), RULES, adapted.header)
        return zone_status(adapted)["screen"], coverage.missing("shock_delivered_on_screen", window)

    def test_ll_video_with_no_screen_visible_is_never_a_fail(self):
        status, missing = self.missing_shock(record("P01_LL", "LL", screen_tracks=0))
        self.assertEqual((status, missing.coverage.status, missing.outcome), ("unknown", "unknown", "unable_to_verify"))
        self.assertEqual(missing.coverage.scope, "region:screen")

    def test_screen_never_visible_is_not_covered(self):
        status, missing = self.missing_shock(record(screen_tracks=1, screen=()))
        self.assertEqual((status, missing.outcome), ("not_covered", "unable_to_verify"))

    def test_screen_visible_throughout_makes_a_missing_shock_a_fail(self):
        status, missing = self.missing_shock(record(screen_tracks=1, screen=[(0, 99)]))
        self.assertEqual((status, missing.outcome), ("covered", "fail"))

    def test_shock_expected_while_the_screen_was_out_of_view(self):
        data = record(screen_tracks=1, screen=[(0, 39), (60, 99)])
        status, gap = self.missing_shock(data, (1.7, 2.2))
        self.assertEqual((status, gap.coverage.status, gap.outcome), ("unknown", "not_covered", "unable_to_verify"))
        _, seen = self.missing_shock(data, (0.2, 1.0))
        self.assertEqual((seen.coverage.status, seen.outcome), ("covered", "fail"))

    def test_an_export_without_screen_fields_is_unknown(self):
        adapted = adapt_record(record(screen_tracks=None), RULES, EXPORT)
        self.assertEqual(zone_status(adapted)["screen"], "unknown")
        self.assertIn("not in this export", adapted.zones[-1].reason)


class Gate(unittest.TestCase):
    """D-088: derived placements reach the engine only for the reviewed export and settings."""

    def adapt(self, config, manifest, settings=DIGEST):
        return adapt_record(record(derived=[derived_event(settings=settings)]), RULES, config, manifest)

    def manifest(self, export_id=EXPORT_ID):
        return {"export_id": export_id, "placement_settings_sha256": DIGEST}

    def test_approved_export_passes_derived_placements_on(self):
        adapted = self.adapt(reviewed(), self.manifest())
        derived = [e for e in adapted.events if e.metadata.get("derived_placement")]
        self.assertEqual(([e.event_name for e in derived], adapted.derived_included, adapted.gate),
                         (["apical_paddle_placed"], 1, "approved"))
        self.assertEqual((derived[0].evidence_type, derived[0].metadata["flags"]), ("direct", ["derived_placement"]))

    def test_unapproved_exports_withhold_them(self):
        cases = (("no review", EXPORT, self.manifest(), DIGEST),
                 ("another export", reviewed(), self.manifest("b" * 64), DIGEST),
                 ("no manifest", reviewed(), None, DIGEST),
                 ("event made with other settings", reviewed(), self.manifest(), "c" * 64))
        for name, config, manifest, settings in cases:
            with self.subTest(name):
                adapted = self.adapt(config, manifest, settings)
                self.assertFalse(any(e.metadata.get("derived_placement") for e in adapted.events))
                self.assertEqual((adapted.derived_included, adapted.derived_withheld), (0, 1))
                self.assertTrue(adapted.gate.startswith("not approved"))


class ThroughTheEngine(unittest.TestCase):
    def test_every_result_is_development_data_and_the_header_round_trips(self):
        adapted = adapt_record(record(tags=[("Gel applied", 10), ("shock_delivered_on_screen", 70)],
                                      tracks={APICAL: 1, STERNAL: 1}, zones=[(APICAL, 0, 99), (STERNAL, 0, 49)]),
                               RULES, EXPORT)
        header = TimelineHeader.from_dict(adapted.timeline()["header"], regions=tuple(RULES.engine.regions))
        self.assertEqual(header, adapted.header)
        result = assess(adapted.events, RULES, header=header)
        self.assertTrue(all(ANNOTATION_COVERAGE_ASSUMED in o.flags for o in result.outcomes))
        self.assertTrue(result.overall.development_data)
        self.assertEqual(result.overall.result, "incomplete")
        self.assertEqual({r: s.status for r, s in result.context.zone_visibility.items()},
                         {"apical_zone": "covered", "sternal_zone": "unknown", "screen": "unknown"})

    def test_header_validation(self):
        regions = tuple(RULES.engine.regions)
        good = adapt_record(record(tracks={APICAL: 1, STERNAL: 0}, zones=[(APICAL, 0, 99)]), RULES, EXPORT).timeline()["header"]
        for change, message in (({"visibility": {"modality:video": [[0, 1]]}}, "only for region scopes"),
                                ({"visibility": {"region:apical_zone": [[0, 2], [1, 3]]}}, "must not overlap"),
                                ({"flags": ["something_else"]}, "flags must be")):
            with self.subTest(change=change), self.assertRaisesRegex(TimelineError, message):
                TimelineHeader.from_dict({**good, **change}, regions=regions)
        late = TimelineHeader.from_dict({**good, "visibility": {"region:apical_zone": [[0, 9.0]]}}, regions=regions)
        with self.assertRaisesRegex(TimelineError, "visibility") as caught:
            assess([], RULES, header=late)
        self.assertEqual(caught.exception.code, "header_mismatch")


class CommandLine(unittest.TestCase):
    def test_adapter_then_rules_run(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            exported = folder / "export"
            exported.mkdir()
            records = [record("P01_LL", "LL", tags=[("Gel applied", 10)], tracks={APICAL: 1, STERNAL: 0},
                              zones=[(APICAL, 0, 99)]),
                       record("P14_LS", "LS")]
            (exported / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code = main(["--records", str(exported / "records.jsonl"), "--output", str(folder / "timelines"),
                             "--exclude", "P14_LS"])
            self.assertEqual(code, 0)
            self.assertEqual(sorted(p.name for p in (folder / "timelines").iterdir()), ["P01_LL.json", "adapter_summary.json"])
            self.assertIn("excluded: P14_LS", out.getvalue())
            with contextlib.redirect_stdout(io.StringIO()):
                code = run_main(["--events", str(folder / "timelines/P01_LL.json"), "--output", str(folder / "report.json")])
            self.assertEqual(code, 0)
            report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
            self.assertTrue(report["development_data"])
            self.assertEqual(report["context"]["header"]["visibility"], {"region:apical_zone": [[0.0, 3.96]]})
            self.assertEqual(report["context"]["header"]["flags"], [ANNOTATION_COVERAGE_ASSUMED])

    def test_refuses_a_non_empty_output(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "records.jsonl").write_text(json.dumps(record()) + "\n", encoding="utf-8")
            (folder / "out").mkdir()
            (folder / "out" / "x").write_text("x")
            with contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(main(["--records", str(folder / "records.jsonl"), "--output", str(folder / "out")]), 2)
            self.assertIn("not empty", err.getvalue())


if __name__ == "__main__":
    unittest.main()
