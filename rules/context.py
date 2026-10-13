"""Procedure context: facts every rule needs, computed once per timeline.

The context never judges the learner and never guesses: when a fact cannot be established
(no shock, two shocks, a command too close to the shock), it is left absent and flagged, and
each rule decides what that means for its own result.

Event time rule: all times are event `start` times (see docs/rule_engine/anomalies.md).
"""
from dataclasses import dataclass, field, replace
from rules.coverage import Coverage, LOW_CONFIDENCE_FLAG, MissingOutcome
from rules.prepare import SHOCK_EVENT
from rules.vocabulary import SOURCE_LABEL_KEY

REMOVAL_EVENT = "paddles_removed_after_shock"

# Context flags (listed in docs/rule_engine/anomalies.md)
SHOCK_FROM_REMOVAL = "shock_time_from_removal"
NO_SHOCK = "no_shock"
MULTIPLE_SHOCKS = "multiple_shocks"
MULTIPLE_CANDIDATES = "multiple_candidates"
COMMAND_NEAR_SHOCK = "command_near_shock"
NO_SHOCK_TIME = "no_shock_time"
UNRESOLVED_COMMANDS = "unresolved_commands"

ANCHOR_EVENTS = {  # anchor -> canonical event (earliest occurrence is used)
    "first_placement": "first_paddle_placed",
    "apical_placement": "apical_paddle_placed",
    "sternal_placement": "sternal_paddle_placed",
    "continue_compressions": "continue_compressions_command",
    "stop_compressions": "stop_compressions_command",
    "start_compressions": "start_compressions_command",
}


@dataclass(frozen=True)
class Anchor:
    """A key time in the procedure. time is None when it could not be established."""
    name: str
    time: float | None
    event_id: str | None = None
    event_name: str | None = None
    candidates: tuple[str, ...] = ()   # every event ID that could have been the anchor
    flags: tuple[str, ...] = ()
    reason: str = ""

    @property
    def present(self):
        return self.time is not None


@dataclass(frozen=True)
class CommandResolution:
    """How one ambiguous command (e.g. resume_compressions_command) was classified."""
    event_id: str
    label: str
    time: float
    resolved_to: str | None            # canonical name, or None when left unresolved
    flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Elapsed:
    """Time from one anchor to another; seconds is None when either anchor is absent."""
    start: Anchor
    end: Anchor
    seconds: float | None
    flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProcedureContext:
    prepared: object
    coverage: Coverage
    events: tuple                      # prepared events with ambiguous commands resolved where possible
    anchors: dict[str, Anchor]
    resolutions: tuple[CommandResolution, ...]
    zone_visibility: dict[str, object] = field(default_factory=dict)  # region -> CoverageStatus

    @property
    def shock(self):
        return self.anchors["shock"]

    def anchor(self, name):
        return self.anchors[name]

    def named(self, event_name):
        """Usable events with this canonical name (after command resolution), in time order."""
        return [e for e in self.events if e.event_name == event_name]

    def phase_of(self, time):
        """before_shock / at_shock / after_shock, or None when there is no shock time."""
        if not self.shock.present:
            return None
        return "before_shock" if time < self.shock.time else "after_shock" if time > self.shock.time else "at_shock"

    def elapsed(self, start, end):
        """Seconds from anchor `start` to anchor `end`; carries both anchors' flags."""
        a, b = self.anchors[start], self.anchors[end]
        flags = tuple(dict.fromkeys(a.flags + b.flags))
        return Elapsed(a, b, b.time - a.time if a.present and b.present else None, flags)

    def missing(self, event_name, window=None):
        """Coverage.missing, plus low-confidence ambiguous commands that could have been this event."""
        outcome = self.coverage.missing(event_name, window)
        low = [e.event_id for e in self.prepared.excluded if self._could_be(e, event_name)]
        if not low or LOW_CONFIDENCE_FLAG in outcome.flags:
            return outcome
        return MissingOutcome(event_name, "unable_to_verify", outcome.coverage, "low confidence is not absence",
                              (LOW_CONFIDENCE_FLAG,), tuple(low))

    def _could_be(self, excluded, event_name):
        resolution = self.coverage.config.vocabulary.resolution(excluded.source, excluded.event_name)
        if resolution is None or event_name not in resolution:
            return False
        resolved, _ = _resolve(resolution, excluded.start, self.shock, self._window)
        return resolved in (None, event_name)  # unresolvable: it could have been either

    @property
    def _window(self):
        return self.coverage.config.engine.value("simultaneous_window_seconds")


