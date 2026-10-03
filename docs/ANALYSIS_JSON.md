# `analysis.json` schema (v1)

Produced by `drumgen analyze` (M2.1). All analysis is **local** — no network, audio never leaves the machine.

## CLI

```
drumgen analyze --audio song.wav --out analysis.json
drumgen analyze --audio song.wav --bpm-override 180 --out analysis.json
drumgen analyze --audio song.wav --time-signature 4/4 --out analysis.json
```

## Schema

```json
{
  "schema_version": "1.0",
  "source": {"sha256": "<hex>", "duration_s": 12.5, "sr": 44100},
  "tempo_bpm": 124.0,
  "tempo_confidence": 0.83,
  "time_signature": "4/4",
  "beats_s": [0.512, 1.001, 1.487],
  "downbeats_s": [0.512, 2.46, 4.4],
  "bars": [{"index": 0, "start_s": 0.512, "end_s": 2.46}]
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `schema_version` | string | `"1.0"` |
| `source.sha256` | string | SHA-256 of the raw input file bytes, computed locally, never transmitted |
| `source.duration_s` | float | Duration in seconds from the container header |
| `source.sr` | int | Native sample rate of the input file |
| `tempo_bpm` | float | Estimated tempo, or the `--bpm-override` value when given |
| `tempo_confidence` | float | 0.0–1.0 heuristic (1.0 when `--bpm-override` is used) |
| `time_signature` | string | From `--time-signature` (default `4/4`) |
| `beats_s` | list[float] | Beat timestamps in seconds |
| `downbeats_s` | list[float] | Every `beats_per_bar`-th beat |
| `bars` | list[Bar] | `index`, `start_s`, `end_s` per bar |

## Behaviour

- Supports `.wav` and `.flac` (via `soundfile`).
- `--bpm-override` skips tempo estimation and derives an even beat grid.
- Output is deterministic for the same input file and pinned library versions (librosa is pinned exactly in `pyproject.toml`; numpy is constrained to `>=1.26,<2.3`).
- Validated by a pydantic model (`beatforge.audio.analyze.Analysis`); unknown keys are rejected.
- Network policy: `none`. No HTTP client is imported anywhere in `beatforge.audio`.
