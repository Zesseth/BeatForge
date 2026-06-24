# AI Strategy for BeatForge

This document outlines the AI/ML strategy for BeatForge, with a focus on **privacy-preserving symbolic processing** and **Mistral model preference**.

## Overview

BeatForge uses AI/ML as **pluggable enhancements** to a rules-based core. All AI operations work on **symbolic data only** (text prompts, MIDI events, beat-grid timestamps) — **raw audio never leaves the machine**.

## Model Priority Order

For symbolic LLM refinement (M5.5), the following priority order is established:

### 1. Mistral Pro Subscription (Preferred)

**Status:** Primary recommendation  
**Access:** Mistral Pro API endpoint  
**Requirements:**
- Mistral Pro subscription
- API key via environment variable `MISTRAL_PRO_API_KEY` or CLI flag `--mistral-pro-key`
- Opt-in flag: `--use-mistral-pro`

**Use Case:**
- Highest quality symbolic refinement
- Production use with commercial licensing
- Best for users who need reliability and performance

**Network Policy:** `symbolic-llm-allowed` (explicit opt-in required)

### 2. Mistral Cloud API

**Status:** Secondary option  
**Access:** Mistral standard API endpoint  
**Requirements:**
- Mistral API key (free tier available)
- Environment variable `MISTRAL_API_KEY` or CLI flag `--mistral-api-key`
- Opt-in flag: `--use-mistral-api`

**Use Case:**
- Good quality/price ratio
- Suitable for testing and development
- Backup when Pro is unavailable

**Network Policy:** `symbolic-llm-allowed` (explicit opt-in required)

### 3. Local Mistral Model

**Status:** Offline fallback  
**Access:** Local inference  
**Requirements:**
- Mistral model weights downloaded via `drumgen models install`
- Local inference backend (mistral-inference, vLLM, or similar)
- Sufficient hardware (GPU recommended for 7B+ models)

**Recommended Models:**

#### Primary Recommendation: mistral-7b-instruct-v0.2
- **License:** Apache-2.0 (fully compatible with AGPL-3.0-or-later)
- **Size:** ~14GB (quantized versions available: 8-bit ~7GB, 4-bit ~4GB)
- **Quality:** Excellent for symbolic tasks, good instruction following
- **Hardware:** Runs on consumer GPU (24GB VRAM for full precision, 8GB for 8-bit, 6GB for 4-bit)
- **Rationale:** Proven stability, Apache-2.0 license, good balance of quality and resource requirements

#### Alternative: mistral-7b-latest
- **License:** Apache-2.0
- **Size:** ~14GB
- **Quality:** Most recent improvements from Mistral
- **Consideration:** May have breaking changes between versions

#### Resource-Constrained: mistral-7b-instruct-v0.1
- **License:** Apache-2.0
- **Size:** ~14GB
- **Quality:** Slightly older but well-tested
- **Advantage:** Maximum stability, known compatibility

**Implementation Notes:**
- Requires `mistral-common` and `mistral-inference` Python packages
- Can use `transformers` library as fallback
- Quantization supported via `bitsandbytes` for reduced memory usage
- CPU inference possible but slow (not recommended for production)

**Network Policy:** `none` (fully local, no network required)

## Local Model Implementation Plan

### Model Download
```bash
# Install Mistral 7B Instruct
drumgen models install --model mistral-7b-instruct-v0.2

# Verify installation
drumgen models list
```

### Inference Backend
The local Mistral model will be integrated via:

1. **Direct API compatibility:** Mistral models can be loaded using the `transformers` library with Mistral's official configuration
2. **Abstraction layer:** All models implement the `SymbolicRefinementModel` interface for consistent integration
3. **Hardware detection:** Automatic fallback to CPU if GPU is unavailable (with performance warning)

### Model Configuration
```yaml
# Example model entry for MODEL_SOURCES.md
- name: mistral-7b-instruct-v0.2
  version: v0.2
  upstream_repo: https://github.com/mistralai/mistral-src
  upstream_license: Apache-2.0
  license_compatible_with_agpl3: true
  weight_files:
    - url: https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2/resolve/main/model.safetensors
      sha256: <to-be-determined>
      bytes: ~14000000000
  loader: src/beatforge/models/backends/mistral_local.py
  notes: |
    Primary recommended local model. Apache-2.0 licensed, excellent for symbolic tasks.
```

## Technical Requirements for Local Inference

### Hardware Recommendations
| Model | Precision | VRAM Required | RAM (CPU) | Inference Speed |
|-------|-----------|---------------|-----------|------------------|
| mistral-7b | 4-bit | 6GB | 16GB+ | ~5-10 tok/s |
| mistral-7b | 8-bit | 8GB | 16GB+ | ~8-15 tok/s |
| mistral-7b | 16-bit | 14GB | 32GB+ | ~10-20 tok/s |
| mistral-7b | 32-bit | 28GB | 64GB+ | ~15-25 tok/s |

