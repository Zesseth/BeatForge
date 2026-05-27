"""Tests for ``drumgen generate-basic`` and the song generator."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from beatforge.cli.main import app
from beatforge.gen.basic import generate_basic_song
from beatforge.gen.song_structure import structure_for
from beatforge.midi import GM_CLOSED_HAT, GM_KICK, GM_SNARE
from beatforge.midi.validator import validate_midi_file

runner = CliRunner()


def _run(tmp_path: Path, **kw: object) -> Path:
    out = tmp_path / "song.mid"
    args = ["generate-basic", "--out", str(out)]
    for k, v in kw.items():
        args.extend([f"--{k.replace('_', '-')}", str(v)])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    return out


def test_generates_valid_midi(tmp_path: Path) -> None:
    out = _run(tmp_path, bars=80, bpm=120, style="rock", seed=42)
    report = validate_midi_file(out)
    assert report.ok, (report.errors, report.warnings)


def test_byte_stable_with_same_seed(tmp_path: Path) -> None:
    a = _run(tmp_path / "a", bars=32, bpm=120, style="rock", seed=7)
    b = _run(tmp_path / "b", bars=32, bpm=120, style="rock", seed=7)
    assert a.read_bytes() == b.read_bytes()


def test_different_seed_changes_fills(tmp_path: Path) -> None:
    a = _run(tmp_path / "a", bars=32, bpm=120, style="rock", seed=7)
    b = _run(tmp_path / "b", bars=32, bpm=120, style="rock", seed=99)
    # the fill rng dither makes velocities differ → bytes differ.
    assert a.read_bytes() != b.read_bytes()


def test_chorus_is_busier_than_verse() -> None:
    bars = 80
    sections = structure_for(bars)
    events = generate_basic_song(bars=bars, style="rock", seed=42, ppq=480)
    ppq = 480
    beats_per_bar = 4

    bar_offsets: dict[str, list[int]] = {}
    running = 0
    for s in sections:
        bar_offsets.setdefault(s.name, []).extend(range(running, running + s.bars))
        running += s.bars

    def hits_per_bar(name: str, note: int) -> float:
        total = 0
        bars_in = bar_offsets.get(name, [])
        for bar in bars_in:
            start = bar * beats_per_bar * ppq
            end = start + beats_per_bar * ppq
            total += sum(1 for ev in events if ev.note == note and start <= ev.start_tick < end)
        return total / len(bars_in) if bars_in else 0.0

    verse_hats = hits_per_bar("verse", GM_CLOSED_HAT)
    chorus_hats = hits_per_bar("chorus", GM_CLOSED_HAT)
    assert chorus_hats > verse_hats, (verse_hats, chorus_hats)

    verse_kicks = hits_per_bar("verse", GM_KICK)
    chorus_kicks = hits_per_bar("chorus", GM_KICK)
    assert chorus_kicks > verse_kicks, (verse_kicks, chorus_kicks)


def test_punk_has_more_kicks_than_rock(tmp_path: Path) -> None:
    rock_events = generate_basic_song(bars=32, style="rock", seed=42, ppq=480)
    punk_events = generate_basic_song(bars=32, style="punk", seed=42, ppq=480)
    rock_kicks = sum(1 for ev in rock_events if ev.note == GM_KICK)
    punk_kicks = sum(1 for ev in punk_events if ev.note == GM_KICK)
    assert punk_kicks > rock_kicks


def test_funk_has_16th_hats() -> None:
    rock_events = generate_basic_song(bars=16, style="rock", seed=1, ppq=480)
    funk_events = generate_basic_song(bars=16, style="funk", seed=1, ppq=480)
    rock_hats = sum(1 for ev in rock_events if ev.note == GM_CLOSED_HAT)
    funk_hats = sum(1 for ev in funk_events if ev.note == GM_CLOSED_HAT)
    assert funk_hats > rock_hats * 1.5


def test_snare_on_2_and_4(tmp_path: Path) -> None:
    events = generate_basic_song(bars=8, style="rock", seed=1, ppq=480)
    ppq = 480
    beats_per_bar = 4
    for bar in range(8):
        bar_start = bar * beats_per_bar * ppq
        for ev in events:
            if ev.note == GM_SNARE and bar_start <= ev.start_tick < bar_start + beats_per_bar * ppq:
                beat = (ev.start_tick - bar_start) // ppq
                assert beat in (1, 3), f"snare on beat {beat} in bar {bar}"


def test_unknown_style_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="unknown style"):
        generate_basic_song(bars=8, style="reggaeton", seed=1)


def test_structure_for_small_bar_count_collapses() -> None:
    sections = structure_for(3)
    assert len(sections) == 1
    assert sections[0].bars == 3
    sections = structure_for(8)
    assert len(sections) == 1
    assert sections[0].bars == 8


def test_structure_sums_to_bars() -> None:
    for n in (12, 32, 80, 137, 256):
        sections = structure_for(n)
        assert sum(s.bars for s in sections) == n, (n, [(s.name, s.bars) for s in sections])
