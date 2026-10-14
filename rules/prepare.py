"""Check a timeline, map names, set aside low-confidence events and flag data anomalies.

Nothing here judges the learner. Malformed input stops with a TimelineError (no assessment);
everything else is recorded so the report can show exactly what evidence the rules used.
Every code raised here is listed in docs/rule_engine/anomalies.md.

Event time rule: order and timing comparisons use each event's `start` time.
"""
from dataclasses import dataclass, field
from schemas.event import Event
from rules.config import count_allows
from rules.errors import TimelineError
from rules.vocabulary import LabelIssue

SHOCK_EVENT = "shock_delivered_on_screen"
APICAL_PLACED, STERNAL_PLACED = "apical_paddle_placed", "sternal_paddle_placed"
MODEL_SOURCES = ("video", "audio")
ANOMALY_CODES = ("multiple_shocks", "mixed_evidence_sources", "unknown_labels_present", "count_violation",
                 "paddle_identity_conflict")
DUPLICATE_NOTE = "possibly the same incident detected twice"


@dataclass(frozen=True)
class ExcludedEvent:
    """An event set aside before rules run; it is never used as evidence.

    Low confidence is not absence: a rule that finds an event missing while an excluded event of
    the same canonical name exists reports Unable to Verify (low_confidence_evidence), never Fail.
    """
    event_id: str
    event_name: str
    source: str
    start: float
    end: float
    confidence: float
    threshold: float
    reason: str = "below_confidence_threshold"


@dataclass(frozen=True)
class Anomaly:
    """A data problem that rules and reviewers must take into account."""
    code: str
    message: str
    event_ids: tuple[str, ...] = ()
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PreparedTimeline:
    events: tuple[Event, ...]
    excluded: tuple[ExcludedEvent, ...] = ()
    unknown_labels: tuple[LabelIssue, ...] = ()
    unused_labels: tuple[LabelIssue, ...] = ()
    unresolved_labels: tuple[LabelIssue, ...] = ()
    anomalies: tuple[Anomaly, ...] = ()
    sources: frozenset[str] = field(default_factory=frozenset)

    def named(self, event_name):
        """Usable events with this canonical name, in time order (repeats are all kept)."""
        return [e for e in self.events if e.event_name == event_name]

    def excluded_named(self, event_name):
        """Low-confidence events with this canonical name, in time order."""
        return [e for e in self.excluded if e.event_name == event_name]

    def has_anomaly(self, code):
        return any(a.code == code for a in self.anomalies)

    def anomaly(self, code):
        return next((a for a in self.anomalies if a.code == code), None)


def prepare_timeline(events, config):
    """Validate, map to canonical names and filter by confidence. Raises TimelineError if malformed."""
    events = _validated(events)
    mapping = config.vocabulary.map_events(events)
    thresholds = {source: setting.value for source, setting in config.engine.confidence_thresholds.items()}
    kept, excluded = [], []
    for event in mapping.events:
        if event.source not in thresholds:
            raise TimelineError("no_confidence_threshold", f"event {event.event_id!r} has source "
                                f"{event.source!r}, which has no confidence threshold in engine.yaml")
        threshold = thresholds[event.source]
        if event.confidence >= threshold:  # a threshold of 0 keeps every event (check disabled)
            kept.append(event)
        else:
            excluded.append(ExcludedEvent(event.event_id, event.event_name, event.source, event.start,
                                          event.end, event.confidence, threshold))
    kept.sort(key=_time_order)
    excluded.sort(key=lambda e: (e.start, e.end, e.event_id))
    anomalies = _anomalies(kept, mapping.unknown, config)
    return PreparedTimeline(tuple(kept), tuple(excluded), tuple(mapping.unknown), tuple(mapping.unused),
                            tuple(mapping.unresolved), tuple(anomalies), frozenset(e.source for e in events))


def _time_order(event):
    return event.start, event.end, event.event_id


