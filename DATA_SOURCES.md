# Data sources

This file lists every third-party dataset BeatForge uses for any local training or evaluation, with upstream license and intended use.

BeatForge does **not** redistribute datasets. Datasets are downloaded by the user via documented commands, and their contents stay on the user's machine.

## Format

```yaml
- name: <dataset id>
  upstream_url: <URL>
  upstream_license: <SPDX or named license>
  redistribution_allowed: true|false
  used_for: training | evaluation | examples
  download_command: |
    <exact shell commands, no audio uploaded anywhere>
  notes: |
    Any caveats, opt-outs, or attribution requirements.
```

## Current entries

> **None yet.** No datasets are required in M0–M3. The first entry will be added in M4 if a local-training path is pursued.

Planned candidates for M4:

- **Groove MIDI Dataset (Magenta)** — CC-BY-4.0. ~13.6 GB of MIDI + (optional) audio. We only need the MIDI portion for symbolic training, which keeps the dataset footprint small and the privacy story clean. Attribution to Google Magenta is required in any derived model card.

## User-provided audio

User-provided audio files (the bass/guitar/mix the user feeds into `drumgen analyze` or `drumgen groove`) are **not** a dataset in the licensing sense. They:

- stay entirely on the user's machine,
- are never logged, telemetered, or transmitted by BeatForge,
- are not stored in any cache that survives the user's process (intermediate analysis artifacts like `analysis.json` are written only to user-controlled output paths).

If you, the user, choose to share an audio fixture in a bug report, you bear sole responsibility for ensuring you have the right to do so. We recommend redacting / replacing copyrighted material with a self-recorded equivalent before sharing.
