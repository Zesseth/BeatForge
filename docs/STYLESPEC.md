# StyleSpec — schema and parsing rules

`StyleSpec` is the structured representation of a drum prompt. It is produced
by `drumgen parse-prompt` and consumed by `drumgen generate`. The schema is
defined in [`src/beatforge/prompt/stylespec.py`](../src/beatforge/prompt/stylespec.py)
and the parser in [`src/beatforge/prompt/parser.py`](../src/beatforge/prompt/parser.py).

## Fields (v1)

| Field          | Type                                              | Default     | Meaning                                                  |
| -------------- | ------------------------------------------------- | ----------- | -------------------------------------------------------- |
| `genre`        | `rock` \| `pop` \| `punk` \| `metal` \| `funk` \| `null` | `null`      | Highest-level style hint.                                |
| `bpm`          | `int` (20–400) \| `null`                          | `null`      | Tempo override. `null` lets the generator pick.          |
| `hats`         | `8th` \| `16th` \| `shuffle` \| `swing` \| `null`  | `null`      | Hi-hat subdivision / feel.                               |
| `backbeat`     | `2_and_4` \| `2` \| `4` \| `null`                  | `null`      | Snare placement.                                         |
| `kick_density` | `less` \| `default` \| `more`                     | `default`   | Coarse kick-frequency knob (≈ ±25% in M1).               |
| `fills`        | `none` \| `fewer` \| `default` \| `more` \| `before_chorus` | `default`   | How often and where fills land.                          |
| `ghost_notes`  | `bool`                                            | `false`     | Whether to insert quiet snare ghost notes.               |
| `feel`         | `tight` \| `default` \| `loose`                   | `default`   | Quantization tightness.                                  |

## Parsing rules

The parser is purely keyword + regex (no LLM, no network). The rules are
intentionally permissive — unknown tokens are silently ignored but can be
inspected via `drumgen parse-prompt --verbose`.

- **Genre** — matched as whole words: `rock`, `pop`, `punk`, `metal`, `funk`.
- **BPM** — `\d{2,3}\s*bpm` (case-insensitive). Out-of-range values fail validation.
- **Hats** — `16th`/`8th`/`sixteenth`/`eighth`/`shuffle`/`swing`.
- **Backbeat** — phrases like `snare on 2&4`, `2 & 4`, `snare on 2`, `snare on 4`.
- **Kick density** — `more kick`, `double kick`, `heavy kick` → `more`; `less kick`, `sparse kick` → `less`.
- **Fills** — `no fills` → `none`; `fewer fills` → `fewer`; `fills before chorus` → `before_chorus`; `more fills`, `busy fills` → `more`.
- **Ghost notes** — any occurrence of `ghost` (with optional `notes`).
- **Feel** — `tight`/`quantized` → `tight`; `loose`/`laid-back`/`humanized` → `loose`.

The order of rules within each category matters: longer / more specific
matches are checked first so `16th` wins over `8th` if both appear.

## Determinism

`parse_prompt(prompt)` is a pure function. Same input → same output bytes
(`stylespec.json` ordering is sorted, indentation is 2-space).
