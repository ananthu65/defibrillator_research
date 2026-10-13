"""Coverage: could the evidence for an event have been observed, and what does "missing" then mean?

Rules never decide what a missing event means. They ask Coverage.missing(event_name), which
returns the outcome from the single configurable coverage policy (engine.yaml: coverage_policy).

Coverage status of an event (most specific first):
  1. region   - header.coverage["region:<r>"], for events governed by a region (e.g. apical_zone)
  2. source   - header.coverage["source:<s>"], for the source that produced the event's modality
  3. modality - header.coverage["modality:<m>"], else header.analyses_run[<m>]
                (analysis ran -> covered; did not run -> not_covered)
  No header at all, or nothing stated -> unknown.

Coverage is per recording for now (decided 2026-10-13: no time windows yet). status() and
missing() already receive the event name plus an optional `window=(start, end)` in which the rule
expected the event, so time-windowed coverage can be added later inside this file without
changing any rule. The window is currently accepted and ignored.
"""
from dataclasses import dataclass, field
import math
from rules.errors import TimelineError

COVERED, NOT_COVERED, UNKNOWN = "covered", "not_covered", "unknown"
STATUSES = (COVERED, NOT_COVERED, UNKNOWN)
MODALITIES = ("video", "audio")
SOURCES = ("annotation", "video", "audio")
LOW_CONFIDENCE_FLAG = "low_confidence_evidence"
UNDECIDED_FLAG = "coverage_policy_undecided"
HEADER_KEYS = {"recording_id", "camera_angle", "duration_seconds", "analyses_run", "coverage"}


@dataclass(frozen=True)
class TimelineHeader:
    """What upstream says about the recording (upstream_requirements.md, "Timeline header")."""
    recording_id: str | None = None
    camera_angle: str | None = None
    duration_seconds: float | None = None
    analyses_run: dict[str, bool] = field(default_factory=dict)  # modality -> did the analysis run?
    coverage: dict[str, str] = field(default_factory=dict)       # "region:apical_zone" -> status

    @classmethod
    def from_dict(cls, data, regions=()):
        def bad(message):
            return TimelineError("invalid_header", f"timeline header: {message}")
        if not isinstance(data, dict):
            raise bad("expected a mapping")
        if set(data) - HEADER_KEYS:
            raise bad(f"unknown keys {sorted(set(data) - HEADER_KEYS)}")
        for key in ("recording_id", "camera_angle"):
            if data.get(key) is not None and (not isinstance(data[key], str) or not data[key].strip()):
                raise bad(f"{key} must be a nonempty string or null")
        duration = data.get("duration_seconds")
        if duration is not None and (isinstance(duration, bool) or not isinstance(duration, (int, float))
                                     or not math.isfinite(duration) or duration <= 0):
            raise bad("duration_seconds must be a positive number or null")
        analyses = data.get("analyses_run") or {}
        if not isinstance(analyses, dict) or set(analyses) - set(MODALITIES) or \
                not all(isinstance(v, bool) for v in analyses.values()):
            raise bad(f"analyses_run must map {list(MODALITIES)} to true/false")
        coverage = data.get("coverage") or {}
        if not isinstance(coverage, dict):
            raise bad("coverage must be a mapping of scope to status")
        allowed = {f"modality:{m}" for m in MODALITIES} | {f"source:{s}" for s in SOURCES} | \
                  {f"region:{r}" for r in regions}
        for scope, status in coverage.items():
            if scope not in allowed:
                raise bad(f"unknown coverage scope {scope!r}; expected one of {sorted(allowed)}")
            if status not in STATUSES:
                raise bad(f"coverage[{scope!r}] must be one of {list(STATUSES)}")
        return cls(data.get("recording_id"), data.get("camera_angle"), duration, dict(analyses), dict(coverage))


@dataclass(frozen=True)
class CoverageStatus:
    status: str          # covered | not_covered | unknown
    scope: str | None    # e.g. "region:apical_zone"; None when nothing is known
    basis: str           # where the status came from, for the report


@dataclass(frozen=True)
class MissingOutcome:
    """What a missing required event means. Rules turn this into their result."""
    event_name: str
    outcome: str                     # fail | unable_to_verify
    coverage: CoverageStatus
    decided_by: str                  # the policy setting (or fixed rule) that chose the outcome
    flags: tuple[str, ...] = ()
    low_confidence_event_ids: tuple[str, ...] = ()


