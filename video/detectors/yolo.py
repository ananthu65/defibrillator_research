"""Local-checkpoint Ultralytics adapter. Optional dependencies load on use."""
import math
from pathlib import Path
from schemas.event import Event
from video.detectors.base import Detector
from video.postprocess import merge_observations


class YOLODetector(Detector):
    backend = "YOLO"

    def __init__(self, weights, confidence=0.25, device="cpu", stride=1, imgsz=640,
                 min_duration_seconds=0.0, max_gap_seconds=None):
        self.weights = Path(weights)
        if not self.weights.is_file():
            raise FileNotFoundError(f"Place a trained checkpoint at {self.weights}")
        if not 0 <= confidence <= 1 or not isinstance(stride, int) or stride < 1:
            raise ValueError("Invalid detector threshold or stride")
        self.confidence, self.device, self.stride, self.imgsz = confidence, device, stride, imgsz
        if not math.isfinite(min_duration_seconds) or min_duration_seconds < 0:
            raise ValueError("Minimum event duration must be finite and nonnegative")
        if max_gap_seconds is not None and (not math.isfinite(max_gap_seconds) or max_gap_seconds < 0):
            raise ValueError("Maximum merge gap must be finite and nonnegative")
        self.min_duration_seconds, self.max_gap_seconds = min_duration_seconds, max_gap_seconds

    def detect(self, video):
        import cv2
        import ultralytics
        if not Path(video).is_file():
            raise FileNotFoundError(video)
        capture = cv2.VideoCapture(str(video))
        try:
            fps = capture.get(cv2.CAP_PROP_FPS)
            if not capture.isOpened() or not math.isfinite(fps) or fps <= 0:
                raise ValueError("Video must have a valid constant frame rate")
            model = getattr(ultralytics, self.backend)(str(self.weights))
            observations = []
            frame_number = 0
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_number % self.stride == 0:
                    result = model.predict(frame, conf=self.confidence, device=self.device, imgsz=self.imgsz, verbose=False)[0]
                    # Presence of an object is not evidence of correct placement or a delivered shock.
                    scores = {}
                    if result.boxes is not None:
                        for box in result.boxes:
                            label = result.names[int(box.cls.item())]
                            scores[label] = max(scores.get(label, 0), float(box.conf.item()))
                    for label, score in scores.items():
                        observations.append(Event(f"object_visible:{label}", frame_number / fps,
                                                  (frame_number + 1) / fps, "video", score,
                                                  metadata={"model": self.backend}))
                frame_number += 1
            if frame_number == 0:
                raise ValueError("No video frames decoded")
            max_gap = self.max_gap_seconds if self.max_gap_seconds is not None else (self.stride - 1) / fps + 1e-6
            return [e for e in merge_observations(observations, max_gap=max_gap)
                    if e.end - e.start >= self.min_duration_seconds]
        finally:
            capture.release()
