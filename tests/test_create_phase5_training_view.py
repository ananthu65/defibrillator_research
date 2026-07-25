import unittest

from scripts.create_phase5_training_view import build_smoke_rows, evenly_spaced


def row(task: str, frame: int, classes: str) -> dict[str, str]:
    return {
        "canonical_task_id": task,
        "source_frame": str(frame),
        "image_path": f"images/train/{task}_{frame}.jpg",
        "class_names": classes,
    }


class SmokeSelectionTests(unittest.TestCase):
    def test_evenly_spaced_has_requested_count(self) -> None:
        rows = [row("P01_T", frame, "first") for frame in range(20)]
        selected = evenly_spaced(rows, 6)
        self.assertEqual(len(selected), 6)
        self.assertEqual(len({item["source_frame"] for item in selected}), 6)

    def test_smoke_selection_covers_tasks_and_classes(self) -> None:
        rows = [
            row("P01_T", 0, "first"),
            row("P01_T", 10, "first"),
            row("P02_T", 0, "first"),
            row("P02_T", 10, "second"),
        ]
        selected = build_smoke_rows(
            rows, images_per_task=1, class_names=("first", "second")
        )
        self.assertEqual(
            {item["canonical_task_id"] for item in selected}, {"P01_T", "P02_T"}
        )
        self.assertIn(
            "second",
            {
                name
                for item in selected
                for name in item["class_names"].split(";")
            },
        )


if __name__ == "__main__":
    unittest.main()
