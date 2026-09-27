# AI Strategy for BeatForge

This document outlines the AI/ML strategy for BeatForge, with a focus on **privacy-preserving symbolic processing**, **Mistral model preference**, and a **two-stage implementation order for symbolic LLM refinement** (M5.5).

## Overview

BeatForge uses AI/ML as **pluggable enhancements** to a rules-based core. All AI operations work on **symbolic data only** (text prompts, MIDI events, beat-grid timestamps) — **raw audio never leaves the machine**.

The LLM never generates MIDI directly. It produces a small, schema-validated **JSON edit list** (a partial `StyleSpec` diff over the affected sections), which the rules-based engine applies to the MIDI. This keeps the musical guardrails deterministic and the LLM task small enough for local models.

## Two-stage implementation order (M5.5)

Symbolic LLM refinement is implemented in two stages, in this order:

| Stage | Scope | Tracking issues | Network policy |
| --- | --- | --- | --- |
| **Stage 1** | Online refine via **Mistral API (La Plateforme)** | #40 | `symbolic-llm-allowed` (opt-in) |
| **Stage 2** | Local backends (model-agnostic evaluation, Ollama/llama.cpp adapters, benchmark) | #43, #44, #45 | `none` (local-only) |

Stage 2 starts only after Stage 1's DoD is met.

**Rationale:**

