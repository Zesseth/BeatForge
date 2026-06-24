# Agent instructions for BeatForge

This file is read by Mistral Vibe, Mistral coding agents, and any other AI agent that opens a PR against `Zesseth/BeatForge`. Human contributors: see [`CONTRIBUTING.md`](CONTRIBUTING.md).

If you only read one section, read **§ 1 Non-negotiables**. Violating any item there will get your PR rejected without further review.

---

## 0. What this project is

BeatForge is a **privacy-first, Debian-first CLI tool** that produces **REAPER-importable drum MIDI** from:

- text prompts (e.g. *"punk 180bpm, snare on 2&4, fills before chorus"*), and/or
- a local audio file (bass, guitar, or rough mix), and/or
- an existing drum MIDI that the user wants edited.

Output is always **editable MIDI**, never rendered audio. The user pairs the MIDI with their own drum sampler in REAPER.

The architecture is intentionally **rules-first, ML-as-a-pluggable-enhancement**, and **privacy-as-a-hard-constraint**. Read [`ROADMAP.md`](ROADMAP.md) for the milestone breakdown and [`PRIVACY.md`](PRIVACY.md) for the privacy policy. Read both before opening a PR that touches more than tests.

---

## 1. Non-negotiables

1. **Audio never leaves the machine.** Not as PCM, not as spectrograms, not as MFCCs, not as embeddings, not as onset *envelopes*. Only the symbolic derivatives listed in `PRIVACY.md` § 2 may appear in any outbound payload, and only for features explicitly marked `network: symbolic-llm-allowed`.
2. **Network is off by default.** Default for every issue is `network: none`. The only features allowed to use the network are:
   - `drumgen models install` (`network: weight-download-only`, allow-list in `MODEL_SOURCES.md`)
   - the optional `drumgen refine-symbolic` (`network: symbolic-llm-allowed`, opt-in via explicit CLI flag)
