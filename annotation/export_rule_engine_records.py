#!/usr/bin/env python3
"""Export rule-engine annotation records directly from CVAT backup ZIPs (Step 9b, D-074).

    python -m annotation.export_rule_engine_records --backup-root <folder of CVAT ZIPs> \
        --output data/rule_engine/annotation_export/<run>

One record per task in ``records.jsonl``. Each record has every CVAT tag under its CVAT name,
zone visibility intervals from the zone tracks, and the frame range and duration. The output is
separate from everything the training pipeline reads. This script changes none of the existing
annotation scripts or their outputs, and refuses to write under ``data/video/``.

Privacy (D-085): the backups may contain the videos. Only the annotation JSON (``task.json``,
``annotations.json``) is read. A media entry's file name is used to recognise the task, but its
content is never opened, hashed or printed.

Reuse (D-079): task discovery comes from ``audit_cvat_backups`` and box geometry from
``build_yolo_video_dataset``, both by import only. A zone therefore counts as visible on exactly
the frames where the training dataset has a box for it (``track_box_at`` then ``clip_box``).
fps, width and height come from ``annotation/reports/phase4/video_conversion.csv`` only
(D-076). A video missing from it is an export issue.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator

import yaml

from annotation.audit_cvat_backups import (
    VIDEO_SUFFIXES,
    Issue,
    annotation_source,
    canonicalize_task_id,
    normalize_jobs,
    read_json_entry,
)
from annotation.build_yolo_video_dataset import Track, clip_box, collect_annotations, read_csv, track_box_at
from annotation.derive_paddle_placements import (
    VALIDATION_COLUMNS,
    PlacementSettings,
    derive_placements,
    load_placement_settings,
    validation_markdown,
    validation_summary,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/rule_engine/annotation_export.yaml"
DEFAULT_ENGINE_CONFIG = ROOT / "configs/rule_engine/engine.yaml"   # simultaneous_window_seconds (9c)
DEFAULT_CONVERSION_REPORT = ROOT / "annotation/reports/phase4/video_conversion.csv"
TRAINING_DATA = ROOT / "data/video"
EXPORTER_VERSION = 2   # 2: paddle_tracks and paddle_visibility (R4, D-108)
RECORD_KIND = "rule_engine_annotation_record"
TASK_ID = re.compile(r"^P\d{2}_(LL|LS|T)$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EXCEPTION_KEYS = {"task", "zone", "confirmed_by", "confirmed_on", "note"}
ANNOTATION_FILES = ("task.json", "annotations.json")  # the only ZIP entries ever read (D-085)
EXIT_REFUSED = 2


# ---- configuration ------------------------------------------------------------------------------

@dataclass(frozen=True)
class ZoneException:
    """An annotator confirmed that this zone was genuinely not visible in this video (D-082)."""
    task: str
    zone: str
    confirmed_by: str
    confirmed_on: str
    note: str = ""


@dataclass(frozen=True)
class ExportConfig:
    zone_labels: tuple[str, ...]
    paddle_labels: tuple[str, ...]
    usual_zone_pattern: dict[str, tuple[str, ...]]
    reviewed_zone_exceptions: tuple[ZoneException, ...]
    zone_motion_fraction_of_diagonal: float
    repeated_tag_window_frames: int
    placements: PlacementSettings
    screen_label: str = "defibrillator_screen"         # CVAT screen track label (D-094)
    screen_event: str = "shock_delivered_on_screen"    # the canonical event the screen governs
    paddle_regions: tuple[tuple[str, str], ...] = ()   # (CVAT paddle label, engine region) for paddle visibility

    def confirmed_not_visible(self, task_id: str) -> set[str]:
        """Zones an annotator confirmed as genuinely not visible in this video."""
        return {e.zone for e in self.reviewed_zone_exceptions if e.task == task_id}


def _read_yaml(path):
    try:
        return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"{path}: cannot read ({error})") from None


def simultaneous_window_seconds(engine_path: Path = DEFAULT_ENGINE_CONFIG) -> float:
    """The rule engine's simultaneous window, read from engine.yaml so the two never differ (D-086)."""
    data = _read_yaml(engine_path)
    value = _setting_value((data or {}).get("simultaneous_window_seconds"))
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{engine_path}: simultaneous_window_seconds must be a nonnegative number")
    return float(value)


