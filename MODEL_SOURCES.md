# Model sources

This file lists every third-party model weight or checkpoint that BeatForge can download via `drumgen models install`, along with its upstream license, expected SHA-256, and the BeatForge code path that loads it.

Pinning each model here serves three purposes:

1. **Reproducibility** — the same `models install --model X --version Y` produces the same bytes for everyone.
2. **License compliance** — every model used downstream is paired with an upstream license that is compatible with AGPL-3.0-or-later (Apache-2.0, MIT, BSD-2/3-Clause, CC-BY, public domain — all fine; CC-BY-NC, research-only, and custom EULAs are NOT).
3. **Privacy auditability** — the model download endpoints are the *only* external hosts BeatForge is allowed to contact in non-opt-in mode. Adding a model here adds a host to the network allow-list.

## Format

Every entry follows this template:

```yaml
- name: <short id used in CLI>
  version: <upstream version or tag>
  upstream_repo: <URL>
  upstream_license: <SPDX id, e.g. Apache-2.0, MIT, CC-BY-4.0>
  license_compatible_with_agpl3: true|false
  weight_files:
    - url: <direct download URL>
      sha256: <hex digest>
      bytes: <int>
  loader: src/beatforge/models/<adapter>.py
  notes: |
    Why this model is included, and any caveats.
```

## Current entries

> **None yet.** No model weights are bundled or downloaded in M0–M3. The first entries will be added in M4 (`drumgen models install`).

## LLM Model Priority for Symbolic Refinement (M5.5)

For the optional symbolic LLM refinement feature, the following priority order applies:

1. **Mistral Pro Subscription** ( Preferred ) - Mistral's hosted Pro model via subscription
   - Access: Requires Mistral Pro API key
   - Network: `symbolic-llm-allowed` (opt-in via `--use-mistral-pro` flag)
   - License: Commercial use according to Mistral terms
   
2. **Mistral Cloud API** - Mistral's hosted API (non-Pro models)
   - Access: Requires Mistral API key
   - Network: `symbolic-llm-allowed` (opt-in via `--use-mistral-api` flag)
   - License: Commercial use according to Mistral terms
   
3. **Local Mistral Model** - Self-hosted Mistral model
   - Access: Local inference via `mistral-inference` or similar
   - Network: `none` (fully local)
   - Recommended model: `mistral-7b-instruct-v0.2` (Apache-2.0 licensed, good balance of quality and resource requirements)
   - Alternative: `mistral-7b-latest` for most recent improvements

Planned candidates for M4 evaluation (not yet committed to):

- **Magenta GrooVAE** drum-checkpoints (Apache-2.0). Will only be added if the symbolic-groove-model backend proves we want it; the architecture treats it as one of many pluggable backends.
- **Small custom transformer** trained locally on the Groove MIDI Dataset (CC-BY-4.0). If we train and publish weights, they will be released under CC-BY-4.0 (matching the training data) or AGPL-3.0 alongside the training script and a `DATA_SOURCES.md` reference.

## Adding a new model

Open a PR that:

1. Adds an entry above following the template.
2. Adds the upstream host to the egress allow-list in the privacy harness config.
3. Provides an adapter under `src/beatforge/models/` that loads the weights and conforms to the `SymbolicGrooveModel` interface.
4. Includes a test that runs `drumgen models install --model <name>` against a local fixture mirror (no live download in CI).

PRs that add a model with a license that is not compatible with AGPL-3.0-or-later (e.g. non-commercial, research-only, custom EULA, or any field-of-use restriction) will be rejected.
