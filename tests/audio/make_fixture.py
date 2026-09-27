"""Generate synthesised audio fixtures for tests — never commit audio.

Usage::

    python tests/audio/make_fixture.py

Writes into ``tests/audio/fixtures/`` (gitignored). All content is
synthesised from math — no copyrighted material. Fixtures are short
(<= 2 s) click/backing tracks with a known BPM.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def synth_click_track(
    bpm: float,
    duration_s: float = 8.0,
    sr: int = 22050,
    accent_every: int = 4,
) -> np.ndarray:
    """Synthesise a click track: one impulse per beat, accented downbeats."""
    n = int(duration_s * sr)
    y = np.zeros(n, dtype=np.float64)
    beat_period = 60.0 / bpm
    t = 0.0
    beat_index = 0
    while t < duration_s:
        start = int(t * sr)
        length = min(int(0.030 * sr), n - start)
        if length > 0:
            decay = np.exp(-np.linspace(0.0, 9.0, length))
            amp = 0.9 if beat_index % accent_every == 0 else 0.55
            y[start : start + length] += amp * decay
        t += beat_period
        beat_index += 1
    return y


def synth_sine_bass(
    bpm: float, duration_s: float = 8.0, sr: int = 22050, freq: float = 82.0
) -> np.ndarray:
    """Sine 'bass' plucked on every beat — a non-click tempo case."""
    n = int(duration_s * sr)
    y = np.zeros(n, dtype=np.float64)
    t = np.arange(n) / sr
    y += 0.25 * np.sin(2 * np.pi * freq * t)
    beat_period = 60.0 / bpm
    beat_index = 0
    start = 0
    while start < n:
        length = min(int(0.20 * sr), n - start)
        if length > 0:
            y[start : start + length] += 0.7 * np.exp(-np.linspace(0.0, 7.0, length))
        beat_index += 1
        start = int(beat_index * beat_period * sr)
    return y


def main() -> int:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    fixtures = [
        ("click_120bpm.wav", synth_click_track(120.0)),
        ("click_140bpm.wav", synth_click_track(140.0)),
        ("click_90bpm.flac", synth_click_track(90.0)),
        ("sinebass_120bpm.wav", synth_sine_bass(120.0)),
    ]
    for name, y in fixtures:
        path = FIXTURE_DIR / name
        sf.write(str(path), y, 22050, subtype="PCM_16" if name.endswith(".wav") else "PCM_16")
        print(f"wrote {path} ({y.size / 22050:.2f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
