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
    audio: Path | None = typer.Option(
        None,
        "--audio",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Local audio to align to (M2.3).",
    ),
    analysis: Path | None = typer.Option(
        None,
        "--analysis",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Existing analysis.json.",
    ),
    groove_path: Path | None = typer.Option(
        None, "--groove", exists=True, dir_okay=False, readable=True, help="Existing groove.json."
    ),
    cache_dir: Path | None = typer.Option(
        None, "--cache-dir", help="Optionally cache in-process analysis JSON here."
    ),
    tempo_mode: str = typer.Option(
        "follow", "--tempo-mode", help="follow (audio tempo) or fixed (ignore analysed tempo)."
    ),
    bars: int = typer.Option(96, "--bars", min=1),
    bpm: int | None = typer.Option(None, "--bpm", min=20, max=400),
    bpm_override: float | None = typer.Option(
        None, "--bpm-override", min=20, max=400, help="Force tempo estimation to this BPM."
    ),
    seed: int = typer.Option(7, "--seed"),
    out: Path = typer.Option(..., "--out"),
    ppq: int = typer.Option(480, "--ppq", min=24),
) -> None:
    """Generate drum MIDI from a StyleSpec or prompt (M1.3), optionally audio-aligned (M2.3)."""
    import json as _json

    from beatforge.audio.analyze import Analysis, analysis_to_json
    from beatforge.audio.groove import analyze_groove, groove_to_json
    from beatforge.gen.aligned import generate_aligned_events, load_analysis, load_groove

    def _coerce_analysis(obj: Analysis) -> Analysis:
        """Narrow a Groove (subclass) or Analysis to Analysis for aligned generation."""
        if not isinstance(obj, Analysis):
            raise TypeError(f"expected Analysis or Groove, got {type(obj).__name__}")
        return obj

    audio_sources = [s for s in (audio, analysis, groove_path) if s is not None]
    if len(audio_sources) > 1:
        raise typer.BadParameter("provide at most one of --audio, --analysis, or --groove")

    if (prompt is None) == (stylespec is None):
        raise typer.BadParameter("provide exactly one of --prompt or --stylespec")

    if prompt is not None:
        spec = _parse_prompt(prompt)
    else:
        assert stylespec is not None
        payload = _json.loads(stylespec.read_text(encoding="utf-8"))
        if "stylespec" in payload:
            payload = payload["stylespec"]
        spec = StyleSpec(**payload)

    if not audio_sources:
        effective_bpm = bpm if bpm is not None else (spec.bpm if spec.bpm is not None else 120)
        events = generate_from_stylespec(spec, bars=bars, seed=seed, ppq=ppq)
        path = write_drum_midi(events, out, bpm=effective_bpm, ppq=ppq)
        typer.echo(
            f"wrote {path} ({len(events)} note events) bpm={effective_bpm} spec={spec.model_dump()}"
        )
        return

    if audio is not None:
        groove_result = analyze_groove(audio, bpm_override=bpm_override)
        analysed: Analysis = groove_result
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)
            stem = audio.stem
            analysis_projection = Analysis(
                schema_version=groove_result.schema_version,
                source=groove_result.source,
                tempo_bpm=groove_result.tempo_bpm,
                tempo_confidence=groove_result.tempo_confidence,
                time_signature=groove_result.time_signature,
                beats_s=groove_result.beats_s,
                downbeats_s=groove_result.downbeats_s,
                bars=groove_result.bars,
            )
            (cache_dir / f"{stem}.analysis.json").write_text(
                analysis_to_json(analysis_projection), encoding="utf-8"
            )
            (cache_dir / f"{stem}.groove.json").write_text(
                groove_to_json(groove_result), encoding="utf-8"
            )
    elif analysis is not None:
        analysed = load_analysis(analysis)
    else:
        assert groove_path is not None
        analysed = load_groove(groove_path)

    analysed = _coerce_analysis(analysed)
    if tempo_mode not in ("follow", "fixed"):
        raise typer.BadParameter(f"unknown --tempo-mode {tempo_mode!r}; use 'follow' or 'fixed'")
    if tempo_mode == "fixed":
        effective_bpm = bpm if bpm is not None else (spec.bpm if spec.bpm is not None else 120)
    else:
        if bpm is not None:
            raise typer.BadParameter(
                "--bpm conflicts with --tempo-mode follow; use --tempo-mode fixed"
            )
        effective_bpm = round(analysed.tempo_bpm)

    events = generate_aligned_events(analysed, spec, seed=seed, ppq=ppq)
    ts_num, ts_den = analysed.time_signature.split("/", 1)
    path = write_drum_midi(
        events,
        out,
        bpm=int(max(20, min(400, effective_bpm))),
        time_signature=(int(ts_num), int(ts_den)),
        ppq=ppq,
    )
    typer.echo(
        f"wrote {path} ({len(events)} note events) bpm={int(max(20, min(400, effective_bpm)))} "
        f"bars={len(analysed.bars)} audio_aligned=True"
    )


@app.command("analyze")
def analyze(
    audio: Path = typer.Option(..., "--audio", exists=True, dir_okay=False, readable=True),
    out: Path = typer.Option(..., "--out"),
    bpm_override: float | None = typer.Option(
        None, "--bpm-override", min=20, max=400, help="Skip tempo estimation and use this BPM."
    ),
    time_signature: str = typer.Option("4/4", "--time-signature", help="e.g. 4/4."),
) -> None:
    """Analyse a local audio file into analysis.json (M2.1). Local-only, no network."""
    from beatforge.audio.analyze import analysis_to_json, analyze_audio

    result = analyze_audio(audio, bpm_override=bpm_override, time_signature=time_signature)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(analysis_to_json(result), encoding="utf-8")
    typer.echo(
        f"wrote {out} bpm={result.tempo_bpm} beats={len(result.beats_s)} bars={len(result.bars)}"
    )


@app.command("groove")
def groove(
    audio: Path = typer.Option(..., "--audio", exists=True, dir_okay=False, readable=True),
    out: Path = typer.Option(..., "--out"),
    bpm_override: float | None = typer.Option(
        None, "--bpm-override", min=20, max=400, help="Skip tempo estimation and use this BPM."
    ),
    time_signature: str = typer.Option("4/4", "--time-signature", help="e.g. 4/4."),
) -> None:
    """Extract groove.json (onsets + section hints) from a local audio file (M2.2)."""
    from beatforge.audio.groove import analyze_groove, groove_to_json

    result = analyze_groove(audio, bpm_override=bpm_override, time_signature=time_signature)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(groove_to_json(result), encoding="utf-8")
    typer.echo(
        f"wrote {out} onsets={len(result.onsets_s)} "
        f"sections={len(result.section_hints)} bars={len(result.bars)}"
    )


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
