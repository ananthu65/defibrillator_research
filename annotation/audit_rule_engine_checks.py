#!/usr/bin/env python3
"""Rule-engine annotation checks on CVAT backup ZIPs (Step 9b, D-074), separate from the Phase 1 audit.

    python -m annotation.audit_rule_engine_checks --backup-root <folder of CVAT ZIPs> \
        --output annotation/reports/rule_engine_audit/<run>

Review list (``issues.csv``): problems an annotator should look at:
  duplicate_paddle_box      two or more boxes of one paddle label on the same frame
  zone_moves_like_paddle    a zone track whose centre moves more than the threshold (5% of the diagonal)
  repeated_incident_tag     one tag twice within the window (15 frames): possibly the same incident tagged twice
  zone_pattern_off          zone tracks that differ from the view's usual pattern (configured), including none
  zone_exception_contradicted  a reviewed "not visible" exception for a zone that is visible
  gel_hand_not_tracked      no learner_hand box in the gel phase (before the first placement tag, else
                            the earliest take of either paddle), so whether gel was applied can't be derived
                            (9d, D-111, D-118)
Information only (``info.csv``), never annotation issues: the learner's procedure order, tags repeated
further apart than the window, a missing first-placement tag, a zone track that is never visible
(not covered), and confirmed zone exceptions.

The usual zone pattern is used only for this review list (D-082). The rule engine never uses it.
Existing annotation scripts and their outputs are not changed.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from annotation.audit_cvat_backups import Issue
from annotation.build_yolo_video_dataset import shape_box, track_box_at
from annotation.derive_gel_applications import gel_phase, hand_frames
from annotation.export_rule_engine_records import (
    DEFAULT_CONFIG,
    DEFAULT_CONVERSION_REPORT,
    EXIT_REFUSED,
    ExportConfig,
    TaskSource,
    VideoInfo,
    backup_list,
    check_output,
    frame_runs,
    iter_tasks,
    load_config,
    load_conversion_report,
    unique_tasks,
    write_issues,
    zone_visible_frames,
)

FIRST_PLACEMENT_TAG = "first_paddle_firmly_on_the_chest"
FOLLOW_IOU = 0.5
REVIEW_SEVERITIES = ("error", "warning", "review")


@dataclass
class ZonePattern:
    canonical_task_id: str
    camera_view: str
    expected: str
    present: str
    visible: str
    never_visible: str
    confirmed_not_visible: str
    missing: str
    unexpected: str
    on_review_list: bool


def audit_task(source: TaskSource, video: VideoInfo | None, config: ExportConfig,
               issues: list[Issue], info: list[Issue]) -> ZonePattern:
    where = dict(archive=source.archive, task_path=source.task_path, canonical_task_id=source.canonical_task_id)
    _repeated_tags(source, config, issues, info, where)
    _tag_information(source, info, where)
    if video is None:
        issues.append(Issue("error", "fps_missing", details="video not in the conversion report; the box and "
                            "zone checks need its frame size", **where))
    else:
        _duplicate_paddle_boxes(source, config, issues, where)
        _moving_zones(source, video, config, issues, where)
        _gel_hand(source, video, config, issues, where)
    return _zone_pattern(source, video, config, issues, info, where)


def _repeated_tags(source, config, issues, info, where):
    frames_by_label: dict[str, list[int]] = {}
    for tag in source.tags:
        frames_by_label.setdefault(str(tag.get("label", "")), []).append(int(tag.get("frame", -1)))
    window = config.repeated_tag_window_frames
    for label, frames in sorted(frames_by_label.items()):
        for earlier, later in zip(sorted(frames), sorted(frames)[1:]):
            gap = later - earlier
            if gap <= window:
                issues.append(Issue("review", "repeated_incident_tag", label=label, frame=earlier,
                                    details=f"frames {earlier} and {later} ({gap} frames apart): possibly the same "
                                    "incident tagged twice", **where))
            else:
                info.append(Issue("info", "repeated_tag", label=label, frame=earlier,
                                  details=f"frames {earlier} and {later} ({gap} frames apart); the learner may have "
                                  "repeated the action, which the rule engine judges", **where))


def _tag_information(source, info, where):
    ordered = sorted(((int(t.get("frame", -1)), str(t.get("label", ""))) for t in source.tags))
    info.append(Issue("info", "tag_sequence", details="; ".join(f"{label}@{frame}" for frame, label in ordered)
                      or "no tags", **where))
    if not any(label == FIRST_PLACEMENT_TAG for _, label in ordered):
        info.append(Issue("info", "first_placement_tag_missing", label=FIRST_PLACEMENT_TAG, **where))


def _gel_hand(source, video, config, issues, where):
    """9d (D-111): the bottle hand must be tracked in the gel phase, the same phase as the export's: it
    ends at the first-placement tag (the apical placement, A-027), else the earliest take of either paddle
    (D-118). Like the export, the audit never uses 9c placements."""
    end, ended_by = gel_phase(source, config.gel)
    if not hand_frames(source, video, config.gel, end):
        issues.append(Issue("review", "gel_hand_not_tracked", label=config.gel.hand_label,
                            details=f"no {config.gel.hand_label} box before frame {end} ({ended_by}); gel "
                            "applications can't be derived for this video", **where))


def _duplicate_paddle_boxes(source, config, issues, where):
    for label in config.paddle_labels:
        tracks = [t for t in source.tracks if t.label == label]
        shapes: dict[int, int] = Counter(int(s.get("frame", -1)) for s in source.standalone_shapes
                                         if str(s.get("label", "")) == label and shape_box(s) is not None)
        counts = {}
        for frame in range(source.start_frame, source.stop_frame + 1):
            boxes = sum(track_box_at(t, frame) is not None for t in tracks) + shapes.get(frame, 0)
            if boxes >= 2:
                counts[frame] = boxes
        for first, last in frame_runs(counts):
            most = max(counts[f] for f in range(first, last + 1))
            issues.append(Issue("review", "duplicate_paddle_box", label=label, frame=first,
                                details=f"frames {first}-{last}: up to {most} boxes of {label} on one frame", **where))


def _moving_zones(source, video, config, issues, where):
    diagonal = math.hypot(video.width, video.height)
    paddles = [t for t in source.tracks if t.label in config.paddle_labels]
    for index, track in enumerate(t for t in source.tracks if t.label in config.zone_labels):
        keyframes = [(int(s.get("frame", 0)), shape_box(s)) for s in track.shapes if not s.get("outside", False)]
        keyframes = [(frame, box) for frame, box in keyframes if box is not None]
        if len(keyframes) < 2:
            continue
        (frame_a, box_a), (frame_b, box_b) = max(itertools.combinations(keyframes, 2),
                                                 key=lambda pair: _distance(pair[0][1], pair[1][1]))
        moved = _distance(box_a, box_b) / diagonal
        if moved <= config.zone_motion_fraction_of_diagonal:
            continue
        follows = [(paddle.label, _iou(box_b, track_box_at(paddle, frame_b))) for paddle in paddles]
        follows = [(label, iou) for label, iou in follows if iou >= FOLLOW_IOU]
        note = "; ".join(f"overlaps {label} (IoU {iou:.2f}) at frame {frame_b}" for label, iou in follows)
        issues.append(Issue("review", "zone_moves_like_paddle", label=track.label, frame=frame_a,
                            details=f"track {index + 1} moved {moved:.1%} of the frame diagonal between frames "
                            f"{frame_a} and {frame_b}" + (f"; {note}" if note else ""), **where))


def _centre(box):
    return (box.x1 + box.x2) / 2.0, (box.y1 + box.y2) / 2.0


def _distance(a, b):
    (ax, ay), (bx, by) = _centre(a), _centre(b)
    return math.hypot(ax - bx, ay - by)


def _iou(a, b):
    if a is None or b is None:
        return 0.0
    width = max(0.0, min(a.x2, b.x2) - max(a.x1, b.x1))
    height = max(0.0, min(a.y2, b.y2) - max(a.y1, b.y1))
    overlap = width * height
    union = a.width * a.height + b.width * b.height - overlap
    return overlap / union if union > 0 else 0.0


def _zone_pattern(source, video, config, issues, info, where):
    present = {z for z in config.zone_labels if any(t.label == z for t in source.tracks)}
    visible = set()
    if video is not None:
        visible = {z for z in present if zone_visible_frames([t for t in source.tracks if t.label == z],
                                                              source.start_frame, source.stop_frame,
                                                              video.width, video.height)}
    never_visible = present - visible if video is not None else set()
    confirmed = config.confirmed_not_visible(source.canonical_task_id)
    for zone in sorted(never_visible):
        info.append(Issue("info", "zone_track_never_visible", label=zone, details="the track is outside on every "
                          "frame, so the zone counts as not covered (D-080)", **where))
    for zone in sorted(confirmed & visible):
        issues.append(Issue("review", "zone_exception_contradicted", label=zone, details="reviewed as genuinely not "
                            "visible, but the zone track is visible", **where))
    for zone in sorted(confirmed - visible):
        info.append(Issue("info", "zone_exception_confirmed", label=zone, details="confirmed not visible by an "
                          "annotator; not on the review list", **where))
    expected = config.usual_zone_pattern.get(source.camera_view)
    if expected is None:
        issues.append(Issue("review", "zone_pattern_unknown_view", details=f"no usual pattern configured for "
                            f"view {source.camera_view!r}", **where))
        missing, unexpected = set(), set()
    else:
        missing = set(expected) - present - confirmed
        unexpected = present - set(expected)
    off = bool(missing or unexpected)
    if off:
        issues.append(Issue("review", "zone_pattern_off", details=f"view {source.camera_view}: expected "
                            f"{_names(expected or ())}, tracks {_names(present)}; missing {_names(missing)}, "
                            f"unexpected {_names(unexpected)}", **where))
    return ZonePattern(source.canonical_task_id, source.camera_view, _names(expected or ()), _names(present),
                       _names(visible), _names(never_visible), _names(confirmed), _names(missing), _names(unexpected), off)


def _names(zones):
    return ";".join(sorted(zones)) or "none"


# ---- output -----------------------------------------------------------------------------------------

def write_rows(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def distribution(patterns: list[ZonePattern], config: ExportConfig) -> dict[str, dict[str, Any]]:
    """Per view: the configured usual pattern and the actual zone-track sets with their counts."""
    views = sorted({p.camera_view for p in patterns} | set(config.usual_zone_pattern))
    return {view: {"usual": _names(config.usual_zone_pattern.get(view, ())),
                   "actual": dict(sorted(Counter(p.present for p in patterns if p.camera_view == view).items()))}
            for view in views}


def readme(manifest: dict[str, Any], patterns: list[ZonePattern], issues: list[Issue]) -> str:
    lines = ["# Rule-engine annotation audit", "",
             "Separate from the Phase 1 audit; nothing in the training dataset is changed (D-074).",
             "Information-only findings (learner order, repeats further apart, never-visible tracks, confirmed",
             "exceptions) are in `info.csv` and are never annotation issues.", "",
             "## Zone tracks per view: usual pattern (config) and actual distribution", "",
             "The usual pattern is used only for this review list; the rule engine never uses it (D-082).", "",
             "| View | Usual pattern | Actual zone-track sets (videos) |", "| --- | --- | --- |"]
    for view, row in manifest["zone_distribution"].items():
        actual = ", ".join(f"{zones}: {count}" for zones, count in row["actual"].items()) or "none"
        lines.append(f"| {view} | {row['usual']} | {actual} |")
    lines += ["", "## Review list", "", "| Code | Count |", "| --- | ---: |"]
    for code, count in sorted(Counter(i.code for i in issues).items()):
        lines.append(f"| `{code}` | {count} |")
    off = [p for p in patterns if p.on_review_list]
    lines += ["", f"## Off-pattern videos ({len(off)})", "", "| Video | View | Zone tracks | Missing | Unexpected |",
              "| --- | --- | --- | --- | --- |"]
    lines += [f"| {p.canonical_task_id} | {p.camera_view} | {p.present} | {p.missing} | {p.unexpected} |" for p in off]
    settings = manifest["settings"]
    lines += ["", f"Settings (placeholders, D-074): zone motion > {settings['zone_motion_fraction_of_diagonal']:.0%} of "
              f"the frame diagonal; repeated tags within {settings['repeated_tag_window_frames']} frames.", ""]
    return "\n".join(lines)


def run_audit(backup_root: Path, output: Path, conversion_report: Path = DEFAULT_CONVERSION_REPORT,
              config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    output = check_output(output)
    config = load_config(config_path)
    videos = load_conversion_report(conversion_report)
    issues: list[Issue] = []
    info: list[Issue] = []
    sources = unique_tasks(iter_tasks(backup_root, issues), issues)
    patterns = [audit_task(s, videos.get(s.canonical_task_id), config, issues, info) for s in sources]
    review = [i for i in issues if i.severity in REVIEW_SEVERITIES]
    manifest = {
        "schema_version": 1,
        "kind": "rule_engine_annotation_audit",
        "audited_on": date.today().isoformat(),
        "backups": backup_list(backup_root),
        "settings": {"zone_motion_fraction_of_diagonal": config.zone_motion_fraction_of_diagonal,
                     "repeated_tag_window_frames": config.repeated_tag_window_frames},
        "counts": {"tasks": len(sources), "review_list": len(review), "info": len(info),
                   "off_pattern_videos": sum(p.on_review_list for p in patterns)},
        "zone_distribution": distribution(patterns, config),
    }
    output.mkdir(parents=True, exist_ok=True)
    write_issues(output / "issues.csv", review)
    write_issues(output / "info.csv", info)
    write_rows(output / "zone_patterns.csv", [asdict(p) for p in patterns], list(ZonePattern.__dataclass_fields__))
    (output / "audit_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "README.md").write_text(readme(manifest, patterns, review), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backup-root", type=Path, required=True, help="folder containing the CVAT backup ZIPs")
    parser.add_argument("--output", type=Path, required=True,
                        help="new run folder, e.g. annotation/reports/rule_engine_audit/2026-10-16")
    parser.add_argument("--conversion-report", type=Path, default=DEFAULT_CONVERSION_REPORT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    if not args.backup_root.is_dir():
        print(f"No audit: backup root not found: {args.backup_root}", file=sys.stderr)
        return EXIT_REFUSED
    try:
        manifest = run_audit(args.backup_root, args.output, args.conversion_report, args.config)
    except ValueError as error:
        print(f"No audit: {error}", file=sys.stderr)
        return EXIT_REFUSED
    counts = manifest["counts"]
    print(f"Audited {counts['tasks']} tasks: {counts['review_list']} review items "
          f"({counts['off_pattern_videos']} off-pattern videos), {counts['info']} information rows")
    print(f"Written to {Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
