"""Keep the rule-engine documentation consistent with the code.

- decision_flow.yaml lists every flag, anomaly and rejection code the code can raise, and nothing
  the code does not raise (planned decision points excepted).
- Every code in decision_flow.yaml is documented in anomalies.md.
- Every D-, A-, OQ- and P- ID referenced anywhere exists in its register, exactly once.
- output_contract.md (the feedback module's contract, D-070) matches the code and the report.
"""
import json
from pathlib import Path
import re
import unittest

import yaml

from pipeline.config import ROOT
from rules import checks, context, coverage, engine, outcome, policy, render, video_rules
from rules.config import load_rules_config
from rules.engine import assess
from rules.outcome import RuleOutcome
from rules.run import load_timeline

DOCS = ROOT / "docs/rule_engine"
FLOW = yaml.safe_load((DOCS / "decision_flow.yaml").read_text(encoding="utf-8"))
POINTS = FLOW["decision_points"]
KINDS = ("flags", "anomalies", "rejections", "failure_codes")
ID = re.compile(r"\b(D|A|OQ|P)-\d{3}\b")
CONTRACT = (DOCS / "output_contract.md").read_text(encoding="utf-8")
CODE_STATUSES = ("built", "planned", "interim", "undecided")


def code_sources():
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "rules").glob("*.py")))


def raised_in_code():
    source = code_sources()
    return {"rejections": set(re.findall(r'(?:TimelineError|RegistryError)\(\s*"([a-z_]+)"', source)),
            "anomalies": set(re.findall(r'Anomaly\(\s*"([a-z_]+)"', source)),
            "flags": set(coverage.FLAGS) | set(coverage.HEADER_FLAGS) | set(context.FLAGS) | set(checks.FLAGS)
                     | set(policy.FLAGS) | set(video_rules.FLAGS),
            "failure_codes": set(engine.FAILURE_CODES)
                             | set(re.findall(r'failed\(\s*"[RA]\d+",\s*"([a-z_]+)"', source))}   # rule modules


def listed_in_flow(status=None):
    found = {kind: set() for kind in KINDS}
    for point in POINTS:
        if status and point["status"] != status:
            continue
        for branch in point["branches"]:
            for kind in KINDS:
                found[kind] |= set(branch.get(kind, []))
    return found


def definitions():
    """ID -> number of times it is defined in its register."""
    defined = {}
    for prefix, file in (("D", "decisions.md"), ("A", "assumptions.md"), ("OQ", "open_questions.md")):
        for match in re.findall(rf"^#+ ({prefix}-\d{{3}})\b", (DOCS / file).read_text(encoding="utf-8"), re.M):
            defined[match] = defined.get(match, 0) + 1
    for point in POINTS:
        defined[point["id"]] = defined.get(point["id"], 0) + 1
    return defined


def referencing_files():
    return [*sorted(DOCS.glob("*.md")), DOCS / "decision_flow.yaml",
            *sorted((ROOT / "rules").glob("*.py")), *sorted((ROOT / "tests").glob("test_rule_engine_*.py"))]


class DecisionFlowMatchesCode(unittest.TestCase):
    def test_built_points_list_only_codes_the_code_raises(self):
        code, flow = raised_in_code(), listed_in_flow("built")
        for kind in KINDS:
            with self.subTest(kind=kind):
                self.assertEqual(flow[kind] - code[kind], set(), f"{kind} in decision_flow.yaml but not in code")

    def test_every_code_raised_in_code_is_in_the_flow(self):
        code, flow = raised_in_code(), listed_in_flow("built")
        for kind in KINDS:
            with self.subTest(kind=kind):
                self.assertEqual(code[kind] - flow[kind], set(), f"{kind} raised in code but missing from decision_flow.yaml")

    def test_every_listed_code_is_documented_in_anomalies_md(self):
        anomalies = (DOCS / "anomalies.md").read_text(encoding="utf-8")
        listed = set().union(*listed_in_flow().values())
        self.assertEqual({c for c in listed if f"`{c}`" not in anomalies}, set())

    def test_every_code_raised_in_code_is_documented_in_anomalies_md(self):
        anomalies = (DOCS / "anomalies.md").read_text(encoding="utf-8")
        raised = set().union(*raised_in_code().values())
        self.assertEqual({c for c in raised if f"`{c}`" not in anomalies}, set())


