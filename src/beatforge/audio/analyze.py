"""Local audio analysis for ``drumgen analyze`` (M2.1).

Library choice: librosa 0.11.x (documented here per AGENTS.md §5 — one
analysis library per module; mido is never mixed into this file).

Privacy contract: everything in this module is local-only. The module must
not import any HTTP client. ``librosa.load`` reads the file from disk and
never transmits it; the no-audio-egress static harness plus the socket
sandbox in ``tests/privacy`` enforce this.

Determinism: the same input file plus the same pinned librosa/numpy
versions produce byte-identical ``analysis.json`` output. No wall-clock,
no unseeded randomness is used anywhere in this module.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"

SUPPORTED_SUFFIXES = frozenset({".wav", ".flac"})
LIBROSA_ANALYSIS_SR = 22050
# 256-sample hop (~11.6 ms at 22.05 kHz) keeps tempo estimation well
# inside the ±2% DoD tolerance for click-track fixtures (512 was ~2.5% off).
LIBROSA_HOP_LENGTH = 256


class SourceInfo(BaseModel):
    """Provenance of the analysed file. Hash is SHA-256 of the raw file bytes."""

    model_config = ConfigDict(extra="forbid")

    sha256: str
    duration_s: float = Field(ge=0.0)
    sr: int = Field(gt=0)


class Bar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    start_s: float = Field(ge=0.0)
    end_s: float = Field(ge=0.0)


class Analysis(BaseModel):
    """The ``analysis.json`` schema (v1). See docs/ANALYSIS_JSON.md."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    source: SourceInfo
    tempo_bpm: float = Field(gt=0.0)
    tempo_confidence: float = Field(ge=0.0, le=1.0)
    time_signature: str
    beats_s: list[float] = Field(default_factory=list)
    downbeats_s: list[float] = Field(default_factory=list)
    bars: list[Bar] = Field(default_factory=list)


def _parse_time_signature(time_signature: str) -> tuple[int, int]:
    try:
        num_str, den_str = time_signature.split("/", 1)
        num, den = int(num_str), int(den_str)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"invalid time signature {time_signature!r}") from exc
    if num <= 0 or den <= 0:
        raise ValueError(f"invalid time signature {time_signature!r}")
    return num, den


def _sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_info(path: Path) -> SourceInfo:
    info = sf.info(str(path))
    return SourceInfo(
        sha256=_sha256_of_file(path), duration_s=float(info.duration), sr=int(info.samplerate)
    )


def _derive_beats_from_bpm(bpm: float, duration_s: float) -> list[float]:
    """Evenly spaced beat grid starting at 0.0 up to the audio duration."""
    if duration_s <= 0.0:
        return []
    beat_period = 60.0 / bpm
    count = int(duration_s / beat_period) + 1
    return [round(i * beat_period, 6) for i in range(count)]


def _median_beat_period(beats: list[float], bpm_hint: float) -> float:
    """Median inter-beat interval, or the hint-derived period when too few beats."""
    if len(beats) >= 2:
        periods = np.diff(np.asarray(beats, dtype=np.float64))
        return float(np.median(periods))
    return 60.0 / bpm_hint


def _confidence_from_beats(beats: list[float], tempo_bpm: float) -> float:
    """Weak heuristic confidence from beat-interval consistency.

    1.0 would mean perfectly even beat spacing. Fewer than three beats
    (a degenerate file) yields 0.0.
    """
    if len(beats) < 3:
        return 0.0
    periods = np.diff(np.asarray(beats, dtype=np.float64))
    expected = 60.0 / tempo_bpm
    if expected <= 0:
        return 0.0
    mad = float(np.mean(np.abs(periods - expected)))
    return round(max(0.0, min(1.0, 1.0 - mad / expected)), 4)


def _downbeats_and_bars(
    beats: list[float], duration_s: float, beats_per_bar: int
) -> tuple[list[float], list[Bar]]:
    """Group beats into bars; drop a trailing incomplete bar.

    A bar is complete only if its last beat exists AND the bar's end
    (last beat + one beat period) fits inside the audio duration — the
    "MIDI length matches audio duration rounded down to the nearest bar"
    requirement from M2.3. ``downbeats_s`` stays a pure property of the
    beat list (every Nth beat) regardless of bar truncation.
    """
    if not beats:
        return [], []
    downbeats = beats[::beats_per_bar]

    periods = np.diff(np.asarray(beats, dtype=np.float64))
    beat_period = float(np.median(periods)) if len(beats) >= 2 else 0.0

    complete_bars = len(beats) // beats_per_bar
    bars: list[Bar] = []
    for i in range(complete_bars):
        start = beats[i * beats_per_bar]
        end_index = (i + 1) * beats_per_bar
        if end_index < len(beats):
            end = beats[end_index]
        elif beat_period > 0:
            end = beats[end_index - 1] + beat_period
            if duration_s > 0 and end > duration_s + 1e-3:
                break
        else:
            break
        bars.append(Bar(index=i, start_s=round(start, 6), end_s=round(end, 6)))

    return downbeats, bars


def analyze_audio(
    audio_path: Path | str,
    *,
    bpm_override: float | None = None,
    time_signature: str = "4/4",
) -> Analysis:
    """Analyse a local audio file and return the :class:`Analysis` result.

    All processing is local. Raises ``ValueError`` for unsupported formats
    or bad parameters.
    """
    path = Path(audio_path)
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"unsupported audio format {path.suffix!r}; supported: {sorted(SUPPORTED_SUFFIXES)}"
        )
    if not path.is_file():
        raise FileNotFoundError(f"audio file not found: {path}")

    if bpm_override is not None and not (20.0 <= bpm_override <= 400.0):
        raise ValueError(f"bpm-override out of range (20-400): {bpm_override}")

    beats_per_bar, _den = _parse_time_signature(time_signature)
    source = _source_info(path)

    if bpm_override is not None:
        tempo_bpm = float(bpm_override)
        beats = _derive_beats_from_bpm(tempo_bpm, source.duration_s)
        tempo_confidence = 1.0
    else:
        y, sr = librosa.load(str(path), sr=LIBROSA_ANALYSIS_SR, mono=True)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=LIBROSA_HOP_LENGTH)
        tempo_value, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env,
            sr=sr,
            hop_length=LIBROSA_HOP_LENGTH,
            trim=False,
            sparse=True,
        )
        tempo_hint = float(np.atleast_1d(tempo_value)[0])
        beats = [
            round(float(t), 6)
            for t in librosa.frames_to_time(beat_frames, sr=sr, hop_length=LIBROSA_HOP_LENGTH)
        ]
        if len(beats) >= 2:
            tempo_bpm = 60.0 / _median_beat_period(beats, tempo_hint)
        elif tempo_hint > 0.0:
            tempo_bpm = tempo_hint
        else:
            raise ValueError(f"could not estimate tempo from {path.name}; try --bpm-override")
        tempo_confidence = _confidence_from_beats(beats, tempo_bpm)

    downbeats, bars = _downbeats_and_bars(beats, source.duration_s, beats_per_bar)

    return Analysis(
        schema_version=SCHEMA_VERSION,
        source=source,
        tempo_bpm=round(tempo_bpm, 4),
        tempo_confidence=tempo_confidence,
        time_signature=f"{beats_per_bar}/{_den}",
        beats_s=beats,
        downbeats_s=[round(float(d), 6) for d in downbeats],
        bars=bars,
    )


def analysis_to_json(analysis: Analysis) -> str:
    """Serialise deterministically (sorted keys, fixed float formatting)."""
    return analysis.model_dump_json(indent=2) + "\n"
