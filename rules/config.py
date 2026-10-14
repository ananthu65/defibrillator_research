"""Load and validate all rule-engine configuration; every problem is a ConfigError naming the entry."""
from dataclasses import dataclass, field
import math
from pathlib import Path
import re
import yaml
from rules.errors import ConfigError
from rules.vocabulary import Vocabulary, load_vocabulary

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "configs/rules.yaml"
DEFAULT_ENGINE_PATH = "configs/rule_engine/engine.yaml"
DEFAULT_VOCABULARY_PATH = "configs/rule_engine/vocabulary.yaml"
RULE_STATUSES = ("pending", "approved")
RULE_KEYS = {"id", "title", "status", "enabled", "implementation", "same_as", "depends_on", "parameters"}
VALUE_KEYS = {"value", "approved_by", "approved_on", "date_pending", "provided_by", "provided_on", "source", "note"}
SETTING_KEYS = {"value", "placeholder", "undecided", "note"}
SOURCES = ("annotation", "video", "audio")
MODALITIES = ("video", "audio")
COVERAGE_STATUSES = ("covered", "not_covered", "unknown")
MISSING_OUTCOMES = ("fail", "unable_to_verify")
OVERALL_UNABLE_OUTCOMES = ("fail", "faculty_review")
COUNT_BOUNDS = ("exactly", "at_least", "at_most")
UNLIMITED = "unlimited"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class ClinicalValue:
    """A clinical value and its provenance. Unprovided values have value None."""
    name: str
    value: float | None = None
    approved_by: str | None = None
    approved_on: str | None = None
    provided_by: str | None = None
    provided_on: str | None = None
    source: str | None = None
    note: str | None = None          # human-readable explanation only; never interpreted
    date_pending: bool = False       # approved, but the approval date is still to be confirmed

    @property
    def approved(self):
        return self.value is not None and self.approved_by is not None


@dataclass(frozen=True)
class Setting:
    """An engineering value or team policy; placeholder/undecided values are reported as such."""
    name: str
    value: object
    placeholder: bool = False
    undecided: bool = False
    note: str | None = None


@dataclass(frozen=True)
class RuleDefinition:
    id: str
    title: str
    status: str
    enabled: bool = True
    implementation: str | None = None
    same_as: str | None = None
    depends_on: tuple[str, ...] = ()
    parameters: dict = field(default_factory=dict)

    @property
    def result_dependencies(self):
        """Rules whose results this rule needs; these alone constrain evaluation order."""
        return self.depends_on + ((self.same_as,) if self.same_as else ())