def contract_section(title):
    """The contract text under a heading, up to the next heading of the same or a higher level."""
    lines = CONTRACT.splitlines()
    start = next(i for i, line in enumerate(lines) if re.fullmatch(rf"(#+) {re.escape(title)}", line))
    level = len(lines[start].split(" ")[0])
    end = next((i for i in range(start + 1, len(lines))
                if re.match(rf"#{{1,{level}}} ", lines[i])), len(lines))
    return "\n".join(lines[start + 1:end])


def table_rows(text):
    """(code, second column) for every table row whose first cell is a `code`."""
    return re.findall(r"^\| `([a-z_]+)` \| ([^|]+?) \|", text, re.M)


def sample_report():
    events, header = load_timeline(ROOT / "tests/fixtures/sample_timeline.json")
    return render.report(assess(events, load_rules_config(ROOT / "configs/rules.yaml")))


def contract_example():
    return json.loads(re.search(r"```json\n(.*?)\n```", CONTRACT, re.S).group(1))


class OutputContractMatchesCode(unittest.TestCase):
    """output_contract.md is what Sanjeevan builds the feedback module against (D-070)."""

    def test_version_matches_the_report(self):
        self.assertEqual(int(re.search(r"\*\*Report version:\*\* (\d+)", CONTRACT).group(1)), render.REPORT_VERSION)
        changelog = [int(v) for v in re.findall(r"^\| (\d+) \|", contract_section("Changelog"), re.M)]
        self.assertEqual(max(changelog), render.REPORT_VERSION)

    def test_structure_table_lists_the_report_keys(self):
        keys = [code for code, _ in table_rows(contract_section("Structure"))]
        self.assertEqual(keys, list(sample_report()))

    def test_example_has_the_report_shape(self):
        example, real = contract_example(), sample_report()
        self.assertEqual(list(example), list(real))
        self.assertEqual(example["report_version"], render.REPORT_VERSION)
        self.assertEqual(example["kind"], render.REPORT_KIND)
        self.assertEqual(list(example["overall"]), list(real["overall"]))
        for rule in example["rules"]:
            with self.subTest(rule=rule["rule_id"]):
                self.assertEqual(set(rule), set(real["rules"][0]))
        self.assertEqual(set(example["timeline"]), set(real["timeline"]))
        self.assertEqual(set(example["context"]), set(real["context"]))
        self.assertEqual(set(example["configuration"]), set(real["configuration"]))

    def test_overall_results_match_the_policy(self):
        self.assertEqual({code for code, _ in table_rows(contract_section("Overall results"))}, set(policy.RESULTS))

    def test_rule_kinds_and_their_shared_status_match_the_code(self):
        rows = re.findall(r"^\| `([a-z_]+)` \| `([a-z_]+)` \|", contract_section("Rule result kinds"), re.M)
        self.assertEqual({kind for kind, _ in rows}, set(outcome.KINDS))
        for kind, status in rows:
            with self.subTest(kind=kind):
                sample = RuleOutcome("R1", kind, "reason", "missing" if kind == outcome.FAIL else None,
                                     ("e1",) if kind in outcome.PASSES else (),
                                     blocked_by="R5" if kind == outcome.NOT_EVALUABLE else None)
                self.assertEqual(sample.to_rule_result().status.value, status)

    def test_the_contract_tables_are_found(self):
        # Guard against the table parsing silently matching nothing.
        codes = {code for code, _ in table_rows(contract_section("Codes"))}
        self.assertTrue({"timing_not_checked", "duplicate_event_id", "pre_shock_pause", "unspecified"} <= codes)

    def test_every_code_has_a_status(self):
        for code, status in table_rows(contract_section("Codes")):
            with self.subTest(code=code):
                self.assertIn(status.split(" ")[0], CODE_STATUSES)

    def test_every_code_in_the_flow_or_the_code_is_in_the_contract(self):
        listed = {code for code, _ in table_rows(contract_section("Codes"))}
        everything = set().union(*listed_in_flow().values(), *raised_in_code().values())
        self.assertEqual(everything - listed, set())

    def test_every_failure_code_in_anomalies_md_is_in_the_contract(self):
        anomalies = (DOCS / "anomalies.md").read_text(encoding="utf-8")
        planned = set(re.findall(r"`([a-z_]+)`", anomalies.split("## Rule failure codes")[1]))
        listed = {code for code, _ in table_rows(contract_section("Codes"))}
        self.assertEqual(planned - listed, set())

    def test_every_contract_code_is_documented_in_anomalies_md(self):
        anomalies = (DOCS / "anomalies.md").read_text(encoding="utf-8")
        listed = {code for code, _ in table_rows(contract_section("Codes"))}
        self.assertEqual({c for c in listed if f"`{c}`" not in anomalies}, set())

    def test_built_status_matches_what_the_code_raises(self):
        raised = set().union(*raised_in_code().values())
        for code, status in table_rows(contract_section("Codes")):
            with self.subTest(code=code):
                if code in raised:
                    self.assertNotEqual(status.split(" ")[0], "planned", "raised in code, so not planned")
                else:
                    self.assertNotEqual(status.split(" ")[0], "built", "not raised in code, so not built")


