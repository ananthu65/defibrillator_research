import os
import subprocess
from pathlib import Path

import imageio_ffmpeg

# Source videos folder
TARGET_DIRECTORY = r"C:\Personal\ARTS - Defibrillation\DATA\30"

# Output folder inside this repository
OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "extracted_audio"

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".m4v"}


def unique_output_path(output_folder: Path, stem: str) -> Path:
    """Avoid overwriting when videos from different subfolders share the same name."""
    candidate = output_folder / f"{stem}_audio.mp3"
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        candidate = output_folder / f"{stem}_audio_{index}.mp3"
        if not candidate.exists():
            return candidate
        index += 1


def batch_extract_audio(input_folder: str, output_folder: Path) -> None:
    input_path = Path(input_folder)
    if not input_path.exists():
        print(f"Error: input folder not found: {input_path}")
        return

    output_folder.mkdir(parents=True, exist_ok=True)

    print(f"Searching videos in: {input_path}")
    print(f"Audio output folder: {output_folder}\n")

    processed = 0
    skipped = 0
    failed = 0

    for current_folder, _, files in os.walk(input_path):
        for file in files:
            file_path = Path(current_folder) / file
            if file_path.suffix.lower() not in VIDEO_EXTENSIONS:
                continue

            output_audio_path = unique_output_path(output_folder, file_path.stem)
            default_output = output_folder / f"{file_path.stem}_audio.mp3"
            if default_output.exists() and output_audio_path == default_output:
                print(f"Processing: {file_path}")
                print("  -> Audio already exists. Skipped.\n")
                skipped += 1
                continue

            print(f"Processing: {file_path}")

            try:
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                cmd = [
                    ffmpeg_exe,
                    "-y",
                    "-i",
                    str(file_path),
                    "-vn",
                    "-acodec",
                    "libmp3lame",
                    "-q:a",
                    "2",
                    str(output_audio_path),
                ]
                result = subprocess.run(
                    cmd,
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if result.returncode != 0:
                    ffmpeg_error = result.stderr or "Unknown ffmpeg error"
                    if "Output file #0 does not contain any stream" in ffmpeg_error:
                        print("  -> No audio track found. Skipped.\n")
                        skipped += 1
                        continue
                    raise RuntimeError(ffmpeg_error.strip())

                print("  -> Done.\n")
                processed += 1
            except Exception as exc:
                print(f"  -> Failed: {exc}\n")
                failed += 1

    print("Finished.")
    print(f"Extracted: {processed}")
    print(f"Skipped (no audio): {skipped}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    batch_extract_audio(TARGET_DIRECTORY, OUTPUT_DIRECTORY)
