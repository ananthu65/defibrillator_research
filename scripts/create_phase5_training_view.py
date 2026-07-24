#!/usr/bin/env python3
"""Create local YOLO file lists while quarantining known-bad tasks."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


SPLITS = ("train", "val", "test")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Phase 5 train/val/test lists from the Phase 4 manifest."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("datasets/phase4_yolo"),
        help="Validated Phase 4 dataset root.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets/phase4_yolo/phase5"),
        help="Ignored local output folder for file lists and YAML files.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/phase5/training_view.json"),
        help="Compact reproducibility report.",
    )
    parser.add_argument(
        "--quarantine-task",
        action="append",
        default=["P50_T"],
        help="Task excluded from every scored split (repeatable).",
    )
    parser.add_argument(
        "--smoke-images-per-task",
        type=int,
        default=6,
        help="Evenly spaced smoke-test images selected per train/val task.",
    )
    return parser.parse_args(argv)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_classes(dataset_yaml: Path) -> dict[int, str]:
    classes: dict[int, str] = {}
    in_names = False
    for line in dataset_yaml.read_text(encoding="utf-8").splitlines():
        if line.strip() == "names:":
            in_names = True
            continue
        if in_names and line.startswith("  "):
            key, separator, value = line.strip().partition(":")
            if separator and key.isdigit():
                classes[int(key)] = value.strip()
    if not classes:
        raise ValueError(f"No classes found in {dataset_yaml}")
    return classes


def evenly_spaced(rows: list[dict[str, str]], count: int) -> list[dict[str, str]]:
    if len(rows) <= count:
        return list(rows)
    indices = [((index + 1) * len(rows)) // (count + 1) for index in range(count)]
    return [rows[index] for index in indices]


def build_smoke_rows(
    rows: Iterable[dict[str, str]],
    *,
    images_per_task: int,
    class_names: Iterable[str],
) -> list[dict[str, str]]:
    by_task: dict[str, list[dict[str, str]]] = defaultdict(list)
    all_rows = list(rows)
    for row in all_rows:
        by_task[row["canonical_task_id"]].append(row)

    selected: list[dict[str, str]] = []
    for task_id in sorted(by_task):
        task_rows = sorted(
            by_task[task_id], key=lambda item: int(item["source_frame"])
        )
        selected.extend(evenly_spaced(task_rows, images_per_task))

    selected_paths = {row["image_path"] for row in selected}
    present_classes = {
        name
        for row in selected
        for name in row.get("class_names", "").split(";")
        if name
    }
    for missing_class in sorted(set(class_names) - present_classes):
        candidate = next(
            (
                row
                for row in all_rows
                if missing_class in row.get("class_names", "").split(";")
            ),
            None,
        )
        if candidate is None:
            raise ValueError(f"Smoke split has no sample for class {missing_class}")
        if candidate["image_path"] not in selected_paths:
            selected.append(candidate)
            selected_paths.add(candidate["image_path"])
    return sorted(
        selected,
        key=lambda item: (item["canonical_task_id"], int(item["source_frame"])),
    )


def write_list(path: Path, rows: Iterable[dict[str, str]], dataset: Path) -> int:
    paths = [(dataset / row["image_path"]).resolve().as_posix() for row in rows]
    path.write_text("\n".join(paths) + "\n", encoding="utf-8")
    return len(paths)


def write_yaml(
    path: Path,
    *,
    dataset: Path,
    train_list: Path,
    val_list: Path,
    classes: dict[int, str],
    test_list: Path | None = None,
) -> None:
    lines = [
        f"path: {dataset.resolve().as_posix()}",
        f"train: {train_list.resolve().as_posix()}",
        f"val: {val_list.resolve().as_posix()}",
    ]
    if test_list is not None:
        lines.append(f"test: {test_list.resolve().as_posix()}")
    lines.append("names:")
    lines.extend(f"  {class_id}: {name}" for class_id, name in classes.items())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize(rows: Iterable[dict[str, str]]) -> dict[str, object]:
    selected = list(rows)
    class_counts: Counter[str] = Counter(
        name
        for row in selected
        for name in row.get("class_names", "").split(";")
        if name
    )
    return {
        "participants": len({row["participant_id"] for row in selected}),
        "videos": len({row["canonical_task_id"] for row in selected}),
        "images": len(selected),
        "boxes": sum(int(row["object_count"]) for row in selected),
        "classes_present": len(class_counts),
    }


def create_view(args: argparse.Namespace) -> dict[str, object]:
    dataset = args.dataset.resolve()
    manifest = dataset / "metadata" / "sample_manifest.csv"
    dataset_yaml = dataset / "dataset.yaml"
    if not manifest.is_file() or not dataset_yaml.is_file():
        raise FileNotFoundError(f"Phase 4 dataset metadata is missing under {dataset}")
    if args.smoke_images_per_task < 1:
        raise ValueError("--smoke-images-per-task must be positive.")

    classes = read_classes(dataset_yaml)
    rows = read_csv(manifest)
    quarantine = set(args.quarantine_task)
    known_tasks = {row["canonical_task_id"] for row in rows}
    missing_tasks = sorted(quarantine - known_tasks)
    if missing_tasks:
        raise ValueError(f"Quarantine tasks are not in the dataset: {missing_tasks}")

    quarantined_rows = [
        row for row in rows if row["canonical_task_id"] in quarantine
    ]
    scored = {
        split: [
            row
            for row in rows
            if row["split"] == split and row["canonical_task_id"] not in quarantine
        ]
        for split in SPLITS
    }
    if any(not scored[split] for split in SPLITS):
        raise ValueError("Quarantine produced an empty scored split.")

    args.output.mkdir(parents=True, exist_ok=True)
    list_paths = {
        split: args.output / f"{split}.txt" for split in SPLITS
    }
    for split in SPLITS:
        write_list(list_paths[split], scored[split], dataset)
    write_list(args.output / "quarantine.txt", quarantined_rows, dataset)

    smoke_train = build_smoke_rows(
        scored["train"],
        images_per_task=args.smoke_images_per_task,
        class_names=classes.values(),
    )
    smoke_val = build_smoke_rows(
        scored["val"],
        images_per_task=args.smoke_images_per_task,
        class_names=classes.values(),
    )
    smoke_train_path = args.output / "train_smoke.txt"
    smoke_val_path = args.output / "val_smoke.txt"
    write_list(smoke_train_path, smoke_train, dataset)
    write_list(smoke_val_path, smoke_val, dataset)

    write_yaml(
        args.output / "dataset_preliminary.yaml",
        dataset=dataset,
        train_list=list_paths["train"],
        val_list=list_paths["val"],
        test_list=list_paths["test"],
        classes=classes,
    )
    write_yaml(
        args.output / "dataset_smoke.yaml",
        dataset=dataset,
        train_list=smoke_train_path,
        val_list=smoke_val_path,
        classes=classes,
    )

    result: dict[str, object] = {
        "schema_version": 1,
        "status": "preliminary",
        "policy": {
            "quarantined_tasks": sorted(quarantine),
            "quarantine_is_scored_test": False,
            "reason": "Known-invalid ground truth is excluded from all metrics.",
            "frozen_phase3_split_modified": False,
        },
        "full": {split: summarize(scored[split]) for split in SPLITS},
        "quarantine": summarize(quarantined_rows),
        "smoke": {
            "train": summarize(smoke_train),
            "val": summarize(smoke_val),
            "images_per_task_target": args.smoke_images_per_task,
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = create_view(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        "Created Phase 5 view: "
        f"train={result['full']['train']['images']:,}, "
        f"val={result['full']['val']['images']:,}, "
        f"test={result['full']['test']['images']:,}, "
        f"quarantine={result['quarantine']['images']:,}."
    )
    print(
        "Smoke view: "
        f"train={result['smoke']['train']['images']:,}, "
        f"val={result['smoke']['val']['images']:,}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
