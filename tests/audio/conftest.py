"""Shared fixture synthesis for audio tests (M2).

Fixtures are synthesised at test time — no audio is ever committed to the
repo (AGENTS.md §5)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_fixture import synth_click_track, synth_sine_bass  # noqa: E402

FIXTURE_PARAMS = [
    ("click_120bpm.wav", 120.0),
    ("click_140bpm.wav", 140.0),
    ("click_90bpm.flac", 90.0),
    ("sinebass_120bpm.wav", 120.0),
]

# Fixture audio is kept short (issue #27: <= 2 s) for fast tempo tests;
# tests that need full analysed bars pass an explicit longer duration.
FIXTURE_DURATION_S = 8.0


@pytest.fixture(scope="session")
def fixture_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    import soundfile as sf

    d = tmp_path_factory.mktemp("audio_fixtures")
    for name, bpm in FIXTURE_PARAMS:
        y = (
            synth_click_track(bpm, duration_s=FIXTURE_DURATION_S)
            if name.startswith("click")
            else synth_sine_bass(bpm, duration_s=FIXTURE_DURATION_S)
        )
        sf.write(str(d / name), y, 22050, subtype="PCM_16")
    return d


@pytest.fixture(scope="session")
def click_120(fixture_dir: Path) -> Path:
    return fixture_dir / "click_120bpm.wav"
