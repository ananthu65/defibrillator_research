"""Map every source label to one canonical event name; rules only see canonical names."""
from dataclasses import dataclass, field, replace
from pathlib import Path
import yaml
from rules.errors import ConfigError
from schemas.event import Event

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "configs/rule_engine/vocabulary.yaml"
SOURCES = ("annotation", "video", "audio")
MODALITIES = ("video", "audio")
SOURCE_LABEL_KEY = "source_label"


@dataclass(frozen=True)
class CanonicalEvent:
    name: str
    modality: str
    description: str


@dataclass(frozen=True)
class LabelIssue:
    """A timeline event whose label is unknown, or known but unused by any rule."""
    event_id: str | None
    source: str
    label: str


@dataclass(frozen=True)
class MappingResult:
    events: list[Event]
    unknown: list[LabelIssue] = field(default_factory=list)
    unused: list[LabelIssue] = field(default_factory=list)


@dataclass(frozen=True)
class Vocabulary:
    events: dict[str, CanonicalEvent]
    labels: dict[tuple[str, str], str]
    placeholder_labels: frozenset[tuple[str, str]] = frozenset()
    unused_labels: frozenset[tuple[str, str]] = frozenset()
    unused_prefixes: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_dict(cls, data, where="vocabulary"):
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ConfigError(f"{where}: expected a mapping with schema_version: 1")
        events = {}
        for name, entry in _mapping(data.get("events"), f"{where} events").items():
            if not isinstance(entry, dict) or entry.get("modality") not in MODALITIES:
                raise ConfigError(f"{where} events.{name}: modality must be one of {MODALITIES}")
            events[name] = CanonicalEvent(name, entry["modality"], str(entry.get("description", "")))
        labels, placeholders = {}, set()
        for source, entries in _sources(data.get("labels"), f"{where} labels").items():
            for index, entry in enumerate(entries or []):
                at = f"{where} labels.{source}[{index}]"
                if not isinstance(entry, dict) or set(entry) - {"label", "event", "placeholder"}:
                    raise ConfigError(f"{at}: expected only label, event and optional placeholder")
                label, event = entry.get("label"), entry.get("event")
                if not isinstance(label, str) or not label:
                    raise ConfigError(f"{at}: label must be a nonempty string")
                if event not in events:
                    raise ConfigError(f"{at}: unknown canonical event {event!r}")
                if (source, label) in labels:
                    raise ConfigError(f"{at}: label {label!r} is mapped twice for source {source}")
                labels[(source, label)] = event
                if entry.get("placeholder", False):
                    placeholders.add((source, label))
        unused, prefixes = set(), []
        for source, entries in _sources(data.get("unused", {}), f"{where} unused").items():
            for index, entry in enumerate(entries or []):
                at = f"{where} unused.{source}[{index}]"
                if isinstance(entry, str) and entry:
                    unused.add((source, entry))
                elif isinstance(entry, dict) and set(entry) == {"prefix"} and entry["prefix"]:
                    prefixes.append((source, str(entry["prefix"])))
                else:
                    raise ConfigError(f"{at}: expected a label or {{prefix: ...}}")
        vocabulary = cls(events, labels, frozenset(placeholders), frozenset(unused), tuple(prefixes))
        clash = sorted(key for key in labels if vocabulary.is_unused(*key))
        if clash:
            raise ConfigError(f"{where}: labels both mapped and unused: {clash}")
        return vocabulary

    def canonical(self, source, label):
        return self.labels.get((source, label))

    def modality(self, event_name):
        return self.events[event_name].modality

    def is_unused(self, source, label):
        return (source, label) in self.unused_labels or any(
            s == source and label.startswith(p) for s, p in self.unused_prefixes)

    def map_events(self, events):
        """Rename to canonical names; keep IDs and the original label. Never drops an event."""
        mapped, unknown, unused = [], [], []
        for event in events:
            if SOURCE_LABEL_KEY in event.metadata and event.event_name in self.events:
                mapped.append(event)  # already mapped, so mapping twice changes nothing
                continue
            name = self.canonical(event.source, event.event_name)
            if name is not None:
                metadata = {**event.metadata, SOURCE_LABEL_KEY: event.event_name}
                mapped.append(replace(event, event_name=name, metadata=metadata))
                continue
            issue = LabelIssue(event.event_id, event.source, event.event_name)
            (unused if self.is_unused(event.source, event.event_name) else unknown).append(issue)
            mapped.append(event)
        return MappingResult(mapped, unknown, unused)


def load_vocabulary(path=DEFAULT_PATH):
    with Path(path).open(encoding="utf-8") as stream:
        return Vocabulary.from_dict(yaml.safe_load(stream), where=str(path))


def _mapping(value, where):
    if not isinstance(value, dict) or not value:
        raise ConfigError(f"{where}: expected a nonempty mapping")
    return value


def _sources(value, where):
    if not isinstance(value, dict):
        raise ConfigError(f"{where}: expected a mapping of source -> list")
    for source, entries in value.items():
        if source not in SOURCES:
            raise ConfigError(f"{where}: unknown source {source!r}; expected one of {SOURCES}")
        if entries is not None and not isinstance(entries, list):
            raise ConfigError(f"{where}.{source}: expected a list")
    return value
