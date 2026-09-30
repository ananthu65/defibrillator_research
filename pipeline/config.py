"""Configuration paths are relative to the repository, including custom YAMLs."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path):
    with Path(path).open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return value


def resolve_path(value):
    return (ROOT / value).resolve()
