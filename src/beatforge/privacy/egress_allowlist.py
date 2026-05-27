"""Explicit allow-list of outbound hosts.

**M0 policy: the list is empty.** Nothing in BeatForge should reach the
network at runtime in M0–M3. Starting from M4 (model installer), a small
number of model-weight hosts will be added — and only the model-installer
code path may reach them. Every other path must remain isolated.

If you need to extend this list, do it in a PR that:

1. Adds the host with a comment citing the model/license.
2. Adds a test that proves only ``drumgen models install`` can reach it.
3. Updates ``MODEL_SOURCES.md`` with checksums for the artefacts.
"""

from __future__ import annotations

ALLOWED_HOSTS: frozenset[str] = frozenset()


def is_host_allowed(host: str) -> bool:
    return host in ALLOWED_HOSTS
