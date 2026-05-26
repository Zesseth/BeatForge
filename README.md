# BeatForge
Ai based MIDI drum generator
# BeatForge (working title) — Audio-driven Drum MIDI Generator for Linux

**BeatForge** is a Debian-first CLI tool that generates a **full-song drum arrangement as MIDI** from an input audio file (e.g., bass or guitar), guided by **prompt-style instructions** and iterative edits.  
Output is always a **Reaper-ready .mid** (GM drum map, channel 10), so you can import it into REAPER and route it to any drum sampler / drum machine you like.

> Status: early development (private repo). Public release later.

---

## Why / Goals

- **Generate drum MIDI from audio**: analyze tempo/beat grid and propose a complete song structure (intro/verse/chorus/bridge/outro).
- **Prompt-driven control**: “punk 180bpm, eighth hats, snare on 2&4, fills before chorus” → drum arrangement follows the prompt.
- **Iterative editing**: import an existing drum MIDI, apply prompt-based transforms, and export a new MIDI.
- **Example-based editing** (planned): hand-edit one bar in REAPER and propagate that “feel” to similar sections.

---

## Non-goals (v1)

- No audio rendering of drums; **MIDI only**.
- No REAPER plugin; integration is via **MIDI import/export**.
- No cloud dependency required; must run locally on Debian.

---

## Key Features (planned)

### v1 (MVP)
- `drumgen generate` creates a full-song drum MIDI from audio + prompt.
- `drumgen edit` modifies an existing drum MIDI based on prompt and section-awareness.
- Deterministic output when `--seed` is provided.
- “Reaper-ready” MIDI: GM map + channel 10 + tempo meta events.

### v2+
- Section detection improvements (better verse/chorus inference).
- Example-bar propagation (copy a user-edited bar style across choruses).
- Groove templates + richer humanization (velocity/microtiming profiles).

---

## Quickstart (developer)

> Target platform: Debian (Python 3.11+).  
> Installation instructions will be updated as dependencies settle.

### Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