def _validated(events):
    if isinstance(events, (str, bytes, dict)):
        raise TimelineError("not_a_list", "timeline must be a list of events")
    try:
        events = list(events)
    except TypeError:
        raise TimelineError("not_a_list", "timeline must be a list of events") from None
    for index, event in enumerate(events):
        if not isinstance(event, Event):
            raise TimelineError("not_an_event", f"timeline[{index}] is {type(event).__name__}, not "
                                "schemas.event.Event; convert source data with an input adapter first")
        if event.event_id is None:
            raise TimelineError("missing_event_id", f"timeline[{index}] ({event.event_name}) has no event_id; "
                                "IDs are assigned by pipeline.merge_timeline or an input adapter")
    seen = set()
    for event in events:
        if event.event_id in seen:
            raise TimelineError("duplicate_event_id", f"duplicate event_id {event.event_id!r}")
        seen.add(event.event_id)
    cameras = sorted({e.camera_angle for e in events if e.camera_angle is not None})  # audio has none
    if len(cameras) > 1:
        raise TimelineError("multiple_camera_angles",
                            f"timeline mixes camera angles {cameras}; assess one camera recording at a time")
    tasks = sorted({str(e.metadata["task_id"]) for e in events if "task_id" in e.metadata})
    if len(tasks) > 1:
        raise TimelineError("multiple_recordings", f"timeline mixes recordings {tasks}; assess one recording at a time")
    return events


def _anomalies(events, unknown, config):
    found = []
    shocks = [e for e in events if e.event_name == SHOCK_EVENT]
    if len(shocks) > 1:
        window = config.engine.value("simultaneous_window_seconds")
        gaps = [later.start - earlier.start for earlier, later in zip(shocks, shocks[1:])]
        duplicate = min(gaps) <= window
        note = " (possibly the same shock detected twice)" if duplicate else ""
        found.append(Anomaly("multiple_shocks", f"{len(shocks)} confident shock indications{note}; every "
                             "recording should have exactly one, so shock-dependent rules cannot be verified",
                             tuple(e.event_id for e in shocks),
                             {"within_simultaneous_window": duplicate, "smallest_gap_seconds": min(gaps),
                              "simultaneous_window_seconds": window}))
    for name in sorted({e.event_name for e in events if e.event_name in config.vocabulary.events}):
        same = [e for e in events if e.event_name == name]
        sources = {e.source for e in same}
        if "annotation" in sources and sources & set(MODEL_SOURCES):
            found.append(Anomaly("mixed_evidence_sources", f"{name} comes from both human annotation and a "
                                 "model; one assessment should use one kind of evidence",
                                 tuple(e.event_id for e in same)))
    if unknown:
        labels = sorted({f"{i.source}:{i.label}" for i in unknown})
        found.append(Anomaly("unknown_labels_present", f"labels not in the vocabulary: {', '.join(labels)}; "
                             "possible naming mismatch, so these events cannot count as evidence",
                             tuple(i.event_id for i in unknown), {"labels": labels}))
    found.extend(_count_anomalies(events, config))
    return found


def _count_anomalies(events, config):
    """Counts of confident events against expected_counts, and paddle identity (D-071).

    No events at all is not a count violation: whether a missing event is a mistake is decided by
    the coverage step and the rules (A-018). Nothing here is ever a Fail by itself.
    """
    found = []
    window = config.engine.value("simultaneous_window_seconds")
    for name, setting in sorted(config.engine.expected_counts.items()):
        expected, same = setting.value, [e for e in events if e.event_name == name]
        if expected is None or not same or count_allows(expected, len(same)):
            continue  # undecided (not checked), missing, or as expected
        details = {"event": name, "expected": dict(expected), "found": len(same)}
        note = ""
        if expected in ({"exactly": 1}, {"at_most": 1}):
            pairs = [[a.event_id, b.event_id] for a, b in zip(same, same[1:]) if b.start - a.start <= window]
            details.update(possible_duplicates=pairs, simultaneous_window_seconds=window)
            note = f"; {len(pairs)} pair(s) {DUPLICATE_NOTE}" if pairs else ""
        (bound, n), = expected.items()
        found.append(Anomaly("count_violation", f"{name}: expected {bound.replace('_', ' ')} {n}, found "
                             f"{len(same)} confident events{note}", tuple(e.event_id for e in same), details))
    apical = [e for e in events if e.event_name == APICAL_PLACED]
    sternal = [e for e in events if e.event_name == STERNAL_PLACED]
    if (len(apical) >= 2 and not sternal) or (len(sternal) >= 2 and not apical):
        repeated, other = (APICAL_PLACED, STERNAL_PLACED) if apical else (STERNAL_PLACED, APICAL_PLACED)
        found.append(Anomaly("paddle_identity_conflict", f"{len(apical or sternal)} {repeated} and no {other}; "
                             "the paddle identity may have been swapped or lost, so the placements cannot be "
                             "trusted", tuple(e.event_id for e in apical + sternal),
                             {APICAL_PLACED: len(apical), STERNAL_PLACED: len(sternal)}))
    return found
