"""faster-whisper adapter using a pre-downloaded local model directory."""
import math
from pathlib import Path
from audio.asr.base import SpeechModel
from schemas.transcript import TranscriptSegment


class WhisperASR(SpeechModel):
    def __init__(self, model_path, device="cpu", compute_type="int8", language="en"):
        self.model_path = Path(model_path)
        if not self.model_path.is_dir():
            raise FileNotFoundError(f"Local faster-whisper model missing: {self.model_path}")
        self.device, self.compute_type, self.language = device, compute_type, language

    def transcribe(self, audio):
        from faster_whisper import WhisperModel
        if not Path(audio).is_file():
            raise FileNotFoundError(audio)
        model = WhisperModel(str(self.model_path), device=self.device, compute_type=self.compute_type, local_files_only=True)
        segments, _ = model.transcribe(str(audio), language=self.language, vad_filter=True)
        # exp(avg_logprob) is an ASR confidence proxy, not a calibrated command probability.
        return [TranscriptSegment(s.start, s.end, s.text.strip(), min(1.0, math.exp(s.avg_logprob))) for s in segments]
