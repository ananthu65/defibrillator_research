from abc import ABC, abstractmethod
from pathlib import Path
from schemas.event import Event


class Detector(ABC):
    @abstractmethod
    def detect(self, video: str | Path) -> list[Event]:
        """Return timestamped observations; clinical interpretation belongs in rules/."""
