"""Run the rule engine on one timeline file and write the JSON report.

    python -m rules.run --events tests/fixtures/sample_timeline.json
    python -m rules.run --events timeline.json --header header.json --output report.json

--events is a JSON list of shared Event records, or {"header": {...}, "events": [...]}. Events
without an event_id get one (event_000001, ... in file order); this command applies no source
offsets (pipeline.run does). A config or timeline that cannot be assessed, or a file that cannot
be read as JSON, prints the error and exits with code 2; no report is written.
"""
import argparse
import json
from pathlib import Path
import sys
from rules.config import DEFAULT_PATH, ROOT, load_rules_config
from rules.coverage import TimelineHeader
from rules.engine import assess
from rules.errors import ConfigError, TimelineError
from rules.render import report
from schemas.event import Event

DEFAULT_OUTPUT = ROOT / "data/outputs/rule_engine_report.json"
EXIT_NO_ASSESSMENT = 2


def load_timeline(path, header_path=None):
    """(events, header) from a timeline file; IDs are assigned in file order where missing."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    header = None
    if isinstance(data, dict):
        header, data = data.get("header"), data.get("events")
    if not isinstance(data, list):
        raise TimelineError("not_a_list", f"{path}: expected a list of events or {{\"events\": [...]}}")
    used = {item.get("event_id") for item in data if isinstance(item, dict)}
    events = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise TimelineError("not_an_event", f"{path}: item {index} is not an event record")
        if item.get("event_id") is None:
            identifier = f"event_{index:06d}"
            while identifier in used:
                identifier += "_"
            used.add(identifier)
            item = {**item, "event_id": identifier}
        try:
            events.append(Event.from_dict(item))
        except (TypeError, ValueError) as error:
            raise TimelineError("not_an_event", f"{path}: item {index} is not a valid event ({error})") from None
    if header_path is not None:
        header = json.loads(Path(header_path).read_text(encoding="utf-8"))
    return events, header


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--header", type=Path, help="timeline header JSON (overrides one inside --events)")
    parser.add_argument("--config", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        config = load_rules_config(args.config)
        events, header = load_timeline(args.events, args.header)
        header = None if header is None else TimelineHeader.from_dict(header, regions=tuple(config.engine.regions))
        assessment = assess(events, config, header=header)
    except (ConfigError, TimelineError, OSError, json.JSONDecodeError) as error:
        print(f"No assessment produced: {error}", file=sys.stderr)
        return EXIT_NO_ASSESSMENT
    document = report(assessment)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    overall = document["overall"]
    if document["demo_notice"]:
        print(document["demo_notice"])
    print(f"Overall: {overall['result']}{' (development data)' if document['development_data'] else ''}")
    print(f"  {overall['summary']}")
    print(f"  decided by: {overall['decided_by']}")
    for rule in document["rules"]:
        code = f" [{rule['failure_code']}]" if rule["failure_code"] else ""
        print(f"  {rule['rule_id']:<3} {rule['kind']:<17}{code} {rule['reason']}")
    print(f"Report written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
