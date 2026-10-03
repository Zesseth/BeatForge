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
    spec = StyleSpec(genre="rock", hats="8th", fills="none")
    events = generate_aligned_events(analysis, spec, seed=42, ppq=480)

    subdivisions = 2
    slot_ticks = 480 // subdivisions
    first_downbeat = min(ev.start_tick for ev in events)
    for ev in events:
        assert (ev.start_tick - first_downbeat) % slot_ticks == 0, (
            f"tick {ev.start_tick} off 8th grid"
        )


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


def _synthetic_analysis(
    bars: int = 2, bpm: float = 120.0, first_beat_s: float = 0.0, time_signature: str = "4/4"
):
    from beatforge.audio.analyze import Analysis, Bar, SourceInfo

    beat_period = 60.0 / bpm
    ts_num = int(time_signature.split("/")[0])
    beats_per_bar = ts_num
    beats = [round(first_beat_s + i * beat_period, 6) for i in range(bars * beats_per_bar + 1)]
    bar_objs = [
        Bar(index=i, start_s=beats[i * beats_per_bar], end_s=beats[(i + 1) * beats_per_bar])
        for i in range(bars)
    ]
    return Analysis(
        schema_version="1.0",
        source=SourceInfo(sha256="0" * 64, duration_s=30.0, sr=22050),
        tempo_bpm=bpm,
        tempo_confidence=1.0,
        time_signature=time_signature,
        beats_s=beats,
        downbeats_s=beats[::beats_per_bar],
        bars=bar_objs,
    )


def test_no_complete_bars_rejected() -> None:
    analysis = _synthetic_analysis(bars=0)
    with pytest.raises(ValueError, match="no complete bar"):
        generate_aligned_events(analysis, StyleSpec(genre="rock"))


def test_non_quarter_denominator_rejected() -> None:
    analysis = _synthetic_analysis(bars=2, time_signature="6/8")
    with pytest.raises(ValueError, match="/4 denominators only"):
        generate_aligned_events(analysis, StyleSpec(genre="rock"))


def test_events_follow_analysed_downbeat_offset() -> None:
    offset_s = 0.512
    analysis = _synthetic_analysis(bars=2, first_beat_s=offset_s)
    events = generate_aligned_events(analysis, StyleSpec(genre="rock"), seed=1, ppq=480)
    ticks_per_second = 120.0 / 60.0 * 480
    expected_first = round(offset_s * ticks_per_second)
    assert min(ev.start_tick for ev in events) == expected_first


def test_fills_policies_differ() -> None:
    analysis = _synthetic_analysis(bars=4)
    specs = {
        mode: StyleSpec(genre="rock", fills=mode)  # type: ignore[arg-type]
        for mode in ("none", "fewer", "default", "before_chorus")
    }
    crash_sets = {
        mode: {ev.start_tick for ev in generate_aligned_events(analysis, s, seed=1)}
        for mode, s in specs.items()
    }
    assert crash_sets["none"] != crash_sets["fewer"]
    assert crash_sets["fewer"] != crash_sets["default"]


def test_fill_stays_within_final_bar() -> None:
    analysis = _synthetic_analysis(bars=2)
    for hats in ("8th", "shuffle", "16th"):
        spec = StyleSpec(genre="rock", hats=hats, fills="fewer")
        events = generate_aligned_events(analysis, spec, seed=1, ppq=480)
        bar_ticks = 4 * 480
        assert max(ev.start_tick for ev in events) < bar_ticks * 2


def test_cli_rejects_unknown_tempo_mode(click_wav: Path, tmp_path: Path) -> None:
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
            "--tempo-mode",
            "fiexed",
            "--seed",
            "42",
            "--out",
            str(tmp_path / "drums.mid"),
        ],
    )
    assert result.exit_code != 0
    assert "tempo-mode" in result.output


def test_cli_cache_analysis_is_valid_analysis(click_wav: Path, tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from beatforge.cli.main import app
    from beatforge.gen.aligned import load_analysis

    cache_dir = tmp_path / "cache"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "generate",
            "--audio",
            str(click_wav),
            "--prompt",
            "rock",
            "--cache-dir",
            str(cache_dir),
            "--seed",
            "42",
            "--out",
            str(tmp_path / "drums.mid"),
        ],
    )
    assert result.exit_code == 0, result.output
    cached = cache_dir / f"{click_wav.stem}.analysis.json"
    assert cached.exists()
    payload = json.loads(cached.read_text(encoding="utf-8"))
    assert "onsets_s" not in payload
    loaded = load_analysis(cached)
    assert loaded.tempo_bpm > 0
