"""Guided interactive wizard for drumgen (`drumgen ui`).

This module implements an interactive, numbered-menu wizard that walks a
user through drum MIDI generation without requiring any knowledge of CLI
flags. It reuses the same pure generation functions as the `generate`
subcommand, so output stays deterministic and REAPER-ready.

The wizard is deliberately dependency-free: it reads lines from stdin
via typer.prompt/typer.confirm so it works in every terminal on Debian
(and remains testable via typer's CliRunner input stream).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import typer

from beatforge.gen.styled import generate_from_stylespec
from beatforge.midi.validator import validate_midi_file
from beatforge.midi.writer import write_drum_midi
from beatforge.prompt.parser import parse_prompt as _parse_prompt
from beatforge.prompt.stylespec import (
    Backbeat,
    Density,
    Feel,
    Fills,
    Genre,
    Hats,
    StyleSpec,
)

GENRES: list[Genre] = ["rock", "pop", "punk", "metal", "funk"]
HATS: list[Hats] = ["8th", "16th", "shuffle", "swing"]
BACKBEATS = ["2 and 4 (standard backbeat)", "2 only", "4 only"]
BACKBEAT_MAP: dict[str, Backbeat] = {
    "2 and 4 (standard backbeat)": "2_and_4",
    "2 only": "2",
    "4 only": "4",
}
KICK_DENSITY: list[Density] = ["less", "default", "more"]
FILLS = ["none", "fewer", "default", "more", "before chorus"]
FILLS_MAP: dict[str, Fills] = {
    "none": "none",
    "fewer": "fewer",
    "default": "default",
    "more": "more",
    "before chorus": "before_chorus",
}
FEELS = ["tight (quantized)", "default", "loose (humanized)"]
FEELS_MAP: dict[str, Feel] = {
    "tight (quantized)": "tight",
    "default": "default",
    "loose (humanized)": "loose",
}


def _menu(title: str, options: Sequence[str]) -> int:
    """Print a numbered menu with a skip option; return 0-based index."""
    lines = [*options, "(skip — keep what the prompt said)"]
    typer.echo(f"\n{title}")
    for i, option in enumerate(lines, start=1):
        typer.echo(f"  {i}. {option}")
    while True:
        raw = typer.prompt("Choose a number (Enter = 1)", default="1").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(lines):
            return int(raw) - 1
        typer.echo(f"  Please enter a number between 1 and {len(lines)}.")


@dataclass(frozen=True)
class WizardChoices:
    """User answers collected by the wizard (before validation)."""

    prompt: str | None = None
    bars: int = 96
    bpm: int | None = None
    seed: int = 7
    out: Path = Path("drums.mid")


def _collect_answers() -> WizardChoices:
    """Ask the user what they want and return raw wizard choices."""
    typer.echo("BeatForge — let's make some drum MIDI.")
    typer.echo("Answer the questions below (press Enter to accept the default).")

    use_prompt = typer.confirm(
        "\nDo you want to describe the drums in your own words?", default=True
    )
    prompt: str | None = None
    if use_prompt:
        while True:
            prompt = typer.prompt(
                "Describe the drums (e.g. 'punk 180 bpm, snare on 2 and 4, 16th hats')"
            ).strip()
            if prompt:
                break
            typer.echo("  The description cannot be empty.")

    bars_raw = typer.prompt("How many bars?", default="96").strip()
    while not (bars_raw.isdigit() and int(bars_raw) >= 1):
        typer.echo("  Please enter a whole number of bars (1 or more).")
        bars_raw = typer.prompt("How many bars?", default="96").strip()
    bars = int(bars_raw)

    bpm: int | None = None
    bpm_raw = typer.prompt("Tempo in BPM (Enter = let the style decide)", default="").strip()
    if bpm_raw:
        while not (bpm_raw.isdigit() and 20 <= int(bpm_raw) <= 400):
            typer.echo("  Please enter a BPM between 20 and 400, or nothing to skip.")
            bpm_raw = typer.prompt(
                "Tempo in BPM (Enter = let the style decide)", default=""
            ).strip()
        bpm = int(bpm_raw)

    seed_raw = typer.prompt("Randomness seed (same seed = same drums)", default="7").strip()
    while not (seed_raw.lstrip("-").isdigit()):
        typer.echo("  Please enter a whole number.")
        seed_raw = typer.prompt("Randomness seed (same seed = same drums)", default="7").strip()
    seed = int(seed_raw)

    out_raw = typer.prompt("Output file", default="drums.mid").strip()
    out = Path(out_raw)

    return WizardChoices(prompt=prompt, bars=bars, bpm=bpm, seed=seed, out=out)


def _collect_style_overrides(spec: StyleSpec) -> StyleSpec:
    """Let the user override or fill in StyleSpec fields via menus."""
    typer.echo("\nFine-tune the style (Enter accepts the shown default).")

    skip = len(GENRES)
    genre_idx = _menu("Genre", GENRES)
    genre: Genre | None = None if genre_idx == skip else GENRES[genre_idx]
    if genre is None:
        genre = spec.genre

    skip = len(HATS)
    hats_idx = _menu("Hi-hats", HATS)
    hats: Hats | None = None if hats_idx == skip else HATS[hats_idx]
    if hats is None:
        hats = spec.hats

    skip = len(BACKBEATS)
    backbeat_idx = _menu("Snare placement", BACKBEATS)
    backbeat: Backbeat | None = (
        None if backbeat_idx == skip else BACKBEAT_MAP[BACKBEATS[backbeat_idx]]
    )
    if backbeat is None:
        backbeat = spec.backbeat

    skip = len(KICK_DENSITY)
    kick_idx = _menu("Kick density", KICK_DENSITY)
    kick_density: Density = spec.kick_density if kick_idx == skip else KICK_DENSITY[kick_idx]

    skip = len(FILLS)
    fills_idx = _menu("Fills", FILLS)
    fills: Fills | None = None if fills_idx == skip else FILLS_MAP[FILLS[fills_idx]]
    if fills is None:
        fills = spec.fills

    skip = len(FEELS)
    feel_idx = _menu("Feel", FEELS)
    feel: Feel | None = None if feel_idx == skip else FEELS_MAP[FEELS[feel_idx]]
    if feel is None:
        feel = spec.feel

    ghost_notes = typer.confirm("\nAdd snare ghost notes?", default=spec.ghost_notes)

    return StyleSpec(
        genre=genre,
        bpm=spec.bpm,
        hats=hats,
        backbeat=backbeat,
        kick_density=kick_density,
        fills=fills,
        ghost_notes=ghost_notes,
        feel=feel,
    )


def _summarise(spec: StyleSpec, bars: int, bpm: int, out: Path) -> None:
    """Print a human-readable summary of what will be generated."""
    typer.echo("\nSummary")
    typer.echo(f"  style   : {spec.model_dump()}")
    typer.echo(f"  bars    : {bars}")
    typer.echo(f"  tempo   : {bpm} BPM")
    typer.echo(f"  output  : {out}")


def run_wizard(out: Path | None = None) -> Path:
    """Run the interactive wizard end-to-end and return the written file path."""
    choices = _collect_answers()

    spec: StyleSpec
    if choices.prompt is not None:
        spec, unparsed = _parse_prompt(choices.prompt, return_unparsed=True)
        if unparsed:
            typer.echo(f"\nNote: could not interpret these words: {', '.join(unparsed)}")
        spec = _collect_style_overrides(spec)
    else:
        spec = _collect_style_overrides(StyleSpec())

    effective_bpm = (
        choices.bpm if choices.bpm is not None else (spec.bpm if spec.bpm is not None else 120)
    )

    final_out = out if out is not None else choices.out

    _summarise(spec, choices.bars, effective_bpm, final_out)

    if not typer.confirm("\nGenerate the MIDI file?", default=True):
        typer.echo("Aborted — nothing was written.")
        raise typer.Exit(code=0)

    events = generate_from_stylespec(spec, bars=choices.bars, seed=choices.seed)
    path = write_drum_midi(events, final_out, bpm=effective_bpm)

    report = validate_midi_file(path)
    status = "valid" if report.ok else "INVALID"
    typer.echo(f"\nDone! wrote {path} ({len(events)} note events) — {status} for REAPER.")
    typer.echo("Import it in REAPER: GM drum map, channel 10. Happy drumming!")
    if not report.ok:
        for err in report.errors:
            typer.echo(f"  ERROR  {err}")
        raise typer.Exit(code=1)
    return path
