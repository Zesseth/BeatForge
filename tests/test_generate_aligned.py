"""Tests for drumgen generate --audio (M2.3, audio-aligned generation)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import mido
import pytest

from beatforge.audio.analyze import analyze_audio
from beatforge.gen.aligned import generate_aligned_events
from beatforge.midi.validator import validate_midi_file
from beatforge.prompt.stylespec import StyleSpec

sys.path.insert(0, str(Path(__file__).resolve().parent / "audio"))
from make_fixture import synth_click_track  # noqa: E402

pytestmark = pytest.mark.no_network


@pytest.fixture(scope="module")
def click_wav(tmp_path_factory: pytest.TempPathFactory) -> Path:
    import soundfile as sf

    path = tmp_path_factory.mktemp("m23") / "click_120bpm.wav"
    sf.write(str(path), synth_click_track(120.0, duration_s=8.0), 22050, subtype="PCM_16")
    return path


def _write_midi(events, out: Path, bpm: float, ppq: int = 480) -> Path:
    from beatforge.midi.writer import write_drum_midi

    return write_drum_midi(events, out, bpm=bpm, ppq=ppq)


def test_output_tempo_matches_audio(click_wav: Path, tmp_path: Path) -> None:
    analysis = analyze_audio(click_wav)
    spec = StyleSpec(genre="rock")
    events = generate_aligned_events(analysis, spec, seed=42)
    out = _write_midi(events, tmp_path / "drums.mid", bpm=round(analysis.tempo_bpm))

    mid = mido.MidiFile(str(out))
    tempos = [m.tempo for m in mid.tracks[0] if m.type == "set_tempo"]
    assert tempos, "no tempo meta event"
    file_bpm = mido.tempo2bpm(tempos[0])
    assert abs(file_bpm - analysis.tempo_bpm) / analysis.tempo_bpm <= 0.02


def test_midi_length_within_one_bar(click_wav: Path, tmp_path: Path) -> None:
    analysis = analyze_audio(click_wav)
    spec = StyleSpec(genre="rock")
    events = generate_aligned_events(analysis, spec, seed=42)
    out = _write_midi(events, tmp_path / "drums.mid", bpm=round(analysis.tempo_bpm))

    mid = mido.MidiFile(str(out))
    total_ticks = sum(m.time for m in mid.tracks[0])
    ppq = mid.ticks_per_beat
    bar_ticks = 4 * ppq
    midi_bars = total_ticks / bar_ticks
    audio_bars = len(analysis.bars)
    assert abs(midi_bars - audio_bars) <= 1.0, f"midi bars {midi_bars} vs audio bars {audio_bars}"


def test_notes_on_grid_positions(click_wav: Path) -> None:
    analysis = analyze_audio(click_wav)
    spec = StyleSpec(genre="rock", hats="8th")
    events = generate_aligned_events(analysis, spec, seed=42, ppq=480)

    subdivisions = 2
    slot_ticks = 480 // subdivisions
    for ev in events:
        assert ev.start_tick % slot_ticks == 0, f"tick {ev.start_tick} off 8th grid"


def test_output_passes_validator(click_wav: Path, tmp_path: Path) -> None:
    analysis = analyze_audio(click_wav)
    spec = StyleSpec(genre="rock", fills="default")
    events = generate_aligned_events(analysis, spec, seed=42)
    out = _write_midi(events, tmp_path / "drums.mid", bpm=round(analysis.tempo_bpm))
    report = validate_midi_file(out, strict=False)
    assert report.ok, f"validator failed: {report.errors}"


def test_byte_stable_same_seed_same_audio(click_wav: Path, tmp_path: Path) -> None:
    analysis = analyze_audio(click_wav)
    spec = StyleSpec(genre="rock")
    e1 = generate_aligned_events(analysis, spec, seed=1)
    e2 = generate_aligned_events(analysis, spec, seed=1)
    p1 = _write_midi(e1, tmp_path / "a.mid", bpm=120)
    p2 = _write_midi(e2, tmp_path / "b.mid", bpm=120)
    assert p1.read_bytes() == p2.read_bytes()


def test_different_seed_different_velocities(click_wav: Path) -> None:
    analysis = analyze_audio(click_wav)
    spec = StyleSpec(genre="rock")
    e1 = generate_aligned_events(analysis, spec, seed=1)
    e2 = generate_aligned_events(analysis, spec, seed=2)
    v1 = [ev.velocity for ev in e1]
    v2 = [ev.velocity for ev in e2]
    assert v1 != v2


def test_sixteenth_hats_doubles_grid(click_wav: Path) -> None:
    analysis = analyze_audio(click_wav)
    eighth = generate_aligned_events(analysis, StyleSpec(genre="rock", hats="8th"), seed=3)
    sixteenth = generate_aligned_events(analysis, StyleSpec(genre="rock", hats="16th"), seed=3)
    hat = 42
    assert sum(1 for ev in sixteenth if ev.note == hat) == 2 * sum(
        1 for ev in eighth if ev.note == hat
    )


def test_cli_generate_audio(click_wav: Path, tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from beatforge.cli.main import app

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "generate",
            "--audio",
            str(click_wav),
            "--prompt",
            "rock",
            "--seed",
            "42",
            "--out",
            str(tmp_path / "drums.mid"),
        ],
    )
    assert result.exit_code == 0, result.output
    out = tmp_path / "drums.mid"
    assert out.exists()
    report = validate_midi_file(out, strict=False)
    assert report.ok, report.errors


def test_cli_generate_conflicting_sources_rejected(click_wav: Path, tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from beatforge.cli.main import app

    analysis_path = tmp_path / "analysis.json"
    analysis_path.write_text(json.dumps({}), encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "generate",
            "--audio",
            str(click_wav),
            "--analysis",
            str(analysis_path),
            "--prompt",
            "rock",
            "--out",
            str(tmp_path / "drums.mid"),
        ],
    )
    assert result.exit_code != 0


def test_cli_generate_from_analysis_file(click_wav: Path, tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from beatforge.cli.main import app

    analysis_path = tmp_path / "analysis.json"
    result = runner_invoke_analyze(click_wav, analysis_path)
    assert result.exit_code == 0, result.output

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "generate",
            "--analysis",
            str(analysis_path),
            "--prompt",
            "rock",
            "--seed",
            "42",
            "--out",
            str(tmp_path / "drums.mid"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert validate_midi_file(tmp_path / "drums.mid", strict=False).ok


def runner_invoke_analyze(click_wav: Path, out: Path):
    from typer.testing import CliRunner

    from beatforge.cli.main import app

    return CliRunner().invoke(app, ["analyze", "--audio", str(click_wav), "--out", str(out)])
