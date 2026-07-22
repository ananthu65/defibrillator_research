import csv
import json
import re
from pathlib import Path

from faster_whisper import WhisperModel

AUDIO_DIR = Path(__file__).resolve().parents[1] / "extracted_audio"
JSON_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "rubric_json"
CSV_OUTPUT_PATH = Path(__file__).resolve().parents[1] / "google_sheet" / "defib_rubric_results.csv"
MODEL_SIZE = "tiny"
COMPUTE_TYPE = "int8"


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def has_any_pattern(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def evaluate_commands(transcript: str) -> dict[str, str]:
    t = normalize(transcript)

    oxygen_away_patterns = [
        r"\boxygen away\b",
        r"\bremove (the )?oxygen\b",
        r"\btake off (the )?(o2|oxygen|mask)\b",
        r"\bmask away\b",
        r"\bo2 away\b",
    ]

    all_clear_patterns = [
        r"\ball stand clear\b",
        r"\bstand clear\b",
        r"\beveryone back\b",
        r"\bi m clear\b",
        r"\byou re clear\b",
        r"\ball clear\b",
        r"\bothers away\b",
    ]

    continue_compressions_patterns = [
        r"\bcontinue (chest )?compressions\b",
        r"\bresume (cpr|compressions)\b",
        r"\bstart (cpr|compressions)\b",
        r"\bget back on the chest\b",
        r"\bcontinue cpr\b",
    ]

    charge_discharge_patterns = [
        r"\bcharging( to)?\b",
        r"\bshock(ing)? now\b",
        r"\bshock delivered\b",
        r"\bdeliver(ing)? shock\b",
        r"\bclear to shock\b",
    ]

    stop_start_patterns = [
        r"\bstop (cpr|compressions|chest compressions)\b",
        r"\bhold compressions\b",
        r"\bresume (cpr|compressions)\b",
        r"\bstart (again|cpr|compressions)\b",
        r"\bcontinue (cpr|compressions)\b",
    ]

    return {
        "Oxygen_Away": "✓" if has_any_pattern(t, oxygen_away_patterns) else "✗",
        "All_Stand_Clear": "✓" if has_any_pattern(t, all_clear_patterns) else "✗",
        "Continue_Compressions": "✓" if has_any_pattern(t, continue_compressions_patterns) else "✗",
        "Charge_Discharge_Acknowledged": "✓" if has_any_pattern(t, charge_discharge_patterns) else "✗",
        "Stop_Start_Commands": "✓" if has_any_pattern(t, stop_start_patterns) else "✗",
    }


def student_id_from_filename(audio_file: Path) -> str:
    name = audio_file.stem
    if name.endswith("_audio"):
        return name[:-6]
    return name


def transcribe_audio(model: WhisperModel, audio_path: Path) -> str:
    segments, _ = model.transcribe(str(audio_path), language="en", vad_filter=True)
    return " ".join(segment.text.strip() for segment in segments if segment.text).strip()


def main() -> None:
    if not AUDIO_DIR.exists():
        raise FileNotFoundError(f"Audio folder not found: {AUDIO_DIR}")

    JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CSV_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    audio_files = sorted(AUDIO_DIR.glob("*.mp3"))
    if not audio_files:
        print("No audio files found to process.")
        return

    print(f"Loading Whisper model: {MODEL_SIZE}")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE)

    csv_rows = []

    for idx, audio_file in enumerate(audio_files, start=1):
        student_id = student_id_from_filename(audio_file)
        print(f"[{idx}/{len(audio_files)}] Processing {audio_file.name}")

        try:
            transcript = transcribe_audio(model, audio_file)
            scores = evaluate_commands(transcript)
        except Exception as exc:
            transcript = ""
            scores = {
                "Oxygen_Away": "✗",
                "All_Stand_Clear": "✗",
                "Continue_Compressions": "✗",
                "Charge_Discharge_Acknowledged": "✗",
                "Stop_Start_Commands": "✗",
            }
            print(f"  Failed: {exc}")

        result = {
            "Student_ID": student_id,
            **scores,
        }

        output_json = JSON_OUTPUT_DIR / f"{student_id}.json"
        with output_json.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        csv_rows.append(result)

    headers = [
        "Student_ID",
        "Oxygen_Away",
        "All_Stand_Clear",
        "Continue_Compressions",
        "Charge_Discharge_Acknowledged",
        "Stop_Start_Commands",
    ]

    with CSV_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"JSON files written to: {JSON_OUTPUT_DIR}")
    print(f"Google Sheets CSV written to: {CSV_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
