"""MFCC mean/std baseline for mono, 16 kHz, one-second WAV windows."""
from pathlib import Path

SAMPLE_RATE = 16000
WINDOW_SECONDS = 1.0
HOP_SECONDS = 0.5


def load_audio(path):
    import numpy as np
    from scipy.io import wavfile
    from scipy.signal import resample_poly
    from math import gcd
    rate, samples = wavfile.read(Path(path))
    dtype = samples.dtype
    samples = samples.astype(np.float64)
    if dtype.kind in "iu":
        info = np.iinfo(dtype)
        if dtype.kind == "u":
            samples -= (info.max + 1) / 2
            samples /= (info.max + 1) / 2
        else:
            samples /= max(abs(info.min), info.max)
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    if rate <= 0 or samples.size == 0 or not np.isfinite(samples).all():
        raise ValueError("WAV must contain finite samples at a positive sample rate")
    if rate != SAMPLE_RATE:
        divisor = gcd(rate, SAMPLE_RATE)
        samples = resample_poly(samples, SAMPLE_RATE // divisor, rate // divisor)
    return samples


def mfcc_stats(samples):
    import numpy as np
    from scipy.fft import dct
    if len(samples) != SAMPLE_RATE:
        raise ValueError("MFCC input must be exactly one second at 16 kHz")
    emphasized = np.append(samples[0], samples[1:] - 0.97 * samples[:-1])
    frames = np.lib.stride_tricks.sliding_window_view(emphasized, 400)[::160]
    power = np.abs(np.fft.rfft(frames * np.hamming(400), n=512)) ** 2 / 512
    mel = np.linspace(0, 2595 * np.log10(1 + (SAMPLE_RATE / 2) / 700), 28)
    hz = 700 * (10 ** (mel / 2595) - 1)
    frequencies = np.fft.rfftfreq(512, 1 / SAMPLE_RATE)
    filters = np.array([np.maximum(0, np.minimum((frequencies - a) / (b - a), (c - frequencies) / (c - b)))
                        for a, b, c in zip(hz[:-2], hz[1:-1], hz[2:])])
    coefficients = dct(np.log(np.maximum(power @ filters.T, 1e-12)), type=2, axis=1, norm="ortho")[:, :13]
    return np.concatenate((coefficients.mean(axis=0), coefficients.std(axis=0)))


def extract_windows(path):
    """Only complete windows are used; recordings shorter than one second fail."""
    import numpy as np
    samples = load_audio(path)
    if len(samples) < SAMPLE_RATE:
        raise ValueError("Charging classifier requires at least one second of audio")
    starts = range(0, len(samples) - SAMPLE_RATE + 1, int(HOP_SECONDS * SAMPLE_RATE))
    times, features = [], []
    for start in starts:
        times.append(start / SAMPLE_RATE)
        features.append(mfcc_stats(samples[start:start + SAMPLE_RATE]))
    return times, np.asarray(features)
