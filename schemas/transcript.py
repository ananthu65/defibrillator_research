"""ASR handover format; confidence may be absent when the backend has none."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    confidence: float | None = None

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (self.start, self.end)) or not 0 <= self.start <= self.end:
            raise ValueError("Invalid transcript interval")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("Invalid transcript confidence")
