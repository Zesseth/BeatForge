"""Audio-aligned drum generation (M2.3).

Bridges ``analysis.json`` / ``groove.json`` (from :mod:`beatforge.audio`)
to MIDI events: tempo follows the analysed audio, and every event is
quantised onto the analysed beat grid. Deterministic for the same
inputs + same seed (M2 sits in the byte-identical M0–M3 tier).

No audio buffers are touched here — the input is the symbolic JSON
produced by local analysis. No network.
"""

from __future__ import annotations

import random
from pathlib import Path

from ..audio.analyze import Analysis
from ..audio.groove import Groove
from ..midi import (
    GM_CLOSED_HAT,
    GM_CRASH,
    GM_KICK,
    GM_RIDE,
    GM_SNARE,
    GM_TOM_HI,
    GM_TOM_LO,
    GM_TOM_MID,
)
from ..midi.writer import DrumEvent
from ..prompt.stylespec import StyleSpec


def load_analysis(path: Path | str) -> Analysis:
    """Load and validate an ``analysis.json`` file."""
    import json

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return Analysis.model_validate(payload)


def load_groove(path: Path | str) -> Groove:
    """Load and validate a ``groove.json`` file."""
    import json

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return Groove.model_validate(payload)


def _parse_time_signature(time_signature: str) -> tuple[int, int]:
    num_str, den_str = time_signature.split("/", 1)
    num, den = int(num_str), int(den_str)
    if num <= 0 or den <= 0:
        raise ValueError(f"invalid time signature: {time_signature!r}")
    return num, den


def _hats_subdivision(spec: StyleSpec) -> int:
    """Subdivision slots per beat based on StyleSpec.hats."""
    if spec.hats == "16th":
        return 4
    if spec.hats in ("shuffle", "swing"):
        return 3
    return 2


def _kick_slots(spec: StyleSpec, beats_per_bar: int, subdivisions: int) -> set[int]:
    """Kick on beats 1 and 3 (scaled to the subdivision grid)."""
    beats = {0, 2} if beats_per_bar >= 4 else {0}
    if spec.kick_density == "more":
        beats = set(range(beats_per_bar))
    elif spec.kick_density == "less":
        beats = {0}
    return {b * subdivisions for b in beats}


def _snare_slots(spec: StyleSpec, beats_per_bar: int, subdivisions: int) -> set[int]:
    """Backbeat snares (beats 2 and 4 by default), scaled to the grid."""
    if beats_per_bar >= 4:
        if spec.backbeat == "2":
            beats = {1}
        elif spec.backbeat == "4":
            beats = {3}
        else:
            beats = {1, 3}
    else:
        beats = {beats_per_bar - 1}
    return {b * subdivisions for b in beats}


def _chorus_bars(analysis: Analysis) -> set[int]:
    """Bar indices the analysis marks as ``chorus`` (empty without hints)."""
    hints = getattr(analysis, "section_hints", None) or []
    return {bar for h in hints if h.label == "chorus" for bar in range(h.bar_start, h.bar_end + 1)}


def _fill_bar_indices(spec: StyleSpec, total_bars: int, chorus_bars: set[int]) -> set[int]:
    """Fill-bar selection honouring every StyleSpec.fills intent.

    ``before_chorus``: last bar of each verse immediately preceding a
    chorus section hint (mirrors the styled generator's section logic).
    ``more``/``default``: every other bar. ``fewer``: the final bar only.
    "none``: never.
    """
    if spec.fills == "none":
        return set()
    if spec.fills == "fewer":
        return {total_bars - 1}
    if spec.fills == "before_chorus":
        fill_bars: set[int] = set()
        if not chorus_bars:
            return {total_bars - 1}
        for bar in range(total_bars - 1):
            if bar not in chorus_bars and (bar + 1) in chorus_bars:
                fill_bars.add(bar)
        return fill_bars or {total_bars - 1}
    return {bar for bar in range(0, total_bars, 2)}


def generate_aligned_events(
    analysis: Analysis,
    spec: StyleSpec,
    *,
    seed: int = 0,
    ppq: int = 480,
    max_bars: int | None = None,
) -> list[DrumEvent]:
    """Generate drum events aligned to the analysed beat grid.

    Events are laid on the analysed beat timestamps (mapped to MIDI ticks
    via the fixed tempo) so the MIDI lines up with the audio, including
    the audio's initial downbeat offset; the analysed bar count bounds the
    output length (rounded down to whole bars).

    Raises ``ValueError`` when the analysis contains no complete bar.
    """
    rng = random.Random(seed)
    beats_per_bar, denominator = _parse_time_signature(analysis.time_signature)
    subdivisions = _hats_subdivision(spec)
    kick_slots = _kick_slots(spec, beats_per_bar, subdivisions)
    snare_slots = _snare_slots(spec, beats_per_bar, subdivisions)

    total_bars = len(analysis.bars) if max_bars is None else min(max_bars, len(analysis.bars))
    if total_bars <= 0:
        raise ValueError("analysis contains no complete bar; nothing to align against")

    if denominator != 4:
        raise ValueError(
            f"unsupported time signature {analysis.time_signature!r}: "
            "audio-aligned generation currently supports /4 denominators only"
        )
    beat_ticks = ppq
    beats_per_bar_eff = beats_per_bar

    slots_per_bar = beats_per_bar_eff * subdivisions
    slot_ticks = beat_ticks // subdivisions
    if slot_ticks < 1:
        raise ValueError(f"subdivision does not fit ppq={ppq}")
    bar_ticks = slots_per_bar * slot_ticks
    chorus_bars = _chorus_bars(analysis)
    fill_bars = _fill_bar_indices(spec, total_bars, chorus_bars)

    ticks_per_second = analysis.tempo_bpm / 60.0 * ppq
    first_beat_s = analysis.beats_s[0] if analysis.beats_s else analysis.bars[0].start_s
    grid_origin = int(round(first_beat_s * ticks_per_second))

    events: list[DrumEvent] = []
    for bar in range(total_bars):
        bar_origin = grid_origin + bar * bar_ticks
        is_chorus = bar in chorus_bars
        is_fill = bar in fill_bars

        for slot in range(slots_per_bar):
            tick = bar_origin + slot * slot_ticks
            if slot in kick_slots:
                vel = max(1, min(127, 108 + rng.randint(-5, 5)))
                events.append(DrumEvent(tick, GM_KICK, velocity=vel))
            if slot in snare_slots:
                base_v = 115 if is_chorus else 105
                vel = max(1, min(127, base_v + rng.randint(-5, 5)))
                events.append(DrumEvent(tick, GM_SNARE, velocity=vel))
            hat_vel = max(1, min(127, 80 + rng.randint(-3, 3)))
            events.append(DrumEvent(tick, GM_CLOSED_HAT, velocity=hat_vel))

        if is_chorus and bar % 2 == 0:
            events.append(DrumEvent(bar_origin, GM_RIDE, velocity=90))

        if is_fill:
            fill_step = beat_ticks // 4
            fill_origin = bar_origin + (beats_per_bar_eff - 1) * beat_ticks
            events.append(DrumEvent(fill_origin, GM_CRASH, velocity=110))
            for i, drum in enumerate((GM_TOM_HI, GM_TOM_MID, GM_TOM_LO, GM_TOM_LO)):
                events.append(DrumEvent(fill_origin + i * fill_step, drum, velocity=100))

    return events


def bars_from_duration(analysis: Analysis) -> int:
    """Whole bars covered by the analysed bars list."""
    return len(analysis.bars)
