#!/usr/bin/env python3
"""Create a deterministic participant-grouped video dataset split.

The generator consumes Phase 1 reports. It keeps each participant's T, LS, and
LL videos together, applies per-annotation-source quotas, and searches for an
assignment that balances frames, labels, and review findings.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


SPLITS = ("train", "val", "test")
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


@dataclass
class VideoRecord:
    canonical_task_id: str
    participant_id: str
    camera_view: str
    annotation_source: str
    archive: str
    task_path: str
    media_name: str
    frame_count: int
    media_size_bytes: int
    tag_count: int
    track_count: int
    track_keyframe_count: int
    rotated_keyframe_count: int
    outside_keyframe_count: int
    event_counts: dict[str, int]
    track_labels: set[str]


@dataclass
class ParticipantRecord:
    participant_id: str
    annotation_source: str
    videos: list[VideoRecord] = field(default_factory=list)
    features: dict[str, float] = field(default_factory=dict)
    warning_count: int = 0
    review_count: int = 0
    issue_codes: Counter[str] = field(default_factory=Counter)


@dataclass
class SplitResult:
    assignments: dict[str, str]
    score: float
    source_quotas: dict[str, dict[str, int]]
    seed: int
    iterations: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a grouped and annotation-source-balanced video split."
    )
    parser.add_argument(
        "--phase1-reports",
        type=Path,
        default=Path("reports/phase1"),
        help="Folder containing Phase 1 CSV/JSON reports.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("splits/phase3"),
        help="Output folder for split manifests.",
    )
    parser.add_argument("--train", type=int, default=33, help="Training set count.")
    parser.add_argument("--val", type=int, default=6, help="Validation set count.")
    parser.add_argument("--test", type=int, default=9, help="Test set count.")
    parser.add_argument("--seed", type=int, default=42, help="Random-search seed.")
    parser.add_argument(
        "--iterations",
        type=int,
        default=100_000,
        help="Number of source-constrained assignments to evaluate.",
    )
    return parser.parse_args(argv)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def parse_event_frames(value: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in value.split(";"):
        if "=" not in item:
            continue
        label, frames = item.split("=", 1)
        counts[label] = len([frame for frame in frames.split(",") if frame])
    return counts


def participant_from_canonical_id(value: str) -> str:
    match = re.match(r"^(P\d+)", value)
    return match.group(1) if match else ""


def load_phase1_reports(report_root: Path) -> tuple[list[VideoRecord], list[dict[str, str]], str]:
    inventory_path = report_root / "dataset_inventory.csv"
    issues_path = report_root / "annotation_issues.csv"
    manifest_path = report_root / "dataset_manifest.json"
    for path in (inventory_path, issues_path, manifest_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required Phase 1 report is missing: {path}")

    inventory_rows = read_csv(inventory_path)
    videos: list[VideoRecord] = []
    for row in inventory_rows:
        videos.append(
            VideoRecord(
                canonical_task_id=row["canonical_task_id"],
                participant_id=row["participant_id"],
                camera_view=row["camera_view"],
                annotation_source=row["annotation_source"],
                archive=row["archive"],
                task_path=row["task_path"],
                media_name=row["media_name"],
                frame_count=int(row["frame_count"]),
                media_size_bytes=int(row["media_size_bytes"]),
                tag_count=int(row["tag_count"]),
                track_count=int(row["track_count"]),
                track_keyframe_count=int(row["track_keyframe_count"]),
                rotated_keyframe_count=int(row["rotated_keyframe_count"]),
                outside_keyframe_count=int(row["outside_keyframe_count"]),
                event_counts=parse_event_frames(row["event_frames"]),
                track_labels={
                    label for label in row["track_labels"].split(";") if label
                },
            )
        )

    issues = read_csv(issues_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_digest = str(manifest["dataset_digest_sha256"])
    digest_rows = [
        {
            "archive": row["archive"],
            "task_path": row["task_path"],
            "canonical_task_id": row["canonical_task_id"],
            "frame_count": int(row["frame_count"]),
            "tags": int(row["tag_count"]),
            "tracks": int(row["track_count"]),
            "keyframes": int(row["track_keyframe_count"]),
        }
        for row in inventory_rows
    ]
    actual_digest = hashlib.sha256(
        json.dumps(digest_rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if actual_digest != expected_digest:
        raise ValueError(
            "Phase 1 inventory does not match dataset_manifest.json: "
            f"expected {expected_digest}, calculated {actual_digest}"
        )
    return videos, issues, expected_digest


def build_participants(
    videos: Iterable[VideoRecord], issues: Iterable[dict[str, str]]
) -> dict[str, ParticipantRecord]:
    participants: dict[str, ParticipantRecord] = {}
    for video in videos:
        if not video.participant_id:
            raise ValueError(f"Video has no participant ID: {video.canonical_task_id}")
        participant = participants.setdefault(
            video.participant_id,
            ParticipantRecord(
                participant_id=video.participant_id,
                annotation_source=video.annotation_source,
            ),
        )
        if participant.annotation_source != video.annotation_source:
            raise ValueError(
                f"{video.participant_id} spans annotation sources: "
                f"{participant.annotation_source!r} and {video.annotation_source!r}"
            )
        participant.videos.append(video)

    for participant in participants.values():
        views = {video.camera_view for video in participant.videos}
        if views != {"T", "LS", "LL"} or len(participant.videos) != 3:
            raise ValueError(
                f"{participant.participant_id} is not a complete three-view set: "
                f"{sorted(views)}"
            )
        participant.videos.sort(key=lambda video: ("T", "LS", "LL").index(video.camera_view))

        features: dict[str, float] = {
            "frames": sum(video.frame_count for video in participant.videos),
            "media_bytes": sum(video.media_size_bytes for video in participant.videos),
            "event_tags_total": sum(video.tag_count for video in participant.videos),
            "tracks_total": sum(video.track_count for video in participant.videos),
            "track_keyframes_total": sum(
                video.track_keyframe_count for video in participant.videos
            ),
            "rotated_keyframes": sum(
                video.rotated_keyframe_count for video in participant.videos
            ),
            "outside_keyframes": sum(
                video.outside_keyframe_count for video in participant.videos
            ),
        }
        for label in EVENT_LABELS:
            features[f"event::{label}"] = sum(
                video.event_counts.get(label, 0) for video in participant.videos
            )
        for label in TRACK_LABELS:
            features[f"track_views::{label}"] = sum(
                label in video.track_labels for video in participant.videos
            )
        participant.features = features

    for issue in issues:
        participant_id = participant_from_canonical_id(issue.get("canonical_task_id", ""))
        if participant_id not in participants:
            continue
        severity = issue.get("severity", "")
        code = issue.get("code", "")
        participant = participants[participant_id]
        if severity == "warning":
            participant.warning_count += 1
        elif severity == "review":
            participant.review_count += 1
        if severity in {"warning", "review"}:
            participant.issue_codes[code] += 1

    for participant in participants.values():
        participant.features["warning_issues"] = participant.warning_count
        participant.features["review_issues"] = participant.review_count
        for code, count in participant.issue_codes.items():
            participant.features[f"issue::{code}"] = count
    return participants


def allocate_proportional_quotas(
    source_sizes: dict[str, int],
    total: int,
    *,
    minimum_each: int = 0,
    capacities: dict[str, int] | None = None,
) -> dict[str, int]:
    """Allocate an integer total proportionally using largest deficits."""

    sources = sorted(source_sizes)
    capacities = capacities or source_sizes
    quotas = {source: 0 for source in sources}
    if minimum_each:
        if total < minimum_each * len(sources):
            raise ValueError("Requested total cannot satisfy the per-source minimum.")
        for source in sources:
            if capacities[source] < minimum_each:
                raise ValueError(f"Insufficient capacity for source {source!r}.")
            quotas[source] = minimum_each

    assigned = sum(quotas.values())
    overall = sum(source_sizes.values())
    ideals = {
        source: total * source_sizes[source] / overall for source in sources
    }
    while assigned < total:
        candidates = [
            source for source in sources if quotas[source] < capacities[source]
        ]
        if not candidates:
            raise ValueError("Source capacities cannot satisfy requested split size.")
        source = max(
            candidates,
            key=lambda item: (ideals[item] - quotas[item], source_sizes[item], item),
        )
        quotas[source] += 1
        assigned += 1
    return quotas


def derive_source_quotas(
    participants: dict[str, ParticipantRecord],
    target_counts: dict[str, int],
) -> dict[str, dict[str, int]]:
    source_sizes = Counter(
        participant.annotation_source for participant in participants.values()
    )
    minimum_val = 1 if target_counts["val"] >= len(source_sizes) else 0
    val_quotas = allocate_proportional_quotas(
        dict(source_sizes), target_counts["val"], minimum_each=minimum_val
    )
    remaining_capacity = {
        source: size - val_quotas[source] for source, size in source_sizes.items()
    }
    minimum_test = 1 if target_counts["test"] >= len(source_sizes) else 0
    test_quotas = allocate_proportional_quotas(
        dict(source_sizes),
        target_counts["test"],
        minimum_each=minimum_test,
        capacities=remaining_capacity,
    )
    train_quotas = {
        source: source_sizes[source] - val_quotas[source] - test_quotas[source]
        for source in source_sizes
    }
    quotas = {
        "train": train_quotas,
        "val": val_quotas,
        "test": test_quotas,
    }
    for split in SPLITS:
        if sum(quotas[split].values()) != target_counts[split]:
            raise AssertionError(f"Invalid {split} source quotas.")
    return quotas


def feature_weight(name: str) -> float:
    if name == "frames":
        return 8.0
    if name in {"event_tags_total", "tracks_total", "track_keyframes_total"}:
        return 3.0
    if name.startswith("event::"):
        return 6.0
    if name.startswith("track_views::"):
        return 5.0
    if name.startswith("issue::"):
        return 2.0
    if name in {"warning_issues", "review_issues"}:
        return 2.0
    return 1.0


def assignment_score(
    participants: dict[str, ParticipantRecord],
    assignments: dict[str, str],
    target_counts: dict[str, int],
) -> float:
    feature_names = sorted(
        {name for participant in participants.values() for name in participant.features}
    )
    totals = {
        name: sum(participant.features.get(name, 0.0) for participant in participants.values())
        for name in feature_names
    }
    split_values: dict[str, dict[str, float]] = {
        split: defaultdict(float) for split in SPLITS
    }
    for participant_id, split in assignments.items():
        for name, value in participants[participant_id].features.items():
            split_values[split][name] += value

    score = 0.0
    participant_total = len(participants)
    for split in SPLITS:
        expected_fraction = target_counts[split] / participant_total
        for name in feature_names:
            total = totals[name]
            if total <= 0:
                continue
            actual_fraction = split_values[split].get(name, 0.0) / total
            difference = actual_fraction - expected_fraction
            score += feature_weight(name) * difference * difference

            # A supported label should not disappear entirely from val or test.
            if (
                split != "train"
                and (name.startswith("event::") or name.startswith("track_views::"))
                and total >= len(SPLITS)
                and split_values[split].get(name, 0.0) == 0
            ):
                score += 100.0
    return score


def generate_split(
    participants: dict[str, ParticipantRecord],
    *,
    train_count: int,
    val_count: int,
    test_count: int,
    seed: int,
    iterations: int,
) -> SplitResult:
    target_counts = {
        "train": train_count,
        "val": val_count,
        "test": test_count,
    }
    if sum(target_counts.values()) != len(participants):
        raise ValueError(
            f"Split counts sum to {sum(target_counts.values())}, "
            f"but {len(participants)} participant sets are available."
        )
    if min(target_counts.values()) <= 0:
        raise ValueError("Every split must contain at least one participant set.")
    if iterations <= 0:
        raise ValueError("Iterations must be positive.")

    source_quotas = derive_source_quotas(participants, target_counts)
    by_source: dict[str, list[str]] = defaultdict(list)
    for participant_id, participant in participants.items():
        by_source[participant.annotation_source].append(participant_id)
    for participant_ids in by_source.values():
        participant_ids.sort(key=lambda value: int(value[1:]))

    random_generator = random.Random(seed)
    best_assignments: dict[str, str] | None = None
    best_score = math.inf

    for _ in range(iterations):
        assignments: dict[str, str] = {}
        for source in sorted(by_source):
            participant_ids = by_source[source][:]
            random_generator.shuffle(participant_ids)
            val_end = source_quotas["val"][source]
            test_end = val_end + source_quotas["test"][source]
            for participant_id in participant_ids[:val_end]:
                assignments[participant_id] = "val"
            for participant_id in participant_ids[val_end:test_end]:
                assignments[participant_id] = "test"
            for participant_id in participant_ids[test_end:]:
                assignments[participant_id] = "train"

        score = assignment_score(participants, assignments, target_counts)
        if score < best_score:
            best_score = score
            best_assignments = assignments.copy()

    if best_assignments is None:
        raise RuntimeError("No split assignment was generated.")
    return SplitResult(
        assignments=best_assignments,
        score=best_score,
        source_quotas=source_quotas,
        seed=seed,
        iterations=iterations,
    )


def validate_split(
    participants: dict[str, ParticipantRecord],
    result: SplitResult,
    target_counts: dict[str, int],
) -> list[str]:
    errors: list[str] = []
    if set(result.assignments) != set(participants):
        errors.append("Assignments do not cover every participant exactly once.")
    for split in SPLITS:
        actual = sum(value == split for value in result.assignments.values())
        if actual != target_counts[split]:
            errors.append(f"{split} has {actual} sets; expected {target_counts[split]}.")

    task_ids: dict[str, set[str]] = {split: set() for split in SPLITS}
    for participant_id, split in result.assignments.items():
        task_ids[split].update(
            video.canonical_task_id for video in participants[participant_id].videos
        )
    for index, left in enumerate(SPLITS):
        for right in SPLITS[index + 1 :]:
            overlap = task_ids[left] & task_ids[right]
            if overlap:
                errors.append(f"Video leakage between {left} and {right}: {sorted(overlap)}")

    for split in SPLITS:
        source_counts = Counter(
            participants[participant_id].annotation_source
            for participant_id, assigned_split in result.assignments.items()
            if assigned_split == split
        )
        if dict(source_counts) != {
            source: count
            for source, count in result.source_quotas[split].items()
            if count
        }:
            errors.append(f"{split} source counts do not match quotas.")
    return errors


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_reports(
    participants: dict[str, ParticipantRecord],
    result: SplitResult,
    output_root: Path,
    dataset_digest: str,
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)

    ordered_participants = sorted(participants, key=lambda value: int(value[1:]))
    for split in SPLITS:
        split_participants = [
            participant_id
            for participant_id in ordered_participants
            if result.assignments[participant_id] == split
        ]
        (output_root / f"{split}_sets.txt").write_text(
            "\n".join(split_participants) + "\n", encoding="utf-8"
        )
        task_ids = [
            video.canonical_task_id
            for participant_id in split_participants
            for video in participants[participant_id].videos
        ]
        (output_root / f"{split}_videos.txt").write_text(
            "\n".join(task_ids) + "\n", encoding="utf-8"
        )

    participant_rows: list[dict[str, Any]] = []
    video_rows: list[dict[str, Any]] = []
    for participant_id in ordered_participants:
        participant = participants[participant_id]
        split = result.assignments[participant_id]
        row: dict[str, Any] = {
            "split": split,
            "participant_id": participant_id,
            "annotation_source": participant.annotation_source,
            "video_count": len(participant.videos),
            "views": ",".join(video.camera_view for video in participant.videos),
            "warning_issues": participant.warning_count,
            "review_issues": participant.review_count,
        }
        row.update({name: int(value) for name, value in participant.features.items()})
        participant_rows.append(row)

        for video in participant.videos:
            video_rows.append(
                {
                    "split": split,
                    "participant_id": participant_id,
                    "canonical_task_id": video.canonical_task_id,
                    "camera_view": video.camera_view,
                    "annotation_source": participant.annotation_source,
                    "archive": video.archive,
                    "task_path": video.task_path,
                    "media_name": video.media_name,
                    "frame_count": video.frame_count,
                    "tag_count": video.tag_count,
                    "track_count": video.track_count,
                    "track_keyframe_count": video.track_keyframe_count,
                }
            )

    base_participant_fields = [
        "split",
        "participant_id",
        "annotation_source",
        "video_count",
        "views",
        "warning_issues",
        "review_issues",
    ]
    participant_fields = base_participant_fields + sorted(
        {
            key
            for row in participant_rows
            for key in row
            if key not in base_participant_fields
        }
    )
    write_csv(
        output_root / "participant_split.csv",
        participant_rows,
        participant_fields,
    )
    write_csv(
        output_root / "video_split_manifest.csv",
        video_rows,
        [
            "split",
            "participant_id",
            "canonical_task_id",
            "camera_view",
            "annotation_source",
            "archive",
            "task_path",
            "media_name",
            "frame_count",
            "tag_count",
            "track_count",
            "track_keyframe_count",
        ],
    )

    summary_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    for split in SPLITS:
        selected = [
            participant
            for participant_id, participant in participants.items()
            if result.assignments[participant_id] == split
        ]
        videos = [video for participant in selected for video in participant.videos]
        summary_rows.append(
            {
                "split": split,
                "participant_sets": len(selected),
                "videos": len(videos),
                "frames": sum(video.frame_count for video in videos),
                "media_size_bytes": sum(video.media_size_bytes for video in videos),
                "event_tags": sum(video.tag_count for video in videos),
                "tracks": sum(video.track_count for video in videos),
                "track_keyframes": sum(video.track_keyframe_count for video in videos),
                "warning_issues": sum(item.warning_count for item in selected),
                "review_issues": sum(item.review_count for item in selected),
            }
        )
        source_counts = Counter(item.annotation_source for item in selected)
        for source in sorted({item.annotation_source for item in participants.values()}):
            source_rows.append(
                {
                    "split": split,
                    "annotation_source": source,
                    "participant_sets": source_counts[source],
                }
            )
        for label in EVENT_LABELS:
            label_rows.append(
                {
                    "split": split,
                    "annotation_kind": "event_tag",
                    "label": label,
                    "annotations": sum(
                        video.event_counts.get(label, 0) for video in videos
                    ),
                    "videos_present": sum(
                        video.event_counts.get(label, 0) > 0 for video in videos
                    ),
                }
            )
        for label in TRACK_LABELS:
            label_rows.append(
                {
                    "split": split,
                    "annotation_kind": "track",
                    "label": label,
                    "annotations": sum(label in video.track_labels for video in videos),
                    "videos_present": sum(label in video.track_labels for video in videos),
                }
            )

    write_csv(
        output_root / "split_summary.csv",
        summary_rows,
        [
            "split",
            "participant_sets",
            "videos",
            "frames",
            "media_size_bytes",
            "event_tags",
            "tracks",
            "track_keyframes",
            "warning_issues",
            "review_issues",
        ],
    )
    write_csv(
        output_root / "source_distribution.csv",
        source_rows,
        ["split", "annotation_source", "participant_sets"],
    )
    write_csv(
        output_root / "label_distribution.csv",
        label_rows,
        ["split", "annotation_kind", "label", "annotations", "videos_present"],
    )

    config = {
        "schema_version": 1,
        "phase1_dataset_digest_sha256": dataset_digest,
        "group_unit": "participant_id",
        "required_views_per_set": ["T", "LS", "LL"],
        "seed": result.seed,
        "iterations": result.iterations,
        "optimization_score": result.score,
        "counts": {
            split: sum(value == split for value in result.assignments.values())
            for split in SPLITS
        },
        "source_quotas": result.source_quotas,
        "assignments": {
            participant_id: result.assignments[participant_id]
            for participant_id in ordered_participants
        },
    }
    (output_root / "split_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    summary_by_split = {row["split"]: row for row in summary_rows}
    lines = [
        "# Phase 3 Grouped Video Split",
        "",
        "Each participant is the split unit. T, LS, and LL videos always remain together.",
        "",
        "| Split | Sets | Videos | Frames | Event tags | Tracks |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split in SPLITS:
        row = summary_by_split[split]
        lines.append(
            f"| {split} | {row['participant_sets']} | {row['videos']} | "
            f"{row['frames']:,} | {row['event_tags']} | {row['tracks']} |"
        )
    lines.extend(
        [
            "",
            "## Source constraints",
            "",
            "- Every annotation source appears in train, validation, and test.",
            "- Validation contains one participant set from every source.",
            "- Test contains three sets from defibliration2, two from kartheepan, and one from every other source.",
            "- No participant or camera view appears in more than one split.",
            "",
            f"Optimization seed: `{result.seed}`  ",
            f"Assignments evaluated: `{result.iterations:,}`  ",
            f"Phase 1 dataset digest: `{dataset_digest}`",
            "",
            "This split is a manifest only. The source CVAT archives were not moved, extracted, or modified.",
            "",
        ]
    )
    (output_root / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        videos, issues, dataset_digest = load_phase1_reports(args.phase1_reports)
        participants = build_participants(videos, issues)
        result = generate_split(
            participants,
            train_count=args.train,
            val_count=args.val,
            test_count=args.test,
            seed=args.seed,
            iterations=args.iterations,
        )
        target_counts = {
            "train": args.train,
            "val": args.val,
            "test": args.test,
        }
        validation_errors = validate_split(participants, result, target_counts)
        if validation_errors:
            for error in validation_errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 2
        write_reports(participants, result, args.output, dataset_digest)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    counts = Counter(result.assignments.values())
    print(
        f"Created grouped split: train={counts['train']}, "
        f"val={counts['val']}, test={counts['test']}."
    )
    print(f"Balanced assignment score: {result.score:.8f}")
    print(f"Reports written to: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
