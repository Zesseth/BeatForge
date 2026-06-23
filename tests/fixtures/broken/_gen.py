"""Generate the broken MIDI fixtures used by tests/test_validator.py.

Run from the repository root::

    python -m tests.fixtures.broken._gen

The fixtures are intentionally produced by code (not committed audio binaries)
so the privacy harness and reviewers can reason about what is in them.
"""

from __future__ import annotations

from pathlib import Path

import mido

HERE = Path(__file__).parent


def _no_tempo() -> mido.MidiFile:
    mid = mido.MidiFile(type=1, ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    # time signature only; no set_tempo
    track.append(
        mido.MetaMessage(
            "time_signature",
            numerator=4,
            denominator=4,
            clocks_per_click=24,
            notated_32nd_notes_per_beat=8,
            time=0,
        )
    )
    track.append(mido.Message("note_on", channel=9, note=36, velocity=100, time=0))
    track.append(mido.Message("note_off", channel=9, note=36, velocity=0, time=30))
    track.append(mido.MetaMessage("end_of_track", time=0))
    return mid


def _wrong_channel() -> mido.MidiFile:
    mid = mido.MidiFile(type=1, ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(
        mido.MetaMessage(
            "time_signature",
            numerator=4,
            denominator=4,
            clocks_per_click=24,
            notated_32nd_notes_per_beat=8,
            time=0,
        )
    )
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
    # channel 0 instead of 9 — wrong for drums
    track.append(mido.Message("note_on", channel=0, note=36, velocity=100, time=0))
    track.append(mido.Message("note_off", channel=0, note=36, velocity=0, time=30))
    track.append(mido.MetaMessage("end_of_track", time=0))
    return mid


def _empty_notes() -> mido.MidiFile:
    mid = mido.MidiFile(type=1, ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(
        mido.MetaMessage(
            "time_signature",
            numerator=4,
            denominator=4,
            clocks_per_click=24,
            notated_32nd_notes_per_beat=8,
            time=0,
        )
    )
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
    track.append(mido.MetaMessage("end_of_track", time=0))
    return mid


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    _no_tempo().save(HERE / "no-tempo.mid")
    _wrong_channel().save(HERE / "wrong-channel.mid")
    _empty_notes().save(HERE / "empty-notes.mid")


if __name__ == "__main__":
    main()
