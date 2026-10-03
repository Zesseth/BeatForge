"""Tests for drumgen analyze / beatforge.audio.analyze (M2.1).

All fixtures are synthesised at test time. No network — tests run under
the ``no_network`` marker as well.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

from beatforge.audio.analyze import (
    SCHEMA_VERSION,
    Analysis,
    analysis_to_json,
    analyze_audio,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_fixture import synth_click_track  # noqa: E402

FIXTURE_PARAMS = [
    ("click_120bpm.wav", 120.0),
    ("click_140bpm.wav", 140.0),
    ("click_90bpm.flac", 90.0),
    ("sinebass_120bpm.wav", 120.0),
]

pytestmark = pytest.mark.no_network


class _NoSockets:
    def __init__(self, *args: object, **kwargs: object) -> None:
        raise AssertionError("network call attempted during audio analysis")


@pytest.fixture
def block_sockets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "socket", _NoSockets)


@pytest.mark.parametrize("name,bpm", FIXTURE_PARAMS[1:], ids=[p[0] for p in FIXTURE_PARAMS[1:]])
def test_estimated_bpm_within_2_percent(
    fixture_dir: Path, block_sockets: None, name: str, bpm: float
) -> None:
    result = analyze_audio(fixture_dir / name)
    assert abs(result.tempo_bpm - bpm) / bpm <= 0.02, (
        f"{name}: estimated {result.tempo_bpm:.2f}, expected {bpm}"
    )


def test_estimated_bpm_click120(fixture_dir: Path, block_sockets: None) -> None:
    result = analyze_audio(fixture_dir / "click_120bpm.wav")
    assert abs(result.tempo_bpm - 120.0) / 120.0 <= 0.02


def test_schema_validates(fixture_dir: Path, block_sockets: None) -> None:
    result = analyze_audio(fixture_dir / "click_120bpm.wav")
    assert result.schema_version == SCHEMA_VERSION
    assert isinstance(result, Analysis)
    assert result.time_signature == "4/4"
    assert len(result.beats_s) >= 2
    assert result.downbeats_s == result.beats_s[::4]
    assert len(result.bars) >= 1
    assert result.bars[0].start_s == pytest.approx(result.beats_s[0])


def test_sha256_matches_file(fixture_dir: Path, block_sockets: None) -> None:
    import hashlib

    path = fixture_dir / "click_120bpm.wav"
    result = analyze_audio(path)
    assert result.source.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_bpm_override_skips_estimation(fixture_dir: Path, block_sockets: None) -> None:
    result = analyze_audio(fixture_dir / "click_120bpm.wav", bpm_override=180.0)
    assert result.tempo_bpm == 180.0
    assert result.tempo_confidence == 1.0
    assert result.beats_s[0] == pytest.approx(0.0)
    assert pytest.approx(result.beats_s[1] - result.beats_s[0], abs=1e-6) == 60.0 / 180.0


def test_time_signature_3_4(fixture_dir: Path, block_sockets: None) -> None:
    result = analyze_audio(
        fixture_dir / "click_120bpm.wav", bpm_override=120.0, time_signature="3/4"
    )
    assert result.time_signature == "3/4"
    assert result.downbeats_s == result.beats_s[::3]


def test_unsupported_format_rejected(tmp_path: Path, block_sockets: None) -> None:
    bad = tmp_path / "song.mp3"
    bad.write_bytes(b"not really audio")
    with pytest.raises(ValueError, match="unsupported audio format"):
        analyze_audio(bad)


def test_missing_file_rejected(tmp_path: Path, block_sockets: None) -> None:
    with pytest.raises(FileNotFoundError):
        analyze_audio(tmp_path / "missing.wav")


def test_bpm_override_range_checked(tmp_path: Path, block_sockets: None) -> None:
    import soundfile as sf

    path = tmp_path / "click.wav"
    sf.write(str(path), synth_click_track(120.0), 22050, subtype="PCM_16")
    with pytest.raises(ValueError, match="bpm-override out of range"):
        analyze_audio(path, bpm_override=1000.0)


def test_deterministic_output(fixture_dir: Path, block_sockets: None) -> None:
    a = analysis_to_json(analyze_audio(fixture_dir / "click_120bpm.wav"))
    b = analysis_to_json(analyze_audio(fixture_dir / "click_120bpm.wav"))
    assert a == b


def test_no_network_modules_imported() -> None:
    import beatforge.audio.analyze as mod
    import beatforge.audio.groove as groove_mod

    banned = ("requests", "httpx", "urllib", "http.client")
    for m in (mod, groove_mod):
        source = Path(m.__file__ or "").read_text(encoding="utf-8")
        for name in banned:
            assert name not in source, f"network symbol {name!r} found in {m.__name__}"


def test_incomplete_trailing_bar_dropped(fixture_dir: Path, block_sockets: None) -> None:
    """8 s at ~120 bpm is 4 bars; the trailing partial bar must be dropped."""
    result = analyze_audio(fixture_dir / "click_120bpm.wav")
    assert len(result.bars) == 4
    for i, bar in enumerate(result.bars):
        assert bar.index == i
        assert bar.start_s < bar.end_s
    assert result.downbeats_s == result.beats_s[::4]


def test_bpm_override_deterministic_json(fixture_dir: Path, block_sockets: None) -> None:
    a = analysis_to_json(analyze_audio(fixture_dir / "click_90bpm.flac", bpm_override=90.0))
    b = analysis_to_json(analyze_audio(fixture_dir / "click_90bpm.flac", bpm_override=90.0))
    assert a == b