def load_config(path: Path = DEFAULT_CONFIG, engine_path: Path = DEFAULT_ENGINE_CONFIG) -> ExportConfig:
    """Load and validate the export/audit config; every problem is a ValueError naming the entry."""
    data = _read_yaml(path)
    expected = {"schema_version", "zone_labels", "paddle_labels", "usual_zone_pattern",
                "reviewed_zone_exceptions", "audit", "derived_placements", "screen", "paddle_regions"}
    if not isinstance(data, dict) or data.get("schema_version") != 1 or set(data) != expected:
        raise ValueError(f"{path}: expected schema_version: 1 and exactly the keys {sorted(expected)}")
    zones = _labels(data["zone_labels"], f"{path} zone_labels")
    paddles = _labels(data["paddle_labels"], f"{path} paddle_labels")
    pattern = data["usual_zone_pattern"]
    if not isinstance(pattern, dict) or not pattern:
        raise ValueError(f"{path} usual_zone_pattern: expected a mapping of camera view -> zone labels")
    usual = {}
    for view, labels in pattern.items():
        if not isinstance(labels, list) or set(labels) - set(zones) or len(set(labels)) != len(labels):
            raise ValueError(f"{path} usual_zone_pattern.{view}: expected distinct zone labels from {list(zones)}")
        usual[str(view)] = tuple(labels)
    exceptions = _exceptions(data["reviewed_zone_exceptions"], zones, f"{path} reviewed_zone_exceptions")
    audit = data["audit"]
    if not isinstance(audit, dict) or set(audit) != {"zone_motion_fraction_of_diagonal", "repeated_tag_window_frames"}:
        raise ValueError(f"{path} audit: expected zone_motion_fraction_of_diagonal and repeated_tag_window_frames")
    motion = _setting_value(audit["zone_motion_fraction_of_diagonal"])
    window = _setting_value(audit["repeated_tag_window_frames"])
    if isinstance(motion, bool) or not isinstance(motion, (int, float)) or not 0 < motion < 1:
        raise ValueError(f"{path} audit.zone_motion_fraction_of_diagonal: must be a number between 0 and 1")
    if isinstance(window, bool) or not isinstance(window, int) or window < 0:
        raise ValueError(f"{path} audit.repeated_tag_window_frames: must be a whole number of frames >= 0")
    placements = load_placement_settings(data["derived_placements"], zones, paddles,
                                         simultaneous_window_seconds(engine_path), f"{path} derived_placements")
    screen = data["screen"]
    if not isinstance(screen, dict) or set(screen) != {"label", "event"} or not all(
            isinstance(screen[k], str) and screen[k] for k in ("label", "event")):
        raise ValueError(f"{path} screen: expected {{label: <CVAT screen track label>, event: <canonical event>}}")
    regions = data["paddle_regions"]
    if not isinstance(regions, dict) or set(regions) != set(paddles) or not all(
            isinstance(r, str) and r for r in regions.values()) or len(set(regions.values())) != len(regions):
        raise ValueError(f"{path} paddle_regions: expected each of {list(paddles)} -> a distinct engine region")
    return ExportConfig(zones, paddles, usual, exceptions, float(motion), window, placements,
                        screen["label"], screen["event"], tuple((p, regions[p]) for p in paddles))


def _labels(value, where):
    if not isinstance(value, list) or not value or not all(isinstance(v, str) and v for v in value) \
            or len(set(value)) != len(value):
        raise ValueError(f"{where}: expected a nonempty list of distinct CVAT labels")
    return tuple(value)


def _setting_value(raw):
    return raw.get("value") if isinstance(raw, dict) else raw


