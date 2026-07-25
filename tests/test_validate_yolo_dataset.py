import tempfile
import unittest
from pathlib import Path

from scripts.validate_yolo_dataset import (
    parse_dataset_classes,
    parse_label_line,
    safe_dataset_path,
)


class LabelValidationTests(unittest.TestCase):
    def test_valid_label(self) -> None:
        box = parse_label_line(
            "2 0.50000000 0.50000000 1.00000000 1.00000000",
            class_count=7,
        )
        self.assertEqual(box.class_id, 2)
        self.assertEqual(box.width, 1.0)

    def test_rejects_wrong_field_count(self) -> None:
        with self.assertRaises(ValueError):
            parse_label_line("2 0.5 0.5 0.2", class_count=7)

    def test_rejects_unknown_class(self) -> None:
        with self.assertRaises(ValueError):
            parse_label_line("7 0.5 0.5 0.2 0.2", class_count=7)

    def test_rejects_box_past_image_edge(self) -> None:
        with self.assertRaises(ValueError):
            parse_label_line("0 0.95 0.5 0.2 0.2", class_count=7)


class DatasetMetadataTests(unittest.TestCase):
    def test_parses_contiguous_classes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.yaml"
            path.write_text(
                "path: .\ntrain: images/train\nnames:\n"
                "  0: first\n  1: second\n",
                encoding="utf-8",
            )
            self.assertEqual(parse_dataset_classes(path), {0: "first", 1: "second"})

    def test_rejects_parent_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                safe_dataset_path(Path(directory).resolve(), "../outside.jpg")


if __name__ == "__main__":
    unittest.main()
