"""Groove extraction for ``drumgen groove`` (M2.2).

Extends :mod:`beatforge.audio.analyze` with onset *timestamps* and coarse
section hints. The output is the contract between local audio analysis and
any future MIDI generator.

Privacy invariants (hard rules, enforced by tests):

* **No amplitude curves, no spectral features, no MFCCs, no chroma** ever
  appear in ``groove.json``. Only timestamps and per-bar counts.
* Everything in this module is local-only; no HTTP client is imported.
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from .analyze import (
    LIBROSA_ANALYSIS_SR,
    LIBROSA_HOP_LENGTH,
    Analysis,
    analyze_audio,
)

GROOVE_SCHEMA_VERSION = "1.0"


class SectionHint(BaseModel):
    """Best-effort section label over an inclusive bar range."""

    model_config = ConfigDict(extra="forbid")

    label: str
    bar_start: int = Field(ge=0)
    bar_end: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)


class Groove(Analysis):
    """The ``groove.json`` schema (v1). Extends ``analysis.json``.

    See docs/GROOVE_JSON.md. Onset data is timestamps only — never
    amplitudes, envelopes, or spectra.
    """

    onsets_s: list[float] = Field(default_factory=list)
    onset_density_per_bar: list[int] = Field(default_factory=list)
    section_hints: list[SectionHint] = Field(default_factory=list)


_ONSET_KEYS_FORBIDDEN = (
    "onset_amplitudes",
    "onset_envelope",
    "onset_strength",
    "mfcc",
    "chroma",
    "spectral_centroid",
    "spectrogram",
    "amplitudes",
)


def _onset_timestamps(path: Path) -> list[float]:
    """Onset timestamps (seconds) detected locally via librosa."""
    y, sr = librosa.load(str(path), sr=LIBROSA_ANALYSIS_SR, mono=True)
    frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames", hop_length=LIBROSA_HOP_LENGTH)
    times = librosa.frames_to_time(frames, sr=sr, hop_length=LIBROSA_HOP_LENGTH)
    return [round(float(t), 6) for t in times]


def _onset_density_per_bar(onsets: list[float], bars: list[tuple[float, float]]) -> list[int]:
    """Count onsets inside each bar half-open interval [start, end)."""
    if not bars:
        return []
    starts = np.asarray([b[0] for b in bars], dtype=np.float64)
    ends = np.asarray([b[1] for b in bars], dtype=np.float64)
    if not onsets:
        return [0] * len(bars)
    onsets_arr = np.asarray(onsets, dtype=np.float64)
    return [
        int(np.count_nonzero((onsets_arr >= s) & (onsets_arr < e)))
        for s, e in zip(starts, ends, strict=True)
    ]


def _section_hints(
    density: list[int], *, window: int = 4, low_confidence: float = 0.35
) -> list[SectionHint]:
    """Coarse verse/chorus hints from onset-density step changes.

    Bars are chunked into windows; a chunk whose mean density is well
    above the overall median is labelled ``chorus``, otherwise ``verse``.
    Confidence is a simple monotone map of how far the chunk mean is from
    the median (0.35 floor so weak hints stay ignorable).
    """
    if not density:
        return []
    med = float(np.median(np.asarray(density, dtype=np.float64)))
    if med <= 0:
        med = max(1.0, float(np.mean(density)))

    hints: list[SectionHint] = []
    for chunk_start in range(0, len(density), window):
        chunk = density[chunk_start : chunk_start + window]
        if not chunk:
            break
        mean = float(np.mean(chunk))
        ratio = mean / med if med > 0 else 0.0
        if ratio > 1.25:
            label = "chorus"
            confidence = min(1.0, low_confidence + 0.65 * min(1.0, (ratio - 1.25)))
        else:
            label = "verse"
            deviation = max(0.0, 1.0 - ratio)
            confidence = min(1.0, low_confidence + 0.65 * min(1.0, deviation))
        hints.append(
            SectionHint(
                label=label,
                bar_start=chunk_start,
                bar_end=chunk_start + len(chunk) - 1,
                confidence=round(confidence, 4),
            )
        )
    return hints


def groove_from_analysis(
    analysis: Analysis,
    onsets_s: list[float],
) -> Groove:
    """Build a :class:`Groove` from an :class:`Analysis` plus onset timestamps."""
    bars = [(b.start_s, b.end_s) for b in analysis.bars]
    density = _onset_density_per_bar(onsets_s, bars)
    hints = _section_hints(density)
    base = analysis.model_dump()
    base["schema_version"] = GROOVE_SCHEMA_VERSION
    return Groove(
        **base,
        onsets_s=onsets_s,
        onset_density_per_bar=density,
        section_hints=hints,
    )


def analyze_groove(
    audio_path: Path | str,
    *,
    bpm_override: float | None = None,
    time_signature: str = "4/4",
) -> Groove:
    """Run full groove analysis on a local audio file. Local-only, no network."""
    path = Path(audio_path)
    analysis = analyze_audio(path, bpm_override=bpm_override, time_signature=time_signature)
    onsets = _onset_timestamps(path)
    return groove_from_analysis(analysis, onsets)


def assert_no_audio_features(payload: dict[str, object]) -> None:
    """Guard used by tests: forbidden audio-feature keys must not appear."""

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(key, str):
                    lowered = key.lower()
                    for forbidden in _ONSET_KEYS_FORBIDDEN:
                        if forbidden in lowered:
                            raise ValueError(
                                f"privacy violation: audio-feature key {key!r} "
                                "present in groove output"
                            )
                _walk(value)
        elif isinstance(node, (list, tuple)):
            for item in node:
                _walk(item)

    _walk(payload)


def groove_to_json(groove: Groove) -> str:
    """Serialise deterministically and fail if audio features leak in."""
    payload = groove.model_dump(mode="json")
    assert_no_audio_features(payload)
    return groove.model_dump_json(indent=2) + "\n"
