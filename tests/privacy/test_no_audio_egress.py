"""Runtime egress harness — no CLI subcommand may open a socket.

Combined with the ripgrep-based static linter in ``tools/static_no_audio_egress.py``,
this is the privacy gate every PR must pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from beatforge.cli.main import app
from beatforge.privacy import ALLOWED_HOSTS

pytestmark = pytest.mark.no_network

runner = CliRunner()


def test_allowlist_is_empty_in_m0() -> None:
    """M0 invariant: the egress allow-list is empty. Update both this test
    and PRIVACY.md if a future milestone adds a host."""
    assert not ALLOWED_HOSTS, (
        "Egress allow-list grew unexpectedly. Update PRIVACY.md and add a "
        "matching positive test that proves only the model-installer path "
        "reaches the new host."
    )


def test_make_empty_opens_no_socket(tmp_path: Path) -> None:
    out = tmp_path / "drums.mid"
    result = runner.invoke(app, ["make-empty", "--bars", "4", "--bpm", "120", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_validate_midi_opens_no_socket(tmp_path: Path) -> None:
    out = tmp_path / "drums.mid"
    runner.invoke(app, ["make-empty", "--bars", "2", "--bpm", "120", "--out", str(out)])
    result = runner.invoke(app, ["validate-midi", str(out)])
    assert result.exit_code == 0, result.output


def test_help_opens_no_socket() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_recorder_sees_no_traffic_from_cli(tmp_path: Path, recorded_socket: list[bytes]) -> None:
    """Even with the recorder enabled (sockets *would* succeed if used),
    the CLI must not emit any bytes."""
    out = tmp_path / "drums.mid"
    runner.invoke(app, ["make-empty", "--bars", "2", "--bpm", "120", "--out", str(out)])
    runner.invoke(app, ["validate-midi", str(out)])
    runner.invoke(app, ["--help"])
    assert recorded_socket == [], (
        f"CLI emitted {len(recorded_socket)} socket payloads totalling "
        f"{sum(len(p) for p in recorded_socket)} bytes — expected zero."
    )