def _exceptions(value, zones, where):
    if not isinstance(value, list):
        raise ValueError(f"{where}: expected a list")
    found, seen = [], set()
    for index, entry in enumerate(value):
        at = f"{where}[{index}]"
        if not isinstance(entry, dict) or set(entry) - EXCEPTION_KEYS:
            raise ValueError(f"{at}: expected only {sorted(EXCEPTION_KEYS)}")
        task, zone = entry.get("task"), entry.get("zone")
        if not isinstance(task, str) or not TASK_ID.match(task):
            raise ValueError(f"{at}: task must be a canonical task ID such as P07_T")
        if zone not in zones:
            raise ValueError(f"{at}: zone must be one of {list(zones)}")
        if not isinstance(entry.get("confirmed_by"), str) or not entry["confirmed_by"].strip():
            raise ValueError(f"{at}: confirmed_by must name the annotator who confirmed it")
        if not isinstance(entry.get("confirmed_on"), str) or not DATE.match(entry["confirmed_on"]):
            raise ValueError(f'{at}: confirmed_on must be a quoted date "YYYY-MM-DD"')
        if (task, zone) in seen:
            raise ValueError(f"{at}: {task} {zone} is listed twice")
        seen.add((task, zone))
        found.append(ZoneException(task, zone, entry["confirmed_by"].strip(), entry["confirmed_on"],
                                   str(entry.get("note") or "")))
    return tuple(found)


# ---- inputs ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class VideoInfo:
    """fps and frame size of one converted video, from Ananth's conversion report (D-076)."""
    fps: float
    width: int
    height: int
    frame_count: int | None


def load_conversion_report(path: Path = DEFAULT_CONVERSION_REPORT) -> dict[str, VideoInfo]:
    rows = read_csv(Path(path))
    needed = {"canonical_task_id", "fps", "width", "height", "source_frame_count_cvat"}
    if rows and needed - set(rows[0]):
        raise ValueError(f"{path}: missing columns {sorted(needed - set(rows[0]))}")
    videos = {}
    for row in rows:
        fps = float(row["fps"])
        if not fps > 0:
            raise ValueError(f"{path}: {row['canonical_task_id']} has fps {row['fps']!r}")
        frames = row.get("source_frame_count_cvat")
        videos[row["canonical_task_id"]] = VideoInfo(fps, int(row["width"]), int(row["height"]),
                                                     int(frames) if frames else None)
    return videos


@dataclass
class TaskSource:
    """One CVAT task found in a backup ZIP, with its annotations (read-only)."""
    archive: str
    annotation_source: str
    task_path: str
    raw_task_name: str
    media_name: str
    canonical_task_id: str
    participant_id: str
    camera_view: str
    start_frame: int
    stop_frame: int
    tags: list[dict[str, Any]] = field(default_factory=list)
    standalone_shapes: list[dict[str, Any]] = field(default_factory=list)
    tracks: list[Track] = field(default_factory=list)


def iter_tasks(backup_root: Path, issues: list[Issue]) -> Iterator[TaskSource]:
    """Every task in every ZIP under backup_root, in a stable order. Problems become issues."""
    backup_root = Path(backup_root).resolve()
    archives = sorted(backup_root.rglob("*.zip"), key=lambda p: str(p).lower())
    if not archives:
        issues.append(Issue("error", "no_zip_archives", details=f"no ZIP files under {backup_root}"))
    for zip_path in archives:
        relative = zip_path.relative_to(backup_root)
        try:
            archive = zipfile.ZipFile(zip_path)
        except zipfile.BadZipFile as error:
            issues.append(Issue("error", "unreadable_zip", archive=relative.as_posix(), details=str(error)))
            continue
        with archive:
            names = archive.namelist()
            task_names = sorted(n for n in names if n == "task.json" or n.endswith("/task.json"))
            if not task_names:
                issues.append(Issue("error", "no_tasks_in_archive", archive=relative.as_posix()))
            for task_name in task_names:
                source = _task_source(archive, relative, task_name, names, issues)
                if source is not None:
                    yield source