@dataclass(frozen=True)
class EngineSettings:
    confidence_thresholds: dict[str, Setting]
    settings: dict[str, Setting]
    coverage_outcomes: dict[str, Setting]
    coverage_overrides: dict[str, dict[str, Setting]] = field(default_factory=dict)  # "region:x" -> status -> outcome
    regions: dict[str, tuple[str, ...]] = field(default_factory=dict)  # region -> canonical events it governs
    expected_counts: dict[str, Setting] = field(default_factory=dict)  # canonical event -> {bound: n} | unlimited | None

    @classmethod
    def from_dict(cls, data, where="engine"):
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ConfigError(f"{where}: expected a mapping with schema_version: 1")
        expected = {"schema_version", "confidence_thresholds", "simultaneous_window_seconds",
                    "gel_minimum_gap_seconds", "placement_match_window_seconds", "assume_first_taken_is_apical",
                    "duration_tolerance_seconds", "coverage_policy", "inferred_fail_outcome",
                    "unable_to_verify_outcome", "review_anomalies", "expected_counts"}
        _exact_keys(data, expected, where)
        thresholds = _exact_keys(data["confidence_thresholds"], set(SOURCES), f"{where} confidence_thresholds")
        confidence = {s: _setting(f"confidence_thresholds.{s}", thresholds[s], where, _probability) for s in SOURCES}
        settings = {name: _setting(name, data[name], where, _nonnegative) for name in
                    ("simultaneous_window_seconds", "gel_minimum_gap_seconds", "placement_match_window_seconds",
                     "duration_tolerance_seconds")}
        settings["assume_first_taken_is_apical"] = _setting(
            "assume_first_taken_is_apical", data["assume_first_taken_is_apical"], where, _boolean)
        settings["inferred_fail_outcome"] = _setting(
            "inferred_fail_outcome", data["inferred_fail_outcome"], where, _choice(MISSING_OUTCOMES))
        settings["unable_to_verify_outcome"] = _setting(
            "unable_to_verify_outcome", data["unable_to_verify_outcome"], where, _choice(OVERALL_UNABLE_OUTCOMES))
        settings["review_anomalies"] = _setting("review_anomalies", data["review_anomalies"], where, _anomaly_list)
        policy = _exact_keys(data["coverage_policy"], {"outcomes", "by_modality", "by_source", "by_region", "regions"},
                             f"{where} coverage_policy")
        outcomes = _exact_keys(policy["outcomes"], set(COVERAGE_STATUSES), f"{where} coverage_policy.outcomes")
        coverage = {s: _setting(f"coverage_policy.outcomes.{s}", outcomes[s], where, _choice(MISSING_OUTCOMES))
                    for s in COVERAGE_STATUSES}
        regions = _regions(policy["regions"], f"{where} coverage_policy.regions")
        overrides = {}
        for kind, allowed in (("modality", MODALITIES), ("source", SOURCES), ("region", tuple(regions))):
            at = f"{where} coverage_policy.by_{kind}"
            entries = policy[f"by_{kind}"] or {}
            if not isinstance(entries, dict):
                raise ConfigError(f"{at}: expected a mapping")
            for name, statuses in entries.items():
                if name not in allowed:
                    raise ConfigError(f"{at}: unknown {kind} {name!r}; expected one of {list(allowed)}")
                if not isinstance(statuses, dict) or not statuses or set(statuses) - set(COVERAGE_STATUSES):
                    raise ConfigError(f"{at}.{name}: expected a mapping of {list(COVERAGE_STATUSES)} to outcomes")
                overrides[f"{kind}:{name}"] = {s: _setting(f"coverage_policy.by_{kind}.{name}.{s}", value, where,
                                                           _choice(MISSING_OUTCOMES)) for s, value in statuses.items()}
        counts = data["expected_counts"]
        if not isinstance(counts, dict) or not counts:
            raise ConfigError(f"{where} expected_counts: expected a mapping of canonical event -> expected count")
        expected_counts = {name: _setting(f"expected_counts.{name}", value, where, _count)
                           for name, value in counts.items()}
        return cls(confidence, settings, coverage, overrides, regions, expected_counts)

    def value(self, name):
        return self.settings[name].value

    def _all_settings(self):
        overrides = [s for statuses in self.coverage_overrides.values() for s in statuses.values()]
        return [*self.confidence_thresholds.values(), *self.settings.values(), *self.coverage_outcomes.values(),
                *overrides, *self.expected_counts.values()]

    @property
    def placeholders(self):
        return sorted(s.name for s in self._all_settings() if s.placeholder)

    @property
    def undecided(self):
        return sorted(s.name for s in self._all_settings() if s.undecided)

    def region_of(self, event_name):
        return next((region for region, events in self.regions.items() if event_name in events), None)


@dataclass(frozen=True)
class RuleEngineConfig:
    rules: tuple[RuleDefinition, ...]
    timing_limits: dict[str, ClinicalValue]
    engine: EngineSettings
    vocabulary: Vocabulary

    @classmethod
    def from_dict(cls, data, where="rules", root=ROOT):
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ConfigError(f"{where}: expected a mapping with schema_version: 1")
        rules = _rules(data.get("rules"), where)
        limits = data.get("timing_limits") or {}
        if not isinstance(limits, dict):
            raise ConfigError(f"{where} timing_limits: expected a mapping")
        timing = {name: _clinical_value(name, value, f"{where} timing_limits.{name}") for name, value in limits.items()}
        engine_path = _path(data.get("engine", DEFAULT_ENGINE_PATH), root, f"{where} engine")
        vocabulary_path = _path(data.get("vocabulary", DEFAULT_VOCABULARY_PATH), root, f"{where} vocabulary")
        engine = EngineSettings.from_dict(_load(engine_path), where=str(engine_path))
        vocabulary = load_vocabulary(vocabulary_path)
        for region, events in engine.regions.items():
            for name in events:
                if name not in vocabulary.events or vocabulary.modality(name) != "video":
                    raise ConfigError(f"{engine_path} coverage_policy.regions.{region}: {name!r} is not a "
                                      "canonical video event in the vocabulary")
        missing = sorted(set(vocabulary.events) - set(engine.expected_counts))
        unknown = sorted(set(engine.expected_counts) - set(vocabulary.events))
        if missing or unknown:
            raise ConfigError(f"{engine_path} expected_counts: every canonical event needs an expected count; "
                              f"missing {missing}, not in the vocabulary {unknown}")
        return cls(rules, timing, engine, vocabulary)

    def rule(self, rule_id):
        return next(r for r in self.rules if r.id == rule_id)

    def limit(self, name):
        """The clinical value record for name; an absent key is treated as not provided."""
        return self.timing_limits.get(name, ClinicalValue(name))

    def evaluation_order(self):
        """Display order, moved only as far as rule-result dependencies require (Kahn's algorithm)."""
        return _topological([r.id for r in self.rules], {r.id: r.result_dependencies for r in self.rules})


