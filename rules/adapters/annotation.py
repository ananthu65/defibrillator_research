"""Annotation adapter (P-001, P-030; Increment 10): exporter records -> shared Events + TimelineHeader.

    python -m rules.adapters.annotation --records data/rule_engine/annotation_export/<run>/records.jsonl \
        --output data/rule_engine/timelines/<run> [--task P01_LL ...] [--exclude P14_LS ...]

Reads ``records.jsonl`` from the rule-engine exporter (D-074), never ``events.jsonl``. Each record
becomes one timeline file in the format ``rules.run`` reads: ``{"header": ..., "events": [...]}``.

- **Events:** every tag under its CVAT name; the vocabulary maps names, and labels are never
  renamed (D-073). Source ``annotation``, confidence 1.0.
- **Header:**
  - `recording_id`, `camera_angle` and `duration_seconds` come from the record;
  - `analyses_run` is `{video: true, audio: false}`; `video: true` is a development assumption;
  - the header is flagged ``annotation_coverage_assumed``, which the engine carries onto every
    result (D-035, D-066).
- **Zone coverage per region (P-030):**
  - reviewed exception: not covered (D-082);
  - no zone track: unknown (D-074);
  - track never visible: not covered (D-080);
  - visible throughout: covered;
  - visible for part of the recording: unknown.

  The visible intervals go into the header, so a rule asking about a time window gets that
  window's coverage (D-092). The defibrillator screen is handled in exactly the same way
  (region `screen`, governing the shock on screen for R5, D-094), and so are the paddles
  (regions `apical_paddle` and `sternal_paddle`, R4's coverage of the button press, D-108).
- **Derived placements (Step 9c)** reach the engine only when ``derived_placements_approved()``
  passes for the export's ID and settings hash, and every event carries that settings hash
  (D-088). Otherwise they are withheld and counted.
- **Derived gel applications (Step 9d)** follow their own gate, ``derived_gel_approved()`` (D-112).
  Past it, the per-zone gel events are added, and each zone's gel status becomes the coverage of
  its region (`apical_gel`, `sternal_gel`): gelled or not gelled -> covered (an application there
  would have been seen), unknown -> unknown. Before it, neither is passed on, and R1 uses the
  tag-count proxy (D-113).

Exported records stay in the gitignored data folder and are never committed (D-084).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
from typing import Any

from annotation.derive_gel_applications import GELLED, NOT_GELLED, derived_gel_approved
from annotation.derive_paddle_placements import derived_placements_approved
from annotation.export_rule_engine_records import DEFAULT_CONFIG as DEFAULT_EXPORT_CONFIG, load_config as load_export_config
from rules.config import DEFAULT_PATH, ROOT, load_rules_config
from rules.coverage import ANNOTATION_COVERAGE_ASSUMED, COVERED, NOT_COVERED, UNKNOWN, TimelineHeader
from rules.errors import ConfigError, TimelineError
from schemas.event import Event

RECORD_KIND = "rule_engine_annotation_record"
SOURCE = "annotation"
EXIT_REFUSED = 2


@dataclass(frozen=True)
class ZoneCoverage:
    region: str
    zone_label: str
    status: str
    reason: str


@dataclass(frozen=True)
class AdaptedRecord:
    task_id: str
    events: tuple[Event, ...]
    header: TimelineHeader
    zones: tuple[ZoneCoverage, ...]
    derived_included: int
    derived_withheld: int
    gate: str
    gel_included: int = 0
    gel_withheld: int = 0
    gel_gate: str = "not in this export"

    def timeline(self) -> dict[str, Any]:
        """The record as a timeline file for rules.run."""
        header = asdict(self.header)
        header["visibility"] = {scope: [list(span) for span in spans] for scope, spans in header["visibility"].items()}
        header["flags"] = list(header["flags"])
        return {"header": header, "events": [e.to_dict() for e in self.events]}


ZONES = ("zone_tracks", "zone_visibility")       # record keys of the placement zones
SCREEN = ("screen_tracks", "screen_visibility")  # record keys of the defibrillator screen (D-094)
PADDLES = ("paddle_tracks", "paddle_visibility")  # record keys of the paddles (R4, D-108)


def visibility_regions(export_config, rules_config) -> list[tuple[str, str, tuple[str, str]]]:
    """(CVAT label, engine region, record keys) for each placement zone, the screen and each paddle.

    Each zone and the screen map to the engine region that governs their event (no new names,
    D-073); each paddle maps to its visibility-only region (annotation_export.yaml paddle_regions).
    """
    found = []
    for paddle in export_config.placements.paddles:
        region = rules_config.engine.region_of(paddle.event)
        if region is not None:
            found.append((paddle.zone, region, ZONES))
    region = rules_config.engine.region_of(export_config.screen_event)
    if region is not None:
        found.append((export_config.screen_label, region, SCREEN))
    for label, region in export_config.paddle_regions:
        if region in rules_config.engine.regions:
            found.append((label, region, PADDLES))
    return found


def zone_coverage(record: dict[str, Any], label: str, confirmed: set[str], keys: tuple[str, str] = ZONES):
    """(status, reason, visible intervals or None) for one zone or the screen of one recording (P-030)."""
    tracks_key, visibility_key = keys
    if label in confirmed:
        return NOT_COVERED, "reviewed exception: an annotator confirmed it was not visible (D-082)", None
    if tracks_key not in record:
        return UNKNOWN, f"not in this export ({tracks_key} missing: exported before it was added)", None
    tracks = record[tracks_key]
    if not (tracks.get(label) if isinstance(tracks, dict) else tracks):
        return UNKNOWN, "no track (D-074)", None
    spans = [z for z in record[visibility_key] if z["label"] == label]
    if not spans:
        return NOT_COVERED, "track never visible (D-080)", ()
    intervals = tuple((z["start_seconds"], z["end_seconds"]) for z in spans)
    visible = sum(z["end_frame"] - z["start_frame"] + 1 for z in spans)
    total = record["stop_frame"] - record["start_frame"] + 1
    if visible >= total:
        return COVERED, "visible throughout the recording", intervals
    return UNKNOWN, f"visible on {visible} of {total} frames; judged per time window (D-092)", intervals


def _metadata(record, frame, kind):
    return {"task_id": record["canonical_task_id"], "participant_id": record["participant_id"], "frame": frame,
            "confidence_kind": kind}


def gate_status(record: dict[str, Any], manifest: dict[str, Any] | None, export_config) -> tuple[bool, str]:
    """D-088: the export must be the reviewed one, with the reviewed settings, and every event must match them."""
    if not record["derived_events"]:
        return False, "no derived placements"
    if manifest is None:
        return False, "not approved: no export_manifest.json beside the records"
    if not derived_placements_approved(export_config.placements, manifest):
        return False, "not approved: no review recorded for this export_id and these placement settings"
    settings = manifest.get("placement_settings_sha256")
    if any(e["metadata"].get("settings_sha256") != settings for e in record["derived_events"]):
        return False, "not approved: a derived event was made with other settings than the export's"
    return True, "approved"


def gel_gate_status(record: dict[str, Any], manifest: dict[str, Any] | None, export_config) -> tuple[bool, str]:
    """D-112: the 9d gate, like the 9c one, for the export's gel settings."""
    if "gel" not in record:
        return False, "not in this export (made before exporter version 3)"
    if manifest is None:
        return False, "not approved: no export_manifest.json beside the records"
    if not derived_gel_approved(export_config.gel, manifest):
        return False, "not approved: no review recorded for this export_id and these gel settings"
    settings = manifest.get("gel_settings_sha256")
    if any(e["metadata"].get("settings_sha256") != settings for e in record["derived_gel_events"]):
        return False, "not approved: a derived gel event was made with other settings than the export's"
    return True, "approved"


