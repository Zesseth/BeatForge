from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from drumgen.cli import GM_CLOSED_HIHAT, GM_KICK, GM_SNARE


def _decode_var_len(data: bytes, index: int) -> tuple[int, int]:
    value = 0
    while True:
        byte = data[index]
        index += 1
        value = (value << 7) | (byte & 0x7F)
        if not (byte & 0x80):
            return value, index


def _parse_midi_track(data: bytes):
    assert data[:4] == b"MThd"
    ppq = int.from_bytes(data[12:14], byteorder="big")
    assert data[14:18] == b"MTrk"
    track_length = int.from_bytes(data[18:22], byteorder="big")
    track = data[22 : 22 + track_length]

    idx = 0
    tick = 0
    events = []
    while idx < len(track):
        delta, idx = _decode_var_len(track, idx)
        tick += delta
        status = track[idx]
        idx += 1

        if status == 0xFF:
            meta_type = track[idx]
            idx += 1
            meta_len, idx = _decode_var_len(track, idx)
            payload = track[idx : idx + meta_len]
            idx += meta_len
            events.append((tick, "meta", meta_type, payload))
            if meta_type == 0x2F:
                break
            continue

        message_type = status & 0xF0
        channel = status & 0x0F
        data_size = 1 if message_type in (0xC0, 0xD0) else 2
        payload = track[idx : idx + data_size]
        idx += data_size
        events.append((tick, "midi", message_type, channel, payload))

    return ppq, events


class DrumMidiGenerationTests(unittest.TestCase):
    def test_cli_generates_reaper_compatible_drum_midi(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "drums.mid"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "drumgen",
                    "make-empty",
                    "--bars",
                    "2",
                    "--bpm",
                    "120",
                    "--out",
                    str(out_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(out_path.exists())

            midi_data = out_path.read_bytes()
            ppq, events = _parse_midi_track(midi_data)
            self.assertEqual(ppq, 480)

            tempo_events = [event for event in events if event[1] == "meta" and event[2] == 0x51]
            time_sig_events = [event for event in events if event[1] == "meta" and event[2] == 0x58]
            self.assertTrue(tempo_events)
            self.assertEqual(tempo_events[0][3], b"\x07\xA1\x20")
            self.assertTrue(time_sig_events)
            self.assertEqual(time_sig_events[0][3], b"\x04\x02\x18\x08")

            note_ons = [
                event
                for event in events
                if event[1] == "midi" and event[2] == 0x90 and event[4][1] > 0
            ]
            self.assertGreater(len(note_ons), 0)

            max_tick = max(event[0] for event in note_ons)
            self.assertGreaterEqual(max_tick, 7 * 480)

            used_notes = {event[4][0] for event in note_ons}
            self.assertTrue({GM_KICK, GM_SNARE, GM_CLOSED_HIHAT}.issubset(used_notes))

            for event in events:
                if event[1] == "midi" and event[2] in (0x90, 0x80):
                    self.assertEqual(event[3], 9)
                    self.assertIn(event[4][0], {GM_KICK, GM_SNARE, GM_CLOSED_HIHAT})


if __name__ == "__main__":
    unittest.main()
