#!/usr/bin/env python3
"""Render deterministic train/validation YOLO overlays for manual QA."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_yolo_dataset import (
    parse_dataset_classes,
    parse_label_line,
    safe_dataset_path,
)


PALETTE = (
    "#ff3b30",
    "#ff9500",
    "#ffcc00",
    "#34c759",
    "#00c7be",
    "#007aff",
    "#af52de",
)
ALLOWED_SPLITS = ("train", "val")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render local YOLO overlays without opening the locked test split."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("datasets/phase4_yolo"),
        help="Generated YOLO dataset root.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets/phase4_yolo/qa_previews"),
        help="Ignored local preview output folder.",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        choices=ALLOWED_SPLITS,
        default=list(ALLOWED_SPLITS),
        help="Preview train and/or validation. Test is deliberately unavailable.",
    )
    parser.add_argument(
        "--per-class",
        type=int,
        default=1,
        help="Number of distinct preview images per class and split.",
    )
    return parser.parse_args(argv)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def select_rows(
    rows: list[dict[str, str]],
    classes: dict[int, str],
    splits: list[str],
    per_class: int,
) -> list[tuple[str, int, dict[str, str]]]:
    selections: list[tuple[str, int, dict[str, str]]] = []
    for split in splits:
        split_rows = [
            row
            for row in rows
            if row["split"] == split and int(row["object_count"]) > 0
        ]
        used_paths: set[str] = set()
        for class_id, class_name in classes.items():
            candidates = [
                row
                for row in split_rows
                if class_name in row["class_names"].split(";")
            ]
            if len(candidates) < per_class:
                raise ValueError(
                    f"{split} has only {len(candidates)} image(s) for {class_name}"
                )
            unused = [
                row for row in candidates if row["image_path"] not in used_paths
            ]
            pool = unused if len(unused) >= per_class else candidates
            indices = [
                ((index + 1) * len(pool)) // (per_class + 1)
                for index in range(per_class)
            ]
            chosen = [pool[index] for index in indices]
            for row in chosen:
                used_paths.add(row["image_path"])
                selections.append((split, class_id, row))
    return selections


def render(args: argparse.Namespace) -> list[Path]:
    if args.per_class < 1:
        raise ValueError("--per-class must be positive.")
    dataset_root = args.dataset.resolve()
    classes = parse_dataset_classes(dataset_root / "dataset.yaml")
    rows = read_rows(dataset_root / "metadata" / "sample_manifest.csv")
    selections = select_rows(rows, classes, args.splits, args.per_class)

    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError("Pillow is required to render previews.") from exc

    args.output.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    occurrence: defaultdict[tuple[str, int], int] = defaultdict(int)
    for split, target_class_id, row in selections:
        image_path = safe_dataset_path(dataset_root, row["image_path"])
        label_path = safe_dataset_path(dataset_root, row["label_path"])
        with Image.open(image_path) as source:
            image = source.convert("RGB")
        draw = ImageDraw.Draw(image)
        label_lines = [
            line
            for line in label_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        for index, line in enumerate(label_lines, start=1):
            box = parse_label_line(
                line,
                class_count=len(classes),
                location=f"{label_path.name}:{index}",
            )
            x1 = max(0.0, (box.center_x - box.width / 2) * image.width)
            y1 = max(0.0, (box.center_y - box.height / 2) * image.height)
            x2 = min(float(image.width), (box.center_x + box.width / 2) * image.width)
            y2 = min(float(image.height), (box.center_y + box.height / 2) * image.height)
            color = PALETTE[box.class_id % len(PALETTE)]
            stroke = 7 if box.class_id == target_class_id else 3
            draw.rectangle((x1, y1, x2, y2), outline=color, width=stroke)
            text = classes[box.class_id]
            text_box = draw.textbbox((x1, y1), text)
            text_height = text_box[3] - text_box[1]
            text_y = max(0, y1 - text_height - 6)
            text_bottom = max(text_y, y1)
            draw.rectangle(
                (x1, text_y, x1 + text_box[2] - text_box[0] + 8, text_bottom),
                fill=color,
            )
            draw.text((x1 + 4, text_y + 2), text, fill="black")

        header = (
            f"{split} | {row['canonical_task_id']} | frame {row['source_frame']} | "
            f"target: {classes[target_class_id]}"
        )
        header_box = draw.textbbox((0, 0), header)
        draw.rectangle(
            (0, 0, image.width, header_box[3] - header_box[1] + 12),
            fill="black",
        )
        draw.text((6, 6), header, fill="white")

        occurrence[(split, target_class_id)] += 1
        output_name = (
            f"{split}_class{target_class_id}_{classes[target_class_id]}_"
            f"{occurrence[(split, target_class_id)]:02d}.jpg"
        )
        output_path = args.output / output_name
        image.save(output_path, format="JPEG", quality=90)
        outputs.append(output_path.resolve())

    tile_width = 480
    tile_height = 320
    columns = 3
    for split in args.splits:
        split_outputs = [
            path for path in outputs if path.name.startswith(f"{split}_class")
        ]
        rows = (len(split_outputs) + columns - 1) // columns
        sheet = Image.new(
            "RGB", (tile_width * columns, tile_height * rows), color="black"
        )
        for index, path in enumerate(split_outputs):
            with Image.open(path) as preview:
                thumbnail = preview.convert("RGB")
            thumbnail.thumbnail(
                (tile_width, tile_height), Image.Resampling.LANCZOS
            )
            x = (index % columns) * tile_width + (tile_width - thumbnail.width) // 2
            y = (index // columns) * tile_height + (tile_height - thumbnail.height) // 2
            sheet.paste(thumbnail, (x, y))
        sheet.save(
            args.output / f"{split}_contact_sheet.jpg",
            format="JPEG",
            quality=92,
        )
    return outputs


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        outputs = render(args)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Rendered {len(outputs)} train/validation previews in {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
