from abc import ABC, abstractmethod
from pathlib import Path
from schemas.transcript import TranscriptSegment


class SpeechModel(ABC):
    @abstractmethod
    def transcribe(self, audio: str | Path) -> list[TranscriptSegment]:
        """Return segments in recording-relative seconds."""
