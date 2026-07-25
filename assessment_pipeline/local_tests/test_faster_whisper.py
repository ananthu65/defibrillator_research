from faster_whisper import WhisperModel
import time

model_size = "large-v3"  # first run will auto-download the model (~2.9GB)
model = WhisperModel(model_size, device="cpu", compute_type="int8")

start = time.time()
segments, info = model.transcribe("../data/audio/P10_LL.wav", vad_filter=True, language="en")

for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")

print(f"\nTook {time.time() - start:.1f}s | detected language: {info.language}")


