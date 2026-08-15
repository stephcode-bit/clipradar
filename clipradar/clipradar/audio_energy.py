"""Cheap audio-energy envelope used as one of the scoring signals.

We decode the audio track to mono 16kHz PCM via ffmpeg (no extra Python
audio deps needed), compute an RMS envelope in fixed windows, and expose a
function that returns a z-score for the loudest window inside a given
[start, end) range. A spike usually means a raised voice, laughter, or a
punchline landing.
"""

import subprocess

import numpy as np

WINDOW_SECONDS = 0.5


def _decode_pcm(media_path: str, sample_rate: int = 16000) -> np.ndarray:
    cmd = [
        "ffmpeg", "-v", "error", "-i", media_path,
        "-f", "f32le", "-ac", "1", "-ar", str(sample_rate), "pipe:1",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0 or not proc.stdout:
        return np.array([], dtype=np.float32)
    return np.frombuffer(proc.stdout, dtype=np.float32)


def build_energy_lookup(media_path: str, sample_rate: int = 16000):
    """Returns a function(start, end) -> z-score of peak RMS energy in that
    window relative to the whole track. Returns None if decoding fails."""
    samples = _decode_pcm(media_path, sample_rate)
    if samples.size == 0:
        return None

    win = int(WINDOW_SECONDS * sample_rate)
    n_windows = max(1, samples.size // win)
    trimmed = samples[: n_windows * win].reshape(n_windows, win)
    rms = np.sqrt(np.mean(trimmed ** 2, axis=1) + 1e-12)
    mean, std = float(np.mean(rms)), float(np.std(rms) + 1e-9)

    def lookup(start: float, end: float) -> float:
        i0 = max(0, int(start / WINDOW_SECONDS))
        i1 = min(n_windows, max(i0 + 1, int(end / WINDOW_SECONDS)))
        if i0 >= n_windows:
            return 0.0
        window_slice = rms[i0:i1]
        if window_slice.size == 0:
            return 0.0
        peak = float(np.max(window_slice))
        return (peak - mean) / std

    return lookup
