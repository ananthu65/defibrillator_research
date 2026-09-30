"""Train an MFCC/random-forest baseline using frozen participant splits."""
import argparse
import csv
from datetime import datetime, timezone
import math
from pathlib import Path
import time
from audio.charging_sound.features import extract_windows
from audio.charging_sound.predict import windows_to_events
from audio.charging_sound.evaluate import event_metrics
from experiments.record import record_experiment


def read_labels(path):
    """Audacity TSV: start, end, charging. Entire recording must be reviewed."""
    intervals = []
    with Path(path).open(encoding="utf-8", newline="") as stream:
        for row in csv.reader(stream, delimiter="\t"):
            if not row:
                continue
            if len(row) != 3 or row[2].strip().lower() != "charging":
                raise ValueError("Label rows must be start<TAB>end<TAB>charging")
            start, end = float(row[0]), float(row[1])
            if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end:
                raise ValueError("Invalid charging interval")
            intervals.append((start, end))
    intervals.sort()
    if any(a[1] > b[0] for a, b in zip(intervals, intervals[1:])):
        raise ValueError("Charging intervals must not overlap")
    return intervals


def participant_splits(directory):
    assignments = {}
    for split in ("train", "val", "test"):
        participants = (Path(directory) / f"{split}_sets.txt").read_text(encoding="utf-8").split()
        for participant in participants:
            if participant in assignments:
                raise ValueError(f"Participant appears more than once in split lists: {participant}")
            assignments[participant] = split
    return assignments


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, help="CSV: participant_id,audio,labels; paths relative to CSV")
    parser.add_argument("--splits", type=Path, default=Path("data/splits/phase3"))
    parser.add_argument("--model-output", type=Path, default=Path("data/weights/audio/charging_rf.joblib"))
    parser.add_argument("--name", required=True)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--min-windows", type=int, default=3)
    args = parser.parse_args(argv)
    if args.model_output.exists():
        parser.error("Model output already exists; choose a new path")
    if not 0 <= args.threshold <= 1 or args.min_windows < 1:
        parser.error("Invalid threshold or minimum window count")
    import joblib
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    assignments = participant_splits(args.splits)
    with args.manifest.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or not all({"participant_id", "audio", "labels"} <= r.keys() for r in rows):
        parser.error("Manifest must contain participant_id,audio,labels")
    train_x, train_y, validation = [], [], []
    seen_audio = set()
    for row in rows:
        participant = row["participant_id"]
        if participant not in assignments:
            raise ValueError(f"Unknown participant: {participant}")
        audio = (args.manifest.parent / row["audio"]).resolve()
        if audio in seen_audio:
            raise ValueError(f"Recording appears more than once: {audio}")
        seen_audio.add(audio)
        if assignments[participant] == "test":
            continue  # Do not read test audio or labels during development.
        truth = read_labels(args.manifest.parent / row["labels"])
        starts, features = extract_windows(audio)
        if truth and truth[-1][1] > starts[-1] + 1.5:
            raise ValueError(f"Label extends beyond the recording: {audio}")
        labels = [int(sum(max(0, min(t + 1, end) - max(t, start)) for start, end in truth) >= 0.5) for t in starts]
        if assignments[participant] == "train":
            train_x.extend(features)
            train_y.extend(labels)
        else:
            validation.append((starts, features, truth))
    if set(train_y) != {0, 1} or not validation:
        raise ValueError("Need both classes in training and at least one validation recording")
    config = {"model": "mfcc_rf", "seed": 42, "trees": 200, "window_seconds": 1.0, "hop_seconds": 0.5,
              "manifest": str(args.manifest), "splits": str(args.splits), "threshold": args.threshold,
              "min_windows": args.min_windows, "model_output": str(args.model_output)}
    metadata = {"status": "running", "started_utc": datetime.now(timezone.utc).isoformat()}
    record_experiment(args.name, "charging_sound", config, {}, metadata=metadata)
    started = time.monotonic()
    try:
        model = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced", n_jobs=-1)
        model.fit(np.asarray(train_x), train_y)
        totals = {"true_positives": 0, "false_positives": 0, "false_negatives": 0}
        errors = []
        for starts, features, truth in validation:
            probabilities = model.predict_proba(features)[:, list(model.classes_).index(1)]
            events = windows_to_events(starts, probabilities, args.threshold, args.min_windows)
            result = event_metrics(events, truth)
            for key in totals:
                totals[key] += result[key]
            errors.extend(result["start_errors_seconds"])
        tp, fp, fn = totals["true_positives"], totals["false_positives"], totals["false_negatives"]
        metrics = {**totals, "event_recall": tp / (tp + fn) if tp + fn else None,
                   "event_precision": tp / (tp + fp) if tp + fp else None,
                   "mean_start_error_seconds": sum(errors) / len(errors) if errors else None,
                   "validation_recordings": len(validation), "train_windows": len(train_y), "matching_iou": 0.1}
        args.model_output.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"feature_version": "mfcc26_16k_v1", "model": model, "config": config}, args.model_output)
    except Exception as exc:
        metadata.update(status="failed", error=str(exc), duration_seconds=time.monotonic() - started)
        record_experiment(args.name, "charging_sound", config, {}, metadata=metadata, update=True)
        raise
    metadata.update(status="completed", duration_seconds=time.monotonic() - started)
    record_experiment(args.name, "charging_sound", config, metrics, metadata=metadata, update=True)
    print(f"Saved {args.model_output}; validation metrics are in experiments/{args.name}")


if __name__ == "__main__":
    main()
