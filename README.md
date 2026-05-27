# BeatForge

**Privacy-first, Debian-first CLI that generates editable drum MIDI for REAPER from local audio and/or text prompts.**

> Status: pre-alpha. Repository is currently a clean slate after architectural restructure (2026-05-27). See [`ROADMAP.md`](ROADMAP.md) and the GitHub Issues backlog.

---

## What BeatForge is

- A **command-line tool** that produces **REAPER-importable drum MIDI** (`.mid`, GM drum map, channel 10).
- Optionally takes **a local audio file** (bass, guitar, or rough mix) and/or **a text prompt** describing the desired feel.
- Always outputs editable MIDI — never rendered audio. You bring the drum sampler/plugin.
- Designed to run **fully locally on Debian Linux**. Audio is processed on your machine and **never uploaded anywhere**.

## What BeatForge is not

- Not a renderer. No audio output, no drum sample bundling.
- Not a REAPER plugin. Integration is via standard MIDI import/export.
- Not a cloud service. The only network use is optional model-weight downloads (see [`MODEL_SOURCES.md`](MODEL_SOURCES.md)) and *optional* symbolic-only assists via external LLM endpoints.

---

## Privacy promise (hard constraint)

**Raw audio never leaves your machine.** Not as PCM, not as spectrograms, not as MFCCs, not as any reversible representation.

Optional external calls (e.g. GitHub Models for prompt-driven symbolic refinement) are allowed only with:

- text prompts you typed,
- and/or small, non-reversible derived features (tempo as a float, beat-grid timestamps, bar structure, symbolic MIDI events).

See [`PRIVACY.md`](PRIVACY.md) for the full policy and the `no-audio-egress` test plan.

---

## Quickstart (planned, will be implemented in M0)

> Target: Debian 12+, Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"

# Baseline: generate a simple REAPER-ready drum MIDI without any audio or prompt
drumgen make-empty --bars 32 --bpm 120 --out drums.mid

# Validate it
drumgen validate-midi drums.mid
```

The full CLI surface (`generate`, `analyze`, `groove`, `edit`, `models install`, …) is implemented incrementally in milestones M1–M5.

---

## Documentation

- [`ROADMAP.md`](ROADMAP.md) — milestones M0–M5 and what each one delivers
- [`PRIVACY.md`](PRIVACY.md) — privacy policy and no-audio-egress test plan
- [`MODEL_SOURCES.md`](MODEL_SOURCES.md) — third-party model weights, versions, licenses, checksums
- [`DATA_SOURCES.md`](DATA_SOURCES.md) — datasets used for any local training, with licenses
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to contribute (humans and GitHub Copilot agents)
- [`AGENTS.md`](AGENTS.md) — instructions for Copilot CLI / Copilot agents working in this repo

---

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).

Apache 2.0 was chosen over AGPL-3.0 because BeatForge is a local CLI tool: AGPL's network-use clause provides no real benefit here, and Apache 2.0 maximizes downstream compatibility with model weights (most Magenta/HuggingFace checkpoints ship under Apache 2.0 or MIT) and lowers contribution friction. The license is intentionally permissive so the tool stays open and reusable forever; it does *not* impose any obligation back on downstream users beyond attribution and the standard patent grant.
