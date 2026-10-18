"""Demo of the rule engine as it stands (D-114): runs the demo scenarios and prints readable tables.

    python -m rules.demo                          # every scenario
    python -m rules.demo --scenario gel_after_placement --full    # one scenario, whole reasons
    python -m rules.demo --records data/rule_engine/annotation_export/<run>/records.jsonl

Scenarios are synthetic timelines in docs/rule_engine/demo/scenarios/ (no participant data), listed
with their expected results in scenarios.yaml. They run with configs/rule_engine/demo/rules_demo.yaml,
where the built rules are marked approved: DEMO ONLY, the rules are not approved by the supervisor,
and every report it produces says so. A scenario with `config: catalogue` runs the real
configs/rules.yaml instead.

--records also runs real interim annotation records (through the annotation adapter, with the demo
config). Those results are development data, not assessments: their reports are written only under
data/rule_engine/ (gitignored), never committed (D-084).
"""
import argparse
from datetime import date
import json
from pathlib import Path
import sys

import yaml

from rules.adapters.annotation import adapt_record, load_manifest, load_records
from rules.config import DEFAULT_PATH, ROOT, load_rules_config
from rules.coverage import TimelineHeader
from rules.engine import assess
from rules.errors import ConfigError, TimelineError
from rules.render import report
from rules.run import load_timeline

DEMO_CONFIG = ROOT / "configs/rule_engine/demo/rules_demo.yaml"
SCENARIOS = ROOT / "docs/rule_engine/demo/scenarios"
DEV_OUTPUT_ROOT = ROOT / "data/rule_engine"
REASON_WIDTH = 72   # --full prints whole reasons
SHORT = {"pass_direct": "Pass", "pass_inferred": "Pass (inferred)", "fail": "FAIL", "unable_to_verify": "Unable to Verify",
         "not_evaluable": "Not evaluable", "pending": "pending", "assumed": "assumed", "engine_error": "ENGINE ERROR"}


def load_scenarios(path=SCENARIOS / "scenarios.yaml"):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return data["scenarios"]


def run_scenario(scenario, root=SCENARIOS):
    """(report document, assessment) for one scenario."""
    config = load_rules_config(DEMO_CONFIG if scenario["config"] == "demo" else DEFAULT_PATH)
    events, header = load_timeline(root / scenario["file"])
    header = None if header is None else TimelineHeader.from_dict(header, regions=tuple(config.engine.regions))
    assessment = assess(events, config, header=header)
    return report(assessment), assessment


def differences(scenario, document):
    """Where the result differs from the scenario's expected results (empty when it matches)."""
    found = {r["rule_id"]: [r["kind"], r["failure_code"]] for r in document["rules"]}
    expected = scenario["expected"]
    problems = [f"overall {document['overall']['result']} (expected {expected['overall']})"
                for _ in [0] if document["overall"]["result"] != expected["overall"]]
    for rule_id, (kind, code) in expected["rules"].items():
        if found.get(rule_id) != [kind, code]:
            problems.append(f"{rule_id} {found.get(rule_id)} (expected {[kind, code]})")
    return problems


def _short(text, width):
    text = " ".join(str(text).split())
    return text if len(text) <= width else text[:width - 3] + "..."


def table(document, width=REASON_WIDTH):
    rows = [("Rule", "Result", "Failure code", "Flags", "Reason")]
    hidden = {"annotation_coverage_assumed"}
    for rule in document["rules"]:
        flags = ", ".join(f for f in rule["flags"] if f not in hidden)
        result = SHORT.get(rule["kind"], rule["kind"])
        if rule["blocked_by"]:
            result += f" ({rule['blocked_by']})"
        rows.append((f"{rule['rule_id']} {_short(rule['title'], 28)}", result, rule["failure_code"] or "-",
                     _short(flags, 30) or "-", _short(rule["reason"], width)))
    widths = [max(len(r[i]) for r in rows) for i in range(4)]
    lines = []
    for index, row in enumerate(rows):
        lines.append("  " + "  ".join(c.ljust(w) for c, w in zip(row[:4], widths)) + "  " + row[4])
        if index == 0:
            lines.append("  " + "  ".join("-" * w for w in widths) + "  " + "-" * 6)
    return lines


