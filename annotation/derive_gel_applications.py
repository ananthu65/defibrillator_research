"""Step 9d: derive per-zone gel applications from the annotated hand and zone boxes (D-111, D-112).

Used by ``export_rule_engine_records.py``, like Step 9c. Only the annotation JSON is used (D-085),
and boxes use the training geometry (``track_box_at`` then ``clip_box``, D-079).

1. **Gel phase:** from the start of the recording to the first paddle placement
   (``first_paddle_firmly_on_the_chest``, else the earliest placement derived by 9c in the same export),
   else to ``first_paddle_taken``, else to the end of the recording.
2. **Per frame** of the gel phase, the ``learner_hand`` box (it covers only the hand holding the gel
   bottle, A-024) is compared with each visible zone box. The gap is the distance between the two
   boxes (0 when they touch or overlap) relative to the frame diagonal; proximity, not overlap (A-025).
   The frame belongs to the nearest zone when its gap is at most ``gel_hand_zone_max_gap`` and the other
   visible zone is clearly further (at least ``gel_zone_nearer_ratio`` times the gap, and strictly
   further); it is ``ambiguous`` when both are about as near; otherwise it belongs to no zone.
3. **Visits:** a visit to a zone is a run of that zone's frames in which gaps of up to
   ``gel_exit_frames`` other frames (a short dip) don't start a new visit. A visit with at least
   ``gel_dwell_frames`` frames near the zone is an application; the hand needn't be still. Separate
   visits count separately; repeats are the supervisor's question (OQ-021).
4. **Could an application have been missed?** The hand is tracked only while it holds the bottle, so
   the bottle period runs from the hand box's first to its last frame in the gel phase; a frame inside
   it without a hand box is hidden. Per zone: an application -> ``gelled``; the zone visible on every
   frame of the bottle period, the hand never hidden there, and no application -> ``not_gelled``;
   otherwise -> ``unknown``. No hand box at all in the gel phase -> every zone ``unknown``, and the
   review issue ``gel_hand_not_tracked``.
5. **Tags:** each application should have a ``Gel applied`` tag within ``gel_tag_agreement_frames`` of
   the visit; disagreements are reported in gel_validation.csv/.md, never used to drop an event.
Derived events are direct evidence, flagged derived_gel_application, with the zone, method and
settings in metadata. R1 may use them only past the 9d gate (D-112).
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

from annotation.audit_cvat_backups import Issue
from annotation.build_yolo_video_dataset import clip_box, shape_box, track_box_at
from annotation.derive_paddle_placements import DATE, HEX64, _count, _distribution, _number

METHOD = "hand_near_zone_v1"
DERIVED_GEL = "derived_gel_application"
GELLED, NOT_GELLED, UNKNOWN = "gelled", "not_gelled", "unknown"
AMBIGUOUS = "ambiguous"
REVIEW_KEYS = ("reviewed_by", "reviewed_on", "export_id", "gel_settings_sha256")
SETTING_KEYS = {"hand_label", "zones", "gel_tag", "first_paddle_taken_tag", "gel_hand_zone_max_gap", "gel_dwell_frames",
                "gel_zone_nearer_ratio", "gel_exit_frames", "gel_tag_agreement_frames", "reviewed_for_r1"}
VALIDATION_COLUMNS = ["canonical_task_id", "camera_view", "zone", "gel_phase_end_frame", "gel_phase_ended_by",
                      "bottle_start_frame", "bottle_end_frame", "hidden_frames", "ambiguous_frames",
                      "zone_visible_throughout", "applications", "application_frames", "smallest_gap", "dwell_frames",
                      "gel_tags_in_phase", "tags_agreeing", "status", "reason", "disagreements"]


# ---- settings ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class GelZone:
    zone: str     # CVAT zone label
    event: str    # canonical per-zone gel event
    region: str   # engine region that carries whether gel there could have been seen (R1)


@dataclass(frozen=True)
class GelReview:
    """The 9d gate (D-112): which export, with which settings, Arnikan reviewed for R1."""
    reviewed_by: str | None = None
    reviewed_on: str | None = None
    export_id: str | None = None
    gel_settings_sha256: str | None = None


@dataclass(frozen=True)
class GelSettings:
    hand_label: str
    zones: tuple[GelZone, ...]
    gel_tag: str
    first_paddle_taken_tag: str
    first_placement_tag: str
    max_gap: float            # gel_hand_zone_max_gap, fraction of the frame diagonal
    dwell_frames: int
    nearer_ratio: float
    exit_frames: int
    tag_agreement_frames: int
    placement_settings_sha256: str   # 9c settings: the gel phase may end at a derived placement
    review: GelReview = GelReview()

    def digest(self) -> str:
        """SHA-256 of every setting that affects a derived gel event (not the review record)."""
        content = {"method": METHOD, "hand_label": self.hand_label, "zones": [vars(z) for z in self.zones],
                   "gel_tag": self.gel_tag, "first_paddle_taken_tag": self.first_paddle_taken_tag,
                   "first_placement_tag": self.first_placement_tag, "gel_hand_zone_max_gap": self.max_gap,
                   "gel_dwell_frames": self.dwell_frames, "gel_zone_nearer_ratio": self.nearer_ratio,
                   "gel_exit_frames": self.exit_frames, "gel_tag_agreement_frames": self.tag_agreement_frames,
                   "placement_settings_sha256": self.placement_settings_sha256}
        return hashlib.sha256(json.dumps(content, sort_keys=True).encode("utf-8")).hexdigest()


def load_gel_settings(data: Any, zone_labels, placements, where: str) -> GelSettings:
    if not isinstance(data, dict) or set(data) != SETTING_KEYS:
        raise ValueError(f"{where}: expected exactly the keys {sorted(SETTING_KEYS)}")
    for key in ("hand_label", "gel_tag", "first_paddle_taken_tag"):
        if not isinstance(data[key], str) or not data[key]:
            raise ValueError(f"{where}.{key}: expected a CVAT label")
    zones = data["zones"]
    if not isinstance(zones, dict) or set(zones) != set(zone_labels):
        raise ValueError(f"{where}.zones: expected each of {list(zone_labels)} -> {{event, region}}")
    rules = []
    for zone, entry in zones.items():
        if not isinstance(entry, dict) or set(entry) != {"event", "region"} or not all(
                isinstance(entry[k], str) and entry[k] for k in ("event", "region")):
            raise ValueError(f"{where}.zones.{zone}: expected {{event: <canonical event>, region: <engine region>}}")
        rules.append(GelZone(zone, entry["event"], entry["region"]))
    if len({z.event for z in rules}) != len(rules) or len({z.region for z in rules}) != len(rules):
        raise ValueError(f"{where}.zones: each zone needs its own event and region")
    ratio = _value(data["gel_zone_nearer_ratio"])
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or ratio < 1:
        raise ValueError(f"{where}.gel_zone_nearer_ratio: must be a number of at least 1")
    return GelSettings(
        data["hand_label"], tuple(rules), data["gel_tag"], data["first_paddle_taken_tag"],
        placements.first_placement_tag,
        _number(data["gel_hand_zone_max_gap"], f"{where}.gel_hand_zone_max_gap", 0, 1),
        _count(data["gel_dwell_frames"], f"{where}.gel_dwell_frames", minimum=1), float(ratio),
        _count(data["gel_exit_frames"], f"{where}.gel_exit_frames", minimum=0),
        _count(data["gel_tag_agreement_frames"], f"{where}.gel_tag_agreement_frames", minimum=0),
        placements.digest(), _review(data["reviewed_for_r1"], f"{where}.reviewed_for_r1"))


def _value(raw):
    return raw.get("value") if isinstance(raw, dict) else raw


def _review(raw, where):
    if not isinstance(raw, dict) or set(raw) != set(REVIEW_KEYS):
        raise ValueError(f"{where}: expected exactly {list(REVIEW_KEYS)}")
    values = [raw[key] for key in REVIEW_KEYS]
    if all(v is None for v in values):
        return GelReview()
    if any(v is None for v in values):
        raise ValueError(f"{where}: fill all of {list(REVIEW_KEYS)} together, or leave all null")
    if not isinstance(raw["reviewed_by"], str) or not raw["reviewed_by"].strip():
        raise ValueError(f"{where}.reviewed_by: must name the reviewer")
    if not isinstance(raw["reviewed_on"], str) or not DATE.match(raw["reviewed_on"]):
        raise ValueError(f'{where}.reviewed_on: must be a quoted date "YYYY-MM-DD"')
    for key in ("export_id", "gel_settings_sha256"):
        if not isinstance(raw[key], str) or not HEX64.match(raw[key]):
            raise ValueError(f"{where}.{key}: must be the 64-character hash from export_manifest.json")
    return GelReview(*values)


def derived_gel_approved(settings: GelSettings, manifest: dict[str, Any]) -> bool:
    """The 9d gate (D-112), for the Increment 10 adapter: approved only for the reviewed export and settings."""
    review = settings.review
    return (review.reviewed_by is not None and review.export_id == manifest.get("export_id")
            and review.gel_settings_sha256 == manifest.get("gel_settings_sha256"))


# ---- geometry ---------------------------------------------------------------------------------------

def _boxes(tracks, shapes, frame, video):
    found = []
    for track in tracks:
        box = track_box_at(track, frame)
        box = None if box is None else clip_box(box, video.width, video.height)[0]
        if box is not None:
            found.append(box)
    return found + shapes.get(frame, [])


def _shapes(source, label, video):
    shapes: dict[int, list] = {}
    for shape in source.standalone_shapes:
        if str(shape.get("label", "")) == label:
            box = shape_box(shape)
            box = None if box is None else clip_box(box, video.width, video.height)[0]
            if box is not None:
                shapes.setdefault(int(shape.get("frame", -1)), []).append(box)
    return shapes


def box_gap(a, b) -> float:
    """Distance between two boxes in pixels; 0 when they touch or overlap."""
    dx = max(0.0, b.x1 - a.x2, a.x1 - b.x2)
    dy = max(0.0, b.y1 - a.y2, a.y1 - b.y2)
    return math.hypot(dx, dy)


def _first_tag(source, label):
    frames = [int(t.get("frame", -1)) for t in source.tags if str(t.get("label", "")) == label]
    return min(frames) if frames else None


def gel_phase(source, settings: GelSettings, placement_frames=()) -> tuple[int, str]:
    """(first frame after the gel phase, what ended it). The phase is start_frame .. end - 1."""
    t1 = _first_tag(source, settings.first_placement_tag)
    if t1 is not None:
        return t1, settings.first_placement_tag
    if placement_frames:
        return min(placement_frames), "derived placement"
    taken = _first_tag(source, settings.first_paddle_taken_tag)
    if taken is not None:
        return taken, settings.first_paddle_taken_tag
    return source.stop_frame + 1, "end of recording"


def hand_frames(source, video, settings: GelSettings, end: int) -> list[int]:
    """Frames of the gel phase on which the bottle hand has a box."""
    tracks = [t for t in source.tracks if t.label == settings.hand_label]
    shapes = _shapes(source, settings.hand_label, video)
    return [f for f in range(source.start_frame, end) if _boxes(tracks, shapes, f, video)]


# ---- per video ----------------------------------------------------------------------------------------

def frame_labels(source, video, settings: GelSettings, bottle: tuple[int, int]):
    """Per frame of the bottle period: (label, gaps). label is a zone label, AMBIGUOUS, "hidden" or None."""
    diagonal = math.hypot(video.width, video.height)
    hands = [t for t in source.tracks if t.label == settings.hand_label]
    hand_shapes = _shapes(source, settings.hand_label, video)
    zone_tracks = {z.zone: [t for t in source.tracks if t.label == z.zone] for z in settings.zones}
    zone_shapes = {z.zone: _shapes(source, z.zone, video) for z in settings.zones}
    result = []
    for frame in range(bottle[0], bottle[1] + 1):
        hand = _boxes(hands, hand_shapes, frame, video)
        zones = {z: _boxes(zone_tracks[z], zone_shapes[z], frame, video) for z in zone_tracks}
        visible = {z for z, boxes in zones.items() if boxes}
        if not hand:
            result.append((frame, "hidden", {}, visible))
            continue
        gaps = {z: min(box_gap(h, b) for h in hand for b in boxes) / diagonal for z, boxes in zones.items() if boxes}
        if not gaps:
            result.append((frame, None, gaps, visible))
            continue
        nearest = min(gaps, key=lambda z: (gaps[z], z))
        near = gaps[nearest]
        others = [g for z, g in gaps.items() if z != nearest]
        if near > settings.max_gap:
            label = None
        elif others and not (min(others) > near and min(others) >= settings.nearer_ratio * near):
            label = AMBIGUOUS
        else:
            label = nearest
        result.append((frame, label, gaps, visible))
    return result


def visits(labels, zone: str, settings: GelSettings) -> list[dict[str, Any]]:
    """Visits to one zone: runs of its frames, where a dip of up to exit_frames other frames doesn't split them."""
    frames = [frame for frame, label, _, _ in labels if label == zone]
    found = []
    for frame in frames:
        if found and frame - found[-1]["end"] - 1 <= settings.exit_frames:
            found[-1]["end"] = frame
            found[-1]["dwell"] += 1
        else:
            found.append({"start": frame, "end": frame, "dwell": 1})
    for frame, label, gaps, _ in labels:
        if label == zone:
            visit = next(v for v in found if v["start"] <= frame <= v["end"])
            visit["smallest_gap"] = min(visit.get("smallest_gap", 1.0), gaps[zone])
    return found


