"""Convert consecutive positive windows into shared charging-sound events."""
from pathlib import Path
from schemas.event import Event
from audio.charging_sound.features import HOP_SECONDS, WINDOW_SECONDS, extract_windows


def windows_to_events(starts, probabilities, threshold=0.5, min_windows=3):
    if len(starts) != len(probabilities) or not 0 <= threshold <= 1 or min_windows < 1:
        raise ValueError("Invalid window predictions or event settings")
    import math
    if any(not math.isfinite(t) or t < 0 for t in starts) or any(b <= a for a, b in zip(starts, starts[1:])):
        raise ValueError("Window starts must be finite, nonnegative and strictly increasing")
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities):
        raise ValueError("Window probabilities must be finite and between zero and one")
    events, run = [], []

    def finish():
        if len(run) >= min_windows:
            events.append(Event("charging_sound", run[0][0], run[-1][0] + WINDOW_SECONDS,
                                "audio", sum(p for _, p in run) / len(run),
                                metadata={"positive_windows": len(run), "model": "mfcc_rf"}))
        run.clear()

    for start, probability in zip(starts, probabilities):
        if run and start - run[-1][0] > HOP_SECONDS + 1e-6:
            finish()
        if probability >= threshold:
            run.append((start, probability))
        else:
            finish()
    finish()
    return events


class ChargingClassifier:
    def __init__(self, model_path, threshold=0.5, min_windows=3):
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Train a charging classifier first: {self.model_path}")
        if not 0 <= threshold <= 1 or not isinstance(min_windows, int) or min_windows < 1:
            raise ValueError("Invalid charging threshold or minimum window count")
        self.threshold, self.min_windows = threshold, min_windows

    def detect(self, audio):
        import joblib
        # joblib/pickle artifacts must come from a trusted training run.
        bundle = joblib.load(self.model_path)
        if bundle.get("feature_version") != "mfcc26_16k_v1":
            raise ValueError("Unsupported charging feature version")
        model = bundle["model"]
        starts, features = extract_windows(audio)
        positive_index = list(model.classes_).index(1)
        probabilities = model.predict_proba(features)[:, positive_index]
        return windows_to_events(starts, probabilities, self.threshold, self.min_windows)
