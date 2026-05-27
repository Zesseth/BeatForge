"""MIDI generation primitives for BeatForge.

Conventions used across this package:

* PPQ defaults to 480.
* All drum notes go to MIDI **channel 10** which is ``channel=9`` in mido's
  0-indexed API. The constant :data:`DRUM_CHANNEL` enforces this — never write
  a raw ``9`` in MIDI code outside this package.
* Standard MIDI File format 1 with a single track unless documented otherwise.
"""

from __future__ import annotations

DRUM_CHANNEL: int = 9
DEFAULT_PPQ: int = 480
DEFAULT_BPM: int = 120
DEFAULT_TIME_SIGNATURE: tuple[int, int] = (4, 4)

GM_KICK: int = 36
GM_SNARE: int = 38
GM_CLOSED_HAT: int = 42
GM_OPEN_HAT: int = 46
GM_RIDE: int = 51
GM_CRASH: int = 49
GM_TOM_HI: int = 50
GM_TOM_MID: int = 47
GM_TOM_LO: int = 43