class DecisionFlowShape(unittest.TestCase):
    def test_points_are_well_formed(self):
        required = {"id", "name", "stage", "status", "decides", "inputs", "branches", "config", "code",
                    "decisions", "assumptions", "open_questions"}
        for point in POINTS:
            with self.subTest(point=point.get("id")):
                self.assertEqual(required - set(point), set())
                self.assertIn(point["stage"], FLOW["stages"])
                self.assertIn(point["status"], ("built", "planned"))
                self.assertTrue(point["branches"])
                for branch in point["branches"]:
                    self.assertIn("condition", branch)
                    self.assertIn("outcome", branch)
                    self.assertEqual(set(branch) - {"condition", "outcome", "next", *KINDS}, set())

    def test_next_points_exist(self):
        ids = {p["id"] for p in POINTS}
        for point in POINTS:
            for branch in point["branches"]:
                if "next" in branch:
                    self.assertIn(branch["next"], ids, f"{point['id']} -> {branch['next']}")


class RegisterIds(unittest.TestCase):
    def test_every_id_is_defined_exactly_once(self):
        duplicated = {i: n for i, n in definitions().items() if n > 1}
        self.assertEqual(duplicated, {})

    def test_every_referenced_id_exists(self):
        defined = definitions()
        missing = {}
        for path in referencing_files():
            for match in ID.finditer(path.read_text(encoding="utf-8")):
                if match.group(0) not in defined:
                    missing.setdefault(match.group(0), []).append(path.name)
        self.assertEqual(missing, {})

    def test_open_question_summary_matches_entries(self):
        text = (DOCS / "open_questions.md").read_text(encoding="utf-8")
        summary = set(re.findall(r"^\| (OQ-\d{3}) \|", text, re.M))
        entries = set(re.findall(r"^### (OQ-\d{3})\b", text, re.M))
        self.assertEqual(summary, entries)

    def test_answered_questions_name_their_decision(self):
        text = (DOCS / "open_questions.md").read_text(encoding="utf-8")
        for block in re.split(r"^### ", text, flags=re.M)[1:]:
            if "**Status:** answered" in block:
                with self.subTest(question=block[:6]):
                    self.assertRegex(block, r"\*\*Answered:\*\* \d{4}-\d{2}-\d{2} → \*\*D-\d{3}\*\*")

    def test_the_test_finds_real_codes(self):
        # Guard against the regexes silently matching nothing.
        code = raised_in_code()
        self.assertIn("duplicate_event_id", code["rejections"])
        self.assertIn("multiple_shocks", code["anomalies"])
        self.assertIn("no_shock", code["flags"])


if __name__ == "__main__":
    unittest.main()
