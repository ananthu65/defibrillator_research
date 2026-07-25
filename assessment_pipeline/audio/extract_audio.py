"""
extract_audio.py

Extracts audio from a video file and saves it as a 16kHz mono WAV,
the format Whisper expects.
"""

import subprocess
import sys
from pathlib import Path

"""
extract_audio.py

Extracts audio from a video file and saves it as a 16kHz mono WAV,
the format Whisper expects.
"""

import subprocess
import sys
from pathlib import Path


def extract_audio(video_path: str, output_dir: str = "data/audio") -> str:
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{video_path.stem}.wav"

    command = [
        "ffmpeg",
        "-y",  # overwrite without asking
        "-i", str(video_path),
        "-vn",  # strip video
        "-acodec", "pcm_s16le",
        "-ar", "16000",  # 16kHz, what Whisper expects
        "-ac", "1",  # mono
        str(output_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {video_path}:\n{result.stderr}")

    return str(output_path)


def extract_audio_batch(video_dir: str = "data/videos", output_dir: str = "data/audio"):
    video_dir = Path(video_dir)
    extensions = ["*.mp4", "*.MP4", "*.mov", "*.MOV"]
    video_files = [f for ext in extensions for f in video_dir.glob(ext)]

    if not video_files:
        print(f"No video files found in {video_dir}")
        return []

    output_paths = []
    for video_file in video_files:
        print(f"Extracting: {video_file.name}...")
        try:
            output_path = extract_audio(str(video_file), output_dir)
            output_paths.append(output_path)
            print(f"  -> {output_path}")
        except RuntimeError as e:
            print(f"  FAILED: {e}")

    return output_paths


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_audio.py <video_path> [output_dir]")
        print("   or: python extract_audio.py --batch <video_dir> [output_dir]")
        sys.exit(1)

    if sys.argv[1] == "--batch":
        video_dir = sys.argv[2] if len(sys.argv) > 2 else "data/videos"
        output_dir = sys.argv[3] if len(sys.argv) > 3 else "data/audio"
        extract_audio_batch(video_dir, output_dir)
    else:
        video_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "data/audio"
        output_path = extract_audio(video_path, output_dir)
        print(f"Extracted audio saved to: {output_path}")

