"""Step 9c: derive per-paddle placement events from the annotated paddle and zone boxes (D-081, D-086 to D-089).

Used by ``export_rule_engine_records.py``. Only the annotation JSON is used (D-085), and boxes use
the training geometry (``track_box_at`` then ``clip_box``, D-079).

Per paddle **label**, across all its tracks (D-087), every frame is classified:
  in       exactly one box of the paddle, its zone visible, and at least ``min_overlap_of_paddle`` of
           the paddle box inside the zone
  unknown  exactly one box of the paddle, but its zone not visible (A-020, D-090): neither in nor out
  out      otherwise (no paddle box, or too little overlap)
  blocked  two or more boxes of the paddle on the frame (overlapping tracks)

A placement starts at the first frame f where frames f .. f+steady_frames-1 are all ``in`` and the
paddle's centre stays within ``max_centre_motion_of_diagonal`` of its position at f. It lasts until
the paddle has been ``out`` on ``exit_frames`` frames with no ``in`` frame between them; ``unknown``
frames are skipped, so an occlusion of the zone neither starts nor ends a placement. Only after an
exit can a re-placement start.
A placement touching a blocked frame (from ``exit_frames`` before its start to its end) gives no event.

The first placements are then checked against the tags (A-019, D-086):
  T1 present, both paddles derived  the earlier must be within the window of T1; otherwise no event for either
  T1 present, one paddle derived    it must not be earlier than T1 minus the window
  T1 missing                        both derived and within simultaneous_window_seconds of each other:
                                    both kept, flagged possible_parallel_placement; otherwise no events
  T2 present                        each kept paddle's first placement must be at or before T2 plus the window
                                    (in the parallel case, both are dropped if either fails)
Derived events are direct evidence, flagged derived_placement, with the method in metadata (D-081).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any

from annotation.audit_cvat_backups import Issue
from annotation.build_yolo_video_dataset import clip_box, shape_box, track_box_at

METHOD = "paddle_in_zone_v1"
DERIVED = "derived_placement"
PARALLEL = "possible_parallel_placement"
IN, OUT, BLOCKED, UNKNOWN = "in", "out", "blocked", "unknown"
STEADY_REPORT_CAP = 50   # steady frames achieved are reported up to this many
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REVIEW_KEYS = ("reviewed_by", "reviewed_on", "export_id", "placement_settings_sha256")
SETTING_KEYS = {"paddles", "min_overlap_of_paddle", "steady_frames", "max_centre_motion_of_diagonal", "exit_frames",
                "tag_agreement_window_frames", "first_placement_tag", "both_placed_tag", "reviewed_for_r8"}
VALIDATION_COLUMNS = ["canonical_task_id", "camera_view", "paddle", "zone", "zone_visible", "t1_frame", "t2_frame",
                      "first_placement_frame", "placements", "gap_to_t1_frames", "highest_overlap",
                      "steady_frames_achieved", "centre_motion_of_diagonal", "frames_zone_not_visible",
                      "frames_overlapping_boxes", "outcome", "reason", "flags"]


# ---- settings ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class PaddleRule:
    paddle: str   # CVAT paddle label
    zone: str     # CVAT zone label
    event: str    # canonical event name


@dataclass(frozen=True)
class PlacementReview:
    """The gate (D-088): which export, with which settings, Arnikan reviewed for R8."""
    reviewed_by: str | None = None
    reviewed_on: str | None = None
    export_id: str | None = None
    placement_settings_sha256: str | None = None


@dataclass(frozen=True)
class PlacementSettings:
    paddles: tuple[PaddleRule, ...]
    min_overlap_of_paddle: float
    steady_frames: int
    max_centre_motion_of_diagonal: float
    exit_frames: int
    tag_agreement_window_frames: int
    first_placement_tag: str
    both_placed_tag: str
    simultaneous_window_seconds: float
    review: PlacementReview = PlacementReview()

    def digest(self) -> str:
        """SHA-256 of every setting that affects a derived event (not the review record)."""
        content = {"method": METHOD, "paddles": [vars(p) for p in self.paddles],
                   "min_overlap_of_paddle": self.min_overlap_of_paddle, "steady_frames": self.steady_frames,
                   "max_centre_motion_of_diagonal": self.max_centre_motion_of_diagonal,
                   "exit_frames": self.exit_frames, "tag_agreement_window_frames": self.tag_agreement_window_frames,
                   "first_placement_tag": self.first_placement_tag, "both_placed_tag": self.both_placed_tag,
                   "simultaneous_window_seconds": self.simultaneous_window_seconds}
        return hashlib.sha256(json.dumps(content, sort_keys=True).encode("utf-8")).hexdigest()


def load_placement_settings(data: Any, zone_labels, paddle_labels, simultaneous_window: float,
                            where: str) -> PlacementSettings:
    if not isinstance(data, dict) or set(data) != SETTING_KEYS:
        raise ValueError(f"{where}: expected exactly the keys {sorted(SETTING_KEYS)}")
    paddles = data["paddles"]
    if not isinstance(paddles, dict) or not paddles:
        raise ValueError(f"{where}.paddles: expected a mapping of paddle label -> {{zone, event}}")
    rules = []
    for paddle, entry in paddles.items():
        if paddle not in paddle_labels or not isinstance(entry, dict) or set(entry) != {"zone", "event"} \
                or entry["zone"] not in zone_labels or not isinstance(entry["event"], str) or not entry["event"]:
            raise ValueError(f"{where}.paddles.{paddle}: expected a paddle label from {list(paddle_labels)} with "
                             f"a zone from {list(zone_labels)} and an event name")
        rules.append(PaddleRule(paddle, entry["zone"], entry["event"]))
    overlap = _number(data["min_overlap_of_paddle"], f"{where}.min_overlap_of_paddle", 0, 1)
    motion = _number(data["max_centre_motion_of_diagonal"], f"{where}.max_centre_motion_of_diagonal", 0, 1)
    steady = _count(data["steady_frames"], f"{where}.steady_frames", minimum=1)
    exit_frames = _count(data["exit_frames"], f"{where}.exit_frames", minimum=1)
    window = _count(data["tag_agreement_window_frames"], f"{where}.tag_agreement_window_frames", minimum=0)
    for key in ("first_placement_tag", "both_placed_tag"):
        if not isinstance(data[key], str) or not data[key]:
            raise ValueError(f"{where}.{key}: expected a CVAT tag label")
    return PlacementSettings(tuple(rules), overlap, steady, motion, exit_frames, window, data["first_placement_tag"],
                             data["both_placed_tag"], float(simultaneous_window),
                             _review(data["reviewed_for_r8"], f"{where}.reviewed_for_r8"))


def _value(raw):
    return raw.get("value") if isinstance(raw, dict) else raw


def _number(raw, where, low, high):
    value = _value(raw)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low < value <= high:
        raise ValueError(f"{where}: must be a number greater than {low} and at most {high}")
    return float(value)


def _count(raw, where, minimum):
    value = _value(raw)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{where}: must be a whole number >= {minimum}")
    return value


def _review(raw, where):
    if not isinstance(raw, dict) or set(raw) != set(REVIEW_KEYS):
        raise ValueError(f"{where}: expected exactly {list(REVIEW_KEYS)}")
    values = [raw[key] for key in REVIEW_KEYS]
    if all(v is None for v in values):
        return PlacementReview()
    if any(v is None for v in values):
        raise ValueError(f"{where}: fill all of {list(REVIEW_KEYS)} together, or leave all null")
    if not isinstance(raw["reviewed_by"], str) or not raw["reviewed_by"].strip():
        raise ValueError(f"{where}.reviewed_by: must name the reviewer")
    if not isinstance(raw["reviewed_on"], str) or not DATE.match(raw["reviewed_on"]):
        raise ValueError(f'{where}.reviewed_on: must be a quoted date "YYYY-MM-DD"')
    for key in ("export_id", "placement_settings_sha256"):
        if not isinstance(raw[key], str) or not HEX64.match(raw[key]):
            raise ValueError(f"{where}.{key}: must be the 64-character hash from export_manifest.json")
    return PlacementReview(*values)


def derived_placements_approved(settings: PlacementSettings, manifest: dict[str, Any]) -> bool:
    """The gate (D-088), for the Increment 10 adapter: approved only for the reviewed export and settings."""
    review = settings.review
    return (review.reviewed_by is not None and review.export_id == manifest.get("export_id")
            and review.placement_settings_sha256 == manifest.get("placement_settings_sha256"))


# ---- per-frame states and placement episodes ---------------------------------------------------------

@dataclass(frozen=True)
class FrameState:
    frame: int
    state: str
    overlap: float | None = None
    centre: tuple[float, float] | None = None
    zone_missing: bool = False


def _box(track, frame, width, height):
    box = track_box_at(track, frame)
    return None if box is None else clip_box(box, width, height)[0]


def _inside_fraction(paddle, zone):
    width = max(0.0, min(paddle.x2, zone.x2) - max(paddle.x1, zone.x1))
    height = max(0.0, min(paddle.y2, zone.y2) - max(paddle.y1, zone.y1))
    area = paddle.width * paddle.height
    return width * height / area if area > 0 else 0.0


def frame_states(source, video, rule: PaddleRule, settings: PlacementSettings) -> list[FrameState]:
    """One state per frame for one paddle label, across all its tracks (D-087)."""
    tracks = [t for t in source.tracks if t.label == rule.paddle]
    zones = [t for t in source.tracks if t.label == rule.zone]
    shapes: dict[int, list] = {}
    for shape in source.standalone_shapes:
        if str(shape.get("label", "")) == rule.paddle:
            box = shape_box(shape)
            box = None if box is None else clip_box(box, video.width, video.height)[0]
            if box is not None:
                shapes.setdefault(int(shape.get("frame", -1)), []).append(box)
    states = []
    for frame in range(source.start_frame, source.stop_frame + 1):
        boxes = [b for b in (_box(t, frame, video.width, video.height) for t in tracks) if b is not None]
        boxes += shapes.get(frame, [])
        if len(boxes) >= 2:
            states.append(FrameState(frame, BLOCKED))
            continue
        if not boxes:
            states.append(FrameState(frame, OUT))
            continue
        paddle = boxes[0]
        centre = ((paddle.x1 + paddle.x2) / 2.0, (paddle.y1 + paddle.y2) / 2.0)
        zone_boxes = [b for b in (_box(z, frame, video.width, video.height) for z in zones) if b is not None]
        if not zone_boxes:   # the zone is not visible: unknown, not out (A-020, D-090)
            states.append(FrameState(frame, UNKNOWN, centre=centre, zone_missing=True))
            continue
        overlap = max(_inside_fraction(paddle, z) for z in zone_boxes)
        states.append(FrameState(frame, IN if overlap >= settings.min_overlap_of_paddle else OUT, overlap, centre))
    return states


def _motion(states, start, count, diagonal):
    origin = states[start].centre
    return max(math.hypot(s.centre[0] - origin[0], s.centre[1] - origin[1])
               for s in states[start:start + count]) / diagonal


def _steady_run(states, start, settings, diagonal, cap):
    """How many frames from start are in, with the centre within the allowed motion of its start."""
    if states[start].state != IN:
        return 0
    origin = states[start].centre
    limit = settings.max_centre_motion_of_diagonal * diagonal
    run = 0
    for state in states[start:start + cap]:
        if state.state != IN or math.hypot(state.centre[0] - origin[0], state.centre[1] - origin[1]) >= limit:
            break
        run += 1
    return run


def episodes(states: list[FrameState], settings: PlacementSettings, diagonal: float) -> list[dict[str, Any]]:
    """Placement episodes: start index, end index, and whether a blocked frame touches it."""
    found, index = [], 0
    while index < len(states):
        if _steady_run(states, index, settings, diagonal, settings.steady_frames) < settings.steady_frames:
            index += 1
            continue
        start, last_in, out_run, cursor, closed = index, index, 0, index, False
        while cursor < len(states):
            state = states[cursor].state
            if state == OUT:
                out_run += 1
                if out_run >= settings.exit_frames:
                    closed = True   # a real exit, not the end of the video or an occlusion
                    break
            elif state == UNKNOWN:
                pass   # neither in nor out: it doesn't end the placement or count towards an exit
            else:
                out_run = 0
                if state == IN:
                    last_in = cursor
            cursor += 1
        touched = range(max(0, start - settings.exit_frames), last_in + 1)
        found.append({"start": start, "end": last_in, "closed": closed,
                      "blocked": any(states[i].state == BLOCKED for i in touched),
                      "overlap": states[start].overlap,
                      "motion": _motion(states, start, settings.steady_frames, diagonal)})
        index = cursor + 1
    return found


def _statistics(states, settings, diagonal):
    overlaps = [s.overlap for s in states if s.overlap is not None]
    best_start, best_run = None, 0
    for index in range(len(states)):
        run = _steady_run(states, index, settings, diagonal, STEADY_REPORT_CAP)
        if run > best_run:
            best_start, best_run = index, run
    motion = None
    if best_start is not None:
        motion = _motion(states, best_start, min(settings.steady_frames, best_run), diagonal)
    return {"highest_overlap": round(max(overlaps), 4) if overlaps else None,
            "steady_frames_achieved": best_run,
            "centre_motion_of_diagonal": None if motion is None else round(motion, 4),
            "frames_zone_not_visible": sum(s.zone_missing for s in states),
            "frames_overlapping_boxes": sum(s.state == BLOCKED for s in states)}


# ---- per video: tag checks and events ---------------------------------------------------------------

def _first_tag(source, label):
    frames = [int(t.get("frame", -1)) for t in source.tags if str(t.get("label", "")) == label]
    return min(frames) if frames else None


def derive_placements(source, video, settings: PlacementSettings, issues: list[Issue]):
    """(derived events, validation rows) for one video."""
    diagonal = math.hypot(video.width, video.height)
    where = dict(archive=source.archive, task_path=source.task_path, canonical_task_id=source.canonical_task_id)
    t1 = _first_tag(source, settings.first_placement_tag)
    t2 = _first_tag(source, settings.both_placed_tag)
    window = settings.tag_agreement_window_frames
    paddles = {}
    for rule in settings.paddles:
        states = frame_states(source, video, rule, settings)
        found = episodes(states, settings, diagonal)
        paddle = {"rule": rule, "states": states, "episodes": found, "reason": "", "flags": [],
                  "zone_visible": _zone_has_box(source, rule, video), "stats": _statistics(states, settings, diagonal)}
        if not paddle["zone_visible"]:
            paddle["reason"] = "zone unknown: no visible zone track"
        elif not found:
            paddle["reason"] = "not found: the paddle never settled in its zone"
        elif found[0]["blocked"]:
            paddle["reason"] = "overlapping boxes of this paddle during its placement"
            issues.append(Issue("review", "placement_duplicate_paddle_box", label=rule.paddle,
                                frame=states[found[0]["start"]].frame, details="two or more boxes of this paddle "
                                "overlap during its placement; no event (fix the tracks: they also affect the "
                                "training labels)", **where))
        paddle["first"] = states[found[0]["start"]].frame if found and not paddle["reason"] else None
        paddles[rule.paddle] = paddle

    derived = [p for p in paddles.values() if p["first"] is not None]
    _check_tags(derived, t1, t2, window, settings, video, issues, where)
    events, rows = [], []
    for paddle in paddles.values():
        rule, states = paddle["rule"], paddle["states"]
        kept = paddle["first"] is not None and not paddle["reason"]
        if kept:
            for number, episode in enumerate(e for e in paddle["episodes"] if not e["blocked"]):
                frame = states[episode["start"]].frame
                events.append({
                    "event_name": rule.event, "frame": frame, "timestamp_seconds": round(frame / video.fps, 6),
                    "evidence_type": "direct", "flags": [DERIVED, *paddle["flags"]], "method": METHOD,
                    "metadata": {"paddle_label": rule.paddle, "zone_label": rule.zone, "placement": number + 1,
                                 # the episode's last frame in the zone, and whether it ended by a real exit
                                 # (exit_frames out of the zone) rather than at the end of the video (R6, D-104)
                                 "end_frame": states[episode["end"]].frame,
                                 "end_seconds": round(states[episode["end"]].frame / video.fps, 6),
                                 "ended_by_exit": episode["closed"],
                                 "overlap": round(episode["overlap"], 4), "steady_frames": settings.steady_frames,
                                 "centre_motion_of_diagonal": round(episode["motion"], 4),
                                 "t1_frame": t1, "t2_frame": t2, "settings_sha256": settings.digest()}})
        rows.append({"canonical_task_id": source.canonical_task_id, "camera_view": source.camera_view,
                     "paddle": rule.paddle, "zone": rule.zone, "zone_visible": paddle["zone_visible"],
                     "t1_frame": _blank(t1), "t2_frame": _blank(t2),
                     "first_placement_frame": _blank(states[paddle["episodes"][0]["start"]].frame
                                                     if paddle["episodes"] else None),
                     "placements": sum(not e["blocked"] for e in paddle["episodes"]) if kept else 0,
                     "gap_to_t1_frames": _blank(None if t1 is None or not paddle["episodes"]
                                                else states[paddle["episodes"][0]["start"]].frame - t1),
                     **{k: _blank(v) for k, v in paddle["stats"].items()},
                     "outcome": "event" if kept else "no_event", "reason": paddle["reason"],
                     "flags": ";".join(paddle["flags"])})
    events.sort(key=lambda e: (e["frame"], e["event_name"]))
    for number, event in enumerate(events, start=1):
        event["id"] = f"{source.canonical_task_id}_derived_{number:03d}"
    return [{"id": e.pop("id"), **e} for e in events], rows


def _check_tags(derived, t1, t2, window, settings, video, issues, where):
    """Apply the tag rules (A-019, D-086) to the paddles with a derived first placement."""
    def reject(paddle, reason, review=True):
        paddle["reason"] = reason
        if review:
            issues.append(Issue("review", "placement_disagrees_with_tag", label=paddle["rule"].paddle,
                                frame=paddle["first"], details=reason, **where))

    if t1 is None:
        apart = abs(derived[0]["first"] - derived[1]["first"]) / video.fps if len(derived) == 2 else None
        if apart is not None and apart <= settings.simultaneous_window_seconds:
            for paddle in derived:
                paddle["flags"].append(PARALLEL)
        else:
            for paddle in derived:
                reject(paddle, f"{settings.first_placement_tag} is not tagged, and the placements are not "
                       "within simultaneous_window_seconds of each other", review=False)
            return
    elif len(derived) == 2:
        earliest = min(p["first"] for p in derived)
        if abs(earliest - t1) > window:
            for paddle in derived:
                reject(paddle, f"the earlier placement (frame {earliest}) is {abs(earliest - t1)} frames from "
                       f"{settings.first_placement_tag} (frame {t1}); more than {window}")
            return
    elif len(derived) == 1 and derived[0]["first"] < t1 - window:
        reject(derived[0], f"placed at frame {derived[0]['first']}, before {settings.first_placement_tag} "
               f"(frame {t1}) minus {window} frames")
        return
    if t2 is not None:
        late = [p for p in derived if not p["reason"] and p["first"] > t2 + window]
        parallel = any(PARALLEL in p["flags"] for p in derived)
        for paddle in (derived if late and parallel else late):
            reject(paddle, f"placed at frame {paddle['first']}, after {settings.both_placed_tag} (frame {t2}) "
                   f"plus {window} frames")


def _zone_has_box(source, rule, video):
    zones = [t for t in source.tracks if t.label == rule.zone]
    return any(_box(z, frame, video.width, video.height) is not None
               for z in zones for frame in range(source.start_frame, source.stop_frame + 1))


def _blank(value):
    return "" if value is None else value


# ---- validation report (the gate's evidence, D-089) -----------------------------------------------------

def _distribution(values):
    values = sorted(v for v in values if v not in ("", None))
    if not values:
        return "none"
    middle = values[len(values) // 2] if len(values) % 2 else (values[len(values) // 2 - 1] + values[len(values) // 2]) / 2
    return f"min {values[0]}, median {round(middle, 4)}, max {values[-1]} (n={len(values)})"


def validation_summary(rows: list[dict[str, Any]], settings: PlacementSettings, manifest: dict[str, Any]) -> dict[str, Any]:
    videos: dict[str, list] = {}
    for row in rows:
        videos.setdefault(row["canonical_task_id"], []).append(row)
    both = sum(all(r["outcome"] == "event" for r in rs) for rs in videos.values())
    none = sum(all(r["outcome"] != "event" for r in rs) for rs in videos.values())
    two_zone = [rs for rs in videos.values() if all(r["zone_visible"] for r in rs) and rs[0]["t1_frame"] != ""
                and all(r["first_placement_frame"] != "" for r in rs)]
    agree = sum(all(r["outcome"] == "event" for r in rs) for rs in two_zone)
    gaps = [min(abs(r["gap_to_t1_frames"]) for r in rs) for rs in two_zone]
    reasons: dict[str, int] = {}
    for row in rows:
        if row["reason"]:
            key = row["reason"].split(":")[0].split(" (")[0]
            key = re.sub(r"\d+", "N", key)
            reasons[key] = reasons.get(key, 0) + 1
    return {
        "export_id": manifest.get("export_id"), "placement_settings_sha256": settings.digest(),
        "videos": len(videos), "videos_both_paddles": both, "videos_one_paddle": len(videos) - both - none,
        "videos_no_paddle": none, "events": sum(r["placements"] for r in rows),
        "videos_possible_parallel_placement": sum(any(PARALLEL in r["flags"] for r in rs) for rs in videos.values()),
        "two_zone_videos_checkable_against_t1": len(two_zone), "two_zone_videos_agreeing_with_t1": agree,
        "gap_to_t1_frames": _distribution(gaps),
        "highest_overlap": _distribution(r["highest_overlap"] for r in rows),
        "steady_frames_achieved": _distribution(r["steady_frames_achieved"] for r in rows),
        "centre_motion_of_diagonal": _distribution(r["centre_motion_of_diagonal"] for r in rows),
        "no_event_reasons": dict(sorted(reasons.items())),
    }


def validation_markdown(summary: dict[str, Any], rows: list[dict[str, Any]], settings: PlacementSettings) -> str:
    lines = ["# Derived placement validation (Step 9c)", "",
             "Evidence for the gate (D-088): R8 may use derived placements only after Arnikan has reviewed this",
             "report and recorded its export_id and placement_settings_sha256 in annotation_export.yaml.", "",
             f"- export_id: `{summary['export_id']}`",
             f"- placement_settings_sha256: `{summary['placement_settings_sha256']}`",
             f"- Settings (placeholders): overlap >= {settings.min_overlap_of_paddle}, steady {settings.steady_frames} "
             f"frames, centre motion < {settings.max_centre_motion_of_diagonal:.0%} of the diagonal, exit "
             f"{settings.exit_frames} frames, tag window {settings.tag_agreement_window_frames} frames, parallel "
             f"window {settings.simultaneous_window_seconds} s", "",
             "| Measure | Value |", "| --- | --- |"]
    for key in ("videos", "videos_both_paddles", "videos_one_paddle", "videos_no_paddle", "events",
                "videos_possible_parallel_placement", "two_zone_videos_checkable_against_t1",
                "two_zone_videos_agreeing_with_t1", "gap_to_t1_frames", "highest_overlap", "steady_frames_achieved",
                "centre_motion_of_diagonal"):
        lines.append(f"| {key.replace('_', ' ')} | {summary[key]} |")
    lines += ["", "## No-event reasons", "", "| Reason | Paddles |", "| --- | ---: |"]
    lines += [f"| {reason} | {count} |" for reason, count in summary["no_event_reasons"].items()]
    disagreements = [r for r in rows if "frames from" in r["reason"] or "minus" in r["reason"] or "plus" in r["reason"]]
    lines += ["", f"## Disagreements with the tags ({len(disagreements)})", "", "| Video | Paddle | Reason |",
              "| --- | --- | --- |"]
    lines += [f"| {r['canonical_task_id']} | {r['paddle']} | {r['reason']} |" for r in disagreements]
    parallel = [r for r in rows if PARALLEL in r["flags"]]
    lines += ["", f"## Possible parallel placements ({len({r['canonical_task_id'] for r in parallel})} videos)", "",
              "| Video | Paddle | First placement frame |", "| --- | --- | --- |"]
    lines += [f"| {r['canonical_task_id']} | {r['paddle']} | {r['first_placement_frame']} |" for r in parallel]
    return "\n".join(lines) + "\n"
