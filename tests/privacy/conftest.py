"""Pytest plumbing for the privacy test suite.

Patches the socket module so any test that even *opens* a TCP/UDP socket
will fail with a clear message. Individual tests in this directory may
opt back into recording mode via the ``recorded_socket`` fixture.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from typing import Any

import pytest


class _NoNetwork(Exception):
    """Raised when test code attempts to open a socket without opting in."""


class _BlockingSocket:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise _NoNetwork(
            "tests in tests/privacy/ must not open sockets; if you need to "
            "verify a payload, use the ``recorded_socket`` fixture which "
            "intercepts traffic without sending it."
        )


@pytest.fixture(autouse=True)
def _block_all_sockets(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(socket, "socket", _BlockingSocket)
    yield


@pytest.fixture
def recorded_socket(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[bytes]]:
    """Replace socket.socket with a recorder. Returns the list of payloads."""
    payloads: list[bytes] = []

    class _Recorder:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def sendall(self, data: bytes) -> None:
            payloads.append(data)

        def send(self, data: bytes) -> int:
            payloads.append(data)
            return len(data)

        def connect(self, *args: Any, **kwargs: Any) -> None:
            pass

        def close(self) -> None:
            pass

        def setsockopt(self, *args: Any, **kwargs: Any) -> None:
            pass

        def settimeout(self, *args: Any, **kwargs: Any) -> None:
            pass

    monkeypatch.setattr(socket, "socket", _Recorder)
    yield payloads
