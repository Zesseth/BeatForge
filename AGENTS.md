# Agent instructions for BeatForge

This file is read by Copilot CLI and Copilot coding agents when they work in this repository. Human contributors: see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Your role

You are implementing one GitHub issue at a time on the `Zesseth/BeatForge` repository. Each issue is written to be self-contained: it specifies files to touch, commands to run, artifacts produced, validation steps, and the network policy you must obey.

## Non-negotiables

1. **Never upload, transmit, or otherwise egress audio** (raw, spectrogram, MFCC, embedding, onset envelope — any form). Read [`PRIVACY.md`](PRIVACY.md) before writing any code that touches audio or any network client.
2. **Stay within the network policy** declared in the issue. Most issues are network-off. The only feature allowed to use the network is `drumgen models install`, and only against the model-source allow-list in [`MODEL_SOURCES.md`](MODEL_SOURCES.md).
3. **Do not introduce new third-party services, APIs, or telemetry** without an issue that explicitly requests it and a corresponding update to `PRIVACY.md`.
4. **Do not commit secrets, tokens, or `.env` files.** Use environment variables and document them in the issue if a secret is needed.
5. **Do not add AI-authorship trailers to commits** (`Co-authored-by: Copilot`, etc.). The human merging the PR is the author.

## How to read an issue

Every issue follows this structure:

- **Intent** — one sentence describing what this issue delivers.
- **Files to touch** — exact paths (create or edit). If you need to create a path outside this list, comment on the issue first.
- **Commands to run** — exact shell commands (Debian / Linux). Windows-only commands are out of scope.
- **Artifacts produced** — files or CLI behaviors that must exist when you finish.
- **Validation steps** — how a reviewer (or you) verifies the result. Usually pytest commands + a manual REAPER import check noted as a TODO for the human.
- **Network policy** — `none` | `weight-download-only` | `symbolic-llm-allowed`. If unsure, treat as `none`.
- **Dependencies** — other issues that must be merged first.
- **DoD (Definition of Done)** — explicit pass/fail bullets.

## Standard tooling baseline (after M0.1)

- Python 3.11, virtualenv at `.venv`.
- `pyproject.toml` with `ruff`, `mypy`, `pytest`, `pretty_midi` (or `mido`), `librosa`, `soundfile`.
- CLI entry point: `drumgen = "beatforge.cli:main"`.
- Tests in `tests/`, with `pytest.ini` enabling the `no_network` marker.

## Pre-merge checklist for every PR

1. `ruff check .` passes.
2. `ruff format --check .` passes.
3. `mypy src` passes (initially permissive; tightened over time).
4. `pytest -q` passes.
5. `pytest -m no_network` passes.
6. The no-audio-egress static lint passes (M0.4 onward).
7. PR description references the issue with `Closes #N` and lists the files touched.

## When you get stuck

- If the issue is ambiguous, comment on the issue describing the ambiguity and proposed resolution. Do **not** silently make a different decision than the one specified.
- If validation steps fail and you cannot fix them within the issue scope, mark the PR draft and document what is missing.
- If you encounter a privacy or licensing risk that the issue does not address, open a new issue with the `privacy` or `infra` label and pause the current PR.
