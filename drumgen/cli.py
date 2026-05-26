from __future__ import annotations

import argparse
import math
from pathlib import Path

DEFAULT_BPM = 120
DEFAULT_PPQ = 480
DEFAULT_TIME_SIGNATURE = (4, 4)
DRUM_CHANNEL = 9
GM_KICK = 36
GM_SNARE = 38
GM_CLOSED_HIHAT = 42


def _var_len(value: int) -> bytes:
    if value < 0:
        raise ValueError("Variable-length MIDI values must be >= 0")
    encoded = [value & 0x7F]
    value >>= 7
    while value:
        encoded.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(encoded))


def _tempo_meta_event(bpm: int) -> bytes:
    microseconds_per_quarter = round(60_000_000 / bpm)
    return b"\xFF\x51\x03" + microseconds_per_quarter.to_bytes(3, byteorder="big")


def _time_signature_meta_event(numerator: int, denominator: int) -> bytes:
    if denominator <= 0 or (denominator & (denominator - 1)) != 0:
        raise ValueError("Time signature denominator must be a power of 2")
    return b"\xFF\x58\x04" + bytes([numerator, int(math.log2(denominator)), 24, 8])


def _note_on(note: int, velocity: int) -> bytes:
    return bytes([0x90 | DRUM_CHANNEL, note, velocity])


def _note_off(note: int) -> bytes:
    return bytes([0x80 | DRUM_CHANNEL, note, 0])


def write_drum_midi(
    out_path: Path,
    bars: int,
    bpm: int = DEFAULT_BPM,
    ppq: int = DEFAULT_PPQ,
    time_signature: tuple[int, int] = DEFAULT_TIME_SIGNATURE,
) -> None:
    if bars <= 0:
        raise ValueError("bars must be greater than 0")
    if bpm <= 0:
        raise ValueError("bpm must be greater than 0")
    if ppq <= 0:
        raise ValueError("ppq must be greater than 0")

    numerator, denominator = time_signature
    events: list[tuple[int, int, bytes]] = [
        (0, -2, _tempo_meta_event(bpm)),
        (0, -1, _time_signature_meta_event(numerator, denominator)),
    ]

    bar_ticks = numerator * ppq

    for bar_index in range(bars):
        start = bar_index * bar_ticks
        for tick in (start, start + (2 * ppq)):
            events.append((tick, 1, _note_on(GM_KICK, 110)))
            events.append((tick + (ppq // 2), 0, _note_off(GM_KICK)))

        for tick in (start + ppq, start + (3 * ppq)):
            events.append((tick, 1, _note_on(GM_SNARE, 100)))
            events.append((tick + (ppq // 2), 0, _note_off(GM_SNARE)))

        eighth = ppq // 2
        for step in range(numerator * 2):
            tick = start + (step * eighth)
            events.append((tick, 1, _note_on(GM_CLOSED_HIHAT, 80)))
            events.append((tick + (ppq // 4), 0, _note_off(GM_CLOSED_HIHAT)))

    events.sort(key=lambda item: (item[0], item[1]))

    track_data = bytearray()
    previous_tick = 0
    for tick, _, event_data in events:
        track_data += _var_len(tick - previous_tick)
        track_data += event_data
        previous_tick = tick

    track_data += _var_len(0)
    track_data += b"\xFF\x2F\x00"

    header = b"MThd" + (6).to_bytes(4, "big") + (0).to_bytes(2, "big") + (1).to_bytes(2, "big") + ppq.to_bytes(2, "big")
    track_chunk = b"MTrk" + len(track_data).to_bytes(4, "big") + bytes(track_data)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(header + track_chunk)


def _parse_time_signature(value: str) -> tuple[int, int]:
    try:
        numerator_text, denominator_text = value.split("/", 1)
        numerator = int(numerator_text)
        denominator = int(denominator_text)
    except (ValueError, TypeError) as error:
        raise argparse.ArgumentTypeError("Time signature must look like 4/4") from error

    if numerator <= 0 or denominator <= 0:
        raise argparse.ArgumentTypeError("Time signature values must be positive")
    if denominator & (denominator - 1):
        raise argparse.ArgumentTypeError("Time signature denominator must be a power of 2")

    return numerator, denominator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="drumgen")
    subcommands = parser.add_subparsers(dest="command", required=True)

    make_empty = subcommands.add_parser("make-empty", help="Generate a basic drum MIDI file")
    make_empty.add_argument("--bars", type=int, required=True, help="Number of bars to generate")
    make_empty.add_argument("--bpm", type=int, default=DEFAULT_BPM, help="Tempo in BPM")
    make_empty.add_argument("--ppq", type=int, default=DEFAULT_PPQ, help="Ticks per quarter note")
    make_empty.add_argument("--time-signature", type=_parse_time_signature, default=DEFAULT_TIME_SIGNATURE)
    make_empty.add_argument("--out", type=Path, required=True, help="Output MIDI file path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "make-empty":
        write_drum_midi(
            out_path=args.out,
            bars=args.bars,
            bpm=args.bpm,
            ppq=args.ppq,
            time_signature=args.time_signature,
        )
        return 0

    parser.error("Unknown command")
    return 2