def load_rules_config(path=DEFAULT_PATH, root=ROOT):
    return RuleEngineConfig.from_dict(_load(Path(path)), where=str(path), root=root)


def _rules(value, where):
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{where} rules: expected a nonempty list")
    definitions, seen = [], set()
    for index, entry in enumerate(value):
        at = f"{where} rules[{index}]"
        if not isinstance(entry, dict):
            raise ConfigError(f"{at}: expected a mapping")
        unknown = set(entry) - RULE_KEYS
        if unknown:
            raise ConfigError(f"{at}: unknown keys {sorted(unknown)}")
        rule_id = entry.get("id")
        if not isinstance(rule_id, str) or not rule_id:
            raise ConfigError(f"{at}: id must be a nonempty string")
        at = f"{where} rules.{rule_id}"
        if rule_id in seen:
            raise ConfigError(f"{at}: duplicate rule ID")
        seen.add(rule_id)
        if entry.get("status") not in RULE_STATUSES:
            raise ConfigError(f"{at}: status must be one of {RULE_STATUSES}")
        implementation = entry.get("implementation")
        if implementation is not None and not re.fullmatch(r"[\w.]+:\w+", str(implementation)):
            raise ConfigError(f"{at}: implementation must be module.path:function")
        if entry.get("same_as") is not None and implementation is not None:
            raise ConfigError(f"{at}: a same_as rule reuses another rule's check and has no implementation")
        depends_on = entry.get("depends_on", [])
        if not isinstance(depends_on, list) or not all(isinstance(d, str) for d in depends_on):
            raise ConfigError(f"{at}: depends_on must be a list of rule IDs")
        if not isinstance(entry.get("parameters", {}), dict) or not isinstance(entry.get("enabled", True), bool):
            raise ConfigError(f"{at}: parameters must be a mapping and enabled a boolean")
        definitions.append(RuleDefinition(rule_id, str(entry.get("title", rule_id)), entry["status"],
                                          entry.get("enabled", True), implementation, entry.get("same_as"),
                                          tuple(depends_on), dict(entry.get("parameters", {}))))
    by_id = {r.id: r for r in definitions}
    for rule in definitions:
        for dependency in rule.result_dependencies:
            if dependency == rule.id:
                raise ConfigError(f"{where} rules.{rule.id}: depends on itself")
            if dependency not in by_id:
                raise ConfigError(f"{where} rules.{rule.id}: depends on unknown rule {dependency!r}")
        if rule.same_as and by_id[rule.same_as].same_as:
            raise ConfigError(f"{where} rules.{rule.id}: same_as must name a rule with its own check, "
                              f"not {rule.same_as} (itself same_as {by_id[rule.same_as].same_as})")
    _topological([r.id for r in definitions], {r.id: r.result_dependencies for r in definitions}, where)
    return tuple(definitions)


def _topological(order, dependencies, where="rules"):
    remaining, done, result = list(order), set(), []
    while remaining:
        ready = next((r for r in remaining if set(dependencies[r]) <= done), None)
        if ready is None:
            raise ConfigError(f"{where}: circular rule-result dependency: {_cycle(remaining, dependencies)}")
        remaining.remove(ready)
        done.add(ready)
        result.append(ready)
    return result


def _cycle(remaining, dependencies):
    """Walk dependencies among the stuck rules until one repeats; that loop is the cycle."""
    path, node = [], remaining[0]
    while node not in path:
        path.append(node)
        node = next(d for d in dependencies[node] if d in remaining)
    loop = path[path.index(node):] + [node]
    return " -> ".join(loop)


def _clinical_value(name, value, where):
    if value is None:
        return ClinicalValue(name)
    if not isinstance(value, dict):
        raise ConfigError(f"{where}: a clinical value must be null or a record with its provenance "
                          f"({sorted(VALUE_KEYS)})")
    unknown = set(value) - VALUE_KEYS
    if unknown:
        raise ConfigError(f"{where}: unknown keys {sorted(unknown)}")
    number = value.get("value")
    if number is not None and (isinstance(number, bool) or not isinstance(number, (int, float))
                               or not math.isfinite(number) or number < 0):
        raise ConfigError(f"{where}: value must be a nonnegative number or null")
    for key in ("approved_on", "provided_on"):
        if value.get(key) is not None and not (isinstance(value[key], str) and DATE.match(value[key])):
            raise ConfigError(f'{where}: {key} must be a quoted date "YYYY-MM-DD"')
    pending = value.get("date_pending", False)
    if not isinstance(pending, bool):
        raise ConfigError(f"{where}: date_pending must be true or false")
    approved_by, approved_on = value.get("approved_by"), value.get("approved_on")
    if approved_on is not None and approved_by is None:
        raise ConfigError(f"{where}: approved_on needs approved_by")
    if approved_by is not None and approved_on is None and not pending:
        raise ConfigError(f"{where}: approved_on may be null only when date_pending: true is set")
    if pending and (approved_by is None or approved_on is not None):
        raise ConfigError(f"{where}: date_pending: true needs approved_by and approved_on: null")
    if approved_by is not None and number is None:
        raise ConfigError(f"{where}: an approval needs a value")
    if number is not None and not value.get("source"):
        raise ConfigError(f"{where}: a value needs a source")
    return ClinicalValue(name, number, *(value.get(k) for k in
                                         ("approved_by", "approved_on", "provided_by", "provided_on", "source", "note")),
                         pending)


