#!/usr/bin/env python3
"""Build a sampled YOLO detection dataset from CVAT backup ZIPs.

The converter follows the Phase 3 video manifest, extracts one source video at
a time to a temporary folder, decodes it with FFmpeg, interpolates CVAT tracks,
and writes frame images plus normalized YOLO labels. Source backups are opened
read-only and are never modified.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import shutil
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator


CLASS_NAMES = (
    "paddle_sternal",
    "paddle_apical",
    "defibrillator_screen",
    "learner_hand",
    "sternal_placement_zone",
    "apical_placement_zone",
    "shock_symbol",
)
CLASS_TO_ID = {name: index for index, name in enumerate(CLASS_NAMES)}

EVENT_LABELS = (
    "Gel applied",
    "first_paddle_taken",
    "second_paddle_taken",
    "paddles_firmly_on_chest",
    "both_paddle_buttons_pressed",
    "shock_delivered_on_screen",
    "paddles_removed_after_shock",
)

SPLITS = ("train", "val", "test")


@dataclass(frozen=True)
class Box:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


@dataclass
class ConversionIssue:
    severity: str
    code: str
    split: str = ""
    canonical_task_id: str = ""
    label: str = ""
    frame: int | str = ""
    details: str = ""


@dataclass
class VideoConversionRecord:
    split: str
    participant_id: str
    canonical_task_id: str
    camera_view: str
    annotation_source: str
    archive: str
    media_name: str
    source_frame_count_cvat: int
    decoded_frame_count: int
    fps: float
    width: int
    height: int
    regular_sample_interval: int
    sampled_frames: int
    labelled_frames: int
    empty_frames: int
    boxes: int
    clipped_boxes: int
    skipped_boxes: int
    event_tags: int


@dataclass
class SampleRecord:
    split: str
    participant_id: str
    canonical_task_id: str
    camera_view: str
    source_frame: int
    timestamp_seconds: float
    image_path: str
    label_path: str
    object_count: int
    class_names: str
    sample_reasons: str


@dataclass
class Track:
    label: str
    shapes: list[dict[str, Any]]
    frames: list[int] = field(init=False)

    def __post_init__(self) -> None:
        self.shapes.sort(key=lambda shape: int(shape.get("frame", 0)))
        self.frames = [int(shape.get("frame", 0)) for shape in self.shapes]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert CVAT video backup tracks into a sampled YOLO dataset."
    )
    parser.add_argument(
        "--backup-root",
        type=Path,
        required=True,
        help="Folder containing the original CVAT backup ZIPs.",
    )
    parser.add_argument(
        "--split-manifest",
        type=Path,
        default=Path("splits/phase3/video_split_manifest.csv"),
        help="Phase 3 video-level split manifest.",
    )
    parser.add_argument(
        "--split-config",
        type=Path,
        default=Path("splits/phase3/split_config.json"),
        help="Phase 3 configuration containing the Phase 1 digest.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets/phase4_yolo"),
        help="Generated dataset folder. It must not already contain files.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("reports/phase4"),
        help="Non-image conversion report folder.",
    )
    parser.add_argument(
        "--sample-fps",
        type=float,
        default=5.0,
        help="Regular time-based sampling rate (default: 5 FPS).",
    )
    parser.add_argument(
        "--event-context-seconds",
        type=float,
        default=0.10,
        help="Include frames within this radius of each event tag.",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=85,
        help="JPEG quality from 1 to 95 (default: 85).",
    )
    parser.add_argument(
        "--include-test",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Generate locked test images automatically (default: true).",
    )
    parser.add_argument(
        "--only-task",
        action="append",
        default=[],
        metavar="PXX_VIEW",
        help="Convert only selected canonical task IDs for a smoke test.",
    )
    return parser.parse_args(argv)


def require_video_dependencies() -> tuple[Any, Any]:
    try:
        import imageio_ffmpeg
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Phase 4 requires imageio-ffmpeg and Pillow in the active environment."
        ) from exc
    return imageio_ffmpeg, Image


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_json_entry(archive: zipfile.ZipFile, name: str) -> Any:
    with archive.open(name) as stream:
        return json.load(stream)


def normalize_annotation_jobs(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def linear(start: float, end: float, ratio: float) -> float:
    return start + (end - start) * ratio


def interpolate_rotation(start: float, end: float, ratio: float) -> float:
    difference = (end - start + 180.0) % 360.0 - 180.0
    return start + difference * ratio


def rectangle_box(points: list[float], rotation: float = 0.0) -> Box | None:
    if len(points) != 4:
        return None
    x1, y1, x2, y2 = (float(value) for value in points)
    left, right = sorted((x1, x2))
    top, bottom = sorted((y1, y2))
    center_x = (left + right) / 2.0
    center_y = (top + bottom) / 2.0
    half_width = (right - left) / 2.0
    half_height = (bottom - top) / 2.0
    angle = math.radians(rotation)
    enclosing_half_width = abs(half_width * math.cos(angle)) + abs(
        half_height * math.sin(angle)
    )
    enclosing_half_height = abs(half_width * math.sin(angle)) + abs(
        half_height * math.cos(angle)
    )
    return Box(
        center_x - enclosing_half_width,
        center_y - enclosing_half_height,
        center_x + enclosing_half_width,
        center_y + enclosing_half_height,
    )


def points_box(points: list[float]) -> Box | None:
    if len(points) < 4 or len(points) % 2:
        return None
    x_values = [float(value) for value in points[0::2]]
    y_values = [float(value) for value in points[1::2]]
    return Box(min(x_values), min(y_values), max(x_values), max(y_values))


def shape_box(shape: dict[str, Any]) -> Box | None:
    points = shape.get("points") or []
    if shape.get("type") == "rectangle":
        return rectangle_box(points, float(shape.get("rotation", 0) or 0))
    return points_box(points)


def interpolate_box(left: Box, right: Box, ratio: float) -> Box:
    return Box(
        linear(left.x1, right.x1, ratio),
        linear(left.y1, right.y1, ratio),
        linear(left.x2, right.x2, ratio),
        linear(left.y2, right.y2, ratio),
    )


def interpolate_shapes(
    left: dict[str, Any], right: dict[str, Any], ratio: float
) -> Box | None:
    left_points = left.get("points") or []
    right_points = right.get("points") or []
    if left.get("type") == right.get("type") and len(left_points) == len(right_points):
        interpolated_points = [
            linear(float(start), float(end), ratio)
            for start, end in zip(left_points, right_points)
        ]
        if left.get("type") == "rectangle":
            rotation = interpolate_rotation(
                float(left.get("rotation", 0) or 0),
                float(right.get("rotation", 0) or 0),
                ratio,
            )
            return rectangle_box(interpolated_points, rotation)
        return points_box(interpolated_points)

    left_box = shape_box(left)
    right_box = shape_box(right)
    if left_box is None or right_box is None:
        return left_box or right_box
    return interpolate_box(left_box, right_box, ratio)


def track_box_at(track: Track, frame_number: int) -> Box | None:
    if not track.shapes:
        return None
    position = bisect.bisect_left(track.frames, frame_number)
    if position < len(track.frames) and track.frames[position] == frame_number:
        shape = track.shapes[position]
        if bool(shape.get("outside", False)):
            return None
        return shape_box(shape)

    if position == 0:
        return None
    left = track.shapes[position - 1]
    if bool(left.get("outside", False)):
        return None
    if position >= len(track.shapes):
        return shape_box(left)

    right = track.shapes[position]
    left_frame = int(left.get("frame", 0))
    right_frame = int(right.get("frame", left_frame))
    if right_frame <= left_frame:
        return shape_box(left)
    ratio = (frame_number - left_frame) / (right_frame - left_frame)
    return interpolate_shapes(left, right, ratio)


def clip_box(box: Box, width: int, height: int) -> tuple[Box | None, bool]:
    clipped = Box(
        max(0.0, min(float(width), box.x1)),
        max(0.0, min(float(height), box.y1)),
        max(0.0, min(float(width), box.x2)),
        max(0.0, min(float(height), box.y2)),
    )
    was_clipped = clipped != box
    if clipped.width < 1.0 or clipped.height < 1.0:
        return None, was_clipped
    return clipped, was_clipped


def yolo_line(class_id: int, box: Box, width: int, height: int) -> str:
    center_x = ((box.x1 + box.x2) / 2.0) / width
    center_y = ((box.y1 + box.y2) / 2.0) / height
    normalized_width = box.width / width
    normalized_height = box.height / height
    return (
        f"{class_id} {center_x:.8f} {center_y:.8f} "
        f"{normalized_width:.8f} {normalized_height:.8f}"
    )


def task_entry_prefix(task_path: str) -> str:
    return "" if task_path in {"", "."} else f"{task_path.rstrip('/')}/"


def locate_media_entry(
    archive: zipfile.ZipFile, prefix: str, expected_name: str
) -> zipfile.ZipInfo:
    exact_name = f"{prefix}data/{expected_name}"
    try:
        return archive.getinfo(exact_name)
    except KeyError:
        candidates = [
            entry
            for entry in archive.infolist()
            if entry.filename.startswith(f"{prefix}data/")
            and PurePosixPath(entry.filename).name.lower() == expected_name.lower()
        ]
        if len(candidates) != 1:
            raise KeyError(
                f"Expected one media entry for {expected_name!r}; found {len(candidates)}"
            )
        return candidates[0]


def load_cvat_task(
    archive: zipfile.ZipFile, task_path: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    prefix = task_entry_prefix(task_path)
    task = read_json_entry(archive, f"{prefix}task.json")
    annotations = normalize_annotation_jobs(
        read_json_entry(archive, f"{prefix}annotations.json")
    )
    return task, annotations


def collect_annotations(
    annotation_jobs: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[Track]]:
    tags: list[dict[str, Any]] = []
    standalone_shapes: list[dict[str, Any]] = []
    tracks: list[Track] = []
    for job in annotation_jobs:
        tags.extend(job.get("tags") or [])
        standalone_shapes.extend(job.get("shapes") or [])
        tracks.extend(
            Track(str(track.get("label", "")), list(track.get("shapes") or []))
            for track in job.get("tracks") or []
        )
    return tags, standalone_shapes, tracks


def build_sample_reasons(
    *,
    start_frame: int,
    stop_frame: int,
    fps: float,
    sample_fps: float,
    event_context_seconds: float,
    tags: Iterable[dict[str, Any]],
    standalone_shapes: Iterable[dict[str, Any]],
    tracks: Iterable[Track],
) -> tuple[dict[int, set[str]], int]:
    interval = max(1, round(fps / sample_fps))
    reasons: dict[int, set[str]] = defaultdict(set)
    for frame in range(start_frame, stop_frame + 1, interval):
        reasons[frame].add("regular")
    reasons[stop_frame].add("last_frame")

    context = max(0, round(fps * event_context_seconds))
    for tag in tags:
        frame = int(tag.get("frame", -1))
        if not start_frame <= frame <= stop_frame:
            continue
        label = str(tag.get("label", ""))
        if label in EVENT_LABELS:
            for context_frame in range(
                max(start_frame, frame - context),
                min(stop_frame, frame + context) + 1,
            ):
                reasons[context_frame].add(
                    "event" if context_frame == frame else "event_context"
                )
        elif label in CLASS_TO_ID:
            reasons[frame].add("mistyped_object_tag")

    for shape in standalone_shapes:
        frame = int(shape.get("frame", -1))
        if start_frame <= frame <= stop_frame:
            reasons[frame].add("standalone_shape")

    for track in tracks:
        if not track.shapes:
            continue
        visible_frames = [
            int(shape.get("frame", 0))
            for shape in track.shapes
            if not bool(shape.get("outside", False))
        ]
        if visible_frames:
            reasons[min(visible_frames)].add("track_boundary")
            reasons[max(visible_frames)].add("track_boundary")
        if track.label == "shock_symbol":
            for shape in track.shapes:
                frame = int(shape.get("frame", -1))
                if start_frame <= frame <= stop_frame:
                    reasons[frame].add("shock_keyframe")
    return dict(reasons), interval


def frame_boxes(
    frame_number: int,
    tracks: Iterable[Track],
    standalone_shapes_by_frame: dict[int, list[dict[str, Any]]],
    width: int,
    height: int,
) -> tuple[list[tuple[str, Box]], int, int]:
    boxes: list[tuple[str, Box]] = []
    clipped_count = 0
    skipped_count = 0
    for track in tracks:
        if track.label not in CLASS_TO_ID:
            continue
        box = track_box_at(track, frame_number)
        if box is None:
            continue
        clipped_box, was_clipped = clip_box(box, width, height)
        clipped_count += int(was_clipped)
        if clipped_box is None:
            skipped_count += 1
            continue
        boxes.append((track.label, clipped_box))

    for shape in standalone_shapes_by_frame.get(frame_number, []):
        label = str(shape.get("label", ""))
        if label not in CLASS_TO_ID:
            continue
        box = shape_box(shape)
        if box is None:
            skipped_count += 1
            continue
        clipped_box, was_clipped = clip_box(box, width, height)
        clipped_count += int(was_clipped)
        if clipped_box is None:
            skipped_count += 1
            continue
        boxes.append((label, clipped_box))
    return boxes, clipped_count, skipped_count


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


class DatasetBuilder:
    def __init__(
        self,
        *,
        backup_root: Path,
        split_manifest: Path,
        split_config: Path,
        output_root: Path,
        report_root: Path,
        sample_fps: float,
        event_context_seconds: float,
        jpeg_quality: int,
        include_test: bool,
        only_task_ids: Iterable[str] = (),
    ) -> None:
        self.backup_root = backup_root.resolve()
        self.split_manifest = split_manifest
        self.split_config = split_config
        self.output_root = output_root.resolve()
        self.report_root = report_root.resolve()
        self.sample_fps = sample_fps
        self.event_context_seconds = event_context_seconds
        self.jpeg_quality = jpeg_quality
        self.include_test = include_test
        self.only_task_ids = set(only_task_ids)
        self.issues: list[ConversionIssue] = []
        self.video_records: list[VideoConversionRecord] = []
        self.sample_records: list[SampleRecord] = []
        self.class_counts: Counter[tuple[str, str]] = Counter()
        self.events: list[dict[str, Any]] = []
        self.imageio_ffmpeg, self.Image = require_video_dependencies()

    def prepare_output(self) -> None:
        if self.output_root.exists() and any(self.output_root.iterdir()):
            raise ValueError(
                f"Output folder is not empty: {self.output_root}. "
                "Use a new versioned output path."
            )
        self.output_root.mkdir(parents=True, exist_ok=True)
        for split in SPLITS:
            if split == "test" and not self.include_test:
                continue
            (self.output_root / "images" / split).mkdir(parents=True, exist_ok=True)
            (self.output_root / "labels" / split).mkdir(parents=True, exist_ok=True)
        (self.output_root / "metadata").mkdir(parents=True, exist_ok=True)

    def add_issue(
        self,
        severity: str,
        code: str,
        row: dict[str, str],
        *,
        label: str = "",
        frame: int | str = "",
        details: str = "",
    ) -> None:
        self.issues.append(
            ConversionIssue(
                severity=severity,
                code=code,
                split=row.get("split", ""),
                canonical_task_id=row.get("canonical_task_id", ""),
                label=label,
                frame=frame,
                details=details,
            )
        )

    def build(self) -> None:
        rows = read_csv(self.split_manifest)
        selected_rows = [
            row
            for row in rows
            if (self.include_test or row["split"] != "test")
            and (
                not self.only_task_ids
                or row["canonical_task_id"] in self.only_task_ids
            )
        ]
        if self.only_task_ids:
            found = {row["canonical_task_id"] for row in selected_rows}
            missing = sorted(self.only_task_ids - found)
            if missing:
                raise ValueError(f"Requested task IDs are not in the manifest: {missing}")
            expected_rows = len(self.only_task_ids)
        else:
            expected_rows = 144 if self.include_test else 117
        if len(selected_rows) != expected_rows:
            raise ValueError(
                f"Expected {expected_rows} manifest videos, found {len(selected_rows)}."
            )

        split_config = json.loads(self.split_config.read_text(encoding="utf-8"))
        phase1_digest = split_config["phase1_dataset_digest_sha256"]
        config_hash = sha256_file(self.split_config)

        by_archive: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in selected_rows:
            by_archive[row["archive"]].append(row)

        completed = 0
        total = len(selected_rows)
        for relative_archive in sorted(by_archive, key=str.lower):
            archive_path = self.backup_root / Path(relative_archive)
            if not archive_path.is_file():
                raise FileNotFoundError(f"Backup archive not found: {archive_path}")
            with zipfile.ZipFile(archive_path) as archive:
                for row in sorted(
                    by_archive[relative_archive],
                    key=lambda item: item["canonical_task_id"],
                ):
                    self.convert_video(archive, row)
                    completed += 1
                    print(
                        f"[{completed:03d}/{total:03d}] "
                        f"{row['split']:<5} {row['canonical_task_id']}",
                        flush=True,
                    )

        self.write_dataset_files(phase1_digest, config_hash)

    def convert_video(
        self, archive: zipfile.ZipFile, row: dict[str, str]
    ) -> None:
        task, annotation_jobs = load_cvat_task(archive, row["task_path"])
        tags, standalone_shapes, tracks = collect_annotations(annotation_jobs)
        prefix = task_entry_prefix(row["task_path"])
        media_entry = locate_media_entry(archive, prefix, row["media_name"])
        data = task.get("data") or {}
        start_frame = int(data.get("start_frame", 0) or 0)
        stop_frame = int(data.get("stop_frame", -1) or -1)
        cvat_frame_count = max(0, stop_frame - start_frame + 1)

        for tag in tags:
            label = str(tag.get("label", ""))
            if label in CLASS_TO_ID:
                self.add_issue(
                    "warning",
                    "object_tag_excluded_no_geometry",
                    row,
                    label=label,
                    frame=tag.get("frame", ""),
                )

        with tempfile.TemporaryDirectory(prefix="defib_phase4_") as temporary:
            temporary_video = Path(temporary) / row["media_name"]
            with archive.open(media_entry) as source, temporary_video.open("wb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)

            reader = self.imageio_ffmpeg.read_frames(
                str(temporary_video), pix_fmt="rgb24"
            )
            metadata = next(reader)
            fps = float(metadata.get("fps") or 0)
            width, height = (int(value) for value in metadata["size"])
            if fps <= 0 or width <= 0 or height <= 0:
                reader.close()
                raise ValueError(
                    f"Invalid video metadata for {row['canonical_task_id']}: {metadata}"
                )

            reasons, interval = build_sample_reasons(
                start_frame=start_frame,
                stop_frame=stop_frame,
                fps=fps,
                sample_fps=self.sample_fps,
                event_context_seconds=self.event_context_seconds,
                tags=tags,
                standalone_shapes=standalone_shapes,
                tracks=tracks,
            )
            sampled_frames = set(reasons)
            standalone_by_frame: dict[int, list[dict[str, Any]]] = defaultdict(list)
            for shape in standalone_shapes:
                standalone_by_frame[int(shape.get("frame", -1))].append(shape)

            labelled_frames = 0
            box_total = 0
            clipped_total = 0
            skipped_total = 0
            decoded_count = 0
            saved_count = 0
            try:
                for frame_number, frame_bytes in enumerate(reader):
                    if frame_number > stop_frame:
                        break
                    decoded_count = frame_number + 1
                    if frame_number not in sampled_frames:
                        continue
                    image_name = (
                        f"{row['canonical_task_id']}_f{frame_number:06d}.jpg"
                    )
                    label_name = (
                        f"{row['canonical_task_id']}_f{frame_number:06d}.txt"
                    )
                    image_relative = Path("images") / row["split"] / image_name
                    label_relative = Path("labels") / row["split"] / label_name
                    image_path = self.output_root / image_relative
                    label_path = self.output_root / label_relative

                    boxes, clipped_count, skipped_count = frame_boxes(
                        frame_number,
                        tracks,
                        standalone_by_frame,
                        width,
                        height,
                    )
                    lines = [
                        yolo_line(CLASS_TO_ID[label], box, width, height)
                        for label, box in boxes
                    ]
                    label_path.write_text(
                        "\n".join(lines) + ("\n" if lines else ""),
                        encoding="utf-8",
                    )
                    image = self.Image.frombytes(
                        "RGB", (width, height), frame_bytes
                    )
                    image.save(
                        image_path,
                        format="JPEG",
                        quality=self.jpeg_quality,
                        optimize=False,
                    )

                    class_names = sorted({label for label, _ in boxes})
                    self.sample_records.append(
                        SampleRecord(
                            split=row["split"],
                            participant_id=row["participant_id"],
                            canonical_task_id=row["canonical_task_id"],
                            camera_view=row["camera_view"],
                            source_frame=frame_number,
                            timestamp_seconds=frame_number / fps,
                            image_path=image_relative.as_posix(),
                            label_path=label_relative.as_posix(),
                            object_count=len(boxes),
                            class_names=";".join(class_names),
                            sample_reasons=";".join(sorted(reasons[frame_number])),
                        )
                    )
                    for label, _ in boxes:
                        self.class_counts[(row["split"], label)] += 1
                    saved_count += 1
                    labelled_frames += int(bool(boxes))
                    box_total += len(boxes)
                    clipped_total += clipped_count
                    skipped_total += skipped_count
            finally:
                reader.close()

        if saved_count != len(sampled_frames):
            missing = sorted(sampled_frames - {
                sample.source_frame
                for sample in self.sample_records
                if sample.canonical_task_id == row["canonical_task_id"]
            })
            self.add_issue(
                "error",
                "sample_frames_not_decoded",
                row,
                details=f"missing_count={len(missing)}; first={missing[:10]}",
            )
        if abs(decoded_count - cvat_frame_count) > 1:
            self.add_issue(
                "warning",
                "decoded_frame_count_mismatch",
                row,
                details=f"cvat={cvat_frame_count}; decoded={decoded_count}",
            )
        if skipped_total:
            self.add_issue(
                "review",
                "degenerate_boxes_skipped",
                row,
                details=f"count={skipped_total}",
            )

        event_items = [
            {
                "label": str(tag.get("label", "")),
                "frame": int(tag.get("frame", 0)),
                "timestamp_seconds": int(tag.get("frame", 0)) / fps,
            }
            for tag in tags
            if str(tag.get("label", "")) in EVENT_LABELS
        ]
        self.events.append(
            {
                "split": row["split"],
                "participant_id": row["participant_id"],
                "canonical_task_id": row["canonical_task_id"],
                "camera_view": row["camera_view"],
                "fps": fps,
                "events": event_items,
            }
        )
        self.video_records.append(
            VideoConversionRecord(
                split=row["split"],
                participant_id=row["participant_id"],
                canonical_task_id=row["canonical_task_id"],
                camera_view=row["camera_view"],
                annotation_source=row["annotation_source"],
                archive=row["archive"],
                media_name=row["media_name"],
                source_frame_count_cvat=cvat_frame_count,
                decoded_frame_count=decoded_count,
                fps=fps,
                width=width,
                height=height,
                regular_sample_interval=interval,
                sampled_frames=saved_count,
                labelled_frames=labelled_frames,
                empty_frames=saved_count - labelled_frames,
                boxes=box_total,
                clipped_boxes=clipped_total,
                skipped_boxes=skipped_total,
                event_tags=len(event_items),
            )
        )

    def write_dataset_files(self, phase1_digest: str, config_hash: str) -> None:
        yaml_lines = [
            "path: .",
            "train: images/train",
            "val: images/val",
        ]
        if self.include_test:
            yaml_lines.append("test: images/test")
        yaml_lines.extend(["names:"] + [
            f"  {index}: {name}" for index, name in enumerate(CLASS_NAMES)
        ])
        (self.output_root / "dataset.yaml").write_text(
            "\n".join(yaml_lines) + "\n", encoding="utf-8"
        )

        with (self.output_root / "metadata" / "events.jsonl").open(
            "w", encoding="utf-8"
        ) as stream:
            for item in sorted(
                self.events,
                key=lambda value: (
                    SPLITS.index(value["split"]),
                    value["canonical_task_id"],
                ),
            ):
                stream.write(json.dumps(item, ensure_ascii=False) + "\n")

        sample_fields = [item.name for item in fields(SampleRecord)]
        write_csv(
            self.output_root / "metadata" / "sample_manifest.csv",
            [asdict(item) for item in self.sample_records],
            sample_fields,
        )

        video_fields = [item.name for item in fields(VideoConversionRecord)]
        write_csv(
            self.report_root / "video_conversion.csv",
            [asdict(item) for item in self.video_records],
            video_fields,
        )
        issue_fields = [item.name for item in fields(ConversionIssue)]
        write_csv(
            self.report_root / "conversion_issues.csv",
            [asdict(item) for item in self.issues],
            issue_fields,
        )

        class_rows = []
        for split in SPLITS:
            if split == "test" and not self.include_test:
                continue
            for class_id, name in enumerate(CLASS_NAMES):
                class_rows.append(
                    {
                        "split": split,
                        "class_id": class_id,
                        "class_name": name,
                        "boxes": self.class_counts[(split, name)],
                    }
                )
        write_csv(
            self.report_root / "class_distribution.csv",
            class_rows,
            ["split", "class_id", "class_name", "boxes"],
        )

        split_rows = []
        for split in SPLITS:
            selected_videos = [
                record for record in self.video_records if record.split == split
            ]
            selected_samples = [
                record for record in self.sample_records if record.split == split
            ]
            if not selected_videos:
                continue
            split_rows.append(
                {
                    "split": split,
                    "participant_sets": len(
                        {record.participant_id for record in selected_videos}
                    ),
                    "videos": len(selected_videos),
                    "sampled_images": len(selected_samples),
                    "labelled_images": sum(
                        record.object_count > 0 for record in selected_samples
                    ),
                    "empty_images": sum(
                        record.object_count == 0 for record in selected_samples
                    ),
                    "boxes": sum(record.object_count for record in selected_samples),
                    "event_tags": sum(record.event_tags for record in selected_videos),
                }
            )
        write_csv(
            self.report_root / "split_summary.csv",
            split_rows,
            [
                "split",
                "participant_sets",
                "videos",
                "sampled_images",
                "labelled_images",
                "empty_images",
                "boxes",
                "event_tags",
            ],
        )

        manifest = {
            "schema_version": 1,
            "phase1_dataset_digest_sha256": phase1_digest,
            "phase3_split_config_sha256": config_hash,
            "sampling": {
                "sample_fps": self.sample_fps,
                "event_context_seconds": self.event_context_seconds,
                "jpeg_quality": self.jpeg_quality,
                "include_test": self.include_test,
                "only_task_ids": sorted(self.only_task_ids),
                "always_include": [
                    "event frames and context",
                    "standalone-shape frames",
                    "track boundaries",
                    "shock_symbol keyframes",
                ],
            },
            "classes": {
                str(index): name for index, name in enumerate(CLASS_NAMES)
            },
            "counts": {
                "videos": len(self.video_records),
                "images": len(self.sample_records),
                "boxes": sum(record.object_count for record in self.sample_records),
                "events": sum(record.event_tags for record in self.video_records),
                "issues": dict(
                    sorted(Counter(issue.severity for issue in self.issues).items())
                ),
            },
        }
        (self.report_root / "dataset_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        summary_by_split = {row["split"]: row for row in split_rows}
        lines = [
            "# Phase 4 YOLO Dataset Build",
            "",
            "| Split | Sets | Videos | Images | Labelled | Empty | Boxes |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for split in SPLITS:
            if split not in summary_by_split:
                continue
            row = summary_by_split[split]
            lines.append(
                f"| {split} | {row['participant_sets']} | {row['videos']} | "
                f"{row['sampled_images']:,} | {row['labelled_images']:,} | "
                f"{row['empty_images']:,} | {row['boxes']:,} |"
            )
        issue_counts = Counter(issue.severity for issue in self.issues)
        lines.extend(
            [
                "",
                f"- Conversion errors: {issue_counts['error']}",
                f"- Conversion warnings: {issue_counts['warning']}",
                f"- Manual-review findings: {issue_counts['review']}",
                f"- Phase 1 digest: `{phase1_digest}`",
                f"- Phase 3 config SHA-256: `{config_hash}`",
                "",
                "Images and YOLO labels are generated under the ignored `datasets/` folder.",
                "The source CVAT ZIP archives were opened read-only and were not modified.",
                "",
            ]
        )
        (self.report_root / "README.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )


def validate_arguments(args: argparse.Namespace) -> None:
    if not args.backup_root.is_dir():
        raise ValueError(f"Backup root does not exist: {args.backup_root}")
    if not args.split_manifest.is_file():
        raise ValueError(f"Split manifest does not exist: {args.split_manifest}")
    if not args.split_config.is_file():
        raise ValueError(f"Split config does not exist: {args.split_config}")
    if args.sample_fps <= 0:
        raise ValueError("sample-fps must be positive.")
    if args.event_context_seconds < 0:
        raise ValueError("event-context-seconds cannot be negative.")
    if not 1 <= args.jpeg_quality <= 95:
        raise ValueError("jpeg-quality must be between 1 and 95.")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        validate_arguments(args)
        builder = DatasetBuilder(
            backup_root=args.backup_root,
            split_manifest=args.split_manifest,
            split_config=args.split_config,
            output_root=args.output,
            report_root=args.report_output,
            sample_fps=args.sample_fps,
            event_context_seconds=args.event_context_seconds,
            jpeg_quality=args.jpeg_quality,
            include_test=args.include_test,
            only_task_ids=args.only_task,
        )
        builder.prepare_output()
        builder.build()
    except (
        FileNotFoundError,
        KeyError,
        RuntimeError,
        ValueError,
        zipfile.BadZipFile,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors = sum(issue.severity == "error" for issue in builder.issues)
    print(
        f"Generated {len(builder.sample_records):,} images with "
        f"{sum(record.object_count for record in builder.sample_records):,} boxes."
    )
    print(f"Conversion error findings: {errors}")
    print(f"Dataset: {builder.output_root}")
    print(f"Reports: {builder.report_root}")
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