### Software Dependencies
```toml
# pyproject.toml additions for local Mistral support
[project.optional-dependencies]
local-mistral = [
    "transformers>=4.40.0",
    "torch>=2.2.0",
    "accelerate>=0.27.0",
    "bitsandbytes>=0.43.0",  # Optional, for quantization
    "sentencepiece>=0.2.0",
]
```

## Integration Architecture

```
src/beatforge/refine/
├── __init__.py
├── llm.py                # Main LLM refinement module
├── backends/
│   ├── __init__.py
│   ├── mistral_pro.py    # Mistral Pro API client
│   ├── mistral_api.py    # Mistral Cloud API client
│   └── mistral_local.py  # Local Mistral model
└── interface.py          # SymbolicRefinementModel protocol
```

### Model Selection Logic
```python
# Pseudocode for model selection
def get_refinement_model(config: RefineConfig) -> SymbolicRefinementModel:
    if config.use_mistral_pro:
        return MistralProClient(api_key=config.mistral_pro_key)
    elif config.use_mistral_api:
        return MistralAPIClient(api_key=config.mistral_api_key)
    elif config.use_local_mistral:
        return MistralLocalModel(
            model_path=config.local_model_path,
            device=config.device
        )
    else:
        # Fallback to rules-based
        return RulesBasedRefiner()
```

## Privacy Considerations

All Mistral model usage complies with BeatForge's privacy requirements:

- **Symbolic-only:** Only text prompts and MIDI data (symbolic representations) are sent to models
- **No audio:** Raw audio, spectrograms, or audio-derived features are never transmitted
- **Opt-in network:** Network access requires explicit CLI flags
- **Local option:** Full offline capability with local models

## CLI Interface

```bash
# Using Mistral Pro
drumgen refine-symbolic --input song.mid --prompt "add more variation" \
    --use-mistral-pro --mistral-pro-key $MISTRAL_PRO_KEY

# Using Mistral Cloud API
drumgen refine-symbolic --input song.mid --prompt "add more variation" \
    --use-mistral-api --mistral-api-key $MISTRAL_API_KEY

# Using local Mistral model
drumgen refine-symbolic --input song.mid --prompt "add more variation" \
    --use-local-mistral --local-model-path ~/.beatforge/models/mistral-7b-instruct-v0.2

# Check available models
drumgen models list --type llm

# Install local model
drumgen models install mistral-7b-instruct-v0.2
```

## Evaluation Criteria for Local Models

When selecting local Mistral models, we evaluate based on:

1. **License Compatibility:** Must be compatible with AGPL-3.0-or-later
2. **Quality:** Performance on symbolic music tasks (MIDI understanding, pattern generation)
3. **Resource Efficiency:** Memory and compute requirements
4. **Stability:** Proven track record, minimal breaking changes
5. **Maintenance:** Active upstream support and updates
6. **Download Size:** Reasonable for users to download and store

### Model Comparison

| Model | License | Quality | Resources | Stability | Recommended |
|-------|---------|---------|-----------|-----------|-------------|
| mistral-7b-instruct-v0.2 | Apache-2.0 | Excellent | Moderate | High | ✅ Yes |
| mistral-7b-latest | Apache-2.0 | Excellent | Moderate | Medium | ⚠️ With caution |
| mistral-7b-instruct-v0.1 | Apache-2.0 | Good | Moderate | Very High | ✅ Yes |
| mixtral-8x7b | Apache-2.0 | Excellent | High | Medium | ❌ Too large |
| mixtral-8x22b | Apache-2.0 | Excellent | Very High | Low | ❌ Too large |

## Future Considerations

1. **Model Updates:** Regular review of new Mistral releases for potential upgrades
2. **Quantization:** Support for 4-bit and 8-bit quantization to reduce memory usage
3. **Model Fusion:** Potential for ensemble approaches combining multiple models
4. **Custom Fine-tuning:** Option to fine-tune models on domain-specific MIDI data
5. **Hardware Acceleration:** Support for TPU, NPU, and other specialized hardware

## Migration from Previous Strategy

**Previous:** GitHub Models / Copilot assist was mentioned as the primary option for M5.5  
**Current:** Mistral models with clear priority order (Pro → API → Local)  

**Rationale for Change:**
- Mistral's Apache-2.0 licensed models are fully compatible with AGPL-3.0-or-later
- Better control over data and privacy with Mistral's transparent approach
- Superior performance on symbolic tasks compared to Copilot
- Local inference option provides complete offline capability
- Mistral's focus on open models aligns with BeatForge's open-source philosophy

## References

- [Mistral AI](https://mistral.ai/)
- [Mistral Models on Hugging Face](https://huggingface.co/mistralai)
- [Mistral License](https://github.com/mistralai/mistral-src/blob/main/LICENSE)
- [Apache-2.0 License](https://www.apache.org/licenses/LICENSE-2.0)