def _regions(value, where):
    if not isinstance(value, dict):
        raise ConfigError(f"{where}: expected a mapping of region -> list of canonical events")
    regions, owner = {}, {}
    for region, events in value.items():
        if not isinstance(region, str) or not region:
            raise ConfigError(f"{where}: region names must be nonempty strings")
        if not isinstance(events, list) or not events or not all(isinstance(e, str) and e for e in events):
            raise ConfigError(f"{where}.{region}: expected a nonempty list of canonical event names")
        for name in events:
            if name in owner:
                raise ConfigError(f"{where}.{region}: {name!r} is already in region {owner[name]!r}")
            owner[name] = region
        regions[region] = tuple(events)
    return regions


def _setting(name, raw, where, check):
    at = f"{where} {name}"
    if isinstance(raw, dict):
        unknown = set(raw) - SETTING_KEYS
        if unknown or "value" not in raw:
            raise ConfigError(f"{at}: expected value and optional placeholder, undecided, note")
        value, placeholder, undecided, note = raw["value"], raw.get("placeholder", False), raw.get("undecided", False), raw.get("note")
        if not isinstance(placeholder, bool) or not isinstance(undecided, bool):
            raise ConfigError(f"{at}: placeholder and undecided must be booleans")
    else:
        value, placeholder, undecided, note = raw, False, False, None
    if value is None and not undecided:
        raise ConfigError(f"{at}: value may be null only while undecided: true")
    if value is not None:
        check(value, at)
    return Setting(name, value, placeholder, undecided, None if note is None else str(note))


def _probability(value, at):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ConfigError(f"{at}: must be a number between 0 and 1")


def _nonnegative(value, at):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ConfigError(f"{at}: must be a nonnegative number")


def _anomaly_list(value, at):
    from rules.prepare import ANOMALY_CODES
    if not isinstance(value, list) or not all(v in ANOMALY_CODES for v in value) or len(set(value)) != len(value):
        raise ConfigError(f"{at}: must be a list of distinct anomaly codes from {list(ANOMALY_CODES)}")


def _count(value, at):
    if value == UNLIMITED:
        return
    bound, n = next(iter(value.items())) if isinstance(value, dict) and len(value) == 1 else (None, None)
    if bound not in COUNT_BOUNDS or isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ConfigError(f"{at}: must be {UNLIMITED} or one of {{exactly: n}}, {{at_least: n}}, {{at_most: n}} "
                          "with n a positive whole number")


def count_allows(expected, found):
    """Whether `found` confident events satisfy an expected count ({bound: n} or unlimited)."""
    if expected == UNLIMITED:
        return True
    (bound, n), = expected.items()
    return {"exactly": found == n, "at_least": found >= n, "at_most": found <= n}[bound]


def _boolean(value, at):
    if not isinstance(value, bool):
        raise ConfigError(f"{at}: must be true or false")


def _choice(options):
    def check(value, at):
        if value not in options:
            raise ConfigError(f"{at}: must be one of {options}")
    return check


def _exact_keys(value, expected, where):
    if not isinstance(value, dict):
        raise ConfigError(f"{where}: expected a mapping")
    missing, unknown = expected - set(value), set(value) - expected
    if missing or unknown:
        raise ConfigError(f"{where}: missing keys {sorted(missing)}, unknown keys {sorted(unknown)}")
    return value


def _path(value, root, where):
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{where}: expected a path relative to the repository root")
    path = (Path(root) / value).resolve()
    if not path.is_file():
        raise ConfigError(f"{where}: file not found: {value}")
    return path


def _load(path):
    try:
        with Path(path).open(encoding="utf-8") as stream:
            return yaml.safe_load(stream)
    except OSError as error:
        raise ConfigError(f"{path}: cannot read ({error.strerror})") from error
    except yaml.YAMLError as error:
        raise ConfigError(f"{path}: invalid YAML ({error})") from error
