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


def generate_aligned_events(
    analysis: Analysis,
    spec: StyleSpec,
    *,
    seed: int = 0,
    ppq: int = 480,
    max_bars: int | None = None,
) -> list[DrumEvent]:
    """Generate drum events aligned to the analysed beat grid.

    Events are laid on an even grid derived from the analysis tempo so the
    MIDI beats line up with the audio; the analysed bar count bounds the
    output length (rounded down to whole bars).
    """
    rng = random.Random(seed)
    beats_per_bar, _den = _parse_time_signature(analysis.time_signature)
    subdivisions = _hats_subdivision(spec)
    kick_slots = _kick_slots(spec, beats_per_bar, subdivisions)
    snare_slots = _snare_slots(spec, beats_per_bar, subdivisions)

    total_bars = len(analysis.bars) if max_bars is None else min(max_bars, len(analysis.bars))
    if total_bars <= 0:
        return []

    slots_per_bar = beats_per_bar * subdivisions
    slot_ticks = ppq // subdivisions
    bar_ticks = slots_per_bar * slot_ticks
    chorus_bars = _chorus_bars(analysis)
    fill_bars: set[int] = set() if spec.fills == "none" else {total_bars - 1}

    events: list[DrumEvent] = []
    for bar in range(total_bars):
        bar_origin = bar * bar_ticks
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
            fill_step = ppq // max(1, subdivisions // 2) or ppq
            fill_origin = bar_origin + (beats_per_bar - 1) * ppq
            events.append(DrumEvent(fill_origin, GM_CRASH, velocity=110))
            for i, drum in enumerate((GM_TOM_HI, GM_TOM_MID, GM_TOM_LO, GM_TOM_LO)):
                events.append(DrumEvent(fill_origin + i * fill_step, drum, velocity=100))

    return events


def bars_from_duration(analysis: Analysis) -> int:
    """Whole bars covered by the analysed bars list."""
    return len(analysis.bars)
