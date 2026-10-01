"""Tests for the `drumgen ui` guided wizard."""

from __future__ import annotations

from typer.testing import CliRunner

from beatforge.cli.main import app

runner = CliRunner()


def _lines(result_output: str) -> list[str]:
    return [line for line in result_output.splitlines() if line.strip()]


def test_ui_runs_end_to_end_with_defaults(tmp_path) -> None:  # type: ignore[no-untyped-def]
    out = tmp_path / "drums.mid"
    result = runner.invoke(app, ["ui", "--out", str(out)], input="n\n\n\n\n\n\n\n\n\n\n\n\ny\n")
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert "wrote" in result.output
    assert "valid for REAPER" in result.output


def test_ui_accepts_prompt_and_overrides(tmp_path) -> None:  # type: ignore[no-untyped-def]
    out = tmp_path / "punk.mid"
    answers = "\n".join(
        [
            "y",  # describe in own words?
            "punk 180 bpm, snare on 2 and 4, 16th hats",  # prompt
            "32",  # bars
            "180",  # bpm
            "7",  # seed
            str(out),  # output file
            "1",  # genre: punk
            "1",  # hats: 8th
            "1",  # backbeat: 2 and 4
            "2",  # kick: default
            "3",  # fills: default
            "2",  # feel: default
            "n",  # ghost notes?
            "y",  # generate?
        ]
    )
    result = runner.invoke(app, ["ui"], input=answers + "\n")
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert "32" in result.output


def test_ui_abort_writes_nothing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    out = tmp_path / "nope.mid"
    answers = "\n".join(
        [
            "n",  # no prompt
            "16",  # bars
            "",  # bpm skip
            "7",  # seed
            str(out),  # out
            "6",  # genre skip
            "5",  # hats skip
            "4",  # backbeat skip
            "2",  # kick default
            "3",  # fills default
            "2",  # feel default
            "n",  # ghost notes
            "n",  # generate? -> abort
        ]
    )
    result = runner.invoke(app, ["ui"], input=answers + "\n")
    assert result.exit_code == 0, result.output
    assert not out.exists()
    assert "Aborted" in result.output


def test_ui_rejects_invalid_number_then_recovers(tmp_path) -> None:  # type: ignore[no-untyped-def]
    out = tmp_path / "retry.mid"
    answers = "\n".join(
        [
            "n",  # no prompt
            "16",  # bars
            "",  # bpm skip
            "7",  # seed
            str(out),  # out
            "99",  # invalid genre
            "1",  # genre: rock
            "5",  # hats: skip
            "4",  # backbeat: skip
            "2",  # kick default
            "3",  # fills default
            "2",  # feel default
            "n",  # ghost notes
            "y",  # generate
        ]
    )
    result = runner.invoke(app, ["ui"], input=answers + "\n")
    assert result.exit_code == 0, result.output
    assert "Please enter a number" in result.output
    assert out.exists()


def test_ui_output_passes_validator(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from beatforge.midi.validator import validate_midi_file

    out = tmp_path / "valid.mid"
    answers = "\n".join(
        [
            "y",
            "funk 105 bpm, ghost notes, shuffle hats",
            "16",
            "",
            "7",
            str(out),
            "5",  # genre skip (prompt already set funk)
            "1",  # hats 8th
            "1",  # backbeat 2 and 4
            "2",
            "3",
            "2",
            "y",  # keep ghost notes from prompt
            "y",
        ]
    )
    result = runner.invoke(app, ["ui"], input=answers + "\n")
    assert result.exit_code == 0, result.output
    report = validate_midi_file(out)
    assert report.ok, report.errors


def test_ui_help_mentions_guided_mode() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "drumgen ui" in result.output


def test_ui_kick_density_skip_keeps_prompt_value(tmp_path) -> None:  # type: ignore[no-untyped-def]
    out = tmp_path / "kick.mid"
    answers = "\n".join(
        [
            "y",
            "punk 120 bpm, double kick",
            "16",
            "",
            "7",
            str(out),
            "6",  # genre skip
            "5",  # hats skip
            "4",  # backbeat skip
            "4",  # kick density SKIP (keep 'more' from prompt)
            "6",  # fills skip
            "4",  # feel skip
            "n",
            "y",
        ]
    )
    result = runner.invoke(app, ["ui"], input=answers + "\n")
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert "'kick_density': 'more'" in result.output