def _task_source(archive, relative, task_json_name, names, issues):
    prefix = task_json_name[: -len("task.json")]
    task_path = prefix.rstrip("/") or "."
    where = dict(archive=relative.as_posix(), task_path=task_path)
    annotation_name = f"{prefix}annotations.json"
    try:
        task = read_json_entry(archive, task_json_name)
        jobs = normalize_jobs(read_json_entry(archive, annotation_name)) if annotation_name in names else None
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        issues.append(Issue("error", "invalid_cvat_json", details=str(error), **where))
        return None
    if jobs is None:
        issues.append(Issue("error", "missing_annotations_json", **where))
        return None
    media = sorted(n for n in names if n.startswith(f"{prefix}data/")
                   and PurePosixPath(n).suffix.lower() in VIDEO_SUFFIXES)
    media_name = PurePosixPath(media[0]).name if media else ""
    raw_name = str(task.get("name", ""))
    task_id, participant_id, _, view = canonicalize_task_id(raw_name, media_name)
    if not task_id:
        issues.append(Issue("error", "unrecognized_task_name",
                            details=f"task={raw_name!r}, media={media_name!r}", **where))
        return None
    data = task.get("data") or {}
    tags, shapes, tracks = collect_annotations(jobs)
    return TaskSource(relative.as_posix(), annotation_source(relative), task_path, raw_name, media_name,
                      task_id, participant_id, view, int(data.get("start_frame", 0) or 0),
                      int(data.get("stop_frame", -1) or -1), tags, shapes, tracks)


# ---- zone visibility --------------------------------------------------------------------------------

def zone_visible_frames(tracks: Iterable[Track], start_frame: int, stop_frame: int, width: int,
                        height: int) -> list[int]:
    """Frames on which any of these tracks gives a training box (same rule as frame_boxes)."""
    tracks = list(tracks)
    return [frame for frame in range(start_frame, stop_frame + 1)
            if any(_training_box(track, frame, width, height) is not None for track in tracks)]


def _training_box(track, frame, width, height):
    box = track_box_at(track, frame)
    return None if box is None else clip_box(box, width, height)[0]


def frame_runs(frames: Iterable[int]) -> list[tuple[int, int]]:
    """Sorted frames as inclusive (first, last) runs of consecutive frames."""
    runs: list[list[int]] = []
    for frame in sorted(set(frames)):
        if runs and frame == runs[-1][1] + 1:
            runs[-1][1] = frame
        else:
            runs.append([frame, frame])
    return [(first, last) for first, last in runs]


def zone_visibility(source: TaskSource, video: VideoInfo, zone_labels: Iterable[str]) -> list[dict[str, Any]]:
    intervals = []
    for zone in zone_labels:
        tracks = [t for t in source.tracks if t.label == zone]
        frames = zone_visible_frames(tracks, source.start_frame, source.stop_frame, video.width, video.height)
        for first, last in frame_runs(frames):
            intervals.append({"label": zone, "start_frame": first, "end_frame": last,
                              "start_seconds": _seconds(first, video.fps), "end_seconds": _seconds(last, video.fps)})
    return intervals


def _seconds(frame, fps):
    return round(frame / fps, 6)


# ---- records ----------------------------------------------------------------------------------------

