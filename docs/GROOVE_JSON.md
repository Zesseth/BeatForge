# `groove.json` schema (v1)

Produced by `drumgen groove` (M2.2). Extends `analysis.json` with onset
timestamps and coarse section hints. This file is the contract between
local audio analysis and any future MIDI generator.

## CLI

```
drumgen groove --audio song.wav --out groove.json
drumgen groove --audio song.wav --bpm-override 180 --out groove.json
```

## Schema

Extends every field of `analysis.json` (see [ANALYSIS_JSON.md](ANALYSIS_JSON.md)) with:

```json
{
  "onsets_s": [0.012, 0.51, 1.0],
  "onset_density_per_bar": [12, 14, 18, 18],
  "section_hints": [
    {"label": "verse", "bar_start": 0, "bar_end": 15, "confidence": 0.6},
    {"label": "chorus", "bar_start": 16, "bar_end": 31, "confidence": 0.55}
  ]
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `onsets_s` | list[float] | Onset **timestamps only** — no amplitudes |
| `onset_density_per_bar` | list[int] | Onset count per analysed bar |
| `section_hints` | list[SectionHint] | Best-effort `verse`/`chorus` labels over inclusive bar ranges, with confidence |

## Privacy invariants (hard rules)

- **No amplitude curves, no spectral features, no MFCCs, no chroma in `groove.json`.** Only timestamps and per-bar counts.
- The serialiser (`groove_to_json`) refuses to write any key whose name contains a forbidden audio-feature term (`amplitude`, `envelope`, `mfcc`, `chroma`, `spectrogram`, `spectral`, ...).
- Section hints are heuristics based on onset-density step changes; confidence scores are exposed so callers can ignore weak hints (confidence floor 0.35).
- Network policy: `none`.
