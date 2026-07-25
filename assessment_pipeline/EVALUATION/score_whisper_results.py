"""
score_whisper_results.py

Compares each Whisper model's transcript against ground truth to
determine command detection rate and timestamp accuracy per model.
"""

import json
from rapidfuzz import fuzz

# Acceptable phrase variants for each command.
# Add more here as you observe real variations students use.
COMMAND_VARIANTS = {
    "free_flow_oxygen_away": ["free flow oxygen away", "free flowing oxygen away", "oxygen away"],
    "continue_chest_compressions": ["continue chest compression", "continue cpr", "continuous cpr", "continuous pr"],
    "all_stand_clear": ["all stand clear", "stand clear", "others away", "everybody away", "clear"],
    "stop_chest_compressions": ["stop chest compression", "stop"],
    "apply_gel": ["apply gel", "applying gel"],
    "start_chest_compressions": ["start chest compression", "start"],
}

MATCH_THRESHOLD = 70  # fuzzy match score (0-100); tune this after seeing results


def find_best_match(segments, variants):
    best_score = 0
    best_segment = None
    for segment in segments:
        text = segment["text"].lower().strip()
        for variant in variants:
            score = fuzz.partial_ratio(variant, text)
            if score > best_score:
                best_score = score
                best_segment = segment
    return best_segment, best_score


def score_file(transcript_segments, ground_truth_commands):
    results = []
    for gt in ground_truth_commands:
        variants = COMMAND_VARIANTS[gt["command"]]
        segment, score = find_best_match(transcript_segments, variants)
        detected = score >= MATCH_THRESHOLD

        timing_error = None
        if detected and gt["said"] and gt["time_seconds"] is not None:
            timing_error = abs(segment["start"] - gt["time_seconds"])

        results.append({
            "command": gt["command"],
            "actually_said": gt["said"],
            "detected": detected,
            "match_score": score,
            "timing_error_seconds": timing_error,
        })
    return results


def main():
    with open("whisper_comparison_results.json") as f:
        whisper_results = json.load(f)
    with open("ground_truth.json") as f:
        ground_truth = json.load(f)

    summary = {}  # model -> list of scored commands across all files

    for entry in whisper_results.values():
        model = entry["model"]
        student_id = entry["file"].split("_")[0]  # "P01_LL.wav" -> "P01"

        if student_id not in ground_truth:
            continue

        scored = score_file(entry["segments"], ground_truth[student_id]["commands"])
        summary.setdefault(model, []).extend(scored)

    print(f"{'Model':<10} {'Detection Rate':<16} {'Avg Timing Error (s)':<22} {'Commands Scored'}")
    for model, results in summary.items():
        said = [r for r in results if r["actually_said"]]
        correct = [r for r in said if r["detected"]]
        rate = len(correct) / len(said) if said else 0

        errors = [r["timing_error_seconds"] for r in correct if r["timing_error_seconds"] is not None]
        avg_error = sum(errors) / len(errors) if errors else float("nan")

        print(f"{model:<10} {rate:<16.1%} {avg_error:<22.2f} {len(said)}")


if __name__ == "__main__":
    main()