"""Tests for ``drumgen make-empty`` and the underlying MIDI writer."""

from __future__ import annotations

from pathlib import Path

import mido
from typer.testing import CliRunner

from beatforge.cli.main import app
from beatforge.midi import DRUM_CHANNEL, GM_CLOSED_HAT, GM_KICK, GM_SNARE

runner = CliRunner()


def _run_make_empty(tmp_path: Path, **kwargs: object) -> Path:
    out = tmp_path / "drums.mid"
    args = ["make-empty", "--out", str(out)]
    for k, v in kwargs.items():
        args.extend([f"--{k.replace('_', '-')}", str(v)])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert out.exists()
    return out


def test_make_empty_default(tmp_path: Path) -> None:
    out = _run_make_empty(tmp_path, bars=32, bpm=120)
    mid = mido.MidiFile(str(out))

    assert mid.ticks_per_beat == 480

    metas = [m for track in mid.tracks for m in track if m.is_meta]
    tempo = next((m for m in metas if m.type == "set_tempo"), None)
    ts = next((m for m in metas if m.type == "time_signature"), None)
    assert tempo is not None and mido.tempo2bpm(tempo.tempo) == 120
    assert ts is not None and (ts.numerator, ts.denominator) == (4, 4)

    notes_on = [m for track in mid.tracks for m in track if m.type == "note_on" and m.velocity > 0]
    assert notes_on, "no note_on events"
    assert all(m.channel == DRUM_CHANNEL for m in notes_on), "notes off drum channel"

    pitches = {m.note for m in notes_on}
    assert pitches.issubset({GM_KICK, GM_SNARE, GM_CLOSED_HAT})

    hat_hits = sum(1 for m in notes_on if m.note == GM_CLOSED_HAT)
    assert hat_hits >= 32 * 8, f"expected ≥ {32 * 8} hat hits, got {hat_hits}"


def test_make_empty_is_byte_stable(tmp_path: Path) -> None:
    a = _run_make_empty(tmp_path / "a", bars=16, bpm=140)
    b = _run_make_empty(tmp_path / "b", bars=16, bpm=140)
    assert a.read_bytes() == b.read_bytes()


def test_make_empty_respects_bpm_arg(tmp_path: Path) -> None:
    out = _run_make_empty(tmp_path, bars=4, bpm=180)
    mid = mido.MidiFile(str(out))
    tempo = next(m for t in mid.tracks for m in t if m.type == "set_tempo")
    assert round(mido.tempo2bpm(tempo.tempo)) == 180


def test_make_empty_respects_time_signature(tmp_path: Path) -> None:
    out = tmp_path / "drums.mid"
    result = runner.invoke(
        app,
        ["make-empty", "--bars", "4", "--bpm", "120", "--time-signature", "3/4", "--out", str(out)],
    )
    assert result.exit_code == 0, result.output
    mid = mido.MidiFile(str(out))
    ts = next(m for t in mid.tracks for m in t if m.type == "time_signature")
    assert (ts.numerator, ts.denominator) == (3, 4)
