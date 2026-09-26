# BeatForge

**Privacy-first, Debian-first CLI that generates editable drum MIDI for REAPER from local audio and/or text prompts.**

> Status: pre-alpha. M0 (foundation) and M1 (rules-based prompt-driven generation) are implemented and merged — 58 tests green, CI clean. Audio analysis, MIDI editing, and the ML groove model land in M2–M5. See [`ROADMAP.md`](ROADMAP.md) and the GitHub Issues backlog.

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

Optional external calls (e.g. a Mistral model for symbolic refinement, see [`AI_STRATEGY.md`](AI_STRATEGY.md)) are allowed only with:

- text prompts you typed,
- and/or small, non-reversible derived features (tempo as a float, beat-grid timestamps, bar structure, symbolic MIDI events).

See [`PRIVACY.md`](PRIVACY.md) for the full policy and the `no-audio-egress` test plan.

---

## Quickstart

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

# Prompt-driven generation (M1): parse a prompt into a StyleSpec, then generate
drumgen parse-prompt --prompt "punk 180 bpm, snare on 2 and 4, 16th hats, fills before chorus" --out spec.json
drumgen generate --stylespec spec.json --out punk_drums.mid

# Or in one step
drumgen generate --prompt "funk 105 bpm, ghost notes, shuffle hats" --out funk_drums.mid
```

Import the resulting `.mid` into REAPER: GM drum map, channel 10, tempo and 4/4 time-signature meta events are already embedded. Map your drum sampler to channel 10 and edit freely.

The remaining CLI surface (`analyze`, `groove`, `edit`, `models install`, `generate-ml`, …) is implemented incrementally in milestones M2–M5; the stub subcommands print a notice and exit 0 until their milestone lands. See [`TESTING.md`](TESTING.md) for the manual test plan and [`docs/STYLESPEC.md`](docs/STYLESPEC.md) for the prompt schema.

---

## Documentation

- [`ROADMAP.md`](ROADMAP.md) — milestones M0–M5 and what each one delivers
- [`PRIVACY.md`](PRIVACY.md) — privacy policy and no-audio-egress test plan
- [`MODEL_SOURCES.md`](MODEL_SOURCES.md) — third-party model weights, versions, licenses, checksums
- [`DATA_SOURCES.md`](DATA_SOURCES.md) — datasets used for any local training, with licenses
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to contribute (humans and AI agents)
- [`AGENTS.md`](AGENTS.md) — instructions for Mistral Vibe / other AI agents working in this repo
- [`AI_STRATEGY.md`](AI_STRATEGY.md) — AI/LLM strategy: Mistral-first model priority for the optional symbolic refinement
- [`TESTING.md`](TESTING.md) — manual and automated testing guide (current state, per-milestone)
- [`docs/STYLESPEC.md`](docs/STYLESPEC.md) — the `StyleSpec` schema and prompt parsing rules

---

## License

GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later) — see [`LICENSE`](LICENSE).

AGPL-3.0 is a **strong copyleft** license chosen to keep BeatForge open forever, even if someone runs it as a hosted service. Anyone who modifies and **distributes** BeatForge — or makes a modified version available over a network — must release their source code under the same license. Permissive forks that close the source are not permitted. Model weights and datasets are tracked separately in [`MODEL_SOURCES.md`](MODEL_SOURCES.md) and [`DATA_SOURCES.md`](DATA_SOURCES.md); their licenses must be AGPL-compatible (Apache-2.0, MIT, BSD, CC-BY, and most open weights qualify).