def overall_lines(document):
    overall = document["overall"]
    summary, name = overall["summary"], overall["result"].replace("_", " ")
    if summary.lower().startswith(name + ": "):
        summary = summary[len(name) + 2:]
    lines = [f"  Overall: {overall['result'].upper()} - {summary}", f"  Why: {overall['decided_by']}"]
    if overall["flags"]:
        lines.append(f"  Overall flags: {', '.join(overall['flags'])}")
    return lines


def print_scenario(number, scenario, document, out=print, width=REASON_WIDTH):
    out("")
    out(f"=== {number}. {scenario['title']}  [{scenario['id']}: {scenario['file']}, config: {scenario['config']}]")
    out(f"  Shows: {' '.join(scenario['shows'].split())}")
    if document["demo_notice"]:
        out(f"  {document['demo_notice']}")
    for line in table(document, width) + overall_lines(document):
        out(line)
    problems = differences(scenario, document)
    out("  Matches the expected result." if not problems else "  DIFFERS from the expected result: " + "; ".join(problems))
    return not problems


def run_records(records_path, output, out=print):
    """Real interim annotation records with the demo config. Development data, written only under data/rule_engine/."""
    output = Path(output).resolve()
    if output != DEV_OUTPUT_ROOT and DEV_OUTPUT_ROOT not in output.parents:
        raise ValueError(f"refusing to write outside {DEV_OUTPUT_ROOT} (gitignored): {output}")
    from annotation.export_rule_engine_records import load_config as load_export_config
    config, export_config = load_rules_config(DEMO_CONFIG), load_export_config()
    records, manifest = load_records(records_path), load_manifest(records_path)
    output.mkdir(parents=True, exist_ok=True)
    rule_ids = [r.id for r in config.rules if r.enabled]
    out("")
    out("=== DEVELOPMENT DATA: interim annotation records, run with the DEMO config (not assessments)")
    out(f"  Records: {records_path}")
    out(f"  Reports written to: {output}")
    header = ["Video", "Overall"] + rule_ids
    rows = [header]
    for record in records:
        adapted = adapt_record(record, config, export_config, manifest)
        document = report(assess(adapted.events, config, header=adapted.header))
        (output / f"{adapted.task_id}.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        kinds = {r["rule_id"]: (r["failure_code"] or SHORT.get(r["kind"], r["kind"])) for r in document["rules"]}
        rows.append([adapted.task_id, document["overall"]["result"]] + [kinds[r] for r in rule_ids])
    widths = [max(len(str(r[i])) for r in rows) for i in range(len(header))]
    for index, row in enumerate(rows):
        out("  " + "  ".join(str(c).ljust(w) for c, w in zip(row, widths)))
        if index == 0:
            out("  " + "  ".join("-" * w for w in widths))
    out(f"  {len(records)} videos. Every report is marked development_data and DEMO ONLY.")
    return len(records)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", action="append", default=[], help="only this scenario id (repeatable)")
    parser.add_argument("--records", type=Path, help="also run real interim annotation records (development data)")
    parser.add_argument("--output", type=Path, help="folder under data/rule_engine/ for the --records reports")
    parser.add_argument("--full", action="store_true", help="print whole reasons instead of shortened ones")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        scenarios = load_scenarios()
        unknown = set(args.scenario) - {s["id"] for s in scenarios}
        if unknown:
            raise ValueError(f"unknown scenario {sorted(unknown)}; expected one of {[s['id'] for s in scenarios]}")
        print("Rule engine demo. DEMO ONLY: rules not approved by the supervisor.")
        print(f"Scenarios: {SCENARIOS.relative_to(ROOT).as_posix()}/ (synthetic, no participant data)")
        matched = True
        for number, scenario in enumerate(scenarios, start=1):
            if args.scenario and scenario["id"] not in args.scenario:
                continue
            document, _ = run_scenario(scenario)
            matched = print_scenario(number, scenario, document, width=10 ** 6 if args.full else REASON_WIDTH) and matched
        if args.records:
            name = f"demo-{args.records.parent.name}-{date.today().isoformat()}"
            run_records(args.records, args.output or DEV_OUTPUT_ROOT / "demo" / name)
    except (ConfigError, TimelineError, ValueError, OSError, KeyError) as error:
        print(f"Demo stopped: {error}", file=sys.stderr)
        return 2
    return 0 if matched else 1


if __name__ == "__main__":
    sys.exit(main())
