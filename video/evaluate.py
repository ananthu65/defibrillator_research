"""Evaluate a local YOLO/RT-DETR checkpoint on validation data by default."""
import argparse
from datetime import datetime, timezone
import time
from pathlib import Path
from experiments.record import record_experiment
from pipeline.config import resolve_path
from video.train import prepare_private_environment, serializable_metrics


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--model", choices=("yolo", "rtdetr"), default="yolo")
    parser.add_argument("--split", choices=("val", "test"), default="val")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args(argv)
    if not args.weights.is_file() or not args.data.is_file():
        parser.error("Both weights and dataset YAML must exist locally")
    prepare_private_environment(resolve_path("."))
    from ultralytics import YOLO, RTDETR
    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    metadata = {"status": "running", "started_utc": datetime.now(timezone.utc).isoformat()}
    record_experiment(args.name, "video_evaluation", config, {}, metadata=metadata)
    started = time.monotonic()
    try:
        model = (YOLO if args.model == "yolo" else RTDETR)(str(args.weights.resolve()))
        result = model.val(data=str(args.data.resolve()), split=args.split, device=args.device,
                           project=str(resolve_path("data/runs/video/evaluation")), name=args.name, exist_ok=False)
    except Exception as exc:
        metadata.update(status="failed", error=str(exc), duration_seconds=time.monotonic() - started)
        record_experiment(args.name, "video_evaluation", config, {}, metadata=metadata, update=True)
        raise
    metadata.update(status="completed", duration_seconds=time.monotonic() - started)
    record_experiment(args.name, "video_evaluation", config, serializable_metrics(result),
                      metadata=metadata, update=True, plots_from=result.save_dir)


if __name__ == "__main__":
    main()
