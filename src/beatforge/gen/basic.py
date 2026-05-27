"""Rule-based song generator used by ``drumgen generate-basic``.

Determinism: the only source of randomness is a ``random.Random`` instance
constructed from the explicit ``seed`` argument. Same args + same seed =>
byte-identical output (enforced by tests).
"""

from __future__ import annotations

import random

from ..midi import (
    GM_CLOSED_HAT,
    GM_KICK,
    GM_SNARE,
    GM_TOM_HI,
    GM_TOM_LO,
    GM_TOM_MID,
)
from ..midi.writer import DrumEvent
from .song_structure import Section, structure_for

KNOWN_STYLES: frozenset[str] = frozenset({"rock", "pop", "punk", "funk"})


def _hats_per_beat(style: str, section_name: str) -> int:
    """Hat density in subdivisions per beat for a given section.

    ``chorus`` always doubles the verse density so chorus busyness is
    structurally guaranteed (asserted in tests).
    """
    base = 2  # 8th notes
    if style == "funk":
        base = 4  # funk → 16th hats throughout
    elif style == "punk":
        base = 2  # punk stays on 8ths, energy comes from kick density
    if section_name == "chorus":
        return base * 2
    if section_name == "outro":
        return max(1, base // 2)
    return base


def _kick_pattern(style: str, section_name: str, beat: int) -> bool:
    """Return True if a kick should land on this beat (0-indexed 0..3)."""
    if section_name == "chorus":
        # chorus → kick on every beat
        return True
    if style == "punk":
        return True  # punk → constant kick
    if style == "funk":
        return beat in (0, 2, 3)  # syncopated
    return beat in (0, 2)  # rock/pop/default


def _generate_section(
    section: Section,
    style: str,
    bar_offset: int,
    ppq: int,
    rng: random.Random,
) -> list[DrumEvent]:
    events: list[DrumEvent] = []
    beats_per_bar = 4
    if section.bars == 0:
        return events

    hats_per_beat = _hats_per_beat(style, section.name)
    hat_tick = ppq // hats_per_beat

    for bar in range(section.bars):
        absolute_bar = bar_offset + bar
        bar_start = absolute_bar * beats_per_bar * ppq

        is_fill_bar = section.name in ("verse", "chorus") and bar == section.bars - 1

        for beat in range(beats_per_bar):
            beat_start = bar_start + beat * ppq

            if _kick_pattern(style, section.name, beat):
                vel = 110 if section.name == "chorus" else 100
                events.append(DrumEvent(beat_start, GM_KICK, velocity=vel))

            if beat in (1, 3):
                vel = 115 if section.name == "chorus" else 105
                events.append(DrumEvent(beat_start, GM_SNARE, velocity=vel))

            for h in range(hats_per_beat):
                events.append(
                    DrumEvent(beat_start + h * hat_tick, GM_CLOSED_HAT, velocity=80)
                )

        # Trivial 4-tom fill on the last beat of the last bar of verse/chorus.
        if is_fill_bar:
            beat_start = bar_start + 3 * ppq
            sixteenth = ppq // 4
            tom_sequence = [GM_TOM_HI, GM_TOM_MID, GM_TOM_LO, GM_TOM_LO]
            # Use rng to choose a per-fill velocity dither; keeps deterministic
            # output stable but exercises the rng so seed actually matters.
            base_v = 100 + rng.randint(-5, 5)
            for i, drum in enumerate(tom_sequence):
                events.append(
                    DrumEvent(beat_start + i * sixteenth, drum, velocity=base_v)
                )

    return events


def generate_basic_song(
    *,
    bars: int,
    style: str = "rock",
    seed: int = 0,
    ppq: int = 480,
) -> list[DrumEvent]:
    """Produce a deterministic list of drum events for the given song."""
    if style not in KNOWN_STYLES:
        raise ValueError(
            f"unknown style {style!r}; known: {sorted(KNOWN_STYLES)}"
        )
    rng = random.Random(seed)
    sections = structure_for(bars)
    events: list[DrumEvent] = []
    bar_offset = 0
    for section in sections:
        events.extend(
            _generate_section(section, style=style, bar_offset=bar_offset, ppq=ppq, rng=rng)
        )
        bar_offset += section.bars
    return events