def derive_gel(source, video, settings: GelSettings, placement_events, issues: list[Issue]):
    """(derived events, gel summary for the record, validation rows) for one video."""
    where = dict(archive=source.archive, task_path=source.task_path, canonical_task_id=source.canonical_task_id)
    end, ended_by = gel_phase(source, settings, [e["frame"] for e in placement_events])
    tags = sorted(int(t.get("frame", -1)) for t in source.tags
                  if str(t.get("label", "")) == settings.gel_tag and int(t.get("frame", -1)) < end)
    present = hand_frames(source, video, settings, end)
    phase = {"end_frame": end, "end_seconds": round(end / video.fps, 6), "ended_by": ended_by}
    if not present:
        issues.append(Issue("review", "gel_hand_not_tracked", label=settings.hand_label,
                            details=f"no {settings.hand_label} box in the gel phase (frames {source.start_frame}-"
                            f"{end - 1}); every zone's gel is unknown", **where))
        zones = [{"zone_label": z.zone, "event": z.event, "region": z.region, "status": UNKNOWN,
                  "reason": f"no {settings.hand_label} box in the gel phase", "applications": 0} for z in settings.zones]
        rows = [_row(source, z.zone, phase, None, 0, 0, None, [], None, 0, tags, 0, UNKNOWN,
                     f"no {settings.hand_label} box in the gel phase", tags and f"tags {tags} with no hand box")
                for z in settings.zones]
        return [], {"phase": phase, "bottle": None, "zones": zones}, rows
    bottle = (present[0], present[-1])
    labels = frame_labels(source, video, settings, bottle)
    hidden = sum(label == "hidden" for _, label, _, _ in labels)
    ambiguous = sum(label == AMBIGUOUS for _, label, _, _ in labels)
    window = settings.tag_agreement_frames
    events, zones, rows, agreed_tags = [], [], [], set()
    for zone in settings.zones:
        found = visits(labels, zone.zone, settings)
        applications = [v for v in found if v["dwell"] >= settings.dwell_frames]
        throughout = all(zone.zone in visible for _, _, _, visible in labels)
        gaps = [g[zone.zone] for _, _, g, _ in labels if zone.zone in g]
        if applications:
            status, reason = GELLED, ""
        elif throughout and not hidden:
            status, reason = NOT_GELLED, "zone visible and hand tracked throughout the bottle period; no application"
        else:
            reasons = ([] if throughout else ["zone not visible throughout the bottle period"]) + \
                      ([f"hand hidden on {hidden} frames of the bottle period"] if hidden else [])
            status, reason = UNKNOWN, "; ".join(reasons)
        disagreements = []
        for number, visit in enumerate(applications, start=1):
            near_tags = [t for t in tags if visit["start"] - window <= t <= visit["end"] + window]
            agreed_tags.update(near_tags)
            if not near_tags:
                disagreements.append(f"application at frame {visit['start']} has no {settings.gel_tag} tag within "
                                     f"{window} frames")
            events.append({
                "event_name": zone.event, "frame": visit["start"], "timestamp_seconds": round(visit["start"] / video.fps, 6),
                "evidence_type": "direct", "flags": [DERIVED_GEL], "method": METHOD,
                "metadata": {"zone_label": zone.zone, "hand_label": settings.hand_label, "application": number,
                             "end_frame": visit["end"], "end_seconds": round(visit["end"] / video.fps, 6),
                             "dwell_frames": visit["dwell"], "smallest_gap": round(visit.get("smallest_gap", 0.0), 4),
                             "tag_frames": near_tags, "settings_sha256": settings.digest()}})
        zones.append({"zone_label": zone.zone, "event": zone.event, "region": zone.region, "status": status,
                      "reason": reason, "applications": len(applications)})
        rows.append(_row(source, zone.zone, phase, bottle, hidden, ambiguous, throughout,
                         [v["start"] for v in applications], min(gaps) if gaps else None,
                         max((v["dwell"] for v in found), default=0), tags, 0, status, reason, disagreements))
    unmatched = [t for t in tags if t not in agreed_tags]
    for row in rows:
        row["tags_agreeing"] = len(agreed_tags)
        if unmatched:
            row["disagreements"] = "; ".join(filter(None, [row["disagreements"], f"{settings.gel_tag} tags with no "
                                                           f"derived application: {unmatched}"]))
    events.sort(key=lambda e: (e["frame"], e["event_name"]))
    for number, event in enumerate(events, start=1):
        event["id"] = f"{source.canonical_task_id}_gel_{number:03d}"
    record = {"phase": phase, "bottle": {"start_frame": bottle[0], "end_frame": bottle[1],
                                         "start_seconds": round(bottle[0] / video.fps, 6),
                                         "end_seconds": round(bottle[1] / video.fps, 6), "hidden_frames": hidden},
              "zones": zones}
    return [{"id": e.pop("id"), **e} for e in events], record, rows


