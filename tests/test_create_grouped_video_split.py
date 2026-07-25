import unittest

from scripts.create_grouped_video_split import (
    ParticipantRecord,
    allocate_proportional_quotas,
    derive_source_quotas,
    generate_split,
    validate_split,
)


def synthetic_participants() -> dict[str, ParticipantRecord]:
    source_sizes = {
        "master": 15,
        "kartheepan": 13,
        "kishonithan": 5,
        "rashad": 5,
        "sharmilan": 5,
        "sujeevan": 5,
    }
    participants: dict[str, ParticipantRecord] = {}
    number = 1
    for source, size in source_sizes.items():
        for _ in range(size):
            participant_id = f"P{number:02d}"
            participants[participant_id] = ParticipantRecord(
                participant_id=participant_id,
                annotation_source=source,
                features={
                    "frames": 1000 + number,
                    "event::Gel applied": 2 + number % 2,
                    "track_views::paddle_sternal": 3,
                    "review_issues": number % 3,
                },
            )
            number += 1
    return participants


class QuotaTests(unittest.TestCase):
    def test_actual_source_quota_shape(self) -> None:
        participants = synthetic_participants()
        quotas = derive_source_quotas(
            participants, {"train": 33, "val": 6, "test": 9}
        )
        self.assertTrue(all(count == 1 for count in quotas["val"].values()))
        self.assertEqual(quotas["test"]["master"], 3)
        self.assertEqual(quotas["test"]["kartheepan"], 2)
        self.assertTrue(
            all(
                quotas["test"][source] == 1
                for source in ("kishonithan", "rashad", "sharmilan", "sujeevan")
            )
        )

    def test_proportional_quota_rejects_impossible_minimum(self) -> None:
        with self.assertRaises(ValueError):
            allocate_proportional_quotas(
                {"a": 2, "b": 2, "c": 2}, 2, minimum_each=1
            )


class SplitTests(unittest.TestCase):
    def test_split_is_deterministic_and_valid(self) -> None:
        participants = synthetic_participants()
        first = generate_split(
            participants,
            train_count=33,
            val_count=6,
            test_count=9,
            seed=42,
            iterations=500,
        )
        second = generate_split(
            participants,
            train_count=33,
            val_count=6,
            test_count=9,
            seed=42,
            iterations=500,
        )
        self.assertEqual(first.assignments, second.assignments)
        self.assertEqual(first.score, second.score)
        self.assertEqual(
            validate_split(
                participants,
                first,
                {"train": 33, "val": 6, "test": 9},
            ),
            [],
        )

    def test_split_counts_must_cover_all_participants(self) -> None:
        participants = synthetic_participants()
        with self.assertRaises(ValueError):
            generate_split(
                participants,
                train_count=32,
                val_count=6,
                test_count=9,
                seed=42,
                iterations=10,
            )


if __name__ == "__main__":
    unittest.main()
