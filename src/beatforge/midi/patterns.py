"""Hard-coded baseline drum patterns used by ``drumgen make-empty``.

The patterns here are intentionally minimal and rhythmically obvious so that
test fixtures and REAPER imports remain easy to eyeball. Anything richer
belongs in ``beatforge.gen``.
"""

from __future__ import annotations

from . import GM_CLOSED_HAT, GM_KICK, GM_SNARE
from .writer import DrumEvent


def basic_rock_pattern(bars: int, ppq: int) -> list[DrumEvent]:
    """Kick on beats 1+3, snare on 2+4, closed hat on every 8th note.

    Assumes 4/4. ``bars`` is the number of bars to repeat across.
    """
    if bars <= 0:
        raise ValueError(f"bars must be positive: {bars}")
    events: list[DrumEvent] = []
    beats_per_bar = 4
    hats_per_beat = 2  # 8th notes
    eighth = ppq // 2

    for bar in range(bars):
        bar_start = bar * beats_per_bar * ppq
        for beat in range(beats_per_bar):
            beat_start = bar_start + beat * ppq
            if beat in (0, 2):
                events.append(DrumEvent(beat_start, GM_KICK, velocity=110))
            if beat in (1, 3):
                events.append(DrumEvent(beat_start, GM_SNARE, velocity=105))
            for h in range(hats_per_beat):
                events.append(
                    DrumEvent(beat_start + h * eighth, GM_CLOSED_HAT, velocity=80)
                )
    return events
