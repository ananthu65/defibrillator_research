import csv
from functools import partial
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from audio.charging_sound.evaluate import event_metrics
from audio.charging_sound.predict import ChargingClassifier, windows_to_events
from audio.charging_sound.train import main, participant_splits, read_labels
from experiments.record import record_experiment


class ChargingEventTests(unittest.TestCase):
    def test_three_windows_required_and_gaps_break_runs(self):
        self.assertEqual(windows_to_events([0, 0.5], [0.9, 0.9]), [])
        self.assertEqual(windows_to_events([0, 0.5, 2], [0.9, 0.9, 0.9]), [])
        events = windows_to_events([0, 0.5, 1, 1.5], [0.9, 0.8, 0.7, 0.1])
        self.assertEqual((events[0].start, events[0].end), (0, 2))
        self.assertAlmostEqual(events[0].confidence, 0.8)

    def test_invalid_predictions_are_rejected(self):
        for starts, scores in (([0], []), ([0], [float("nan")]), ([1, 0], [0.8, 0.8])):
            with self.assertRaises(ValueError):
                windows_to_events(starts, scores)

    def test_event_matching_is_one_to_one(self):
        event = windows_to_events([0, 0.5, 1], [0.9] * 3)[0]
        metrics = event_metrics([event, event], [(0.25, 2)])
        self.assertEqual(metrics["true_positives"], 1)
        self.assertEqual(metrics["false_positives"], 1)
        self.assertEqual(metrics["start_errors_seconds"], [0.25])

    def test_split_leakage_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for split, text in (("train", "P01"), ("val", "P01"), ("test", "P03")):
                (root / f"{split}_sets.txt").write_text(text)
            with self.assertRaisesRegex(ValueError, "more than once"):
                participant_splits(root)

    def test_overlapping_annotation_intervals_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "labels.txt"
            path.write_text("0\t2\tcharging\n1\t3\tcharging\n")
            with self.assertRaises(ValueError):
                read_labels(path)

    @unittest.skipUnless(all(importlib.util.find_spec(name) for name in ("numpy", "scipy", "sklearn", "joblib")),
                         "Install requirements/charging-sound.txt for the synthetic training integration test")
    def test_synthetic_training_prediction_and_test_holdout(self):
        import numpy as np
        from scipy.io import wavfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for split, participant in (("train", "P01"), ("val", "P02"), ("test", "P03")):
                (root / f"{split}_sets.txt").write_text(participant)
            rate = 16000
            t = np.arange(6 * rate) / rate
            samples = np.zeros_like(t)
            active = (t >= 2) & (t < 4)
            samples[active] = 0.5 * np.sin(2 * np.pi * 2000 * t[active])
            for name in ("train", "val"):
                wavfile.write(root / f"{name}.wav", rate, samples.astype(np.float32))
                (root / f"{name}.txt").write_text("2\t4\tcharging\n")
            manifest = root / "manifest.csv"
            # Test paths intentionally do not exist: training must not read them.
            manifest.write_text("participant_id,audio,labels\nP01,train.wav,train.txt\nP02,val.wav,val.txt\nP03,missing.wav,missing.txt\n")
            model = root / "charging.joblib"
            with patch("audio.charging_sound.train.record_experiment", partial(record_experiment, root=root / "experiments")):
                main(["--manifest", str(manifest), "--splits", str(root), "--model-output", str(model), "--name", "synthetic"])
            events = ChargingClassifier(model).detect(root / "val.wav")
            self.assertEqual(len(events), 1)
            self.assertLessEqual(abs(events[0].start - 2), 0.5)
            self.assertTrue((root / "experiments/synthetic/metrics.json").is_file())


if __name__ == "__main__":
    unittest.main()
