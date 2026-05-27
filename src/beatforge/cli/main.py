"""BeatForge CLI entrypoint.

Subcommands are wired here. In M0.1 every subcommand (other than the trivial
ones implemented in later issues) prints a "not implemented in this issue"
notice and exits with code 0 so that ``drumgen --help`` and tab-completion are
discoverable from day one.
"""

from __future__ import annotations

from pathlib import Path

import typer

from beatforge.midi.patterns import basic_rock_pattern
from beatforge.midi.writer import write_drum_midi

app = typer.Typer(
    name="drumgen",
    add_completion=False,
    no_args_is_help=True,
    help="BeatForge — privacy-first, prompt-driven drum MIDI generator.",
)


_NOT_IMPLEMENTED_TEMPLATE = (
    "drumgen {subcommand}: not implemented in this issue.\n"
    "Tracking issue: see ROADMAP.md and the BeatForge issue board."
)


def _stub(subcommand: str) -> None:
    typer.echo(_NOT_IMPLEMENTED_TEMPLATE.format(subcommand=subcommand))


@app.callback()
def _root(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging."),
) -> None:
    """BeatForge root command. Use ``drumgen <subcommand> --help`` for details."""
    # Verbose flag is plumbed here so subcommands can read it via the Typer
    # context in future issues. M0.1 keeps it as a no-op switch.
    _ = verbose


@app.command("make-empty")
def make_empty(
    bars: int = typer.Option(32, "--bars", help="Number of 4/4 bars to generate.", min=1),
    bpm: int = typer.Option(120, "--bpm", help="Tempo in BPM.", min=20, max=400),
    out: Path = typer.Option(..., "--out", help="Output .mid path."),
    ppq: int = typer.Option(480, "--ppq", help="Pulses per quarter note.", min=24),
    time_signature: str = typer.Option(
        "4/4", "--time-signature", help="Time signature, e.g. 4/4."
    ),
) -> None:
    """Write a REAPER-ready baseline drum MIDI file (M0.2)."""
    num_str, den_str = time_signature.split("/", 1)
    ts = (int(num_str), int(den_str))
    events = basic_rock_pattern(bars=bars, ppq=ppq)
    path = write_drum_midi(events, out, bpm=bpm, time_signature=ts, ppq=ppq)
    typer.echo(f"wrote {path}")


@app.command("validate-midi")
def validate_midi() -> None:
    """Validate a MIDI file against BeatForge's REAPER-ready ruleset (M0.3)."""
    _stub("validate-midi")


@app.command("generate-basic")
def generate_basic() -> None:
    """Generate a full-song deterministic drum MIDI without prompts (M1.1)."""
    _stub("generate-basic")


@app.command("parse-prompt")
def parse_prompt() -> None:
    """Parse a natural-language prompt into a StyleSpec (M1.2)."""
    _stub("parse-prompt")


@app.command("generate")
def generate() -> None:
    """Generate drum MIDI from a StyleSpec or prompt (M1.3)."""
    _stub("generate")


@app.command("analyze")
def analyze() -> None:
    """Analyse a local audio stem and emit derived features (M2.1)."""
    _stub("analyze")


@app.command("groove")
def groove() -> None:
    """Extract a per-bar groove fingerprint from analysis output (M2.2)."""
    _stub("groove")


@app.command("edit")
def edit() -> None:
    """Edit an existing MIDI file using symbolic operations (M3.2)."""
    _stub("edit")


@app.command("generate-ml")
def generate_ml() -> None:
    """Generate drums via the pluggable symbolic groove model (M4.3)."""
    _stub("generate-ml")


@app.command("models")
def models() -> None:
    """Manage local model checkpoints (M4.1)."""
    _stub("models")


if __name__ == "__main__":
    app()
