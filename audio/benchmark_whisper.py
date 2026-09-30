"""Benchmark a local ASR model against CSV columns audio,reference (held-out data)."""
import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import re
import time
from experiments.record import record_experiment
from pipeline.config import load_yaml
from pipeline.registry import create_model


def word_errors(reference, hypothesis):
    ref = re.findall(r"\w+", reference.lower())
    hyp = re.findall(r"\w+", hypothesis.lower())
    row = list(range(len(hyp) + 1))
    for i, expected in enumerate(ref, 1):
        next_row = [i]
        for j, actual in enumerate(hyp, 1):
            next_row.append(min(next_row[-1] + 1, row[j] + 1, row[j - 1] + (expected != actual)))
        row = next_row
    return row[-1], len(ref)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/pipeline.yaml"))
    parser.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    config = load_yaml(args.config)["asr"]
    model = create_model("asr", config)
    with args.manifest.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or not all("audio" in r and "reference" in r for r in rows):
        parser.error("Manifest needs audio and reference columns and at least one row")
    metadata = {"status": "running", "started_utc": datetime.now(timezone.utc).isoformat()}
    experiment_config = {**config, "manifest": str(args.manifest)}
    record_experiment(args.name, "asr_benchmark", experiment_config, {}, metadata=metadata)
    started = time.monotonic()
    try:
        errors = words = 0
        for row in rows:
            segments = model.transcribe(args.manifest.parent / row["audio"])
            error, count = word_errors(row["reference"], " ".join(s.text for s in segments))
            errors += error
            words += count
        if not words:
            raise ValueError("Reference transcripts contain no words")
    except Exception as exc:
        metadata.update(status="failed", error=str(exc), duration_seconds=time.monotonic() - started)
        record_experiment(args.name, "asr_benchmark", experiment_config, {}, metadata=metadata, update=True)
        raise
    metadata.update(status="completed", duration_seconds=time.monotonic() - started)
    record_experiment(args.name, "asr_benchmark", experiment_config,
                      {"wer": errors / words, "word_errors": errors, "reference_words": words, "recordings": len(rows)},
                      metadata=metadata, update=True)


if __name__ == "__main__":
    main()
