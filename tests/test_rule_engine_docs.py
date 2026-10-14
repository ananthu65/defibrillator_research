"""Keep the rule-engine documentation consistent with the code.

- decision_flow.yaml lists every flag, anomaly and rejection code the code can raise, and nothing
  the code does not raise (planned decision points excepted).
- Every code in decision_flow.yaml is documented in anomalies.md.
- Every D-, A-, OQ- and P- ID referenced anywhere exists in its register, exactly once.
"""
from pathlib import Path
import re
import unittest

import yaml

from pipeline.config import ROOT
from rules import checks, context, coverage, policy

DOCS = ROOT / "docs/rule_engine"
FLOW = yaml.safe_load((DOCS / "decision_flow.yaml").read_text(encoding="utf-8"))
POINTS = FLOW["decision_points"]
KINDS = ("flags", "anomalies", "rejections", "failure_codes")
ID = re.compile(r"\b(D|A|OQ|P)-\d{3}\b")


def code_sources():
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "rules").glob("*.py")))


def raised_in_code():
    source = code_sources()
    return {"rejections": set(re.findall(r'(?:TimelineError|RegistryError)\(\s*"([a-z_]+)"', source)),
            "anomalies": set(re.findall(r'Anomaly\(\s*"([a-z_]+)"', source)),
            "flags": set(coverage.FLAGS) | set(context.FLAGS) | set(checks.FLAGS) | set(policy.FLAGS)}


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
        for kind in ("flags", "anomalies", "rejections"):
            with self.subTest(kind=kind):
                self.assertEqual(flow[kind] - code[kind], set(), f"{kind} in decision_flow.yaml but not in code")
        self.assertEqual(flow["failure_codes"], set(), "built points have no rule failure codes yet")

    def test_every_code_raised_in_code_is_in_the_flow(self):
        code, flow = raised_in_code(), listed_in_flow("built")
        for kind in ("flags", "anomalies", "rejections"):
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
        self.assertIn("shock_time_from_removal", code["flags"])


if __name__ == "__main__":
    unittest.main()
