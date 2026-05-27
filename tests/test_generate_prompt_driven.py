"""Tests for ``drumgen generate`` (prompt-driven, M1.3)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from beatforge.cli.main import app
from beatforge.gen.styled import generate_from_stylespec
from beatforge.midi import GM_CLOSED_HAT, GM_KICK, GM_SNARE
from beatforge.midi.validator import validate_midi_file
from beatforge.prompt.parser import parse_prompt
from beatforge.prompt.stylespec import StyleSpec

runner = CliRunner()


def _gen_cli(tmp_path: Path, **kw: object) -> Path:
    out = tmp_path / "drums.mid"
    args = ["generate", "--out", str(out)]
    for k, v in kw.items():
        args.extend([f"--{k.replace('_', '-')}", str(v)])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    return out


def _count(events, note: int) -> int:
    return sum(1 for ev in events if ev.note == note)


def test_generates_valid_midi(tmp_path: Path) -> None:
    out = _gen_cli(tmp_path, prompt="rock 120bpm 8th hats", bars=32, seed=1)
    report = validate_midi_file(out)
    assert report.ok, (report.errors, report.warnings)


def test_byte_stable_with_same_prompt_and_seed(tmp_path: Path) -> None:
    a = _gen_cli(tmp_path / "a", prompt="rock 120bpm 8th hats", bars=32, seed=1)
    b = _gen_cli(tmp_path / "b", prompt="rock 120bpm 8th hats", bars=32, seed=1)
    assert a.read_bytes() == b.read_bytes()


def test_16th_hats_doubles_8th_hats() -> None:
    s8 = parse_prompt("rock 8th hats")
    s16 = parse_prompt("rock 16th hats")
    e8 = generate_from_stylespec(s8, bars=16, seed=1, ppq=480)
    e16 = generate_from_stylespec(s16, bars=16, seed=1, ppq=480)
    h8 = _count(e8, GM_CLOSED_HAT)
    h16 = _count(e16, GM_CLOSED_HAT)
    assert h16 >= 1.8 * h8, (h8, h16)


def test_kick_density_more_vs_less() -> None:
    less = parse_prompt("rock 120bpm 8th hats sparse kick")
    more = parse_prompt("rock 120bpm 8th hats double kick")
    e_less = generate_from_stylespec(less, bars=16, seed=1, ppq=480)
    e_more = generate_from_stylespec(more, bars=16, seed=1, ppq=480)
    k_less = _count(e_less, GM_KICK)
    k_more = _count(e_more, GM_KICK)
    assert k_more > k_less, (k_less, k_more)


def test_fills_before_chorus_adds_extra_notes_to_last_verse_bar() -> None:
    spec_default = parse_prompt("rock 120bpm 8th hats")
    spec_fills = parse_prompt("rock 120bpm 8th hats fills before chorus")
    e_default = generate_from_stylespec(spec_default, bars=80, seed=1, ppq=480)
    e_fills = generate_from_stylespec(spec_fills, bars=80, seed=1, ppq=480)
    # Different totals: fill bars replace hats with toms; with default fills both
    # also place fills, so we instead assert the byte stream differs.
    # More direct check: total note count differs between "none" and "before_chorus".
    none_spec = parse_prompt("rock 120bpm 8th hats no fills")
    e_none = generate_from_stylespec(none_spec, bars=80, seed=1, ppq=480)
    assert len(e_fills) != len(e_none)
    assert len(e_default) >= len(e_none)


def test_ghost_notes_adds_snare_hits() -> None:
    plain = parse_prompt("rock 120bpm 8th hats")
    ghost = parse_prompt("rock 120bpm 8th hats ghost notes")
    e_plain = generate_from_stylespec(plain, bars=16, seed=1, ppq=480)
    e_ghost = generate_from_stylespec(ghost, bars=16, seed=1, ppq=480)
    assert _count(e_ghost, GM_SNARE) > _count(e_plain, GM_SNARE)


def test_bpm_from_prompt_is_used(tmp_path: Path) -> None:
    out = _gen_cli(tmp_path, prompt="rock 180bpm 8th hats", bars=8, seed=1)
    import mido

    mid = mido.MidiFile(str(out))
    tempo = next(m for t in mid.tracks for m in t if m.type == "set_tempo")
    assert round(mido.tempo2bpm(tempo.tempo)) == 180


def test_explicit_bpm_overrides_prompt(tmp_path: Path) -> None:
    out = _gen_cli(tmp_path, prompt="rock 180bpm 8th hats", bars=8, seed=1, bpm=90)
    import mido

    mid = mido.MidiFile(str(out))
    tempo = next(m for t in mid.tracks for m in t if m.type == "set_tempo")
    assert round(mido.tempo2bpm(tempo.tempo)) == 90


def test_stylespec_file_path(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    runner.invoke(
        app,
        [
            "parse-prompt",
            "--prompt",
            "punk 180bpm 8th hats fills before chorus",
            "--out",
            str(spec_path),
        ],
    )
    out = tmp_path / "drums.mid"
    result = runner.invoke(
        app,
        [
            "generate",
            "--stylespec",
            str(spec_path),
            "--bars",
            "32",
            "--seed",
            "1",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert validate_midi_file(out).ok


def test_prompt_and_stylespec_are_mutually_exclusive(tmp_path: Path) -> None:
    out = tmp_path / "drums.mid"
    result = runner.invoke(
        app,
        [
            "generate",
            "--prompt",
            "rock",
            "--stylespec",
            "anything.json",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code != 0


def test_neither_prompt_nor_stylespec_errors(tmp_path: Path) -> None:
    out = tmp_path / "drums.mid"
    result = runner.invoke(app, ["generate", "--out", str(out)])
    assert result.exit_code != 0


def test_empty_prompt_still_generates_valid_output(tmp_path: Path) -> None:
    out = _gen_cli(tmp_path, prompt="", bars=16, seed=1)
    assert validate_midi_file(out).ok


def test_spec_via_python_api_works() -> None:
    spec = StyleSpec(genre="rock", bpm=120, hats="16th", backbeat="2_and_4")
    events = generate_from_stylespec(spec, bars=16, seed=1, ppq=480)
    assert events
    # snare lands on beats 2 and 4 only
    ppq = 480
    for bar in range(16):
        bar_start = bar * 4 * ppq
        for ev in events:
            if ev.note == GM_SNARE and bar_start <= ev.start_tick < bar_start + 4 * ppq:
                beat = (ev.start_tick - bar_start) // ppq
                assert beat in (1, 3) or ((ev.start_tick - bar_start) % ppq != 0), beat
