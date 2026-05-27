# Privacy policy

BeatForge is built around one non-negotiable rule:

> **Your audio never leaves your machine.**

This document defines what that means in practice, what may leave the machine, and how we test that the rule holds.

## 1. What stays local — always

The following data is processed **only** on the user's machine and is **never** transmitted to any external service, telemetry endpoint, or third-party API:

- Raw audio buffers (PCM, float, int — any form).
- Audio file paths and file names (these often carry personal/project context, e.g. *"client-X-rough-mix.wav"*).
- Spectrograms (mel, STFT, CQT), MFCCs, chroma features, or any other dense audio-derived feature that could reconstruct or fingerprint the original audio.
- Onset envelopes and raw onset amplitude curves (the *strength* curve, not just timestamps).
- Any neural audio embeddings (CLAP, Wav2Vec, OpenL3, etc.).
- Any audio file the user has not explicitly chosen to share.

## 2. What may leave the machine — only with explicit user opt-in

Some optional features (e.g. symbolic MIDI refinement via GitHub Models) require a network call. When such a feature is invoked, **only** the following data is allowed in the request payload:

- Text prompts the user typed.
- Tempo as a single number (e.g. `124.0`).
- Beat-grid timestamps as a list of floats in seconds or PPQ ticks (no amplitudes, no spectral data).
- Onset *timestamps* as a list of floats (no amplitude curve).
- Bar/section structure as a small JSON object (e.g. `{"verse": "1-16", "chorus": "17-32"}`).
- Symbolic MIDI events (notes, channels, velocities, onsets) — already symbolic by definition.
- Run metadata: model name/version, seed, sampling parameters.

**Rationale for non-reversibility:** tempo + beat-grid timestamps + onset timestamps + bar structure together occupy on the order of 1 KB per song. They contain no frequency content, no harmonic content, no vocal content, and no dynamic envelope. The statement *"an onset occurred at 0.512 s"* does not reveal which instrument played, in what key, with what timbre, or what was being said or sung. Reconstructing the original audio from this representation is not possible.

## 3. Network policy by feature

| Feature                            | Network use                                  |
| ---------------------------------- | -------------------------------------------- |
| `drumgen make-empty`               | None                                         |
| `drumgen validate-midi`            | None                                         |
| `drumgen parse-prompt`             | None                                         |
| `drumgen generate-basic`           | None                                         |
| `drumgen generate` (no `--audio`)  | None                                         |
| `drumgen analyze`                  | None                                         |
| `drumgen groove`                   | None                                         |
| `drumgen generate --audio`         | None                                         |
| `drumgen edit`                     | None                                         |
| `drumgen models install`           | **Only** model-weight download from whitelist |
| `drumgen generate-ml`              | None (after `models install`)                |
| Optional symbolic LLM refine (M5.5) | Symbolic payload only (see §2)               |

## 4. No-audio-egress test harness

Implemented in M0.4 and required-green in CI for every PR.

### 4.1 Static lint (CI)

A ripgrep-based CI step fails if any function in `src/` references both:

- an audio-loading symbol (`librosa.load`, `soundfile.read`, `pretty_midi` audio paths, `numpy.ndarray` flagged as audio), and
- a network-egress symbol (`requests`, `httpx`, `urllib`, `openai`, `anthropic`, `github`, `socket`)

within the same scope. False positives are silenced with an explicit `# beatforge: no-audio-egress-exempt` comment plus a code-review-required justification.

### 4.2 Runtime mock egress test

A pytest fixture monkey-patches every HTTP client and `socket.socket` to a local recording mock. The full pipeline is then run against a small test audio file. Assertions:

- Total outbound payload size ≤ 8 KB per request.
- No request `Content-Type` is `audio/*`, `multipart/form-data`, or `application/octet-stream`.
- No request body contains a contiguous sequence of more than 64 numeric values from a defined "audio-like" range check, OR more than 256 bytes of base64-decoded binary data.
- All outbound requests target hosts on the explicit allow-list (currently empty for M0; expanded later only with documented justification).

### 4.3 Network sandbox marker

All paths except `drumgen models install` are decorated with `@pytest.mark.no_network`. The fixture aggressively patches `socket.socket` to raise on any call. The test suite must pass entirely under `pytest -m no_network`.

## 5. Reporting a privacy regression

If you find a case where BeatForge transmits audio or audio-derived dense features to any external service, open an issue with the `privacy` label and the `breaking-change` label. Privacy regressions block release.
