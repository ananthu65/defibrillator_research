"""Procedure context: facts every rule needs, computed once per timeline.

The context never judges the learner and never guesses: when a fact cannot be established
(no shock, two shocks, a command too close to the shock), it is left absent and flagged, and
each rule decides what that means for its own result.

Shock time (D-093, D-115): only from shock_delivered_on_screen. No shock on screen means no shock
time. A paddle removal is never taken as evidence of a shock or of its time.

Event time rule: all times are event `start` times (see docs/rule_engine/anomalies.md).
"""
from dataclasses import dataclass, field, replace
from rules.coverage import Coverage, LOW_CONFIDENCE_FLAG, MissingOutcome
from rules.prepare import SHOCK_EVENT
from rules.vocabulary import SOURCE_LABEL_KEY

# Context flags (listed in docs/rule_engine/anomalies.md)
NO_SHOCK = "no_shock"
MULTIPLE_SHOCKS = "multiple_shocks"
MULTIPLE_CANDIDATES = "multiple_candidates"
COMMAND_NEAR_SHOCK = "command_near_shock"
NO_SHOCK_TIME = "no_shock_time"
UNRESOLVED_COMMANDS = "unresolved_commands"
START_BEFORE_SHOCK = "start_command_before_shock"
FLAGS = (NO_SHOCK, MULTIPLE_SHOCKS, MULTIPLE_CANDIDATES, COMMAND_NEAR_SHOCK, NO_SHOCK_TIME, UNRESOLVED_COMMANDS,
         START_BEFORE_SHOCK)

START_EVENT = "start_compressions_command"
ANCHOR_EVENTS = {  # anchor -> canonical event (earliest occurrence is used)
    "first_placement": "first_paddle_placed",
    "apical_placement": "apical_paddle_placed",
    "sternal_placement": "sternal_paddle_placed",
    "continue_compressions": "continue_compressions_command",
    "stop_compressions": "stop_compressions_command",
}  # start_compressions: earliest start command AFTER the shock (D-025), see _start_anchor


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
    ineligible: tuple[str, ...] = ()   # do not count, and are a mistake for a rule to report (start before shock)
    ambiguous: tuple[str, ...] = ()    # do not count, but are NOT a mistake: their timing is unknown (D-053)

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
    paddle_order: object = None        # PaddleOrder (D-118): which paddle came first, from event times

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
    def config(self):
        return self.coverage.config

    @property
    def _window(self):
        return self.config.engine.value("simultaneous_window_seconds")


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
            events.append(replace(event, event_name=resolved, metadata=metadata))
    events.sort(key=lambda e: (e.start, e.end, e.event_id))
    unresolved = tuple(r for r in resolutions if r.resolved_to is None)
    anchors = {"shock": shock}
    for name, event_name in ANCHOR_EVENTS.items():
        anchors[name] = _earliest(name, event_name, events, prepared)
    anchors["start_compressions"] = _start_anchor(events, shock, prepared, resolutions)
    for name in ("continue_compressions", "start_compressions"):
        if unresolved:  # an unresolved command might have been this one: do not pretend the anchor is complete
            anchors[name] = replace(anchors[name], flags=anchors[name].flags + (UNRESOLVED_COMMANDS,))
    zones = {region: coverage.status(events_in_region[0]) if events_in_region else coverage.region_status(region)
             for region, events_in_region in config.engine.regions.items()}
    return ProcedureContext(prepared, coverage, tuple(events), anchors, tuple(resolutions), zones,
                            paddle_order(events, window))


# Paddle tags (A-027): the names give identity, never time order (D-118).
PADDLE_TAKEN = {"apical": "first_paddle_taken", "sternal": "second_paddle_taken"}
# firm placement: for the apical paddle the annotators' tag (first_paddle_placed) wins, else its per-paddle
# placement; the sternal paddle has no tag, so only its per-paddle placement
PADDLE_PLACED = {"apical": ("first_paddle_placed", "apical_paddle_placed"), "sternal": ("sternal_paddle_placed",)}


@dataclass(frozen=True)
class PaddleOrder:
    """D-118: which paddle came first, computed from event times. Under A-027 `first_paddle_*` means
    the apical paddle and `second_paddle_*` the sternal one, so no rule reads order from the names.

    taken / placed: paddle ("apical", "sternal") -> its earliest taken / firm-placement event, or None.
    first_taken: the paddle taken first (an exact tie counts as apical; a paddle placed before the other
        was taken counts as first even without its take), or None when that can't be established.
    earliest_placement: the earliest known firm placement of either paddle, or None.
    earliest_certain: False when the other paddle's placement is unknown and could have been earlier.
    unknown_from: when not certain, the earliest time that unknown placement could be (its take, else 0).
    take_deduced: True when first_taken was deduced from a placement (its take isn't tagged).
    """
    taken: dict
    placed: dict
    first_taken: str | None
    earliest_placement: object
    earliest_certain: bool
    unknown_from: float | None
    reason: str
    take_deduced: bool = False

    @property
    def earliest_taken(self):
        found = [e for e in self.taken.values() if e is not None]
        return min(found, key=lambda e: (e.start, e.event_id)) if found else None

    @property
    def gel_phase_end(self):
        """The event ending the gel phase (R1; Step 9d computes the same in frames): the earliest firm
        placement of either paddle, else the earliest paddle taken, else None (the end of the recording)."""
        return self.earliest_placement if self.earliest_placement is not None else self.earliest_taken


