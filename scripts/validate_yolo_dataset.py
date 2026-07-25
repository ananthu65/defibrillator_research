#!/usr/bin/env python3
"""Validate a YOLO dataset against its frozen grouped video split."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SPLITS = ("train", "val", "test")


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    details: str


@dataclass(frozen=True)
class LabelBox:
    class_id: int
    center_x: float
    center_y: float
    width: float
    height: float


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Phase 4 image/label integrity and split isolation."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("datasets/phase4_yolo"),
        help="Generated YOLO dataset root.",
    )
    parser.add_argument(
        "--split-manifest",
        type=Path,
        default=Path("splits/phase3/video_split_manifest.csv"),
        help="Frozen Phase 3 video split manifest.",
    )
    parser.add_argument(
        "--class-report",
        type=Path,
        default=Path("reports/phase4/class_distribution.csv"),
        help="Phase 4 class-distribution report to cross-check.",
    )
    parser.add_argument(
        "--split-report",
        type=Path,
        default=Path("reports/phase4/split_summary.csv"),
        help="Phase 4 split-summary report to cross-check.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/phase4/validation.json"),
        help="Machine-readable validation report.",
    )
    parser.add_argument(
        "--verify-images",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Decode-check every JPEG with Pillow (default: true).",
    )
    return parser.parse_args(argv)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def parse_dataset_classes(dataset_yaml: Path) -> dict[int, str]:
    classes: dict[int, str] = {}
    in_names = False
    for raw_line in dataset_yaml.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if stripped == "names:":
            in_names = True
            continue
        if not in_names or not raw_line.startswith("  "):
            continue
        class_text, separator, name = stripped.partition(":")
        if separator and class_text.isdigit() and name.strip():
            classes[int(class_text)] = name.strip()
    if not classes:
        raise ValueError(f"No class mapping found in {dataset_yaml}")
    if sorted(classes) != list(range(len(classes))):
        raise ValueError("Dataset class IDs must be contiguous and start at zero.")
    return classes


def parse_label_line(
    line: str, *, class_count: int, location: str = "label"
) -> LabelBox:
    parts = line.split()
    if len(parts) != 5:
        raise ValueError(f"{location}: expected 5 fields, found {len(parts)}")
    try:
        class_id = int(parts[0])
        values = [float(value) for value in parts[1:]]
    except ValueError as exc:
        raise ValueError(f"{location}: non-numeric YOLO field") from exc
    if not 0 <= class_id < class_count:
        raise ValueError(f"{location}: invalid class ID {class_id}")
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f"{location}: non-finite coordinate")

    center_x, center_y, width, height = values
    if not 0.0 <= center_x <= 1.0 or not 0.0 <= center_y <= 1.0:
        raise ValueError(f"{location}: center is outside [0, 1]")
    if not 0.0 < width <= 1.0 or not 0.0 < height <= 1.0:
        raise ValueError(f"{location}: width/height must be in (0, 1]")

    epsilon = 1e-6
    if (
        center_x - width / 2 < -epsilon
        or center_x + width / 2 > 1 + epsilon
        or center_y - height / 2 < -epsilon
        or center_y + height / 2 > 1 + epsilon
    ):
        raise ValueError(f"{location}: box extends outside normalized image bounds")
    return LabelBox(class_id, center_x, center_y, width, height)


def safe_dataset_path(dataset_root: Path, relative: str) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"Unsafe dataset-relative path: {relative}")
    resolved = (dataset_root / relative_path).resolve()
    try:
        resolved.relative_to(dataset_root)
    except ValueError as exc:
        raise ValueError(f"Path escapes dataset root: {relative}") from exc
    return resolved


def add_finding(
    findings: list[Finding], severity: str, code: str, details: str
) -> None:
    findings.append(Finding(severity, code, details))


def read_report_counts(
    class_report: Path, split_report: Path
) -> tuple[Counter[tuple[str, int]], dict[str, dict[str, int]]]:
    class_counts: Counter[tuple[str, int]] = Counter()
    for row in read_csv(class_report):
        class_counts[(row["split"], int(row["class_id"]))] = int(row["boxes"])

    split_counts: dict[str, dict[str, int]] = {}
    numeric_fields = (
        "participant_sets",
        "videos",
        "sampled_images",
        "labelled_images",
        "empty_images",
        "boxes",
        "event_tags",
    )
    for row in read_csv(split_report):
        split_counts[row["split"]] = {
            field: int(row[field]) for field in numeric_fields
        }
    return class_counts, split_counts


def validate(args: argparse.Namespace) -> dict[str, object]:
    dataset_root = args.dataset.resolve()
    manifest_path = dataset_root / "metadata" / "sample_manifest.csv"
    events_path = dataset_root / "metadata" / "events.jsonl"
    required = (
        dataset_root / "dataset.yaml",
        manifest_path,
        events_path,
        args.split_manifest,
        args.class_report,
        args.split_report,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing validation inputs: {missing}")

    classes = parse_dataset_classes(dataset_root / "dataset.yaml")
    class_count = len(classes)
    frozen_rows = read_csv(args.split_manifest)
    expected_task_split = {
        row["canonical_task_id"]: row["split"] for row in frozen_rows
    }
    expected_participant_split = {
        row["participant_id"]: row["split"] for row in frozen_rows
    }
    expected_tasks_by_split = Counter(row["split"] for row in frozen_rows)
    expected_participants_by_split = {
        split: {
            row["participant_id"] for row in frozen_rows if row["split"] == split
        }
        for split in SPLITS
    }

    findings: list[Finding] = []
    rows = read_csv(manifest_path)
    seen_images: set[str] = set()
    seen_labels: set[str] = set()
    seen_samples: set[tuple[str, int]] = set()
    observed_tasks_by_split: dict[str, set[str]] = defaultdict(set)
    observed_participants_by_split: dict[str, set[str]] = defaultdict(set)
    image_counts: Counter[str] = Counter()
    labelled_counts: Counter[str] = Counter()
    box_counts: Counter[str] = Counter()
    class_counts: Counter[tuple[str, int]] = Counter()
    corrupt_images = 0

    Image = None
    if args.verify_images:
        try:
            from PIL import Image as PillowImage
        except ImportError as exc:
            raise RuntimeError(
                "Pillow is required when --verify-images is enabled."
            ) from exc
        Image = PillowImage

    for row_number, row in enumerate(rows, start=2):
        split = row.get("split", "")
        participant = row.get("participant_id", "")
        task_id = row.get("canonical_task_id", "")
        location = f"sample_manifest.csv:{row_number}"
        if split not in SPLITS:
            add_finding(findings, "error", "invalid_split", f"{location}: {split!r}")
            continue
        if expected_task_split.get(task_id) != split:
            add_finding(
                findings,
                "error",
                "task_split_mismatch",
                f"{location}: {task_id} is {split}, expected {expected_task_split.get(task_id)}",
            )
        if expected_participant_split.get(participant) != split:
            add_finding(
                findings,
                "error",
                "participant_split_mismatch",
                f"{location}: {participant} is {split}",
            )

        try:
            source_frame = int(row["source_frame"])
            expected_objects = int(row["object_count"])
            image_path = safe_dataset_path(dataset_root, row["image_path"])
            label_path = safe_dataset_path(dataset_root, row["label_path"])
        except (KeyError, ValueError) as exc:
            add_finding(findings, "error", "invalid_manifest_row", f"{location}: {exc}")
            continue

        if row["image_path"] in seen_images or row["label_path"] in seen_labels:
            add_finding(
                findings, "error", "duplicate_path", f"{location}: {row['image_path']}"
            )
        if (task_id, source_frame) in seen_samples:
            add_finding(
                findings,
                "error",
                "duplicate_source_frame",
                f"{location}: {task_id} frame {source_frame}",
            )
        seen_images.add(row["image_path"])
        seen_labels.add(row["label_path"])
        seen_samples.add((task_id, source_frame))

        expected_image_parent = Path("images") / split
        expected_label_parent = Path("labels") / split
        if Path(row["image_path"]).parent != expected_image_parent:
            add_finding(
                findings,
                "error",
                "image_path_split_mismatch",
                f"{location}: {row['image_path']}",
            )
        if Path(row["label_path"]).parent != expected_label_parent:
            add_finding(
                findings,
                "error",
                "label_path_split_mismatch",
                f"{location}: {row['label_path']}",
            )
        if image_path.stem != label_path.stem:
            add_finding(
                findings,
                "error",
                "image_label_stem_mismatch",
                f"{location}: {image_path.name} vs {label_path.name}",
            )
        if not image_path.is_file() or not label_path.is_file():
            add_finding(
                findings,
                "error",
                "sample_file_missing",
                f"{location}: image={image_path.is_file()}, label={label_path.is_file()}",
            )
            continue

        parsed_boxes: list[LabelBox] = []
        for label_line_number, line in enumerate(
            label_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                parsed_boxes.append(
                    parse_label_line(
                        line,
                        class_count=class_count,
                        location=f"{label_path.name}:{label_line_number}",
                    )
                )
            except ValueError as exc:
                add_finding(findings, "error", "invalid_yolo_label", str(exc))

        if len(parsed_boxes) != expected_objects:
            add_finding(
                findings,
                "error",
                "object_count_mismatch",
                f"{location}: manifest={expected_objects}, label={len(parsed_boxes)}",
            )
        expected_names = {
            classes[box.class_id] for box in parsed_boxes if box.class_id in classes
        }
        manifest_names = {
            name for name in row.get("class_names", "").split(";") if name
        }
        if expected_names != manifest_names:
            add_finding(
                findings,
                "error",
                "class_names_mismatch",
                f"{location}: manifest={sorted(manifest_names)}, label={sorted(expected_names)}",
            )
        if not row.get("sample_reasons", ""):
            add_finding(
                findings, "error", "missing_sample_reason", location
            )

        if Image is not None:
            try:
                with Image.open(image_path) as image:
                    if image.format != "JPEG" or image.width <= 0 or image.height <= 0:
                        raise ValueError(
                            f"format={image.format}, size={image.size}"
                        )
                    image.verify()
            except Exception as exc:  # Pillow exposes several decoder exceptions.
                corrupt_images += 1
                add_finding(
                    findings,
                    "error",
                    "invalid_image",
                    f"{image_path.name}: {exc}",
                )

        image_counts[split] += 1
        labelled_counts[split] += bool(parsed_boxes)
        box_counts[split] += len(parsed_boxes)
        for box in parsed_boxes:
            class_counts[(split, box.class_id)] += 1
        observed_tasks_by_split[split].add(task_id)
        observed_participants_by_split[split].add(participant)

    actual_images = {
        path.relative_to(dataset_root).as_posix()
        for split in SPLITS
        for path in (dataset_root / "images" / split).glob("*.jpg")
    }
    actual_labels = {
        path.relative_to(dataset_root).as_posix()
        for split in SPLITS
        for path in (dataset_root / "labels" / split).glob("*.txt")
    }
    for code, manifest_set, actual_set in (
        ("image_file_set_mismatch", seen_images, actual_images),
        ("label_file_set_mismatch", seen_labels, actual_labels),
    ):
        if manifest_set != actual_set:
            add_finding(
                findings,
                "error",
                code,
                f"missing={len(manifest_set - actual_set)}, extra={len(actual_set - manifest_set)}",
            )

    for split in SPLITS:
        expected_tasks = {
            task for task, task_split in expected_task_split.items() if task_split == split
        }
        if observed_tasks_by_split[split] != expected_tasks:
            add_finding(
                findings,
                "error",
                "task_coverage_mismatch",
                f"{split}: expected={len(expected_tasks)}, observed={len(observed_tasks_by_split[split])}",
            )
        if observed_participants_by_split[split] != expected_participants_by_split[split]:
            add_finding(
                findings,
                "error",
                "participant_coverage_mismatch",
                f"{split}: expected={len(expected_participants_by_split[split])}, "
                f"observed={len(observed_participants_by_split[split])}",
            )
        missing_classes = [
            classes[class_id]
            for class_id in classes
            if class_counts[(split, class_id)] == 0
        ]
        if missing_classes:
            add_finding(
                findings,
                "error",
                "class_missing_from_split",
                f"{split}: {missing_classes}",
            )

    for left_index, left in enumerate(SPLITS):
        for right in SPLITS[left_index + 1 :]:
            overlap = observed_participants_by_split[left] & observed_participants_by_split[right]
            if overlap:
                add_finding(
                    findings,
                    "error",
                    "participant_leakage",
                    f"{left}/{right}: {sorted(overlap)}",
                )

    event_rows: list[dict[str, object]] = []
    with events_path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                add_finding(
                    findings,
                    "error",
                    "invalid_event_json",
                    f"events.jsonl:{line_number}: {exc}",
                )
                continue
            event_rows.append(item)
            task_id = str(item.get("canonical_task_id", ""))
            if expected_task_split.get(task_id) != item.get("split"):
                add_finding(
                    findings,
                    "error",
                    "event_split_mismatch",
                    f"events.jsonl:{line_number}: {task_id}",
                )
    event_task_ids = [str(item.get("canonical_task_id", "")) for item in event_rows]
    if len(event_task_ids) != len(set(event_task_ids)):
        add_finding(findings, "error", "duplicate_event_task", "events.jsonl")
    if set(event_task_ids) != set(expected_task_split):
        add_finding(
            findings,
            "error",
            "event_task_coverage_mismatch",
            f"expected={len(expected_task_split)}, observed={len(set(event_task_ids))}",
        )

    reported_classes, reported_splits = read_report_counts(
        args.class_report, args.split_report
    )
    if class_counts != reported_classes:
        add_finding(
            findings,
            "error",
            "class_report_mismatch",
            f"observed={sum(class_counts.values())}, reported={sum(reported_classes.values())}",
        )
    for split in SPLITS:
        observed = {
            "participant_sets": len(observed_participants_by_split[split]),
            "videos": len(observed_tasks_by_split[split]),
            "sampled_images": image_counts[split],
            "labelled_images": labelled_counts[split],
            "empty_images": image_counts[split] - labelled_counts[split],
            "boxes": box_counts[split],
            "event_tags": sum(
                len(item.get("events", []))
                for item in event_rows
                if item.get("split") == split
            ),
        }
        if reported_splits.get(split) != observed:
            add_finding(
                findings,
                "error",
                "split_report_mismatch",
                f"{split}: observed={observed}, reported={reported_splits.get(split)}",
            )

    severity_counts = Counter(item.severity for item in findings)
    return {
        "schema_version": 1,
        "status": "pass" if not severity_counts["error"] else "fail",
        "verify_images": bool(args.verify_images),
        "summary": {
            "videos": len(set().union(*observed_tasks_by_split.values())),
            "participants": len(set().union(*observed_participants_by_split.values())),
            "images": sum(image_counts.values()),
            "labelled_images": sum(labelled_counts.values()),
            "empty_images": sum(image_counts.values()) - sum(labelled_counts.values()),
            "boxes": sum(box_counts.values()),
            "event_tags": sum(len(item.get("events", [])) for item in event_rows),
            "corrupt_images": corrupt_images,
            "findings": dict(sorted(severity_counts.items())),
        },
        "splits": {
            split: {
                "participants": len(observed_participants_by_split[split]),
                "videos": len(observed_tasks_by_split[split]),
                "expected_videos": expected_tasks_by_split[split],
                "images": image_counts[split],
                "boxes": box_counts[split],
                "classes_present": sum(
                    class_counts[(split, class_id)] > 0 for class_id in classes
                ),
            }
            for split in SPLITS
        },
        "findings": [asdict(item) for item in findings],
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = validate(args)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary = result["summary"]
    print(
        f"Validation {str(result['status']).upper()}: "
        f"{summary['videos']} videos, {summary['images']:,} images, "
        f"{summary['boxes']:,} boxes, {summary['corrupt_images']} corrupt images."
    )
    print(f"Report: {args.output.resolve()}")
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