def adapt_record(record: dict[str, Any], rules_config, export_config, manifest: dict[str, Any] | None = None) -> AdaptedRecord:
    if not isinstance(record, dict) or record.get("kind") != RECORD_KIND or record.get("schema_version") != 1:
        raise ValueError("not a rule-engine annotation record (kind rule_engine_annotation_record, schema_version 1)")
    task, view = record["canonical_task_id"], record["camera_view"]
    events = [Event(tag["label"], tag["timestamp_seconds"], tag["timestamp_seconds"], SOURCE, 1.0, camera_angle=view,
                    event_id=tag["id"], metadata=_metadata(record, tag["frame"], "human_annotation"))
              for tag in record["tags"]]
    approved, gate = gate_status(record, manifest, export_config)
    if approved:
        for derived in record["derived_events"]:
            metadata = {**_metadata(record, derived["frame"], "derived_from_annotation"), "derived_placement": True,
                        "flags": list(derived["flags"]), "method": derived["method"], **derived["metadata"]}
            events.append(Event(derived["event_name"], derived["timestamp_seconds"], derived["timestamp_seconds"],
                                SOURCE, 1.0, evidence_type=derived["evidence_type"], camera_angle=view,
                                event_id=derived["id"], metadata=metadata))
    gel_approved, gel_gate = gel_gate_status(record, manifest, export_config)
    gel_events = record.get("derived_gel_events", [])
    if gel_approved:
        for derived in gel_events:
            metadata = {**_metadata(record, derived["frame"], "derived_from_annotation"), "derived_gel_application": True,
                        "flags": list(derived["flags"]), "method": derived["method"], **derived["metadata"]}
            events.append(Event(derived["event_name"], derived["timestamp_seconds"], derived["timestamp_seconds"],
                                SOURCE, 1.0, evidence_type=derived["evidence_type"], camera_angle=view,
                                event_id=derived["id"], metadata=metadata))
    confirmed = export_config.confirmed_not_visible(task)
    coverage, visibility, zones = {}, {}, []
    if gel_approved:   # each zone's gel status as the coverage of its region (D-111)
        for zone in record["gel"]["zones"]:
            if zone["region"] in rules_config.engine.regions:
                status = COVERED if zone["status"] in (GELLED, NOT_GELLED) else UNKNOWN
                coverage[f"region:{zone['region']}"] = status
                zones.append(ZoneCoverage(zone["region"], zone["zone_label"], status, f"gel {zone['status']}"
                                          + (f": {zone['reason']}" if zone["reason"] else "")))
    for label, region, keys in visibility_regions(export_config, rules_config):
        status, reason, intervals = zone_coverage(record, label, confirmed, keys)
        coverage[f"region:{region}"] = status
        if intervals is not None:
            visibility[f"region:{region}"] = intervals
        zones.append(ZoneCoverage(region, label, status, reason))
    header = TimelineHeader(recording_id=task, camera_angle=view, duration_seconds=record["duration_seconds"],
                            analyses_run={"video": True, "audio": False}, coverage=coverage,
                            visibility=visibility, flags=(ANNOTATION_COVERAGE_ASSUMED,))
    count = len(record["derived_events"])
    return AdaptedRecord(task, tuple(events), header, tuple(zones), count if approved else 0,
                         0 if approved else count, gate, len(gel_events) if gel_approved else 0,
                         0 if gel_approved else len(gel_events), gel_gate)