def export_record(source: TaskSource, videos: dict[str, VideoInfo], config: ExportConfig,
                  issues: list[Issue], validation: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """The rule-engine record for one task, or None (with an issue) when it cannot be timed."""
    where = dict(archive=source.archive, task_path=source.task_path, canonical_task_id=source.canonical_task_id)
    video = videos.get(source.canonical_task_id)
    if video is None:
        issues.append(Issue("error", "fps_missing", details="video not in the conversion report, so its "
                            "frames cannot be converted to seconds", **where))
        return None
    frame_count = source.stop_frame - source.start_frame + 1
    if video.frame_count is not None and video.frame_count != frame_count:
        issues.append(Issue("warning", "frame_count_mismatch", details=f"backup={frame_count}, "
                            f"conversion report={video.frame_count}", **where))
    tags = sorted(((str(t.get("label", "")), int(t.get("frame", -1))) for t in source.tags), key=lambda t: (t[1], t[0]))
    exported_tags = []
    for index, (label, frame) in enumerate(tags, start=1):
        if not source.start_frame <= frame <= source.stop_frame:
            issues.append(Issue("warning", "tag_outside_frames", label=label, frame=frame, **where))
        exported_tags.append({"id": f"{source.canonical_task_id}_tag_{index:03d}", "label": label, "frame": frame,
                              "timestamp_seconds": _seconds(frame, video.fps)})
    for shape in source.standalone_shapes:
        if str(shape.get("label", "")) in config.zone_labels:
            issues.append(Issue("review", "zone_shape_without_track", label=str(shape.get("label")),
                                frame=int(shape.get("frame", -1)), details="a single-frame zone shape is not "
                                "converted to visibility; only zone tracks are", **where))
    derived, rows = derive_placements(source, video, config.placements, issues)
    if validation is not None:
        validation.extend(rows)
    return {
        "schema_version": 1,
        "kind": RECORD_KIND,
        "canonical_task_id": source.canonical_task_id,
        "participant_id": source.participant_id,
        "camera_view": source.camera_view,
        "annotation_source": source.annotation_source,
        "archive": source.archive,
        "task_path": source.task_path,
        "media_name": source.media_name,
        "fps": video.fps,
        "width": video.width,
        "height": video.height,
        "start_frame": source.start_frame,
        "stop_frame": source.stop_frame,
        "duration_seconds": _seconds(source.stop_frame + 1, video.fps),
        "tags": exported_tags,
        "zone_tracks": {zone: sum(t.label == zone for t in source.tracks) for zone in config.zone_labels},
        "zone_visibility": zone_visibility(source, video, config.zone_labels),
        # The defibrillator screen, derived exactly like the zones (D-094).
        "screen_tracks": sum(t.label == config.screen_label for t in source.tracks),
        "screen_visibility": zone_visibility(source, video, (config.screen_label,)),
        # The paddles, derived exactly like the zones: R4's coverage of the button press (D-108).
        "paddle_tracks": {paddle: sum(t.label == paddle for t in source.tracks) for paddle in config.paddle_labels},
        "paddle_visibility": zone_visibility(source, video, config.paddle_labels),
        "derived_events": derived,  # Step 9c: per-paddle placements (D-081, D-086 to D-089)
    }


def unique_tasks(sources: Iterable[TaskSource], issues: list[Issue]) -> list[TaskSource]:
    """The first source of each canonical task ID; later duplicates are export issues."""
    kept: dict[str, TaskSource] = {}
    for source in sources:
        if source.canonical_task_id in kept:
            first = kept[source.canonical_task_id]
            issues.append(Issue("error", "duplicate_task", archive=source.archive, task_path=source.task_path,
                                canonical_task_id=source.canonical_task_id,
                                details=f"already exported from {first.archive}:{first.task_path}"))
            continue
        kept[source.canonical_task_id] = source
    return [kept[key] for key in sorted(kept)]


# ---- output -----------------------------------------------------------------------------------------

def check_output(output: Path) -> Path:
    """The resolved output folder; refused inside the training data or when not empty."""
    output = Path(output).resolve()
    if output == TRAINING_DATA or TRAINING_DATA in output.parents:
        raise ValueError(f"{output}: refusing to write inside {TRAINING_DATA}, which the training pipeline reads")
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"{output}: output folder is not empty; use a new run folder")
    return output


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_issues(path: Path, issues: Iterable[Issue]) -> None:
    columns = list(Issue.__dataclass_fields__)
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for issue in issues:
            writer.writerow(asdict(issue))


def backup_list(backup_root: Path) -> list[dict[str, Any]]:
    """Each backup ZIP with a SHA-256 of its annotation JSON only.

    Privacy (D-085): media entries are never opened, hashed or listed; only ``task.json`` and
    ``annotations.json`` are read.
    """
    backup_root = Path(backup_root).resolve()
    listed = []
    for path in sorted(backup_root.rglob("*.zip"), key=lambda p: str(p).lower()):
        entry = {"archive": path.relative_to(backup_root).as_posix(), "size_bytes": path.stat().st_size}
        try:
            entry["annotation_sha256"] = annotation_digest(path)
        except zipfile.BadZipFile:
            entry["annotation_sha256"] = None
        listed.append(entry)
    return listed


def annotation_digest(zip_path: Path) -> str:
    """SHA-256 over the task.json and annotations.json entries of one ZIP, in name order."""
    digest = hashlib.sha256()
    with zipfile.ZipFile(zip_path) as archive:
        for name in sorted(n for n in archive.namelist() if PurePosixPath(n).name in ANNOTATION_FILES):
            digest.update(name.encode("utf-8") + b"\0")
            with archive.open(name) as stream:
                digest.update(stream.read())
    return digest.hexdigest()


