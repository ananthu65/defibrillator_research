import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.audit_cvat_backups import (
    audit_backups,
    canonicalize_task_id,
    write_reports,
)


LABELS = [
    {"name": "paddle_sternal", "type": "any"},
    {"name": "Gel applied", "type": "tag"},
    {"name": "first_paddle_taken", "type": "tag"},
    {"name": "second_paddle_taken", "type": "tag"},
    {"name": "paddles_firmly_on_chest", "type": "tag"},
    {"name": "both_paddle_buttons_pressed", "type": "tag"},
    {"name": "shock_delivered_on_screen", "type": "tag"},
    {"name": "paddles_removed_after_shock", "type": "tag"},
]


def write_task_backup(
    path: Path, task_name: str, media_name: str, *, out_of_bounds: bool = False
) -> None:
    task = {
        "name": task_name,
        "status": "annotation",
        "subset": "",
        "labels": LABELS,
        "data": {"start_frame": 0, "stop_frame": 9},
        "jobs": [{"status": "annotation"}],
    }
    annotations = [
        {
            "version": 0,
            "tags": [
                {"label": "Gel applied", "frame": 1},
                {"label": "first_paddle_taken", "frame": 3},
                {"label": "second_paddle_taken", "frame": 2},
                {"label": "paddle_sternal", "frame": 4},
            ],
            "shapes": [],
            "tracks": [
                {
                    "label": "paddle_sternal",
                    "shapes": [
                        {
                            "type": "rectangle",
                            "frame": 0,
                            "points": [1, 1, 5, 5],
                            "rotation": 0,
                            "outside": False,
                        },
                        *(
                            [
                                {
                                    "type": "rectangle",
                                    "frame": 1,
                                    "points": [1, 1, 20, 20],
                                    "rotation": 0,
                                    "outside": False,
                                },
                                {
                                    "type": "rectangle",
                                    "frame": 2,
                                    "points": [2, 2, 21, 21],
                                    "rotation": 0,
                                    "outside": False,
                                },
                            ]
                            if out_of_bounds
                            else []
                        ),
                    ],
                }
            ],
        }
    ]
    manifest = "\n".join(
        [
            json.dumps({"version": "1.1"}),
            json.dumps({"type": "video"}),
            json.dumps(
                {
                    "properties": {
                        "name": media_name,
                        "resolution": [10, 10],
                        "length": 10,
                    }
                }
            ),
        ]
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("task.json", json.dumps(task))
        archive.writestr("annotations.json", json.dumps(annotations))
        archive.writestr(f"data/{media_name}", b"not-a-real-video")
        archive.writestr("data/manifest.jsonl", manifest)


class CanonicalizationTests(unittest.TestCase):
    def test_uses_media_name_to_repair_task_typo(self) -> None:
        self.assertEqual(
            canonicalize_task_id("PP48_LS", "P48_LS.mp4"),
            ("P48_LS", "P48", 48, "LS"),
        )

    def test_strips_extension_from_task_name(self) -> None:
        self.assertEqual(
            canonicalize_task_id("P42_T.MOV"),
            ("P42_T", "P42", 42, "T"),
        )


class AuditTests(unittest.TestCase):
    def test_audit_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "backups"
            output_root = root / "reports"
            input_root.mkdir()
            write_task_backup(input_root / "member.zip", "PP48_LS", "P48_LS.mp4")

            result = audit_backups(
                input_root, expected_participants=48, verify_crc=True
            )
            self.assertEqual(len(result.archives), 1)
            self.assertEqual(result.archives[0].integrity, "ok")
            self.assertEqual(len(result.tasks), 1)
            self.assertEqual(result.tasks[0].canonical_task_id, "P48_LS")

            codes = {issue.code for issue in result.issues}
            self.assertIn("task_name_normalized", codes)
            self.assertIn("object_label_used_as_tag", codes)
            self.assertIn("event_order_violation", codes)
            self.assertIn("incomplete_camera_set", codes)

            write_reports(result, output_root)
            self.assertTrue((output_root / "dataset_inventory.csv").is_file())
            self.assertTrue((output_root / "annotation_issues.csv").is_file())
            manifest = json.loads(
                (output_root / "dataset_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["counts"]["tasks"], 1)
            self.assertEqual(manifest["counts"]["participants"], 1)

    def test_coordinate_issues_are_grouped_by_task_and_label(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_root = root / "backups"
            input_root.mkdir()
            write_task_backup(
                input_root / "member.zip",
                "P01_T",
                "P01_T.mov",
                out_of_bounds=True,
            )

            result = audit_backups(input_root)
            coordinate_issues = [
                issue
                for issue in result.issues
                if issue.code == "coordinates_outside_frame"
            ]
            self.assertEqual(len(coordinate_issues), 1)
            self.assertIn("keyframes=2", coordinate_issues[0].details)


if __name__ == "__main__":
    unittest.main()
