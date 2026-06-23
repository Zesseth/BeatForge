"""BeatForge CLI entrypoint.

Subcommands are wired here. In M0.1 every subcommand (other than the trivial
ones implemented in later issues) prints a "not implemented in this issue"
notice and exits with code 0 so that ``drumgen --help`` and tab-completion are
discoverable from day one.
"""

from __future__ import annotations

from pathlib import Path

import typer

from beatforge.gen.basic import KNOWN_STYLES, generate_basic_song
from beatforge.gen.styled import generate_from_stylespec
from beatforge.midi.patterns import basic_rock_pattern
from beatforge.midi.validator import validate_midi_file
from beatforge.midi.writer import write_drum_midi
from beatforge.prompt.parser import parse_prompt as _parse_prompt
from beatforge.prompt.stylespec import StyleSpec

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
    time_signature: str = typer.Option("4/4", "--time-signature", help="Time signature, e.g. 4/4."),
) -> None:
    """Write a REAPER-ready baseline drum MIDI file (M0.2)."""
    num_str, den_str = time_signature.split("/", 1)
    ts = (int(num_str), int(den_str))
    events = basic_rock_pattern(bars=bars, ppq=ppq)
    path = write_drum_midi(events, out, bpm=bpm, time_signature=ts, ppq=ppq)
    typer.echo(f"wrote {path}")


@app.command("validate-midi")
def validate_midi(
    path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of text."),
    strict: bool = typer.Option(
        False, "--strict", help="Treat warnings (e.g. missing time signature) as errors."
    ),
) -> None:
    """Validate a MIDI file against BeatForge's REAPER-ready ruleset (M0.3)."""
    import json as _json

    report = validate_midi_file(path, strict=strict)
    if json_output:
        typer.echo(_json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        status = "PASS" if report.ok else "FAIL"
        typer.echo(f"{status}  {report.path}")
        for err in report.errors:
            typer.echo(f"  ERROR  {err}")
        for warn in report.warnings:
            typer.echo(f"  WARN   {warn}")
        if report.stats:
            for k, v in sorted(report.stats.items()):
                typer.echo(f"  stat   {k}={v}")
    raise typer.Exit(code=0 if report.ok else 1)


@app.command("generate-basic")
def generate_basic(
    bars: int = typer.Option(80, "--bars", min=1),
    bpm: int = typer.Option(120, "--bpm", min=20, max=400),
    style: str = typer.Option("rock", "--style", help=f"One of {sorted(KNOWN_STYLES)}."),
    seed: int = typer.Option(42, "--seed"),
    out: Path = typer.Option(..., "--out"),
    ppq: int = typer.Option(480, "--ppq", min=24),
) -> None:
    """Generate a full-song deterministic drum MIDI without prompts (M1.1)."""
    events = generate_basic_song(bars=bars, style=style, seed=seed, ppq=ppq)
    path = write_drum_midi(events, out, bpm=bpm, ppq=ppq)
    typer.echo(f"wrote {path} ({len(events)} note events)")


@app.command("parse-prompt")
def parse_prompt(
    prompt: str = typer.Option(..., "--prompt"),
    out: Path | None = typer.Option(None, "--out", help="Write JSON to this path."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Parse a natural-language prompt into a StyleSpec (M1.2)."""
    import json as _json

    spec, unparsed = _parse_prompt(prompt, return_unparsed=True)
    payload: dict[str, object] = {"stylespec": spec.model_dump()}
    if verbose:
        payload["unparsed"] = unparsed
    text = _json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        typer.echo(f"wrote {out}")
    else:
        typer.echo(text, nl=False)


@app.command("generate")
def generate(
    prompt: str | None = typer.Option(None, "--prompt"),
    stylespec: Path | None = typer.Option(None, "--stylespec", help="StyleSpec JSON file."),
    bars: int = typer.Option(96, "--bars", min=1),
    bpm: int | None = typer.Option(None, "--bpm", min=20, max=400),
    seed: int = typer.Option(7, "--seed"),
    out: Path = typer.Option(..., "--out"),
    ppq: int = typer.Option(480, "--ppq", min=24),
) -> None:
    """Generate drum MIDI from a StyleSpec or prompt (M1.3)."""
    import json as _json

    if (prompt is None) == (stylespec is None):
        raise typer.BadParameter("provide exactly one of --prompt or --stylespec")

    if prompt is not None:
        spec = _parse_prompt(prompt)
    else:
        assert stylespec is not None
        payload = _json.loads(stylespec.read_text(encoding="utf-8"))
        # accept either bare spec or {"stylespec": {...}} (what parse-prompt writes)
        if "stylespec" in payload:
            payload = payload["stylespec"]
        spec = StyleSpec(**payload)

    effective_bpm = bpm if bpm is not None else (spec.bpm if spec.bpm is not None else 120)
    events = generate_from_stylespec(spec, bars=bars, seed=seed, ppq=ppq)
    path = write_drum_midi(events, out, bpm=effective_bpm, ppq=ppq)
    typer.echo(
        f"wrote {path} ({len(events)} note events) bpm={effective_bpm} spec={spec.model_dump()}"
    )


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
