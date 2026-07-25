import unittest

from scripts.render_yolo_previews import select_rows


class PreviewSelectionTests(unittest.TestCase):
    def test_selects_each_class_without_test_rows(self) -> None:
        rows = [
            {
                "split": "train",
                "image_path": "images/train/a.jpg",
                "object_count": "1",
                "class_names": "first",
            },
            {
                "split": "train",
                "image_path": "images/train/b.jpg",
                "object_count": "1",
                "class_names": "second",
            },
            {
                "split": "test",
                "image_path": "images/test/c.jpg",
                "object_count": "1",
                "class_names": "first;second",
            },
        ]
        selected = select_rows(
            rows, {0: "first", 1: "second"}, ["train"], per_class=1
        )
        self.assertEqual(len(selected), 2)
        self.assertTrue(all(item[0] == "train" for item in selected))
        self.assertTrue(
            all(item[2]["image_path"].startswith("images/train/") for item in selected)
        )


if __name__ == "__main__":
    unittest.main()
