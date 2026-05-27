"""Default song structure used by ``drumgen generate-basic``.

A song is a sequence of named :class:`Section` objects with bar counts. The
section name drives generator intensity (verse vs chorus etc).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Section:
    name: str
    bars: int

    def __post_init__(self) -> None:
        if self.bars < 0:
            raise ValueError(f"bars must be non-negative: {self.bars}")


DEFAULT_STRUCTURE: tuple[Section, ...] = (
    Section("intro", 8),
    Section("verse", 16),
    Section("chorus", 16),
    Section("verse", 16),
    Section("chorus", 16),
    Section("outro", 8),
)


def structure_for(total_bars: int) -> list[Section]:
    """Scale :data:`DEFAULT_STRUCTURE` so bar counts sum to ``total_bars``.

    Sections are scaled proportionally and the outro absorbs any rounding
    remainder. Below 12 bars we collapse to a single ``main`` section since
    six labelled sections become musically meaningless.
    """
    if total_bars <= 0:
        raise ValueError(f"total_bars must be positive: {total_bars}")
    if total_bars < 12:
        return [Section("main", total_bars)]

    default_total = sum(s.bars for s in DEFAULT_STRUCTURE)
    scaled: list[Section] = []
    running = 0
    for s in DEFAULT_STRUCTURE[:-1]:
        bars = max(1, round(s.bars * total_bars / default_total))
        scaled.append(Section(s.name, bars))
        running += bars
    remainder = total_bars - running
    if remainder < 1:
        # rounding pushed us over; trim from the biggest section.
        deficit = 1 - remainder
        idx = max(range(len(scaled)), key=lambda i: scaled[i].bars)
        scaled[idx] = Section(scaled[idx].name, scaled[idx].bars - deficit)
        remainder = 1
    scaled.append(Section(DEFAULT_STRUCTURE[-1].name, remainder))
    return scaled
