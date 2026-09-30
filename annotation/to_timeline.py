"""Convert one task's audited CVAT point tags to the shared timeline schema."""
import argparse
import json
from pathlib import Path
from schemas.event import Event


def convert(record):
    return [Event(tag["label"], tag["timestamp_seconds"], tag["timestamp_seconds"], "annotation", 1.0,
                  camera_angle=record.get("camera_view"),
                  metadata={"task_id": record["canonical_task_id"], "participant_id": record["participant_id"],
                            "frame": tag["frame"], "confidence_kind": "human_annotation"})
            for tag in record["events"]]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/video/phase4_yolo/metadata/events.jsonl"))
    parser.add_argument("--task", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    with args.input.open(encoding="utf-8") as stream:
        records = [json.loads(line) for line in stream if line.strip()]
    matching = [r for r in records if r["canonical_task_id"] == args.task]
    if len(matching) != 1:
        parser.error("Expected exactly one matching task; do not combine unsynchronized camera views")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps([e.to_dict() for e in convert(matching[0])], indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
