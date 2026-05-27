"""Tests for ``drumgen parse-prompt`` and the StyleSpec parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from beatforge.cli.main import app
from beatforge.prompt.parser import parse_prompt
from beatforge.prompt.stylespec import StyleSpec

runner = CliRunner()


CASES: list[tuple[str, dict[str, object]]] = [
    ("punk 180bpm, snare on 2&4", {"genre": "punk", "bpm": 180, "backbeat": "2_and_4"}),
    ("rock 120bpm, 8th hats", {"genre": "rock", "bpm": 120, "hats": "8th"}),
    ("metal double kick, tight feel", {"genre": "metal", "kick_density": "more", "feel": "tight"}),
    ("funk 16th hats, ghost notes", {"genre": "funk", "hats": "16th", "ghost_notes": True}),
    ("pop, no fills, loose feel", {"genre": "pop", "fills": "none", "feel": "loose"}),
    (
        "rock 100bpm, 16th hats, fills before chorus",
        {"genre": "rock", "bpm": 100, "hats": "16th", "fills": "before_chorus"},
    ),
    ("shuffle 96bpm", {"bpm": 96, "hats": "shuffle"}),
    ("swing feel 140bpm", {"bpm": 140, "hats": "swing"}),
    ("sparse kick, fewer fills", {"kick_density": "less", "fills": "fewer"}),
    (
        "punk 200bpm 8th hats heavy kick more fills",
        {"genre": "punk", "bpm": 200, "hats": "8th", "kick_density": "more", "fills": "more"},
    ),
    ("", {}),  # empty prompt → all defaults
]


@pytest.mark.parametrize("prompt,expected", CASES)
def test_parse_prompt_table(prompt: str, expected: dict[str, object]) -> None:
    spec = parse_prompt(prompt)
    assert isinstance(spec, StyleSpec)
    dumped = spec.model_dump()
    for k, v in expected.items():
        assert dumped[k] == v, (prompt, k, dumped[k], v)


def test_unknown_tokens_do_not_crash() -> None:
    spec = parse_prompt("rock, asdkjasdh, zzz, 120bpm, woof")
    assert spec.genre == "rock"
    assert spec.bpm == 120


def test_return_unparsed_reports_garbage() -> None:
    spec, unparsed = parse_prompt("rock 120bpm asdfqwer wibble", return_unparsed=True)
    assert spec.genre == "rock"
    assert spec.bpm == 120
    assert {"asdfqwer", "wibble"} <= set(unparsed)


def test_cli_writes_stable_json(tmp_path: Path) -> None:
    out_a = tmp_path / "a.json"
    out_b = tmp_path / "b.json"
    args = ["parse-prompt", "--prompt", "punk 180bpm, snare on 2&4"]
    runner.invoke(app, [*args, "--out", str(out_a)])
    runner.invoke(app, [*args, "--out", str(out_b)])
    assert out_a.read_bytes() == out_b.read_bytes()
    parsed = json.loads(out_a.read_text())
    assert parsed["stylespec"]["genre"] == "punk"
    assert parsed["stylespec"]["bpm"] == 180


def test_cli_verbose_includes_unparsed(tmp_path: Path) -> None:
    out = tmp_path / "verbose.json"
    result = runner.invoke(
        app, ["parse-prompt", "--prompt", "rock 120bpm wibble", "--verbose", "--out", str(out)]
    )
    assert result.exit_code == 0
    parsed = json.loads(out.read_text())
    assert "wibble" in parsed["unparsed"]


def test_cli_stdout_when_no_out() -> None:
    result = runner.invoke(app, ["parse-prompt", "--prompt", "rock 120bpm"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["stylespec"]["bpm"] == 120