- Stage 1 is the fastest path to a working end-to-end refine with the highest output quality (hosted models), and it forces the provider interface (`SymbolicRefineModel` protocol) to be designed up front, so Stage 2 local backends can plug in without breaking the CLI.
- Stage 2 then delivers the fully-offline path, with the default local backend chosen from measured data (benchmark in #45) instead of assumptions.

## Provider priority order

Within symbolic LLM refinement, the following priority order applies:

### 1. Mistral API (La Plateforme) — Stage 1

**Status:** Primary recommendation (implemented first)
**Access:** `https://api.mistral.ai` (OpenAI-compatible REST)
**Requirements:**

- Mistral API key (free tier available)
- Environment variable `MISTRAL_API_KEY` or CLI flag `--mistral-api-key`
- Opt-in flags: `--provider mistral-api` + `--allow-network-symbolic-llm`

**Use Case:**

- Highest quality symbolic refinement (hosted Mistral models)
- Fastest path to a working feature; no local model installation required
- Establishes the `SymbolicRefineModel` protocol and payload contract

**Network Policy:** `symbolic-llm-allowed` (explicit opt-in required)

### 2. Local backends — Stage 2

**Status:** Offline path, implemented after Stage 1
**Access:** Local inference via Ollama or llama.cpp (`llama-server`), loopback only
**Requirements:**

- Local runtime installed by the user (Ollama or llama.cpp; not a BeatForge dependency)
- Model ID configurable per backend (e.g. `--local-backend ollama --model mistral:7b`)
- Hardware: ~8 GB RAM minimum for 7B-class models at Q4_K_M; GPU optional

**Model-agnostic by design:** Mistral local models are the preferred candidate family (Apache-2.0), but the evaluation in #43 must compare at least three non-Mistral models (Llama 3.1/3.2 Instruct, Qwen2.5 Instruct, DeepSeek-R1-Distill). The default local backend and default local model are chosen from the #45 benchmark, not hard-coded.

**Network Policy:** `none` (fully local, loopback only; no egress)

### 3. Rules-based fallback

**Status:** Always available
**Access:** None required — this is the deterministic core

If the selected provider fails validation twice or is unavailable, `refine-symbolic` falls back to the rules-based refiner and emits a warning. The command must never fail silently.

## Local model candidates (Stage 2, evaluation subject of #43)

All weights are Apache-2.0 (one-way compatible with AGPL-3.0-or-later) and available as pre-quantized GGUF for Ollama/llama.cpp. Sizes are approximate Q4_K_M downloads; add runtime overhead and KV cache.

| Model | Ollama tag | Size (Q4_K_M) | Minimum hardware | Context | Notes |
| --- | --- | --- | --- | --- | --- |
| Mistral 7B Instruct v0.3 | `mistral:7b` | ~4.4 GB | 8 GB RAM / 6 GB VRAM | 32K | Most proven; native function-calling tokens |
| Ministral 3 8B (2512) | `ministral-3:8b` | ~5 GB | 8–12 GB RAM / 8 GB VRAM | 262K | Newest edge generation; requires Ollama ≥ 0.13.1 |
| Mistral NeMo 12B (2407) | `mistral-nemo:12b` | ~7.1 GB | 16 GB RAM / 8–10 GB VRAM | 128K | Drop-in replacement for Mistral 7B |
| Ministral 3 14B (2512) | `ministral-3:14b` | ~9 GB | 16 GB RAM / 12 GB VRAM | 262K | Best quality/RAM ratio without a GPU |
| Mistral Small 3.2 24B | `mistral-small:24b` | ~14 GB | 16 GB VRAM (tight) / 32 GB RAM | 32K | Best quality on a single consumer GPU |

CPU-only inference works at roughly 4–16 tok/s for 7–14B models depending on the CPU; refine calls are batch-like, so seconds of latency is acceptable. GPU offload brings this to 30–85 tok/s.

**Non-Mistral comparison candidates (required by #43):** `qwen2.5:7b/14b-instruct` (Apache-2.0), `deepseek-r1-distill-*` (MIT), `llama3.1:8b` (Llama Community License — benchmark candidate only, not a default: the license is not OSI-open and carries a 700M MAU threshold and competitor restrictions).

## Integration architecture

The same provider interface serves both stages:

```
src/beatforge/refine/
├── __init__.py
├── interface.py          # SymbolicRefineModel protocol
├── llm.py                # Stage 1: Mistral API client (api.mistral.ai)
├── local_provider.py     # Stage 2: local backend selection
└── backends/             # Stage 2 (#45)
    ├── __init__.py
    ├── ollama_backend.py     # Ollama REST (localhost:11434), schema-constrained via format
    └── llamacpp_backend.py   # llama-server OpenAI-compatible API, GBNF grammar
```

### Model selection logic

```python
def get_refinement_model(config: RefineConfig) -> SymbolicRefineModel:
    if config.provider == "mistral-api":
        return MistralAPIClient(api_key=config.mistral_api_key)
    elif config.provider == "local":
        return LocalRefineBackend(
            backend=config.local_backend,
            model_id=config.local_model_id,
        )
    else:
        return RulesBasedRefiner()
```

## Privacy considerations

All LLM usage complies with BeatForge's privacy requirements:

- **Symbolic-only:** Only text prompts and MIDI data (symbolic representations) are sent to models
- **No audio:** Raw audio, spectrograms, or audio-derived features are never transmitted
- **Opt-in network:** Network access requires explicit CLI flags (`--allow-network-symbolic-llm`)
- **Local option:** Full offline capability with local models (loopback only, no egress)
- **Payload cap:** Outbound payloads are hard-capped (16 KB) and covered by the no-audio-egress harness

## CLI interface

```bash
# Stage 1: Mistral API (opt-in, network)
drumgen refine-symbolic --midi song.mid --groove groove.json \
    --prompt "add more variation" \
    --provider mistral-api --allow-network-symbolic-llm

# Stage 2: local backend (no network)
drumgen refine-symbolic --midi song.mid --groove groove.json \
    --prompt "add more variation" \
    --provider local --local-backend ollama --model mistral:7b
```

API keys are read from `MISTRAL_API_KEY` or `--mistral-api-key`; never stored, never logged, never committed.

## Evaluation criteria for local models (#43)

When selecting local models, we evaluate based on:

1. **License Compatibility:** Must be compatible with AGPL-3.0-or-later (Apache-2.0 or MIT preferred)
2. **Quality:** Performance on the symbolic drum-refine task (schema-valid edit lists, musically sensible changes)
3. **Resource Efficiency:** Memory and compute requirements on Debian 12+ target hardware
4. **Stability:** Proven track record, minimal breaking changes
5. **Maintenance:** Active upstream support and updates
6. **Download Size:** Reasonable for users to download and store

The #45 benchmark must record, per backend/model: refine success rate, median latency, memory footprint, and a subjective quality rating. The default local backend is chosen from these results.

## Future considerations

1. **Mistral Pro subscription tier:** can be added later as an additional remote provider behind the same protocol if the free API tier proves limiting
2. **Quantization:** Support for Q4/Q5/Q6 GGUF quants to reduce memory usage
3. **Custom fine-tuning:** Option to fine-tune models on domain-specific MIDI data
4. **Hardware acceleration:** CUDA/ROCm offload support via the same backends

## Migration history

**Previous:** GitHub Models / Copilot assist was mentioned as the primary option for M5.5
**Current:** Two-stage plan — Stage 1: Mistral API (online, #40); Stage 2: local backends (#43–#45), Mistral-preferred but model-agnostic

**Rationale for change:**

- Mistral's Apache-2.0 licensed models are fully compatible with AGPL-3.0-or-later
- Online-first gives the fastest working feature and forces the provider interface up front
- Local backends then deliver complete offline capability, chosen from measured benchmark data
- Mistral's focus on open models aligns with BeatForge's open-source philosophy

## References

- [Mistral AI](https://mistral.ai/)
- [Mistral API (La Plateforme)](https://docs.mistral.ai/)
- [Mistral Models on Hugging Face](https://huggingface.co/mistralai)
- [Apache-2.0 License](https://www.apache.org/licenses/LICENSE-2.0)
- Tracking issues: [#40](https://github.com/Zesseth/BeatForge/issues/40) (Stage 1), [#43](https://github.com/Zesseth/BeatForge/issues/43), [#44](https://github.com/Zesseth/BeatForge/issues/44), [#45](https://github.com/Zesseth/BeatForge/issues/45) (Stage 2)
