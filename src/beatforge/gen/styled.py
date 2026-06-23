"""Prompt-driven (StyleSpec-driven) generator used by ``drumgen generate``.

Sits on top of the M1.1 rule-based engine and shapes its output according
to the supplied :class:`StyleSpec`. No audio path here — that arrives in
M2.3.
"""

from __future__ import annotations

import random
from collections.abc import Iterable

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
from .basic import KNOWN_STYLES
from .song_structure import Section, structure_for


def _hats_per_beat(spec: StyleSpec, section_name: str) -> int:
    if spec.hats == "16th":
        base = 4
    elif spec.hats in ("shuffle", "swing"):
        base = 3
    else:
        base = 2
    if section_name == "chorus":
        return base * 2
    if section_name == "outro":
        return max(1, base // 2)
    return base


def _kick_beats(spec: StyleSpec, section_name: str) -> tuple[int, ...]:
    """Return the set of beats (0..3) on which a kick lands."""
    base: tuple[int, ...]
    if section_name == "chorus":
        base = (0, 1, 2, 3)
    elif (spec.genre == "punk") or (section_name == "intro" and spec.genre in ("rock", "pop")):
        base = (0, 1, 2, 3) if spec.genre == "punk" else (0, 2)
    elif spec.genre == "funk":
        base = (0, 2, 3)
    elif spec.genre == "metal":
        base = (0, 1, 2, 3)
    else:
        base = (0, 2)

    if spec.kick_density == "more":
        # add the offbeat between hits
        extra = tuple(sorted(set(base) | {1, 3}))
        return extra
    if spec.kick_density == "less":
        return tuple(b for i, b in enumerate(base) if i % 2 == 0) or (0,)
    return base


def _snare_beats(spec: StyleSpec) -> tuple[int, ...]:
    if spec.backbeat == "2":
        return (1,)
    if spec.backbeat == "4":
        return (3,)
    return (1, 3)  # default and "2_and_4"


def _generate_section(
    section: Section,
    spec: StyleSpec,
    bar_offset: int,
    ppq: int,
    rng: random.Random,
    *,
    next_section_name: str | None,
) -> Iterable[DrumEvent]:
    if section.bars == 0:
        return []
    events: list[DrumEvent] = []
    beats_per_bar = 4

    hats_per_beat = _hats_per_beat(spec, section.name)
    hat_tick = ppq // hats_per_beat

    kick_beats = _kick_beats(spec, section.name)
    snare_beats = _snare_beats(spec)

    fill_last_bar = False
    if spec.fills == "before_chorus":
        fill_last_bar = next_section_name == "chorus" and section.name == "verse"
    elif spec.fills == "more":
        fill_last_bar = section.name in ("verse", "chorus")
    elif spec.fills == "fewer":
        fill_last_bar = section.name == "verse" and next_section_name == "chorus"
    elif spec.fills == "default":
        fill_last_bar = section.name in ("verse", "chorus")
    # "none" leaves fill_last_bar False.

    for bar in range(section.bars):
        absolute_bar = bar_offset + bar
        bar_start = absolute_bar * beats_per_bar * ppq
        is_fill_bar = fill_last_bar and bar == section.bars - 1

        for beat in range(beats_per_bar):
            beat_start = bar_start + beat * ppq

            if beat in kick_beats:
                base_vel = 108
                vel = max(1, min(127, base_vel + rng.randint(-5, 5)))
                events.append(DrumEvent(beat_start, GM_KICK, velocity=vel))

            if beat in snare_beats:
                base_vel = 115 if section.name == "chorus" else 105
                vel = max(1, min(127, base_vel + rng.randint(-5, 5)))
                events.append(DrumEvent(beat_start, GM_SNARE, velocity=vel))
                if spec.ghost_notes:
                    ghost_offset = ppq // 2  # halfway to the next beat
                    ghost_vel = max(1, min(127, 45 + rng.randint(-2, 2)))
                    events.append(
                        DrumEvent(beat_start + ghost_offset, GM_SNARE, velocity=ghost_vel)
                    )

            for h in range(hats_per_beat):
                hat_vel = max(1, min(127, 80 + rng.randint(-3, 3)))
                events.append(DrumEvent(beat_start + h * hat_tick, GM_CLOSED_HAT, velocity=hat_vel))

            # Ride cymbal: on beat 0 in verse/chorus, more frequent in chorus
            if section.name in ("verse", "chorus") and (
                beat == 0 or (section.name == "chorus" and beat % 2 == 0)
            ):
                ride_vel = max(1, min(127, 90 + rng.randint(-5, 5)))
                events.append(DrumEvent(beat_start, GM_RIDE, velocity=ride_vel))

        if is_fill_bar:
            # Fill pattern: crash + toms
            beat_start = bar_start + 3 * ppq
            sixteenth = ppq // 4

            # Add crash cymbal on the first beat of the fill
            crash_vel = max(1, min(127, 110 + rng.randint(-5, 5)))
            events.append(DrumEvent(beat_start, GM_CRASH, velocity=crash_vel))

            # Tom fill pattern
            tom_sequence = [GM_TOM_HI, GM_TOM_MID, GM_TOM_LO, GM_TOM_LO]
            base_v = 100 + rng.randint(-5, 5)
            # remove any hats we already queued on this beat to keep the fill clean
            events = [
                ev
                for ev in events
                if not (ev.note == GM_CLOSED_HAT and beat_start <= ev.start_tick < beat_start + ppq)
            ]
            for i, drum in enumerate(tom_sequence):
                events.append(DrumEvent(beat_start + i * sixteenth, drum, velocity=base_v))

    return events


def generate_from_stylespec(
    spec: StyleSpec,
    *,
    bars: int,
    seed: int = 0,
    ppq: int = 480,
) -> list[DrumEvent]:
    """Return the list of drum events for a song shaped by ``spec``."""
    if spec.genre is not None and spec.genre not in KNOWN_STYLES and spec.genre != "metal":
        raise ValueError(f"unknown genre {spec.genre!r}")
    rng = random.Random(seed)
    sections = structure_for(bars)
    events: list[DrumEvent] = []
    bar_offset = 0
    for idx, section in enumerate(sections):
        next_section_name = sections[idx + 1].name if idx + 1 < len(sections) else None
        events.extend(
            _generate_section(
                section,
                spec,
                bar_offset=bar_offset,
                ppq=ppq,
                rng=rng,
                next_section_name=next_section_name,
            )
        )
        bar_offset += section.bars
    return events
