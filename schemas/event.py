"""Shared evidence format. Times are seconds on the recording's common clock."""
from dataclasses import asdict, dataclass, field
import math
from typing import Any


@dataclass(frozen=True)
class Event:
    event_name: str
    start: float
    end: float
    source: str
    confidence: float
    evidence_type: str = "direct"
    metadata: dict[str, Any] = field(default_factory=dict)
    camera_angle: str | None = None
    event_id: str | None = None
    schema_version: int = 1

    def __post_init__(self):
        if self.schema_version != 1:
            raise ValueError("Unsupported event schema version")
        if self.camera_angle is not None and not self.camera_angle.strip():
            raise ValueError("Camera angle must be a nonempty label or null")
        if self.event_id is not None and not self.event_id.strip():
            raise ValueError("Event ID must be nonempty or null")
        if not self.event_name or self.source not in {"video", "audio", "annotation"}:
            raise ValueError("Event needs a name and a video/audio/annotation source")
        if not all(math.isfinite(v) for v in (self.start, self.end, self.confidence)):
            raise ValueError("Event times and confidence must be finite")
        if self.start < 0 or self.end < self.start or not 0 <= self.confidence <= 1:
            raise ValueError("Invalid event interval or confidence")
        if self.evidence_type not in {"direct", "inferred"}:
            raise ValueError("Unknown evidence type")
        if self.evidence_type == "inferred" and not self.metadata.get("inferred_from"):
            raise ValueError("Inferred evidence must identify its supporting evidence")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        return cls(**value)