def paddle_order(events, window):
    """The shared paddle-order facts (D-118) from the context's events."""
    def earliest(names):
        found = [e for e in events if e.event_name in names]
        return min(found, key=lambda e: (e.start, e.event_id)) if found else None
    taken = {p: earliest((name,)) for p, name in PADDLE_TAKEN.items()}
    placed = {p: next((e for e in (earliest((name,)) for name in names) if e is not None), None)
              for p, names in PADDLE_PLACED.items()}
    deduced = False
    if taken["apical"] is None or taken["sternal"] is None:
        missing = [p for p in ("apical", "sternal") if taken[p] is None]
        first, reason = None, f"no confident take of the {' and '.join(missing)} paddle"
        if len(missing) == 1:   # a paddle placed before the other was taken must have been taken first
            gap, other = missing[0], ("sternal" if missing[0] == "apical" else "apical")
            if placed[gap] is not None and placed[gap].start < taken[other].start - window:
                first, deduced = gap, True
                reason = (f"the {gap} paddle was taken first: its take isn't tagged, but it was placed before the "
                          f"{other} paddle was taken")
    else:   # an exact tie counts as apical first; either way the other was taken before any placement
        first = "sternal" if taken["sternal"].start < taken["apical"].start else "apical"
        reason = f"the {first} paddle was taken first"
    known = [e for e in placed.values() if e is not None]
    if not known:
        return PaddleOrder(taken, placed, first, None, True, None, reason, deduced)
    earliest_placed = min(known, key=lambda e: (e.start, e.event_id))
    unknown = [p for p in ("apical", "sternal") if placed[p] is None]
    if not unknown:
        return PaddleOrder(taken, placed, first, earliest_placed, True, None, reason, deduced)
    other_taken = taken[unknown[0]]
    if other_taken is not None and other_taken.start >= earliest_placed.start:
        # the other paddle was taken after this placement, so it can't have been placed before it
        return PaddleOrder(taken, placed, first, earliest_placed, True, None, reason, deduced)
    unknown_from = other_taken.start if other_taken is not None else 0.0
    return PaddleOrder(taken, placed, first, earliest_placed, False, unknown_from, reason, deduced)


def _shock_anchor(prepared):
    """The shock time comes only from the shock on screen (D-093, D-115); it is never inferred."""
    if prepared.has_anomaly(MULTIPLE_SHOCKS):
        ids = prepared.anomaly(MULTIPLE_SHOCKS).event_ids
        return Anchor("shock", None, candidates=ids, flags=(MULTIPLE_SHOCKS,),
                      reason="more than one shock indication; shock time not established")
    shocks = prepared.named(SHOCK_EVENT)
    if shocks:
        return Anchor("shock", shocks[0].start, shocks[0].event_id, SHOCK_EVENT, (shocks[0].event_id,))
    return Anchor("shock", None, flags=(NO_SHOCK,),
                  reason="no shock seen on the screen; the shock time is never inferred (D-093)")


def _resolve(resolution, time, shock, window):
    """(canonical name or None, flags) for an ambiguous command at `time`."""
    if not shock.present:
        return None, (NO_SHOCK_TIME,)
    if abs(time - shock.time) <= window:
        return None, (COMMAND_NEAR_SHOCK,)
    before, after = resolution
    return (before if time < shock.time else after), ()


def _start_anchor(events, shock, prepared, resolutions=()):
    """D-025: the restart is the earliest start command after the shock; earlier ones do not count.

    Each start command is checked on its own, so a later one can still be the restart. Start
    commands at or before the shock do not count and are a sequence mistake. D-054: with no shock
    time at all, every start command is timing-ambiguous (not counted, not a mistake).
    """
    starts = [e for e in events if e.event_name == START_EVENT]
    if not shock.present:
        return Anchor("start_compressions", None, flags=(NO_SHOCK_TIME,) + shock.flags,
                      reason="no shock time, so the restart command cannot be identified",
                      ambiguous=tuple(e.event_id for e in starts))
    after = [e for e in starts if e.start > shock.time]
    before = tuple(e.event_id for e in starts if e.start <= shock.time)
    flags, ambiguous = ((START_BEFORE_SHOCK,) if before else ()), ()
    if not after:
        low = (LOW_CONFIDENCE_FLAG,) if prepared.excluded_named(START_EVENT) else ()
        return Anchor("start_compressions", None, flags=flags + low,
                      reason=f"no confident {START_EVENT} event after the shock",
                      ineligible=before, ambiguous=ambiguous)
    many = (MULTIPLE_CANDIDATES,) if len(after) > 1 else ()
    return Anchor("start_compressions", after[0].start, after[0].event_id, START_EVENT,
                  tuple(e.event_id for e in after), flags + many, ineligible=before, ambiguous=ambiguous)


def _earliest(anchor, event_name, events, prepared):
    found = [e for e in events if e.event_name == event_name]
    if not found:
        flags = (LOW_CONFIDENCE_FLAG,) if prepared.excluded_named(event_name) else ()
        return Anchor(anchor, None, flags=flags, reason=f"no confident {event_name} event")
    ids = tuple(e.event_id for e in found)
    flags = (MULTIPLE_CANDIDATES,) if len(found) > 1 else ()
    return Anchor(anchor, found[0].start, found[0].event_id, event_name, ids, flags)
