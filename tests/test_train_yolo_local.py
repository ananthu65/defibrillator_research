import json
import tempfile
import unittest
from pathlib import Path

from scripts.train_yolo_local import load_config


class TrainingConfigTests(unittest.TestCase):
    def write_config(self, data: dict[str, object]) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "config.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def valid(self) -> dict[str, object]:
        return {
            "name": "smoke",
            "model": "weights/yolov8n.pt",
            "data": "dataset.yaml",
            "epochs": 1,
            "imgsz": 640,
            "batch": 2,
        }

    def test_valid_config(self) -> None:
        self.assertEqual(load_config(self.write_config(self.valid()))["epochs"], 1)

    def test_missing_required_key(self) -> None:
        config = self.valid()
        del config["model"]
        with self.assertRaises(ValueError):
            load_config(self.write_config(config))

    def test_rejects_non_yaml_data(self) -> None:
        config = self.valid()
        config["data"] = "dataset.json"
        with self.assertRaises(ValueError):
            load_config(self.write_config(config))


if __name__ == "__main__":
    unittest.main()
