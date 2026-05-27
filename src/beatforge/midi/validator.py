"""Validator for ``drumgen validate-midi``.

Checks a MIDI file against BeatForge's REAPER-ready ruleset:

1. File parses as a Standard MIDI File.
2. A ``set_tempo`` meta event is present.
3. A ``time_signature`` meta event is present (warning unless ``strict``).
4. Every ``note_on`` is on MIDI channel 10 (mido index 9).
5. Notes fall within the GM percussion range 35–81; at least one of
   ``{36, 38, 42}`` is present.
6. The file has non-zero drum note content.

Returns a :class:`ValidationReport` instead of raising — callers (CLI, tests)
decide how to surface results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import mido

from . import DRUM_CHANNEL, GM_CLOSED_HAT, GM_KICK, GM_SNARE

GM_PERCUSSION_MIN: int = 35
GM_PERCUSSION_MAX: int = 81
_REQUIRED_ANCHOR_NOTES: frozenset[int] = frozenset({GM_KICK, GM_SNARE, GM_CLOSED_HAT})


@dataclass(slots=True)
class ValidationReport:
    """Result of validating a MIDI file."""

    path: str
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, int | float | str] = field(default_factory=dict)

    def add_error(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "stats": dict(self.stats),
        }


def validate_midi_file(path: Path | str, *, strict: bool = False) -> ValidationReport:
    """Validate ``path`` and return a :class:`ValidationReport`."""
    report = ValidationReport(path=str(path))

    try:
        mid = mido.MidiFile(str(path))
    except OSError as exc:
        report.add_error(f"cannot open file: {exc}")
        return report
    except Exception as exc:  # noqa: BLE001 - mido raises bare Exception on bad SMF
        report.add_error(f"failed to parse as MIDI: {exc}")
        return report

    all_messages = [m for track in mid.tracks for m in track]
    has_tempo = any(m.is_meta and m.type == "set_tempo" for m in all_messages)
    has_ts = any(m.is_meta and m.type == "time_signature" for m in all_messages)

    if not has_tempo:
        report.add_error("missing set_tempo meta event")
    if not has_ts:
        msg = "missing time_signature meta event"
        if strict:
            report.add_error(msg)
        else:
            report.add_warning(msg)

    note_ons = [m for m in all_messages if m.type == "note_on" and m.velocity > 0]
    report.stats["note_on_count"] = len(note_ons)
    report.stats["ppq"] = mid.ticks_per_beat

    if not note_ons:
        report.add_error("file contains zero note_on events")
        return report

    off_channel = [m for m in note_ons if m.channel != DRUM_CHANNEL]
    if off_channel:
        report.add_error(
            f"{len(off_channel)} note_on events not on MIDI channel 10 "
            f"(mido channel {DRUM_CHANNEL})"
        )

    pitches = {m.note for m in note_ons}
    report.stats["unique_pitches"] = len(pitches)

    out_of_range = [n for n in pitches if not GM_PERCUSSION_MIN <= n <= GM_PERCUSSION_MAX]
    if out_of_range:
        report.add_warning(
            f"{len(out_of_range)} pitches outside GM percussion range "
            f"({GM_PERCUSSION_MIN}-{GM_PERCUSSION_MAX}): {sorted(out_of_range)}"
        )

    if not pitches & _REQUIRED_ANCHOR_NOTES:
        report.add_error(
            f"no anchor drum notes found (need at least one of "
            f"{sorted(_REQUIRED_ANCHOR_NOTES)}, got {sorted(pitches)})"
        )

    return report