def _row(source, zone, phase, bottle, hidden, ambiguous, throughout, applications, smallest, dwell, tags, agreeing,
         status, reason, disagreements):
    return {"canonical_task_id": source.canonical_task_id, "camera_view": source.camera_view, "zone": zone,
            "gel_phase_end_frame": phase["end_frame"], "gel_phase_ended_by": phase["ended_by"],
            "bottle_start_frame": "" if bottle is None else bottle[0],
            "bottle_end_frame": "" if bottle is None else bottle[1], "hidden_frames": hidden,
            "ambiguous_frames": ambiguous, "zone_visible_throughout": "" if throughout is None else throughout,
            "applications": len(applications), "application_frames": ";".join(map(str, applications)),
            "smallest_gap": "" if smallest is None else round(smallest, 4), "dwell_frames": dwell,
            "gel_tags_in_phase": ";".join(map(str, tags)), "tags_agreeing": agreeing, "status": status,
            "reason": reason, "disagreements": "; ".join(disagreements) if isinstance(disagreements, list)
            else (disagreements or "")}


# ---- validation report (the 9d gate's evidence) -------------------------------------------------------

def gel_validation_summary(rows: list[dict[str, Any]], settings: GelSettings, manifest: dict[str, Any]) -> dict[str, Any]:
    videos: dict[str, list] = {}
    for row in rows:
        videos.setdefault(row["canonical_task_id"], []).append(row)
    statuses = {s: sum(r["status"] == s for r in rows) for s in (GELLED, NOT_GELLED, UNKNOWN)}
    applications = sum(r["applications"] for r in rows)
    tags = sum(len(rs[0]["gel_tags_in_phase"].split(";")) if rs[0]["gel_tags_in_phase"] else 0 for rs in videos.values())
    agreeing = sum(rs[0]["tags_agreeing"] for rs in videos.values())
    return {
        "export_id": manifest.get("export_id"), "gel_settings_sha256": settings.digest(),
        "videos": len(videos), "zones_gelled": statuses[GELLED], "zones_not_gelled": statuses[NOT_GELLED],
        "zones_unknown": statuses[UNKNOWN], "applications": applications, "gel_tags_in_phase": tags,
        "gel_tags_agreeing": agreeing,
        "videos_with_disagreements": sum(any(r["disagreements"] for r in rs) for rs in videos.values()),
        "videos_hand_not_tracked": sum(rs[0]["bottle_start_frame"] == "" for rs in videos.values()),
        "smallest_gap": _distribution(r["smallest_gap"] for r in rows),
        "smallest_gap_of_gelled_zones": _distribution(r["smallest_gap"] for r in rows if r["status"] == GELLED),
        "dwell_frames": _distribution(r["dwell_frames"] for r in rows if r["dwell_frames"]),
        "hidden_frames": _distribution(rs[0]["hidden_frames"] for rs in videos.values()),
        "ambiguous_frames": _distribution(rs[0]["ambiguous_frames"] for rs in videos.values()),
    }