def export(backup_root: Path, output: Path, conversion_report: Path = DEFAULT_CONVERSION_REPORT,
           config_path: Path = DEFAULT_CONFIG, engine_path: Path = DEFAULT_ENGINE_CONFIG) -> dict[str, Any]:
    """Write records.jsonl, export_issues.csv, placement_validation.csv/.md and export_manifest.json."""
    output = check_output(output)
    config = load_config(config_path, engine_path)
    videos = load_conversion_report(conversion_report)
    issues: list[Issue] = []
    validation: list[dict[str, Any]] = []
    sources = unique_tasks(iter_tasks(backup_root, issues), issues)
    records = [r for r in (export_record(s, videos, config, issues, validation) for s in sources) if r is not None]
    output.mkdir(parents=True, exist_ok=True)
    # Written as bytes (LF on every OS), so export_id is the SHA-256 of the file exactly as sent.
    lines = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records).encode("utf-8")
    (output / "records.jsonl").write_bytes(lines)
    write_issues(output / "export_issues.csv", issues)
    with (output / "placement_validation.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=VALIDATION_COLUMNS)
        writer.writeheader()
        writer.writerows(validation)
    severities = {}
    for issue in issues:
        severities[issue.severity] = severities.get(issue.severity, 0) + 1
    manifest = {
        "schema_version": 1,
        "kind": "rule_engine_annotation_export",
        "exporter_version": EXPORTER_VERSION,
        # Identifies exactly this export (the records written); the 9c gate names it (D-088).
        "export_id": hashlib.sha256(lines).hexdigest(),
        "placement_settings_sha256": config.placements.digest(),
        "exported_on": date.today().isoformat(),
        "backups": backup_list(backup_root),
        "conversion_report": {"path": _display(conversion_report), "sha256": sha256_file(conversion_report)},
        "config": {"path": _display(config_path), "sha256": sha256_file(config_path)},
        "counts": {"tasks": len(sources), "records": len(records), "tags": sum(len(r["tags"]) for r in records),
                   "zone_intervals": sum(len(r["zone_visibility"]) for r in records),
                   "screen_intervals": sum(len(r["screen_visibility"]) for r in records),
                   "paddle_intervals": sum(len(r["paddle_visibility"]) for r in records),
                   "derived_events": sum(len(r["derived_events"]) for r in records)},
        "issues": dict(sorted(severities.items())),
    }
    summary = validation_summary(validation, config.placements, manifest)
    manifest["placement_validation"] = summary
    (output / "placement_validation.md").write_text(validation_markdown(summary, validation, config.placements),
                                                    encoding="utf-8")
    (output / "export_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _display(path):
    path = Path(path).resolve()
    return path.relative_to(ROOT).as_posix() if ROOT in path.parents else str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backup-root", type=Path, required=True, help="folder containing the CVAT backup ZIPs")
    parser.add_argument("--output", type=Path, required=True,
                        help="new run folder, e.g. data/rule_engine/annotation_export/2026-10-16")
    parser.add_argument("--conversion-report", type=Path, default=DEFAULT_CONVERSION_REPORT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--engine-config", type=Path, default=DEFAULT_ENGINE_CONFIG,
                        help="rule-engine engine.yaml (for simultaneous_window_seconds)")
    args = parser.parse_args(argv)
    if not args.backup_root.is_dir():
        print(f"No export: backup root not found: {args.backup_root}", file=sys.stderr)
        return EXIT_REFUSED
    try:
        manifest = export(args.backup_root, args.output, args.conversion_report, args.config, args.engine_config)
    except ValueError as error:
        print(f"No export: {error}", file=sys.stderr)
        return EXIT_REFUSED
    counts = manifest["counts"]
    print(f"Exported {counts['records']} of {counts['tasks']} tasks ({counts['tags']} tags, "
          f"{counts['zone_intervals']} zone intervals, {counts['derived_events']} derived placements); "
          f"issues: {manifest['issues'] or 'none'}")
    print(f"export_id {manifest['export_id']}; placement settings {manifest['placement_settings_sha256']}")
    print(f"Written to {Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