def build_context(prepared, config, header=None):
    coverage = Coverage(prepared, config, header)
    window = config.engine.value("simultaneous_window_seconds")
    shock = _shock_anchor(prepared)
    events, resolutions = [], []
    for event in prepared.events:
        resolution = config.vocabulary.resolution(event.source, event.metadata.get(SOURCE_LABEL_KEY, event.event_name))
        if resolution is None or event.event_name in config.vocabulary.events:
            events.append(event)
            continue
        resolved, flags = _resolve(resolution, event.start, shock, window)
        resolutions.append(CommandResolution(event.event_id, event.event_name, event.start, resolved, flags))
        if resolved is None:
            events.append(event)
        else:
            metadata = {**event.metadata, "resolved_by": "position relative to shock", "shock_time": shock.time}
            if SHOCK_FROM_REMOVAL in shock.flags:
                metadata["resolution_flags"] = [SHOCK_FROM_REMOVAL]
            events.append(replace(event, event_name=resolved, metadata=metadata))
    events.sort(key=lambda e: (e.start, e.end, e.event_id))
    unresolved = tuple(r for r in resolutions if r.resolved_to is None)
    anchors = {"shock": shock}
    for name, event_name in ANCHOR_EVENTS.items():
        anchors[name] = _earliest(name, event_name, events, prepared)
    for name in ("continue_compressions", "start_compressions"):
        if unresolved:  # an unresolved command might have been this one: do not pretend the anchor is complete
            anchors[name] = replace(anchors[name], flags=anchors[name].flags + (UNRESOLVED_COMMANDS,))
    zones = {region: coverage.status(events_in_region[0])
             for region, events_in_region in config.engine.regions.items()}
    return ProcedureContext(prepared, coverage, tuple(events), anchors, tuple(resolutions), zones)


def _shock_anchor(prepared):
    if prepared.has_anomaly(MULTIPLE_SHOCKS):
        ids = prepared.anomaly(MULTIPLE_SHOCKS).event_ids
        return Anchor("shock", None, candidates=ids, flags=(MULTIPLE_SHOCKS,),
                      reason="more than one shock indication; shock time not established")
    shocks = prepared.named(SHOCK_EVENT)
    if shocks:
        return Anchor("shock", shocks[0].start, shocks[0].event_id, SHOCK_EVENT, (shocks[0].event_id,))
    removals = prepared.named(REMOVAL_EVENT)
    if removals:
        flags = (SHOCK_FROM_REMOVAL,) + ((MULTIPLE_CANDIDATES,) if len(removals) > 1 else ())
        return Anchor("shock", removals[0].start, removals[0].event_id, REMOVAL_EVENT,
                      tuple(e.event_id for e in removals), flags,
                      "no shock on screen; shock time taken from paddle removal, which happens after the shock")
    return Anchor("shock", None, flags=(NO_SHOCK,), reason="no confirmed shock or paddle removal")


def _resolve(resolution, time, shock, window):
    """(canonical name or None, flags) for an ambiguous command at `time`."""
    if not shock.present:
        return None, (NO_SHOCK_TIME,)
    carried = (SHOCK_FROM_REMOVAL,) if SHOCK_FROM_REMOVAL in shock.flags else ()
    if abs(time - shock.time) <= window:
        return None, (COMMAND_NEAR_SHOCK,) + carried
    before, after = resolution
    return (before if time < shock.time else after), carried


def _earliest(anchor, event_name, events, prepared):
    found = [e for e in events if e.event_name == event_name]
    if not found:
        flags = (LOW_CONFIDENCE_FLAG,) if prepared.excluded_named(event_name) else ()
        return Anchor(anchor, None, flags=flags, reason=f"no confident {event_name} event")
    ids = tuple(e.event_id for e in found)
    flags = (MULTIPLE_CANDIDATES,) if len(found) > 1 else ()
    return Anchor(anchor, found[0].start, found[0].event_id, event_name, ids, flags)