3. **REAPER-ready, always.** Any change that produces a `.mid` artifact must keep it valid: GM drum notes, MIDI channel 10 (note: that is `channel=9` in `mido`'s 0-indexed API — the channel-9-vs-10 confusion is the most common bug in this repo, so name variables `gm_drum_channel_0idx = 9` to make it obvious).
4. **Determinism levels are per milestone**, not "always byte-identical":
   - **M0–M3** (rules-based) — **byte-identical** outputs for the same inputs + same `--seed`.
   - **M4–M5** (ML-backed) — **structurally equivalent** outputs (note-count per bar ± 5%, same section structure, same overall density profile). Byte-identical outputs across CPU/GPU/CUDA versions are **not** promised.
5. **AGPL-3.0-or-later licensing flows downstream.** BeatForge is strong copyleft. Do not introduce a dependency, model checkpoint, or dataset that ships under a license incompatible with AGPL-3.0-or-later — that means no non-commercial, research-only, custom EULA, or field-of-use-restricted assets, and no Apache-2.0 *code* that contains incompatible patent terms in edge cases (vanilla Apache-2.0 IS one-way compatible into AGPL-3.0, so most permissive deps are fine). When in doubt, comment on the issue and wait for human review.
6. **No secrets in commits. No AI-authorship trailers in commit messages.** The human merging the PR is the author. `Co-authored-by: Mistral Vibe`, `Co-authored-by: Copilot`, and similar are banned.

---

## 2. Repository state and milestones

The repo is currently a clean slate (post-restructure on 2026-05-27). Source code does not yet exist. The work is organised into six milestones:

| Milestone | Theme | Issues |
| --- | --- | --- |
| M0 | Foundation (scaffold, MIDI baseline, validator, privacy harness) | M0.1 – M0.4 |
| M1 | Rules-based generation (no audio, no network) | M1.1 – M1.3 |
| M2 | Local audio analysis & alignment | M2.1 – M2.3 |
| M3 | Sections + MIDI editing | M3.1 – M3.3 |
| M4 | Symbolic groove model (pluggable backend, weight download only) | M4.1 – M4.3 |
| M5 | Humanization, polish, optional symbolic LLM refine | M5.1 – M5.5 |

Each issue specifies: files to touch, commands to run, artifacts produced, validation steps, network policy, dependencies, and DoD. Treat that template as a contract.

ML work (M4 onward) is **blocked** until M0–M2 are merged. This is not a suggestion — opening an ML PR while the privacy harness is missing is a privacy regression.

---

## 3. Target file layout

You may create paths from this list freely. Anything outside it requires a comment on the issue first.

```
src/beatforge/
  __init__.py
  cli/main.py              # drumgen entrypoint
  midi/
    writer.py              # Standard MIDI File output
    validator.py           # REAPER-ready ruleset
    patterns.py            # rule-based patterns
  prompt/
    stylespec.py           # StyleSpec schema
    parser.py              # rule-based prompt → StyleSpec
  gen/
    basic.py               # generate-basic
    styled.py              # prompt-driven generate
    aligned.py             # audio-aligned generate
    ml.py                  # generate-ml (uses models/)
  audio/
    analyze.py             # tempo + beats (librosa/madmom)
    groove.py              # onsets + section hints (timestamps only)
  edit/
    transforms.py
    engine.py
    propagate.py
    hybrid.py              # edit-ml
  humanize/layer.py
  project/
    schema.py              # project.yaml model
    loader.py
  models/
    registry.py
    install.py
    interface.py           # SymbolicGrooveModel protocol
    backends/
      rules.py
      transformer.py
  privacy/
    egress_allowlist.py
  refine/llm.py            # M5.5, optional, opt-in
tests/
  fixtures/
  audio/
  models/
  privacy/
  test_*.py
tools/
  static_no_audio_egress.py
docs/
  STYLESPEC.md
  ANALYSIS_JSON.md
  GROOVE_JSON.md
  PROJECT_YAML.md
  REAPER_WORKFLOW.md
  LLM_REFINE.md
examples/
  01_make_empty.sh
  02_prompt_only.sh
  03_audio_aligned.sh
  04_edit_hybrid.sh
.github/workflows/
  ci.yml
  privacy.yml
```

---

## 4. Standard tooling baseline

- Python 3.11 (Debian 12+ / Ubuntu 24.04 target).
- Virtualenv at `.venv`.
- `pyproject.toml` is the source of truth; pin major versions of `librosa`, `mido`/`pretty_midi`, and any ML libs exactly.
- Linters: `ruff check .` + `ruff format --check .`.
- Typing: `mypy src` (start permissive, tighten over time).
- Tests: `pytest -q`. Markers: `no_network` (must always pass), `slow` (CI may skip on PRs).
- Privacy gate: `python tools/static_no_audio_egress.py` + `pytest tests/privacy -q`.

Pre-merge checklist for every PR:

1. `ruff check .`
2. `ruff format --check .`
3. `mypy src`
4. `pytest -q`
5. `pytest -m no_network`
6. `python tools/static_no_audio_egress.py`
7. (M0.4 onward) `pytest tests/privacy -q`

---

## 5. Common pitfalls (read this before your first PR)

- **MIDI channel 10 vs `mido`'s 0-indexed channel 9.** Use a named constant.
- **`pretty_midi` vs `mido` lock-in.** Pick one library per module, do not mix in the same file. Document the choice in the module docstring.
- **`librosa.load` resamples by default.** That's fine for analysis but document the sample rate in `analysis.json` so reproducibility holds.
- **Determinism on Linux CI vs developer laptop.** Hash-randomization (`PYTHONHASHSEED`) is the usual culprit. Set `PYTHONHASHSEED=0` in tests that assert byte-identical output, and document why.
- **`time.time()` and `random.random()` are forbidden in generation paths.** Use a passed-in `np.random.Generator` or `random.Random(seed)` instance. Anything else breaks determinism.
- **Do not commit audio fixtures.** Test fixtures must be synthesised at test time (e.g. a 2-second click track via `numpy` + `soundfile`) so the repo stays small and free of copyright concerns. See `tests/audio/make_fixture.py` for the pattern (introduced in M2.1).
- **REAPER channel routing.** Generated MIDI must use channel 10. REAPER routes channel 10 to whatever sampler the user maps. Do not assume any specific sampler.
- **Linux is the runtime target.** Development on Windows or macOS is fine, but CI runs on Ubuntu and the runtime must work on Debian 12+. Avoid path-separator and shell-specific assumptions.

---

## 6. How to read an issue

Every issue uses this structure:

- **Intent** — one sentence describing what this issue delivers.
- **Files to touch** — exact paths to create or edit. Outside this list = comment first.
- **CLI surface** — exact command line(s).
- **Requirements** — behavioural spec.
- **Commands to run** — exact shell commands the agent should run to validate.
- **Artifacts produced** — files or CLI behaviours that must exist when done.
- **Validation steps** — tests and manual checks.
- **Network policy** — `none` / `weight-download-only` / `symbolic-llm-allowed`.
- **Dependencies** — other issues that must be merged first.
- **DoD** — explicit pass/fail bullets.

If an issue is ambiguous, comment on it describing the ambiguity and your proposed resolution. **Do not silently make a different decision.**

---

## 7. Branching, commits, PRs

- Branch off `main` as `feat/<short-slug>`, `fix/<short-slug>`, `docs/<short-slug>`, or `chore/<short-slug>`.
- `main` is protected: direct pushes are blocked, force pushes are blocked, deletions are blocked.
- Commit messages: Conventional Commits style preferred (`feat:`, `fix:`, `docs:`, `chore:`). Reference the issue with `Closes #N` in the PR body.
- One issue = one PR whenever possible. If a PR closes multiple issues, list them all in the description.
- Do **not** add `Co-authored-by: Mistral Vibe`, `Co-authored-by: Copilot`, or any AI-authorship trailer. The author is the human who merges.

---

## 8. When you get stuck

- **Ambiguity:** comment on the issue with the ambiguity + your proposed resolution. Pause until human responds.
- **Failing validation:** mark the PR draft, document what's failing and why, ping in the PR description.
- **Privacy or licensing risk discovered mid-PR:** open a separate issue with the `privacy` (or `infra`) label and pause the current PR until that issue is resolved.
- **Scope creep:** if the work expands beyond the issue's "Files to touch" list, stop and open a follow-up issue. Do not silently grow the PR.

---

## 9. Going-public checklist (forward-looking)

This repo is currently **private on the GitHub Free tier**, which means **branch protection and rulesets are not enforced by GitHub** (the API rejects with HTTP 403 until the repo is made public *or* the account is upgraded to Pro/Team/Enterprise).

The ruleset that should be applied the moment one of those conditions is met lives at [`.github/branch-protection-ruleset.json`](.github/branch-protection-ruleset.json) and can be applied with [`scripts/apply-branch-protection.sh`](../scripts/apply-branch-protection.sh).

It protects `main` with:

- direct pushes blocked (PR required)
- force pushes blocked
- branch deletion blocked
- conversation resolution required before merge
- 0 required approvers (so a solo dev can self-merge)
- the `admin` role (`actor_id: 5`) is in the bypass list so the owner can still fix `main` directly when needed

Before flipping the visibility switch from private to public, verify:

- [ ] No secrets or `.env` files in history (`git log --all -p | rg -i 'token|secret|password|api[_-]?key'` returns clean).
- [ ] No user audio fixtures committed.
- [ ] All third-party model checkpoints in `MODEL_SOURCES.md` are license-compatible with AGPL-3.0-or-later.
- [ ] `PRIVACY.md` and the no-audio-egress harness are in CI and green.
- [ ] `CONTRIBUTING.md`, `AGENTS.md`, `CODE_OF_CONDUCT.md` (TBD), and an issue template (TBD) are in place.
- [ ] CI is green on `main` and on the last 5 PRs.
- [ ] Run `./scripts/apply-branch-protection.sh` immediately after the visibility change so `main` is locked the moment external contributors can see it. For full-public hardening, consider also flipping the bypass actor's `bypass_mode` from `always` to `pull_request` so admin bypasses still go through a PR audit trail.

When all of the above is checked, change repo visibility and apply the ruleset. Until then, treat `main` discipline as a self-imposed convention — there is no GitHub-side enforcement on Free-tier private repos.
