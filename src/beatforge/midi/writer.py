"""Standard MIDI File writer used by all BeatForge generators.

This is a thin, deterministic layer over :mod:`mido` so we can:

* enforce drum channel 10 (mido index 9) at write time,
* emit a tempo + time-signature meta event at tick 0,
* and keep byte-stable output across runs (mido is byte-stable provided we feed
  it events in the same order with the same timings).

Higher-level pattern generators emit :class:`DrumEvent` instances which this
module turns into a :class:`mido.MidiFile`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import mido

from . import (
    DEFAULT_BPM,
    DEFAULT_PPQ,
    DEFAULT_TIME_SIGNATURE,
    DRUM_CHANNEL,
)


@dataclass(frozen=True, slots=True)
class DrumEvent:
    """A single percussion hit.

    ``start_tick`` is absolute (ticks from start-of-file). The writer is
    responsible for converting to delta-times before serialisation.
    """

    start_tick: int
    note: int
    velocity: int = 100
    duration_ticks: int = 30

    def __post_init__(self) -> None:
        if not 0 <= self.note <= 127:
            raise ValueError(f"note out of MIDI range: {self.note}")
        if not 1 <= self.velocity <= 127:
            raise ValueError(f"velocity out of range: {self.velocity}")
        if self.start_tick < 0:
            raise ValueError(f"start_tick must be non-negative: {self.start_tick}")
        if self.duration_ticks <= 0:
            raise ValueError(f"duration_ticks must be positive: {self.duration_ticks}")


def write_drum_midi(
    events: list[DrumEvent],
    out_path: Path | str,
    *,
    bpm: int = DEFAULT_BPM,
    time_signature: tuple[int, int] = DEFAULT_TIME_SIGNATURE,
    ppq: int = DEFAULT_PPQ,
) -> Path:
    """Serialise ``events`` to a Standard MIDI File at ``out_path``.

    All notes are forced to MIDI channel 10 (mido index 9). The tempo and
    time-signature meta events are emitted at tick 0. The track is closed
    with an ``end_of_track`` meta event.
    """
    if ppq <= 0:
        raise ValueError(f"ppq must be positive: {ppq}")
    if bpm <= 0:
        raise ValueError(f"bpm must be positive: {bpm}")
    if time_signature[0] <= 0 or time_signature[1] <= 0:
        raise ValueError(f"invalid time signature: {time_signature}")

    mid = mido.MidiFile(type=1, ticks_per_beat=ppq)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(
        mido.MetaMessage(
            "time_signature",
            numerator=time_signature[0],
            denominator=time_signature[1],
            clocks_per_click=24,
            notated_32nd_notes_per_beat=8,
            time=0,
        )
    )
    track.append(
        mido.MetaMessage(
            "set_tempo",
            tempo=mido.bpm2tempo(bpm),
            time=0,
        )
    )

    timeline: list[tuple[int, str, int, int]] = []
    for ev in events:
        timeline.append((ev.start_tick, "on", ev.note, ev.velocity))
        timeline.append((ev.start_tick + ev.duration_ticks, "off", ev.note, 0))
    # Sort by absolute tick, then off-before-on at the same tick so back-to-back
    # hits on the same note retrigger cleanly in DAWs.
    off_first = {"off": 0, "on": 1}
    timeline.sort(key=lambda t: (t[0], off_first[t[1]], t[2]))

    prev_tick = 0
    for abs_tick, kind, note, velocity in timeline:
        delta = abs_tick - prev_tick
        prev_tick = abs_tick
        msg_type = "note_on" if kind == "on" else "note_off"
        track.append(
            mido.Message(
                msg_type,
                channel=DRUM_CHANNEL,
                note=note,
                velocity=velocity,
                time=delta,
            )
        )
    track.append(mido.MetaMessage("end_of_track", time=0))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(out_path)
    return out_path
