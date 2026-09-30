"""Single-writer experiment records; raw recordings and checkpoints stay in data/."""
import csv
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
SUMMARY_FIELDS = ["run_id", "task", "status", "model", "started_utc", "duration_seconds", "metrics_json"]


def record_experiment(run_id, task, config, metrics, *, metadata=None, root=None, update=False, plots_from=None):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", run_id):
        raise ValueError("run_id must be a simple directory name")
    root = Path(root) if root is not None else ROOT / "experiments"
    directory = root / run_id
    if directory.exists() and not update:
        raise FileExistsError(f"Experiment already exists: {directory}; choose a new run name")
    directory.mkdir(parents=True, exist_ok=True)
    metadata = {**(metadata or {}), "task": task}
    for name, value in (("config.json", config), ("metrics.json", metrics), ("run.json", metadata)):
        path = directory / name
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(path)
    plots = directory / "plots"
    plots.mkdir(exist_ok=True)
    (plots / ".gitkeep").touch()
    if plots_from is not None:
        # Aggregate plots only: never copy train/val frame previews.
        for pattern in ("results.png", "confusion_matrix*.png", "Box*_curve.png"):
            for source in Path(plots_from).glob(pattern):
                shutil.copy2(source, plots / source.name)
    summary = root / "results_summary.csv"
    rows = []
    if summary.exists():
        with summary.open(encoding="utf-8", newline="") as stream:
            rows = [r for r in csv.DictReader(stream) if r["run_id"] != run_id]
    rows.append({"run_id": run_id, "task": task, "status": metadata.get("status", "completed"),
                 "model": config.get("model", ""), "started_utc": metadata.get("started_utc", ""),
                 "duration_seconds": metadata.get("duration_seconds", ""),
                 "metrics_json": json.dumps(metrics, sort_keys=True, allow_nan=False)})
    temporary = summary.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: r["run_id"]))
    temporary.replace(summary)
    return directory