def load_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def load_manifest(records_path: Path) -> dict[str, Any] | None:
    path = Path(records_path).parent / "export_manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--records", type=Path, required=True, help="records.jsonl from the rule-engine exporter")
    parser.add_argument("--output", type=Path, required=True, help="new folder for the timeline files")
    parser.add_argument("--task", action="append", default=[], help="only these tasks (repeatable)")
    parser.add_argument("--exclude", action="append", default=[], help="skip these tasks, e.g. unreliable ones")
    parser.add_argument("--config", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--export-config", type=Path, default=DEFAULT_EXPORT_CONFIG)
    args = parser.parse_args(argv)
    try:
        rules_config = load_rules_config(args.config)
        export_config = load_export_config(args.export_config)
        records = load_records(args.records)
        manifest = load_manifest(args.records)
        output = args.output.resolve()
        if output == ROOT / "data/video" or ROOT / "data/video" in output.parents:
            raise ValueError("refusing to write inside data/video, which the training pipeline reads")
        if output.exists() and any(output.iterdir()):
            raise ValueError(f"{output}: output folder is not empty; use a new run folder")
        selected = [r for r in records if (not args.task or r.get("canonical_task_id") in args.task)
                    and r.get("canonical_task_id") not in args.exclude]
        adapted = [adapt_record(r, rules_config, export_config, manifest) for r in selected]
    except (ConfigError, TimelineError, ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"No timelines written: {error}", file=sys.stderr)
        return EXIT_REFUSED
    output.mkdir(parents=True, exist_ok=True)
    summary = []
    for item in adapted:
        (output / f"{item.task_id}.json").write_text(json.dumps(item.timeline(), indent=2) + "\n", encoding="utf-8")
        summary.append({"task": item.task_id, "events": len(item.events), "derived_included": item.derived_included,
                        "derived_withheld": item.derived_withheld, "gate": item.gate,
                        "gel_included": item.gel_included, "gel_withheld": item.gel_withheld, "gel_gate": item.gel_gate,
                        "zones": [asdict(z) for z in item.zones]})
        zones = ", ".join(f"{z.region} {z.status}" for z in item.zones)
        print(f"{item.task_id}: {len(item.events)} events; {zones}; derived placements: {item.gate}; "
              f"derived gel: {item.gel_gate}")
    (output / "adapter_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{len(adapted)} timelines written to {output}" + (f" (excluded: {', '.join(args.exclude)})" if args.exclude else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
