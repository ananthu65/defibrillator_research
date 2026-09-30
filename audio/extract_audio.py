import argparse
import os
import subprocess
from pathlib import Path

def extract_track(video: Path, output: Path) -> Path:
    """Decode one recording to mono 16 kHz WAV; configure any track offset explicitly."""
    import imageio_ffmpeg
    if not video.is_file():
        raise FileNotFoundError(video)
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-v", "error", "-n", "-i", str(video),
                    "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(output)],
                   check=True, capture_output=True)
    return output

# Output folder inside this repository
OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "data/audio/extracted"

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".m4v"}


def batch_extract_audio(input_folder: str, output_folder: Path) -> None:
    import imageio_ffmpeg
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

            # Preserve source subdirectories so equal stems cannot overwrite
            # or silently skip recordings belonging to another participant.
            relative_parent = file_path.parent.relative_to(input_path)
            output_parent = output_folder / relative_parent
            output_parent.mkdir(parents=True, exist_ok=True)
            default_output = output_parent / f"{file_path.stem}_audio.mp3"
            if default_output.exists():
                print(f"Processing: {file_path}")
                print("  -> Audio already exists. Skipped.\n")
                skipped += 1
                continue
            output_audio_path = default_output

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
    print(f"Skipped (already extracted or no audio): {skipped}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract audio from a local video directory")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", default=OUTPUT_DIRECTORY, type=Path)
    args = parser.parse_args()
    if not args.input.is_dir():
        parser.error("Input must be an existing directory")
    batch_extract_audio(str(args.input), args.output)
