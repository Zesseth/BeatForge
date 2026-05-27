# BeatForge Roadmap

This roadmap supersedes the old `dev_info. md` and the original 19-issue backlog. It reflects the architectural restructure of 2026-05-27.

## Guiding principles

1. **Privacy first.** Raw audio never leaves the machine. Every networked feature must pass the no-audio-egress harness before it lands.
2. **Symbolic core.** All "AI" — including the optional ML model and any external LLM assist — operates on symbolic data (text prompts, MIDI events, beat-grid timestamps), never on audio buffers.
3. **Rules before ML.** Each milestone delivers usable output with deterministic rule-based logic first; ML is a *pluggable* enhancement, not a hard dependency.
4. **REAPER-ready, always.** Every MIDI artifact must import cleanly into REAPER on Linux (GM drums, channel 10, tempo + time-signature meta events).
5. **Copilot-executable.** Every issue is written so a Copilot agent can execute it: exact files to touch, exact commands, explicit output artifacts, deterministic validation steps, explicit network policy.

## Milestones

### M0 — Foundation (no music logic, no network)

Delivers the privacy harness, project skeleton, and the absolute-minimum MIDI baseline + validator.

- M0.1 Project scaffold + CLI entrypoint (`pyproject.toml`, `drumgen --help`, pytest, ruff, mypy)
- M0.2 `drumgen make-empty` — minimal REAPER-ready drum MIDI (channel 10, GM notes, tempo + 4/4)
- M0.3 `drumgen validate-midi` — REAPER-ready ruleset validator
- M0.4 **No-audio-egress test harness** (static lint + runtime mock + network sandbox marker)
- M0.5 Repo documentation set (PRIVACY, MODEL_SOURCES, DATA_SOURCES, CONTRIBUTING, AGENTS — initial drafts already present; M0.5 fleshes them out as the policy crystallises)

**Exit criteria for M0:** `drumgen make-empty` produces a file that passes `drumgen validate-midi` and imports into REAPER. The no-audio-egress harness runs in CI and is green.

### M1 — Rules-based generation (no audio, no network)

Deterministic full-song generation driven entirely by a structured `StyleSpec`. No ML, no audio, no external calls.

- M1.1 `drumgen generate-basic` — full-song MIDI with default sections (intro/verse/chorus/outro), measurable verse↔chorus variation
- M1.2 `drumgen parse-prompt` — rule-based prompt → `StyleSpec` parser (genre, bpm, hats, backbeat, density, fills, ghost notes)
- M1.3 `drumgen generate` (no `--audio`) — `StyleSpec` drives generation choices, output passes validator

**Exit criteria for M1:** prompt-only generation works end-to-end and changing the prompt produces measurable musical differences across at least 6 prompt variants.

### M2 — Local audio analysis + alignment (still no network beyond model downloads)

Pure-local audio → small JSON of beat-grid / onset features. All audio processing stays on the machine.

- M2.1 `drumgen analyze` — librosa/madmom-based tempo + beat-grid extraction → `analysis.json`
- M2.2 `drumgen groove` — extend `analyze` with onset density / section hints → `groove.json` (stable schema, deterministic)
- M2.3 `drumgen generate --audio` — audio-aligned rules-based MIDI (tempo follow, beat-grid quantization)

**Exit criteria for M2:** runs on at least one real .wav without crashing, schemas are documented, and the no-audio-egress harness still passes (i.e. no library accidentally phones home with audio).

### M3 — Sections + MIDI editing (still no network)

User-controlled section maps and prompt-based transformations on existing MIDI files.

- M3.1 `project.yaml` schema + section overrides (verse/chorus/bridge)
- M3.2 `drumgen edit` — read existing drum MIDI, apply prompt-driven transforms (kick density, hat subdivision, fills, ghost notes)
- M3.3 Example-bar propagation — copy a hand-edited bar style across matching sections

**Exit criteria for M3:** user can hand-edit one chorus bar in REAPER, run `drumgen edit --example-range … --prompt "propagate to all choruses"`, and get a coherent updated MIDI.

### M4 — Symbolic groove model (pluggable backend, weights downloaded once)

A *pluggable* ML backend that produces expressive symbolic drum performances from `groove.json` + `StyleSpec`. **GrooVAE is one possible backend, not the spec.** The default backend is a small transformer trained on the Groove MIDI Dataset; GrooVAE-style checkpoints can be loaded via an adapter.

- M4.1 `drumgen models install` — model weight cache, integrity checks, version pinning, license metadata (network used **only** for weight download, never for audio)
- M4.2 Symbolic groove model backend interface (`SymbolicGrooveModel`) — abstract over backend implementations
- M4.3 Default backend: pretrained small transformer or rule+template fallback (whichever proves more reliable in M4 prototype)
- M4.4 `drumgen generate-ml` — uses `groove.json` + `StyleSpec` + model to produce expressive MIDI (velocities, microtiming where supported)

**Exit criteria for M4:** generation produces non-constant velocities and bounded microtiming, output still passes `validate-midi`, and the no-audio-egress harness still passes.

### M5 — Humanization, prompt-driven ML control, iterative editing, polish

- M5.1 Humanization layer (velocity variation, microtiming, swing) — seeded and deterministic
- M5.2 Prompt-controlled ML generation — prompt drives both model sampling parameters and post-processing
- M5.3 Hybrid iterative editing — preserve protected bar ranges, regenerate selected sections
- M5.4 Examples folder + REAPER import walkthrough
- M5.5 *Optional* GitHub Models / Copilot assist for symbolic-only MIDI refinement (text-prompt + symbolic-MIDI in, modified symbolic-MIDI out — **no audio in the payload, ever**)

**Exit criteria for M5:** end-to-end demo on a real song stem produces drum MIDI that the developer (Jesse) finds musically usable in REAPER without further hand-editing of more than ~20% of the bars.

## Hard rule

ML features (M4 onward) **must not** be merged before:

- M0 fully complete (privacy harness in CI)
- M1 fully complete (rules-based generation works end-to-end)
- M2 fully complete (audio analysis stable and private)

This protects against the failure mode where the project ships an ML promise that depends on missing infrastructure.

## Determinism policy

- M0–M3 (rules-based): **event-identical** outputs for the same inputs + same `--seed` (same notes, channels, velocities, onset ticks ± 1).
- M4–M5 (ML-backed): **structurally equivalent** outputs for the same inputs + same `--seed` (same section count, note-count per bar ± 5%, same overall density profile). Byte-identical ML outputs across CPU/GPU/CUDA versions are **not** promised.
