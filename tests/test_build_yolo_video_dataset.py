import math
import unittest

from scripts.build_yolo_video_dataset import (
    Box,
    Track,
    build_sample_reasons,
    clip_box,
    rectangle_box,
    track_box_at,
    yolo_line,
)


def rectangle(frame: int, points: list[float], *, outside: bool = False, rotation: float = 0):
    return {
        "type": "rectangle",
        "frame": frame,
        "points": points,
        "outside": outside,
        "rotation": rotation,
    }


class GeometryTests(unittest.TestCase):
    def test_rotated_rectangle_uses_enclosing_box(self) -> None:
        box = rectangle_box([0, 0, 10, 20], 90)
        self.assertIsNotNone(box)
        assert box is not None
        self.assertAlmostEqual(box.width, 20)
        self.assertAlmostEqual(box.height, 10)
        self.assertAlmostEqual((box.x1 + box.x2) / 2, 5)
        self.assertAlmostEqual((box.y1 + box.y2) / 2, 10)

    def test_track_interpolates_between_keyframes(self) -> None:
        track = Track(
            "paddle_sternal",
            [
                rectangle(0, [0, 0, 10, 10]),
                rectangle(10, [10, 20, 20, 30]),
            ],
        )
        box = track_box_at(track, 5)
        self.assertEqual(box, Box(5, 10, 15, 20))

    def test_outside_keyframe_excludes_exact_frame_and_later(self) -> None:
        track = Track(
            "paddle_sternal",
            [
                rectangle(0, [0, 0, 10, 10]),
                rectangle(10, [10, 10, 20, 20], outside=True),
            ],
        )
        self.assertIsNotNone(track_box_at(track, 9))
        self.assertIsNone(track_box_at(track, 10))
        self.assertIsNone(track_box_at(track, 11))

    def test_clip_and_yolo_normalization(self) -> None:
        box, was_clipped = clip_box(Box(-10, 10, 50, 60), 100, 100)
        self.assertTrue(was_clipped)
        self.assertEqual(box, Box(0, 10, 50, 60))
        assert box is not None
        values = yolo_line(2, box, 100, 100).split()
        self.assertEqual(values[0], "2")
        self.assertTrue(
            all(0 <= float(value) <= 1 for value in values[1:])
        )


class SamplingTests(unittest.TestCase):
    def test_sampling_includes_regular_events_context_and_shock_keyframes(self) -> None:
        tags = [{"label": "Gel applied", "frame": 25}]
        tracks = [
            Track(
                "shock_symbol",
                [
                    rectangle(40, [0, 0, 10, 10]),
                    rectangle(45, [0, 0, 10, 10], outside=True),
                ],
            )
        ]
        reasons, interval = build_sample_reasons(
            start_frame=0,
            stop_frame=49,
            fps=25,
            sample_fps=5,
            event_context_seconds=0.08,
            tags=tags,
            standalone_shapes=[],
            tracks=tracks,
        )
        self.assertEqual(interval, 5)
        self.assertIn("regular", reasons[0])
        self.assertIn("event", reasons[25])
        self.assertIn("event_context", reasons[23])
        self.assertIn("shock_keyframe", reasons[40])
        self.assertIn("last_frame", reasons[49])


if __name__ == "__main__":
    unittest.main()
