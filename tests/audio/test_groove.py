"""Tests for drumgen groove / beatforge.audio.groove (M2.2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from beatforge.audio.analyze import Analysis
from beatforge.audio.groove import (
    Groove,
    analyze_groove,
    assert_no_audio_features,
    groove_from_analysis,
    groove_to_json,
)

pytestmark = pytest.mark.no_network


def test_groove_schema_validates(fixture_dir: Path) -> None:
    groove = analyze_groove(fixture_dir / "click_120bpm.wav")
    assert isinstance(groove, Groove)
    assert isinstance(groove, Analysis)
    assert groove.onsets_s
    assert groove.onset_density_per_bar
    assert len(groove.onset_density_per_bar) == len(groove.bars)
    assert sum(groove.onset_density_per_bar) <= len(groove.onsets_s)


def test_onset_count_sensible_range(fixture_dir: Path) -> None:
    groove = analyze_groove(fixture_dir / "click_120bpm.wav", bpm_override=120.0)
    beats = len(groove.beats_s)
    onsets = len(groove.onsets_s)
    # a click track yields roughly one onset per beat; the detector may miss
    # the first (t=0) and last decaying clicks
    assert abs(onsets - beats) <= 3, f"onsets={onsets} beats={beats}"
    assert onsets >= 4


def test_no_amplitude_or_spectral_data_in_output(fixture_dir: Path) -> None:
    text = groove_to_json(analyze_groove(fixture_dir / "click_120bpm.wav"))
    payload = json.loads(text)
    assert_no_audio_features(payload)
    forbidden = ("amplitude", "envelope", "mfcc", "chroma", "spectrogram", "spectral")
    lowered = json.dumps(payload).lower()
    for term in forbidden:
        assert term not in lowered, f"privacy violation: {term!r} in groove.json"


def test_allow_list_keys_only(fixture_dir: Path) -> None:
    payload = json.loads(groove_to_json(analyze_groove(fixture_dir / "click_120bpm.wav")))
    allowed = {
        "schema_version",
        "source",
        "tempo_bpm",
        "tempo_confidence",
        "time_signature",
        "beats_s",
        "downbeats_s",
        "bars",
        "onsets_s",
        "onset_density_per_bar",
        "section_hints",
        "sha256",
        "duration_s",
        "sr",
        "index",
        "start_s",
        "end_s",
        "label",
        "bar_start",
        "bar_end",
        "confidence",
    }
    found: set[str] = set()

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            found.update(node.keys())
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)
    assert found <= allowed, f"unexpected keys: {found - allowed}"


def test_assert_no_audio_features_catches_violation() -> None:
    with pytest.raises(ValueError, match="privacy violation"):
        assert_no_audio_features({"onset_envelope": [0.1, 0.2]})


def test_section_hints_confidence_range(fixture_dir: Path) -> None:
    groove = analyze_groove(fixture_dir / "click_120bpm.wav")
    for hint in groove.section_hints:
        assert hint.label in ("verse", "chorus")
        assert 0.0 <= hint.confidence <= 1.0
        assert hint.bar_start <= hint.bar_end


def test_groove_from_analysis_with_synthetic_onsets() -> None:
    analysis = analyze_audio_bpm_override()
    onsets = [0.0, 0.5, 1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
    groove = groove_from_analysis(analysis, onsets)
    assert sum(groove.onset_density_per_bar) > 0


def analyze_audio_bpm_override() -> Analysis:
    """Helper: construct a synthetic 4/4 120bpm analysis without a file."""
    from beatforge.audio.analyze import Bar, SourceInfo

    beat = 0.5
    beats = [round(i * beat, 6) for i in range(16)]
    bars = [Bar(index=i, start_s=beats[i * 4], end_s=beats[(i + 1) * 4]) for i in range(3)] + [
        Bar(index=3, start_s=beats[12], end_s=beats[15] + beat)
    ]
    return Analysis(
        schema_version="1.0",
        source=SourceInfo(sha256="0" * 64, duration_s=8.0, sr=22050),
        tempo_bpm=120.0,
        tempo_confidence=1.0,
        time_signature="4/4",
        beats_s=beats,
        downbeats_s=beats[::4],
        bars=bars,
    )
