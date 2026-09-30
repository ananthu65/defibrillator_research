"""Run from the repository root: python -m pipeline.run --events <timeline.json>."""
import argparse
import json
from dataclasses import replace
from pathlib import Path
import tempfile
from audio.commands.detect import detect_commands
from feedback.generate import generate
from pipeline.config import ROOT, load_yaml, resolve_path
from pipeline.merge_timeline import merge_timeline
from pipeline.registry import create_model
from rules.engine import evaluate
from schemas.event import Event


def assess(config, *, events=None, video=None, audio=None):
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported pipeline configuration")
    streams = [] if events is None else [events]
    catalog = load_yaml(resolve_path(config.get("models", "configs/models.yaml")))
    for kind, input_path in (("video", video), ("asr", audio), ("charging_sound", audio)):
        branch = config.get(kind, {})
        if not branch.get("enabled", False):
            continue
        if input_path is None:
            raise ValueError(f"{kind} is enabled but its input file was not supplied")
        model = create_model(kind, branch, catalog=catalog)
        if kind == "asr":
            streams.append(detect_commands(model.transcribe(input_path), config.get("commands", {})))
        else:
            observations = model.detect(input_path)
            if kind == "video":
                observations = [replace(e, camera_angle=config.get("camera_angle")) for e in observations]
            streams.append(observations)
    if not streams:
        raise ValueError("Supply --events or enable a model branch and supply its input")
    timeline = merge_timeline(*streams, offsets=config.get("offsets"))
    rules_config = load_yaml(resolve_path(config["rules"]))
    results = evaluate(timeline, rules_config)
    templates = load_yaml(resolve_path(config.get("feedback_templates", "feedback/templates.yaml")))
    return {"schema_version": 1, "assessment_status": "development_scaffold",
            "events": [e.to_dict() for e in timeline],
            "rules": [r.to_dict() for r in results], "feedback": generate(results, templates),
            "configuration": {"pipeline": config, "models": catalog, "rules": rules_config}}


def assess_recording(config, *, events=None, video=None, audio=None):
    """Extract audio when needed; source offsets remain explicit in config."""
    needs_audio = any(config.get(kind, {}).get("enabled", False) for kind in ("asr", "charging_sound"))
    if needs_audio and audio is None and video is not None:
        from audio.extract_audio import extract_track
        with tempfile.TemporaryDirectory(prefix="arts-audio-") as directory:
            extracted = extract_track(Path(video), Path(directory) / "audio.wav")
            return assess(config, events=events, video=video, audio=extracted)
    return assess(config, events=events, video=video, audio=audio)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/pipeline.yaml")
    parser.add_argument("--events", type=Path)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/outputs/assessment.json")
    args = parser.parse_args(argv)
    events = None
    if args.events is not None:
        events = [Event.from_dict(e) for e in json.loads(args.events.read_text(encoding="utf-8"))]
    report = assess_recording(load_yaml(args.config), events=events, video=args.video, audio=args.audio)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Development report written to {args.output}; clinical rules are pending.")


if __name__ == "__main__":
    main()
