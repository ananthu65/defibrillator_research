#!/usr/bin/env python3
"""Audit CVAT task/project backup ZIPs without modifying or extracting them.

The auditor reads CVAT ``task.json`` and ``annotations.json`` files directly
from backup archives. It produces deterministic CSV/JSON reports that can be
reviewed before any train/validation/test split or model-data conversion.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


EVENT_LABELS = (
    "Gel applied",
    "first_paddle_taken",
    "second_paddle_taken",
    "paddles_firmly_on_chest",
    "both_paddle_buttons_pressed",
    "shock_delivered_on_screen",
    "paddles_removed_after_shock",
)

TRACK_LABELS = (
    "paddle_sternal",
    "paddle_apical",
    "defibrillator_screen",
    "learner_hand",
    "sternal_placement_zone",
    "apical_placement_zone",
    "shock_symbol",
)

VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ISSUE_SEVERITY_ORDER = {"error": 0, "warning": 1, "review": 2, "info": 3}


@dataclass
class Issue:
    severity: str
    code: str
    archive: str = ""
    task_path: str = ""
    canonical_task_id: str = ""
    label: str = ""
    frame: int | str = ""
    details: str = ""


@dataclass
class TaskRecord:
    archive: str
    archive_type: str
    annotation_source: str
    task_path: str
    raw_task_name: str
    media_name: str
    canonical_task_id: str
    participant_id: str
    participant_number: int | str
    camera_view: str
    subset: str
    task_status: str
    job_statuses: str
    start_frame: int
    stop_frame: int
    frame_count: int
    width: int | str
    height: int | str
    media_size_bytes: int
    declared_label_count: int
    tag_count: int
    standalone_shape_count: int
    track_count: int
    track_keyframe_count: int
    rotated_keyframe_count: int
    outside_keyframe_count: int
    tag_labels: str
    track_labels: str
    shape_types: str
    event_frames: str
    schema_fingerprint: str


@dataclass
class ArchiveRecord:
    archive: str
    archive_type: str
    annotation_source: str
    compressed_size_bytes: int
    uncompressed_size_bytes: int = 0
    task_count: int = 0
    participant_count: int = 0
    video_count: int = 0
    frame_count: int = 0
    tag_count: int = 0
    standalone_shape_count: int = 0
    track_count: int = 0
    track_keyframe_count: int = 0
    integrity: str = "not_checked"


@dataclass
class AuditResult:
    tasks: list[TaskRecord] = field(default_factory=list)
    archives: list[ArchiveRecord] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    class_stats: dict[str, dict[str, Any]] = field(default_factory=dict)
    class_view_stats: dict[tuple[str, str, str], dict[str, Any]] = field(
        default_factory=dict
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit CVAT backup ZIPs and generate Phase 1 reports."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Folder containing CVAT task/project backup ZIPs.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/phase1"),
        help="Report output folder (default: reports/phase1).",
    )
    parser.add_argument(
        "--expected-participants",
        type=int,
        default=None,
        metavar="N",
        help="Optionally report missing participant IDs from P01 through PN.",
    )
    parser.add_argument(
        "--verify-crc",
        action="store_true",
        help="Read every ZIP entry and verify its CRC.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 2 when error-severity issues are found.",
    )
    return parser.parse_args(argv)


def read_json_entry(archive: zipfile.ZipFile, name: str) -> Any:
    with archive.open(name) as stream:
        return json.load(stream)


def read_manifest_properties(
    archive: zipfile.ZipFile, manifest_name: str
) -> dict[str, Any]:
    with archive.open(manifest_name) as stream:
        for raw_line in stream:
            line = raw_line.decode("utf-8-sig").strip()
            if not line:
                continue
            item = json.loads(line)
            if "properties" in item:
                return item["properties"]
    return {}


def annotation_source(relative_archive: Path) -> str:
    if len(relative_archive.parts) > 1:
        return relative_archive.parts[0]
    return relative_archive.stem


def strip_video_suffix(name: str) -> str:
    candidate = name.strip().rstrip(".")
    while Path(candidate).suffix.lower() in VIDEO_SUFFIXES:
        candidate = Path(candidate).stem
    return candidate.strip().rstrip(".")


def canonicalize_task_id(task_name: str, media_name: str = "") -> tuple[str, str, int | str, str]:
    """Return canonical task ID, participant ID/number, and camera view."""

    source = strip_video_suffix(media_name or task_name)
    compact = re.sub(r"[\s-]+", "_", source.upper())
    compact = re.sub(r"^P+_?", "P", compact)

    match = re.search(r"P_?0*(\d+)_?(LL|LS|T)$", compact)
    if not match:
        fallback = strip_video_suffix(task_name)
        fallback = re.sub(r"[\s-]+", "_", fallback.upper())
        fallback = re.sub(r"^P+_?", "P", fallback)
        match = re.search(r"P_?0*(\d+)_?(LL|LS|T)$", fallback)
    if not match:
        return "", "", "", ""

    number = int(match.group(1))
    view = match.group(2)
    participant_id = f"P{number:02d}"
    return f"{participant_id}_{view}", participant_id, number, view


def schema_fingerprint(labels: Iterable[dict[str, Any]]) -> str:
    pairs = sorted(f"{item.get('name', '')}:{item.get('type', '')}" for item in labels)
    return "|".join(pairs)


def normalize_jobs(annotation_data: Any) -> list[dict[str, Any]]:
    if isinstance(annotation_data, list):
        return [item for item in annotation_data if isinstance(item, dict)]
    if isinstance(annotation_data, dict):
        return [annotation_data]
    return []


def point_pairs(points: Any) -> Iterable[tuple[float, float]]:
    if not isinstance(points, list):
        return
    for index in range(0, len(points) - 1, 2):
        try:
            yield float(points[index]), float(points[index + 1])
        except (TypeError, ValueError):
            continue


def add_issue(
    issues: list[Issue],
    severity: str,
    code: str,
    *,
    archive: str = "",
    task_path: str = "",
    canonical_task_id: str = "",
    label: str = "",
    frame: int | str = "",
    details: str = "",
) -> None:
    issues.append(
        Issue(
            severity=severity,
            code=code,
            archive=archive,
            task_path=task_path,
            canonical_task_id=canonical_task_id,
            label=label,
            frame=frame,
            details=details,
        )
    )


def audit_task(
    archive: zipfile.ZipFile,
    archive_relative: str,
    archive_type: str,
    source: str,
    task_json_name: str,
    issues: list[Issue],
) -> tuple[TaskRecord | None, dict[str, dict[str, Any]], list[dict[str, Any]]]:
    prefix = task_json_name[: -len("task.json")]
    task_path = prefix.rstrip("/") or "."
    annotation_name = f"{prefix}annotations.json"

    try:
        task = read_json_entry(archive, task_json_name)
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        add_issue(
            issues,
            "error",
            "invalid_task_json",
            archive=archive_relative,
            task_path=task_path,
            details=str(exc),
        )
        return None, {}, []

    if annotation_name not in archive.namelist():
        add_issue(
            issues,
            "error",
            "missing_annotations_json",
            archive=archive_relative,
            task_path=task_path,
        )
        annotation_jobs: list[dict[str, Any]] = []
    else:
        try:
            annotation_jobs = normalize_jobs(read_json_entry(archive, annotation_name))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            add_issue(
                issues,
                "error",
                "invalid_annotations_json",
                archive=archive_relative,
                task_path=task_path,
                details=str(exc),
            )
            annotation_jobs = []

    media_entries = [
        entry
        for entry in archive.infolist()
        if entry.filename.startswith(f"{prefix}data/")
        and PurePosixPath(entry.filename).suffix.lower() in VIDEO_SUFFIXES
    ]
    if not media_entries:
        add_issue(
            issues,
            "error",
            "missing_media",
            archive=archive_relative,
            task_path=task_path,
        )
    elif len(media_entries) > 1:
        add_issue(
            issues,
            "warning",
            "multiple_media_files",
            archive=archive_relative,
            task_path=task_path,
            details=", ".join(entry.filename for entry in media_entries),
        )

    media_entry = media_entries[0] if media_entries else None
    media_name = PurePosixPath(media_entry.filename).name if media_entry else ""
    raw_task_name = str(task.get("name", ""))
    canonical_id, participant_id, participant_number, view = canonicalize_task_id(
        raw_task_name, media_name
    )
    if not canonical_id:
        add_issue(
            issues,
            "error",
            "unrecognized_task_name",
            archive=archive_relative,
            task_path=task_path,
            details=f"task={raw_task_name!r}, media={media_name!r}",
        )
    elif raw_task_name.strip().upper() != canonical_id:
        add_issue(
            issues,
            "warning",
            "task_name_normalized",
            archive=archive_relative,
            task_path=task_path,
            canonical_task_id=canonical_id,
            details=f"{raw_task_name!r} normalized using media {media_name!r}",
        )

    data = task.get("data") or {}
    start_frame = int(data.get("start_frame", 0) or 0)
    stop_frame = int(data.get("stop_frame", -1) or -1)
    frame_count = max(0, stop_frame - start_frame + 1)

    manifest_name = f"{prefix}data/manifest.jsonl"
    manifest_properties: dict[str, Any] = {}
    if manifest_name in archive.namelist():
        try:
            manifest_properties = read_manifest_properties(archive, manifest_name)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            add_issue(
                issues,
                "warning",
                "invalid_manifest",
                archive=archive_relative,
                task_path=task_path,
                canonical_task_id=canonical_id,
                details=str(exc),
            )

    resolution = manifest_properties.get("resolution") or []
    width = resolution[0] if len(resolution) >= 2 else ""
    height = resolution[1] if len(resolution) >= 2 else ""
    manifest_length = manifest_properties.get("length")
    if manifest_length is not None and int(manifest_length) != frame_count:
        add_issue(
            issues,
            "warning",
            "frame_count_mismatch",
            archive=archive_relative,
            task_path=task_path,
            canonical_task_id=canonical_id,
            details=f"task={frame_count}, manifest={manifest_length}",
        )

    declared_labels = task.get("labels") or []
    declared_types = {
        str(label.get("name", "")): str(label.get("type", ""))
        for label in declared_labels
    }

    tags: list[dict[str, Any]] = []
    standalone_shapes: list[dict[str, Any]] = []
    tracks: list[dict[str, Any]] = []
    for job in annotation_jobs:
        tags.extend(job.get("tags") or [])
        standalone_shapes.extend(job.get("shapes") or [])
        tracks.extend(job.get("tracks") or [])

    all_track_shapes: list[dict[str, Any]] = []
    for track in tracks:
        label = str(track.get("label", ""))
        shapes = track.get("shapes") or []
        all_track_shapes.extend(shapes)
        if not shapes:
            add_issue(
                issues,
                "warning",
                "empty_track",
                archive=archive_relative,
                task_path=task_path,
                canonical_task_id=canonical_id,
                label=label,
            )

    task_class_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "declared_type": "",
            "tags": 0,
            "standalone_shapes": 0,
            "tracks": 0,
            "track_keyframes": 0,
            "tasks_present": 0,
        }
    )
    present_labels: set[str] = set()

    for kind, annotations in (
        ("tag", tags),
        ("standalone_shape", standalone_shapes),
        ("track", tracks),
    ):
        for annotation in annotations:
            label = str(annotation.get("label", ""))
            present_labels.add(label)
            stats = task_class_stats[label]
            stats["declared_type"] = declared_types.get(label, "")
            if kind == "tag":
                stats["tags"] += 1
                if declared_types.get(label) != "tag":
                    add_issue(
                        issues,
                        "warning",
                        "object_label_used_as_tag",
                        archive=archive_relative,
                        task_path=task_path,
                        canonical_task_id=canonical_id,
                        label=label,
                        frame=annotation.get("frame", ""),
                    )
            elif kind == "standalone_shape":
                stats["standalone_shapes"] += 1
                add_issue(
                    issues,
                    "review",
                    "standalone_shape_in_video_task",
                    archive=archive_relative,
                    task_path=task_path,
                    canonical_task_id=canonical_id,
                    label=label,
                    frame=annotation.get("frame", ""),
                )
            else:
                stats["tracks"] += 1
                stats["track_keyframes"] += len(annotation.get("shapes") or [])
                if declared_types.get(label) == "tag":
                    add_issue(
                        issues,
                        "warning",
                        "event_label_used_as_track",
                        archive=archive_relative,
                        task_path=task_path,
                        canonical_task_id=canonical_id,
                        label=label,
                    )
    for label in present_labels:
        task_class_stats[label]["tasks_present"] = 1

    for annotation_kind, annotations in (
        ("tag", tags),
        ("shape", standalone_shapes),
    ):
        for annotation in annotations:
            frame = annotation.get("frame")
            if isinstance(frame, int) and not start_frame <= frame <= stop_frame:
                add_issue(
                    issues,
                    "error",
                    "annotation_frame_out_of_range",
                    archive=archive_relative,
                    task_path=task_path,
                    canonical_task_id=canonical_id,
                    label=str(annotation.get("label", "")),
                    frame=frame,
                    details=annotation_kind,
                )

    coordinates_outside_frame: dict[str, list[int]] = defaultdict(list)
    for track in tracks:
        label = str(track.get("label", ""))
        for shape in track.get("shapes") or []:
            frame = shape.get("frame")
            if isinstance(frame, int) and not start_frame <= frame <= stop_frame:
                add_issue(
                    issues,
                    "error",
                    "annotation_frame_out_of_range",
                    archive=archive_relative,
                    task_path=task_path,
                    canonical_task_id=canonical_id,
                    label=label,
                    frame=frame,
                    details="track keyframe",
                )
            points = list(point_pairs(shape.get("points")))
            if shape.get("type") == "rectangle" and len(points) != 2:
                add_issue(
                    issues,
                    "warning",
                    "invalid_rectangle_points",
                    archive=archive_relative,
                    task_path=task_path,
                    canonical_task_id=canonical_id,
                    label=label,
                    frame=frame if isinstance(frame, int) else "",
                )
            if width and height:
                outside_bounds = [
                    (x, y)
                    for x, y in points
                    if x < 0 or y < 0 or x > float(width) or y > float(height)
                ]
                if outside_bounds:
                    coordinates_outside_frame[label].append(
                        frame if isinstance(frame, int) else -1
                    )

    for label, frames in sorted(coordinates_outside_frame.items()):
        valid_frames = sorted(frame for frame in frames if frame >= 0)
        frame_summary = ""
        if valid_frames:
            frame_summary = f"; frame_range={valid_frames[0]}-{valid_frames[-1]}"
        add_issue(
            issues,
            "review",
            "coordinates_outside_frame",
            archive=archive_relative,
            task_path=task_path,
            canonical_task_id=canonical_id,
            label=label,
            frame=valid_frames[0] if valid_frames else "",
            details=(
                f"keyframes={len(frames)}; resolution={width}x{height}{frame_summary}"
            ),
        )

    tag_groups: dict[str, list[int]] = defaultdict(list)
    for tag in tags:
        frame = tag.get("frame")
        if isinstance(frame, int):
            tag_groups[str(tag.get("label", ""))].append(frame)

    for label, frames in tag_groups.items():
        duplicate_frames = [frame for frame, count in Counter(frames).items() if count > 1]
        for frame in duplicate_frames:
            add_issue(
                issues,
                "warning",
                "duplicate_event_tag",
                archive=archive_relative,
                task_path=task_path,
                canonical_task_id=canonical_id,
                label=label,
                frame=frame,
            )
        if label in EVENT_LABELS and len(frames) > 1:
            add_issue(
                issues,
                "review",
                "repeated_event_tag",
                archive=archive_relative,
                task_path=task_path,
                canonical_task_id=canonical_id,
                label=label,
                details="frames=" + ",".join(str(frame) for frame in sorted(frames)),
            )

    ordered_events = [
        (label, min(tag_groups[label]))
        for label in EVENT_LABELS
        if tag_groups.get(label)
    ]
    for previous, current in zip(ordered_events, ordered_events[1:]):
        if current[1] < previous[1]:
            add_issue(
                issues,
                "review",
                "event_order_violation",
                archive=archive_relative,
                task_path=task_path,
                canonical_task_id=canonical_id,
                label=current[0],
                frame=current[1],
                details=f"{previous[0]}@{previous[1]} -> {current[0]}@{current[1]}",
            )

    missing_events = [label for label in EVENT_LABELS if label not in tag_groups]
    if missing_events:
        add_issue(
            issues,
            "info",
            "missing_event_tags",
            archive=archive_relative,
            task_path=task_path,
            canonical_task_id=canonical_id,
            details=", ".join(missing_events),
        )

    track_labels = {str(track.get("label", "")) for track in tracks}
    missing_tracks = [label for label in TRACK_LABELS if label not in track_labels]
    if missing_tracks:
        add_issue(
            issues,
            "info",
            "missing_track_labels",
            archive=archive_relative,
            task_path=task_path,
            canonical_task_id=canonical_id,
            details=", ".join(missing_tracks),
        )

    if not str(task.get("subset", "")).strip():
        add_issue(
            issues,
            "info",
            "blank_cvat_subset",
            archive=archive_relative,
            task_path=task_path,
            canonical_task_id=canonical_id,
            details="A new grouped split will be generated; CVAT subset is ignored.",
        )

    event_frames = ";".join(
        f"{label}={','.join(str(frame) for frame in sorted(frames))}"
        for label, frames in sorted(tag_groups.items())
        if label in EVENT_LABELS
    )
    record = TaskRecord(
        archive=archive_relative,
        archive_type=archive_type,
        annotation_source=source,
        task_path=task_path,
        raw_task_name=raw_task_name,
        media_name=media_name,
        canonical_task_id=canonical_id,
        participant_id=participant_id,
        participant_number=participant_number,
        camera_view=view,
        subset=str(task.get("subset", "")),
        task_status=str(task.get("status", "")),
        job_statuses=",".join(
            sorted(
                {
                    str(job.get("status", ""))
                    for job in task.get("jobs") or []
                    if job.get("status") is not None
                }
            )
        ),
        start_frame=start_frame,
        stop_frame=stop_frame,
        frame_count=frame_count,
        width=width,
        height=height,
        media_size_bytes=media_entry.file_size if media_entry else 0,
        declared_label_count=len(declared_labels),
        tag_count=len(tags),
        standalone_shape_count=len(standalone_shapes),
        track_count=len(tracks),
        track_keyframe_count=len(all_track_shapes),
        rotated_keyframe_count=sum(
            float(shape.get("rotation", 0) or 0) != 0 for shape in all_track_shapes
        ),
        outside_keyframe_count=sum(
            bool(shape.get("outside", False)) for shape in all_track_shapes
        ),
        tag_labels=";".join(sorted({str(tag.get("label", "")) for tag in tags})),
        track_labels=";".join(sorted(track_labels)),
        shape_types=";".join(
            sorted({str(shape.get("type", "")) for shape in all_track_shapes})
        ),
        event_frames=event_frames,
        schema_fingerprint=schema_fingerprint(declared_labels),
    )
    return record, dict(task_class_stats), tags + tracks


def audit_backups(
    input_root: Path,
    *,
    expected_participants: int | None = None,
    verify_crc: bool = False,
) -> AuditResult:
    result = AuditResult()
    input_root = input_root.resolve()
    archives = sorted(input_root.rglob("*.zip"), key=lambda path: str(path).lower())
    if not archives:
        add_issue(
            result.issues,
            "error",
            "no_zip_archives",
            details=f"No ZIP files found under {input_root}",
        )
        return result

    class_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "declared_type": "",
            "tags": 0,
            "standalone_shapes": 0,
            "tracks": 0,
            "track_keyframes": 0,
            "tasks_present": 0,
        }
    )
    class_view_stats: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {"annotations": 0, "tasks": set()}
    )

    for zip_path in archives:
        relative_path = zip_path.relative_to(input_root)
        relative = relative_path.as_posix()
        source = annotation_source(relative_path)
        archive_record = ArchiveRecord(
            archive=relative,
            archive_type="unknown",
            annotation_source=source,
            compressed_size_bytes=zip_path.stat().st_size,
        )
        try:
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
                archive_record.uncompressed_size_bytes = sum(
                    entry.file_size for entry in archive.infolist()
                )
                if "project.json" in names:
                    archive_type = "project_backup"
                elif "task.json" in names:
                    archive_type = "task_backup"
                else:
                    archive_type = "unknown"
                    add_issue(
                        result.issues,
                        "error",
                        "unknown_backup_structure",
                        archive=relative,
                    )
                archive_record.archive_type = archive_type

                if verify_crc:
                    bad_entry = archive.testzip()
                    archive_record.integrity = (
                        "ok" if bad_entry is None else f"bad_entry:{bad_entry}"
                    )
                    if bad_entry is not None:
                        add_issue(
                            result.issues,
                            "error",
                            "zip_crc_failure",
                            archive=relative,
                            details=bad_entry,
                        )

                task_json_names = sorted(
                    name
                    for name in names
                    if name == "task.json" or name.endswith("/task.json")
                )
                if not task_json_names:
                    add_issue(
                        result.issues,
                        "error",
                        "no_tasks_in_archive",
                        archive=relative,
                    )

                archive_tasks: list[TaskRecord] = []
                for task_json_name in task_json_names:
                    task, task_stats, annotations = audit_task(
                        archive,
                        relative,
                        archive_type,
                        source,
                        task_json_name,
                        result.issues,
                    )
                    if task is None:
                        continue
                    result.tasks.append(task)
                    archive_tasks.append(task)
                    for label, stats in task_stats.items():
                        destination = class_stats[label]
                        destination["declared_type"] = (
                            destination["declared_type"] or stats["declared_type"]
                        )
                        for key in (
                            "tags",
                            "standalone_shapes",
                            "tracks",
                            "track_keyframes",
                            "tasks_present",
                        ):
                            destination[key] += stats[key]

                    for annotation in annotations:
                        label = str(annotation.get("label", ""))
                        if "shapes" in annotation:
                            kind = "track"
                            count = 1
                        elif "frame" in annotation:
                            kind = "tag"
                            count = 1
                        else:
                            continue
                        view_key = (kind, label, task.camera_view)
                        class_view_stats[view_key]["annotations"] += count
                        class_view_stats[view_key]["tasks"].add(task.canonical_task_id)

                archive_record.task_count = len(archive_tasks)
                archive_record.participant_count = len(
                    {task.participant_id for task in archive_tasks if task.participant_id}
                )
                archive_record.video_count = sum(bool(task.media_name) for task in archive_tasks)
                archive_record.frame_count = sum(task.frame_count for task in archive_tasks)
                archive_record.tag_count = sum(task.tag_count for task in archive_tasks)
                archive_record.standalone_shape_count = sum(
                    task.standalone_shape_count for task in archive_tasks
                )
                archive_record.track_count = sum(task.track_count for task in archive_tasks)
                archive_record.track_keyframe_count = sum(
                    task.track_keyframe_count for task in archive_tasks
                )
        except (zipfile.BadZipFile, OSError) as exc:
            archive_record.integrity = "unreadable"
            add_issue(
                result.issues,
                "error",
                "unreadable_zip",
                archive=relative,
                details=str(exc),
            )
        result.archives.append(archive_record)

    by_canonical_id: dict[str, list[TaskRecord]] = defaultdict(list)
    by_participant: dict[str, set[str]] = defaultdict(set)
    for task in result.tasks:
        if task.canonical_task_id:
            by_canonical_id[task.canonical_task_id].append(task)
        if task.participant_id and task.camera_view:
            by_participant[task.participant_id].add(task.camera_view)

    for canonical_id, tasks in sorted(by_canonical_id.items()):
        if len(tasks) > 1:
            add_issue(
                result.issues,
                "error",
                "duplicate_canonical_task",
                canonical_task_id=canonical_id,
                details="; ".join(f"{task.archive}:{task.task_path}" for task in tasks),
            )

    required_views = {"T", "LS", "LL"}
    for participant_id, views in sorted(by_participant.items()):
        if views != required_views:
            add_issue(
                result.issues,
                "warning",
                "incomplete_camera_set",
                canonical_task_id=participant_id,
                details=f"present={','.join(sorted(views))}; missing={','.join(sorted(required_views - views))}",
            )

    if expected_participants is not None:
        for number in range(1, expected_participants + 1):
            participant_id = f"P{number:02d}"
            if participant_id not in by_participant:
                add_issue(
                    result.issues,
                    "info",
                    "missing_expected_participant",
                    canonical_task_id=participant_id,
                    details="No task backup found for this participant.",
                )

    schema_counts = Counter(task.schema_fingerprint for task in result.tasks)
    for fingerprint, count in sorted(schema_counts.items()):
        if count != len(result.tasks):
            add_issue(
                result.issues,
                "warning",
                "schema_variant",
                details=f"tasks={count}; schema={fingerprint}",
            )

    result.tasks.sort(key=lambda task: (int(task.participant_number or 999999), task.camera_view))
    result.archives.sort(key=lambda archive: archive.archive.lower())
    result.issues.sort(
        key=lambda issue: (
            ISSUE_SEVERITY_ORDER.get(issue.severity, 99),
            issue.code,
            issue.canonical_task_id,
            issue.archive,
            str(issue.frame),
        )
    )
    result.class_stats = dict(class_stats)
    result.class_view_stats = dict(class_view_stats)
    return result


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def report_digest(tasks: list[TaskRecord]) -> str:
    stable_rows = [
        {
            "archive": task.archive,
            "task_path": task.task_path,
            "canonical_task_id": task.canonical_task_id,
            "frame_count": task.frame_count,
            "tags": task.tag_count,
            "tracks": task.track_count,
            "keyframes": task.track_keyframe_count,
        }
        for task in tasks
    ]
    payload = json.dumps(stable_rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_reports(result: AuditResult, output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)

    task_rows = [asdict(task) for task in result.tasks]
    task_fields = [item.name for item in fields(TaskRecord)]
    write_csv(output_root / "dataset_inventory.csv", task_rows, task_fields)

    archive_rows = [asdict(archive) for archive in result.archives]
    archive_fields = [item.name for item in fields(ArchiveRecord)]
    write_csv(output_root / "annotation_summary.csv", archive_rows, archive_fields)

    issue_rows = [asdict(issue) for issue in result.issues]
    issue_fields = [item.name for item in fields(Issue)]
    write_csv(output_root / "annotation_issues.csv", issue_rows, issue_fields)

    class_rows: list[dict[str, Any]] = []
    for label, stats in sorted(result.class_stats.items()):
        class_rows.append({"label": label, **stats})
    write_csv(
        output_root / "class_distribution.csv",
        class_rows,
        [
            "label",
            "declared_type",
            "tags",
            "standalone_shapes",
            "tracks",
            "track_keyframes",
            "tasks_present",
        ],
    )

    view_rows: list[dict[str, Any]] = []
    for (kind, label, view), stats in sorted(result.class_view_stats.items()):
        view_rows.append(
            {
                "annotation_kind": kind,
                "label": label,
                "camera_view": view,
                "annotations": stats["annotations"],
                "tasks_present": len(stats["tasks"]),
            }
        )
    write_csv(
        output_root / "class_distribution_by_view.csv",
        view_rows,
        ["annotation_kind", "label", "camera_view", "annotations", "tasks_present"],
    )

    participants: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"views": set(), "tasks": [], "sources": set()}
    )
    for task in result.tasks:
        if not task.participant_id:
            continue
        participants[task.participant_id]["views"].add(task.camera_view)
        participants[task.participant_id]["tasks"].append(task.canonical_task_id)
        participants[task.participant_id]["sources"].add(task.annotation_source)

    manifest = {
        "schema_version": 1,
        "dataset_digest_sha256": report_digest(result.tasks),
        "counts": {
            "archives": len(result.archives),
            "tasks": len(result.tasks),
            "participants": len(participants),
            "videos": sum(bool(task.media_name) for task in result.tasks),
            "frames": sum(task.frame_count for task in result.tasks),
            "event_tags": sum(task.tag_count for task in result.tasks),
            "standalone_shapes": sum(task.standalone_shape_count for task in result.tasks),
            "tracks": sum(task.track_count for task in result.tasks),
            "track_keyframes": sum(task.track_keyframe_count for task in result.tasks),
        },
        "issue_counts": dict(sorted(Counter(issue.severity for issue in result.issues).items())),
        "participants": [
            {
                "participant_id": participant_id,
                "views": sorted(data["views"]),
                "complete_three_view_set": data["views"] == {"T", "LS", "LL"},
                "tasks": sorted(data["tasks"]),
                "annotation_sources": sorted(data["sources"]),
            }
            for participant_id, data in sorted(
                participants.items(), key=lambda item: int(item[0][1:])
            )
        ],
    }
    with (output_root / "dataset_manifest.json").open("w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False)
        stream.write("\n")

    severity_counts = Counter(issue.severity for issue in result.issues)
    code_counts = Counter(issue.code for issue in result.issues)
    lines = [
        "# CVAT Backup Audit Summary",
        "",
        f"- Archives: {len(result.archives)}",
        f"- Tasks/videos: {len(result.tasks)}",
        f"- Participant sets: {len(participants)}",
        f"- Frames: {sum(task.frame_count for task in result.tasks):,}",
        f"- Event tags: {sum(task.tag_count for task in result.tasks):,}",
        f"- Tracks: {sum(task.track_count for task in result.tasks):,}",
        f"- Track keyframes: {sum(task.track_keyframe_count for task in result.tasks):,}",
        f"- Dataset digest: `{report_digest(result.tasks)}`",
        "",
        "## Issues by severity",
        "",
    ]
    for severity in ("error", "warning", "review", "info"):
        lines.append(f"- {severity}: {severity_counts.get(severity, 0)}")
    lines.extend(["", "## Issues by code", ""])
    for code, count in sorted(code_counts.items()):
        lines.append(f"- `{code}`: {count}")
    lines.extend(
        [
            "",
            "The original CVAT ZIP archives were read only and were not extracted or modified.",
            "",
        ]
    )
    (output_root / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.input.is_dir():
        print(f"Input folder does not exist: {args.input}", file=sys.stderr)
        return 1

    result = audit_backups(
        args.input,
        expected_participants=args.expected_participants,
        verify_crc=args.verify_crc,
    )
    write_reports(result, args.output)

    severity_counts = Counter(issue.severity for issue in result.issues)
    participant_count = len({task.participant_id for task in result.tasks if task.participant_id})
    print(f"Audited {len(result.archives)} archives.")
    print(f"Found {len(result.tasks)} tasks/videos in {participant_count} participant sets.")
    print(
        "Issues: "
        + ", ".join(
            f"{severity}={severity_counts.get(severity, 0)}"
            for severity in ("error", "warning", "review", "info")
        )
    )
    print(f"Reports written to: {args.output.resolve()}")

    if args.strict and severity_counts.get("error", 0):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