class Coverage:
    """Coverage for one prepared timeline; computed once and shared by all rules."""

    def __init__(self, prepared, config, header=None):
        self.prepared, self.config, self.header = prepared, config, header
        self._sources = _sources_by_modality(prepared, config.vocabulary)
        if header is not None:
            _check_header(header, prepared, config.vocabulary, config.engine.value("duration_tolerance_seconds"))

    def scopes(self, event_name):
        """Scopes that apply to an event, most specific first."""
        modality = self.config.vocabulary.modality(event_name)
        region = self.config.engine.region_of(event_name)
        source = self._sources[modality] if len(self._sources[modality]) == 1 else ()
        return ([f"region:{region}"] if region else []) + [f"source:{s}" for s in source] + [f"modality:{modality}"]

    def status(self, event_name, window=None):
        """Coverage of event_name; `window` (start, end) is reserved for time-windowed coverage."""
        _check_window(window)
        if self.header is None:
            return CoverageStatus(UNKNOWN, None, "no timeline header")
        for scope in self.scopes(event_name):
            if scope in self.header.coverage:
                return CoverageStatus(self.header.coverage[scope], scope, "header.coverage")
            kind, name = scope.split(":", 1)
            if kind == "modality" and name in self.header.analyses_run:
                ran = self.header.analyses_run[name]
                return CoverageStatus(COVERED if ran else NOT_COVERED, scope, "header.analyses_run")
        return CoverageStatus(UNKNOWN, None, "not stated in timeline header")

    def missing(self, event_name, window=None):
        """Outcome for a required event that is absent from the usable evidence."""
        coverage = self.status(event_name, window)
        low = tuple(e.event_id for e in self.prepared.excluded_named(event_name))
        if low:  # low confidence is not absence: never Fail
            return MissingOutcome(event_name, "unable_to_verify", coverage, "low confidence is not absence",
                                  (LOW_CONFIDENCE_FLAG,), low)
        setting = self._policy(event_name, coverage.status)
        flags = (UNDECIDED_FLAG,) if setting.undecided else ()
        return MissingOutcome(event_name, setting.value, coverage, setting.name, flags)

    def _policy(self, event_name, status):
        overrides = self.config.engine.coverage_overrides
        for scope in self.scopes(event_name):
            if status in overrides.get(scope, {}):
                return overrides[scope][status]
        return self.config.engine.coverage_outcomes[status]


def _check_window(window):
    if window is None:
        return
    if not (isinstance(window, tuple) and len(window) == 2 and
            all(isinstance(t, (int, float)) and not isinstance(t, bool) and math.isfinite(t) for t in window)
            and 0 <= window[0] <= window[1]):
        raise ValueError(f"window must be (start, end) seconds with 0 <= start <= end, got {window!r}")


def _sources_by_modality(prepared, vocabulary):
    found = {m: set() for m in MODALITIES}
    for item in [*prepared.events, *prepared.excluded]:
        if item.event_name in vocabulary.events:
            found[vocabulary.modality(item.event_name)].add(item.source)
    return {m: tuple(sorted(s)) for m, s in found.items()}


def _check_header(header, prepared, vocabulary, tolerance):
    def mismatch(message):
        return TimelineError("header_mismatch", f"timeline header does not match its events: {message}")
    cameras = {e.camera_angle for e in prepared.events if e.camera_angle is not None}
    if header.camera_angle is not None and cameras - {header.camera_angle}:
        raise mismatch(f"header camera_angle {header.camera_angle!r}, events {sorted(cameras)}")
    tasks = {str(e.metadata["task_id"]) for e in prepared.events if "task_id" in e.metadata}
    if header.recording_id is not None and tasks - {header.recording_id}:
        raise mismatch(f"header recording_id {header.recording_id!r}, events {sorted(tasks)}")
    if header.duration_seconds is not None:  # rounding at the end of a recording is tolerated
        limit = header.duration_seconds + tolerance
        late = [e.event_id for e in [*prepared.events, *prepared.excluded] if e.end > limit]
        if late:
            raise mismatch(f"events {late} end after duration_seconds {header.duration_seconds} "
                           f"+ duration_tolerance_seconds {tolerance}")
    for modality, ran in header.analyses_run.items():
        produced = [e.event_id for e in [*prepared.events, *prepared.excluded]
                    if e.event_name in vocabulary.events and vocabulary.modality(e.event_name) == modality]
        if not ran and produced:
            raise mismatch(f"analyses_run says {modality} did not run, but {modality} events exist: {produced}")
