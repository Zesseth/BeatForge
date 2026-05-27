"""Tests for ``drumgen validate-midi`` and ``validate_midi_file``."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from beatforge.cli.main import app
from beatforge.midi.validator import validate_midi_file

runner = CliRunner()

FIXTURES = Path(__file__).parent / "fixtures" / "broken"


def test_known_good_passes(tmp_path: Path) -> None:
    out = tmp_path / "good.mid"
    result = runner.invoke(
        app, ["make-empty", "--bars", "8", "--bpm", "120", "--out", str(out)]
    )
    assert result.exit_code == 0, result.output

    report = validate_midi_file(out)
    assert report.ok, (report.errors, report.warnings)
    assert not report.errors


def test_validator_cli_returns_zero_on_good(tmp_path: Path) -> None:
    out = tmp_path / "good.mid"
    runner.invoke(app, ["make-empty", "--bars", "4", "--bpm", "120", "--out", str(out)])
    result = runner.invoke(app, ["validate-midi", str(out)])
    assert result.exit_code == 0, result.output
    assert "PASS" in result.output


def test_no_tempo_fails() -> None:
    report = validate_midi_file(FIXTURES / "no-tempo.mid")
    assert not report.ok
    assert any("set_tempo" in e for e in report.errors)


def test_wrong_channel_fails() -> None:
    report = validate_midi_file(FIXTURES / "wrong-channel.mid")
    assert not report.ok
    assert any("channel" in e.lower() for e in report.errors)


def test_empty_notes_fails() -> None:
    report = validate_midi_file(FIXTURES / "empty-notes.mid")
    assert not report.ok
    assert any("zero note_on" in e for e in report.errors)


def test_strict_promotes_missing_ts_to_error(tmp_path: Path) -> None:
    # build a file with tempo but no time signature
    import mido

    mid = mido.MidiFile(type=1, ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
    track.append(mido.Message("note_on", channel=9, note=36, velocity=100, time=0))
    track.append(mido.Message("note_off", channel=9, note=36, velocity=0, time=30))
    track.append(mido.MetaMessage("end_of_track", time=0))

    p = tmp_path / "no-ts.mid"
    mid.save(p)

    lenient = validate_midi_file(p, strict=False)
    assert lenient.ok
    assert any("time_signature" in w for w in lenient.warnings)

    strict = validate_midi_file(p, strict=True)
    assert not strict.ok
    assert any("time_signature" in e for e in strict.errors)


def test_validator_json_output(tmp_path: Path) -> None:
    out = tmp_path / "good.mid"
    runner.invoke(app, ["make-empty", "--bars", "4", "--bpm", "120", "--out", str(out)])

    result = runner.invoke(app, ["validate-midi", str(out), "--json"])
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert parsed["ok"] is True
    assert parsed["stats"]["ppq"] == 480