def gel_validation_markdown(summary: dict[str, Any], rows: list[dict[str, Any]], settings: GelSettings) -> str:
    lines = ["# Derived gel application validation (Step 9d)", "",
             "Evidence for the 9d gate (D-112): R1 may use derived gel applications only after Arnikan has reviewed",
             "this report and recorded its export_id and gel_settings_sha256 in annotation_export.yaml.", "",
             f"- export_id: `{summary['export_id']}`",
             f"- gel_settings_sha256: `{summary['gel_settings_sha256']}`",
             f"- Settings (placeholders): hand-zone gap <= {settings.max_gap:.0%} of the diagonal, dwell "
             f"{settings.dwell_frames} frames, nearer zone {settings.nearer_ratio}x, exit {settings.exit_frames} frames, "
             f"tag window {settings.tag_agreement_frames} frames", "",
             "| Measure | Value |", "| --- | --- |"]
    for key in ("videos", "zones_gelled", "zones_not_gelled", "zones_unknown", "applications", "gel_tags_in_phase",
                "gel_tags_agreeing", "videos_with_disagreements", "videos_hand_not_tracked", "smallest_gap",
                "smallest_gap_of_gelled_zones", "dwell_frames", "hidden_frames", "ambiguous_frames"):
        lines.append(f"| {key.replace('_', ' ')} | {summary[key]} |")
    lines += ["", "## Per video and zone", "",
              "| Video | Zone | Status | Applications (frames) | Smallest gap | Dwell | Hidden | Tags | Reason |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    lines += [f"| {r['canonical_task_id']} | {r['zone']} | {r['status']} | {r['applications']} "
              f"({r['application_frames'] or '-'}) | {r['smallest_gap']} | {r['dwell_frames']} | {r['hidden_frames']} | "
              f"{r['gel_tags_in_phase'] or '-'} | {r['reason'] or '-'} |" for r in rows]
    disagreements = [r for r in rows if r["disagreements"]]
    lines += ["", f"## Disagreements with the tags ({len(disagreements)})", "", "| Video | Zone | Disagreement |",
              "| --- | --- | --- |"]
    lines += [f"| {r['canonical_task_id']} | {r['zone']} | {r['disagreements']} |" for r in disagreements]
    return "\n".join(lines) + "\n"
