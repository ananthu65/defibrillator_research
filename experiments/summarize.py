"""Rebuild the comparison table from authoritative per-run files after merging PRs."""
import csv
import json
from pathlib import Path
from experiments.record import ROOT, SUMMARY_FIELDS


def rebuild(root=None):
    root = Path(root) if root is not None else ROOT / "experiments"
    rows = []
    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or not (directory / "config.json").is_file():
            continue
        config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
        metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
        metadata = json.loads((directory / "run.json").read_text(encoding="utf-8"))
        rows.append({"run_id": directory.name, "task": metadata.get("task", "video_training"),
                     "status": metadata.get("status", "completed"), "model": config.get("model", ""),
                     "started_utc": metadata.get("started_utc", ""),
                     "duration_seconds": metadata.get("duration_seconds", ""),
                     "metrics_json": json.dumps(metrics, sort_keys=True, allow_nan=False)})
    path = root / "results_summary.csv"
    temporary = path.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)
    return path


if __name__ == "__main__":
    print(rebuild())
