#!/usr/bin/env python3
"""Run a reproducible, private local Ultralytics YOLO training experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_CONFIG_KEYS = {
    "name",
    "model",
    "data",
    "epochs",
    "imgsz",
    "batch",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a local YOLO detector.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/phase5/yolov8n_smoke.json"),
        help="Tracked experiment configuration.",
    )
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = sorted(REQUIRED_CONFIG_KEYS - data.keys())
    if missing:
        raise ValueError(f"Training config is missing keys: {missing}")
    if int(data["epochs"]) < 1:
        raise ValueError("epochs must be positive.")
    if int(data["imgsz"]) < 32:
        raise ValueError("imgsz must be at least 32.")
    if int(data["batch"]) < 1:
        raise ValueError("batch must be positive.")
    if Path(str(data["data"])).suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError("data must point to a YAML file.")
    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def prepare_private_environment(repo_root: Path) -> None:
    config_parent = repo_root / "runs" / "ultralytics_config"
    (config_parent / "Ultralytics").mkdir(parents=True, exist_ok=True)
    os.environ["YOLO_CONFIG_DIR"] = str(config_parent)
    os.environ["YOLO_OFFLINE"] = "true"
    os.environ.setdefault("MPLBACKEND", "Agg")


def serializable_metrics(results: Any) -> dict[str, float]:
    output: dict[str, float] = {}
    for key, value in getattr(results, "results_dict", {}).items():
        try:
            output[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return output


def run(config_path: Path) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    config = load_config(config_path)
    data_path = (repo_root / str(config["data"])).resolve()
    model_path = (repo_root / str(config["model"])).resolve()
    if not data_path.is_file():
        raise FileNotFoundError(f"Dataset YAML does not exist: {data_path}")
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Pretrained model does not exist: {model_path}. "
            "Download it before offline training."
        )

    prepare_private_environment(repo_root)
    import torch
    import ultralytics
    from ultralytics import YOLO, settings

    settings.update(
        {
            "sync": False,
            "hub": False,
            "clearml": False,
            "comet": False,
            "dvc": False,
            "mlflow": False,
            "neptune": False,
            "raytune": False,
            "wandb": False,
            "vscode_msg": False,
        }
    )
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; refusing an accidental CPU run.")

    run_name = str(config["name"])
    report_path = repo_root / "reports" / "phase5" / f"{run_name}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    project_path = repo_root / "runs" / "phase5"
    started = datetime.now(timezone.utc)
    torch.cuda.reset_peak_memory_stats()
    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "running",
        "experiment": run_name,
        "preliminary": True,
        "config": {
            key: value
            for key, value in config.items()
            if key not in {"project"}
        },
        "environment": {
            "python": sys.version.split()[0],
            "torch": torch.__version__,
            "cuda_runtime": torch.version.cuda,
            "ultralytics": ultralytics.__version__,
            "gpu": torch.cuda.get_device_name(0),
            "gpu_total_mib": round(
                torch.cuda.get_device_properties(0).total_memory / 1024 / 1024
            ),
        },
        "reproducibility": {
            "git_commit_at_start": git_commit(repo_root),
            "config_sha256": sha256_file(config_path),
            "dataset_yaml_sha256": sha256_file(data_path),
        },
        "started_utc": started.isoformat(),
    }
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    train_args = {
        "data": str(data_path),
        "epochs": int(config["epochs"]),
        "imgsz": int(config["imgsz"]),
        "batch": int(config["batch"]),
        "device": 0,
        "workers": int(config.get("workers", 0)),
        "cache": bool(config.get("cache", False)),
        "amp": bool(config.get("amp", True)),
        "seed": int(config.get("seed", 42)),
        "deterministic": bool(config.get("deterministic", True)),
        "project": str(project_path),
        "name": run_name,
        "exist_ok": False,
        "plots": bool(config.get("plots", True)),
        "verbose": True,
    }
    if "patience" in config:
        train_args["patience"] = int(config["patience"])
    if "optimizer" in config:
        train_args["optimizer"] = str(config["optimizer"])

    started_clock = time.monotonic()
    try:
        results = YOLO(str(model_path)).train(**train_args)
    except Exception as exc:
        report.update(
            {
                "status": "failed",
                "duration_seconds": round(time.monotonic() - started_clock, 2),
                "error_type": type(exc).__name__,
                "error": str(exc).replace(str(repo_root), "<repo>"),
                "peak_gpu_memory_mib": round(
                    torch.cuda.max_memory_allocated() / 1024 / 1024, 1
                ),
            }
        )
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        raise

    report.update(
        {
            "status": "completed",
            "duration_seconds": round(time.monotonic() - started_clock, 2),
            "completed_utc": datetime.now(timezone.utc).isoformat(),
            "metrics": serializable_metrics(results),
            "peak_gpu_memory_mib": round(
                torch.cuda.max_memory_allocated() / 1024 / 1024, 1
            ),
            "artifacts": f"runs/phase5/{run_name}",
        }
    )
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = run(args.config)
    except (FileNotFoundError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        f"Training {report['status']}: {report['experiment']} in "
        f"{report['duration_seconds']:.1f}s; "
        f"peak GPU memory {report['peak_gpu_memory_mib']:.1f} MiB."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
