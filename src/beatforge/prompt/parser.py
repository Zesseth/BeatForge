"""Keyword + regex parser converting natural-language prompts to a StyleSpec.

Hard rules:

* Purely local — no network, no LLM.
* Unknown tokens are silently ignored but reported via ``parse_prompt`` when
  ``return_unparsed=True``.
* Same input → same output (deterministic).
"""

from __future__ import annotations

import re
from typing import Literal, overload

from .stylespec import Backbeat, Density, Feel, Fills, Genre, Hats, StyleSpec

_GENRES: dict[str, Genre] = {
    "rock": "rock",
    "pop": "pop",
    "punk": "punk",
    "metal": "metal",
    "funk": "funk",
}

_HATS_PATTERNS: list[tuple[re.Pattern[str], Hats]] = [
    (re.compile(r"\b16th\b|\b16ths?\b|\bsixteenth\b"), "16th"),
    (re.compile(r"\b8th\b|\b8ths?\b|\beighth\b"), "8th"),
    (re.compile(r"\bshuffle\b"), "shuffle"),
    (re.compile(r"\bswing\b"), "swing"),
]

_BACKBEAT_PATTERNS: list[tuple[re.Pattern[str], Backbeat]] = [
    (re.compile(r"\b(snare|backbeat)\s+on\s+2\s*[&+and]+\s*4\b", re.IGNORECASE), "2_and_4"),
    (re.compile(r"\b2\s*[&+]\s*4\b"), "2_and_4"),
    (re.compile(r"\bsnare\s+on\s+2\b", re.IGNORECASE), "2"),
    (re.compile(r"\bsnare\s+on\s+4\b", re.IGNORECASE), "4"),
]

_KICK_DENSITY: list[tuple[re.Pattern[str], Density]] = [
    (
        re.compile(r"\bmore\s+kick(s|ing)?\b|\bdouble\s+kick\b|\bheavy\s+kick\b", re.IGNORECASE),
        "more",
    ),
    (re.compile(r"\bless\s+kick(s|ing)?\b|\bsparse\s+kick\b", re.IGNORECASE), "less"),
]

_FILLS: list[tuple[re.Pattern[str], Fills]] = [
    (re.compile(r"\bno\s+fills?\b", re.IGNORECASE), "none"),
    (re.compile(r"\bfewer\s+fills?\b|\bless\s+fills?\b", re.IGNORECASE), "fewer"),
    (re.compile(r"\bfills?\s+before\s+chorus\b", re.IGNORECASE), "before_chorus"),
    (re.compile(r"\bmore\s+fills?\b|\bbusy\s+fills?\b", re.IGNORECASE), "more"),
]

_GHOST = re.compile(r"\bghost(\s+notes)?\b", re.IGNORECASE)

_FEEL: list[tuple[re.Pattern[str], Feel]] = [
    (re.compile(r"\btight\b|\bquantiz", re.IGNORECASE), "tight"),
    (re.compile(r"\bloose\b|\blaid[\s-]?back\b|\bhumaniz", re.IGNORECASE), "loose"),
]

_BPM = re.compile(r"(\d{2,3})\s*(?:bpm|BPM)\b")
_TOKEN_SPLIT = re.compile(r"[,\s]+")


def _find_genre(lowered: str) -> Genre | None:
    for word, g in _GENRES.items():
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return g
    return None


def _find_hats(text: str) -> Hats | None:
    for pattern, value in _HATS_PATTERNS:
        if pattern.search(text):
            return value
    return None


def _find_backbeat(text: str) -> Backbeat | None:
    for pattern, value in _BACKBEAT_PATTERNS:
        if pattern.search(text):
            return value
    return None


def _find_kick_density(text: str) -> Density:
    for pattern, value in _KICK_DENSITY:
        if pattern.search(text):
            return value
    return "default"


def _find_fills(text: str) -> Fills:
    for pattern, value in _FILLS:
        if pattern.search(text):
            return value
    return "default"


def _find_feel(text: str) -> Feel:
    for pattern, value in _FEEL:
        if pattern.search(text):
            return value
    return "default"


def _find_bpm(text: str) -> int | None:
    m = _BPM.search(text)
    return int(m.group(1)) if m else None


def _build_stylespec(text: str) -> StyleSpec:
    lowered = text.lower()
    return StyleSpec(
        genre=_find_genre(lowered),
        bpm=_find_bpm(text),
        hats=_find_hats(lowered),
        backbeat=_find_backbeat(text),
        kick_density=_find_kick_density(text),
        fills=_find_fills(text),
        ghost_notes=bool(_GHOST.search(text)),
        feel=_find_feel(text),
    )


@overload
def parse_prompt(prompt: str) -> StyleSpec: ...
@overload
def parse_prompt(prompt: str, *, return_unparsed: Literal[False]) -> StyleSpec: ...
@overload
def parse_prompt(prompt: str, *, return_unparsed: Literal[True]) -> tuple[StyleSpec, list[str]]: ...


def parse_prompt(
    prompt: str, *, return_unparsed: bool = False
) -> StyleSpec | tuple[StyleSpec, list[str]]:
    """Parse ``prompt`` into a :class:`StyleSpec`.

    If ``return_unparsed`` is True, also returns the list of tokens that did
    not match any rule (useful for ``--verbose`` CLI output).
    """
    text = prompt.strip()
    spec = _build_stylespec(text)
    if not return_unparsed:
        return spec
    return spec, _collect_unparsed_tokens(text)


def _collect_unparsed_tokens(text: str) -> list[str]:
    lowered = text.lower()
    matched_spans: list[tuple[int, int]] = []
    rule_patterns: list[re.Pattern[str]] = [
        *(p for p, _ in _HATS_PATTERNS),
        *(p for p, _ in _BACKBEAT_PATTERNS),
        *(p for p, _ in _KICK_DENSITY),
        *(p for p, _ in _FILLS),
        *(p for p, _ in _FEEL),
        _GHOST,
        _BPM,
    ]
    for pattern in rule_patterns:
        for m in pattern.finditer(text):
            matched_spans.append(m.span())
    for word in _GENRES:
        for m in re.finditer(rf"\b{re.escape(word)}\b", lowered):
            matched_spans.append(m.span())

    def _is_matched(start: int, end: int) -> bool:
        return any(s <= start and end <= e for s, e in matched_spans)

    unparsed: list[str] = []
    pos = 0
    for token in _TOKEN_SPLIT.split(text):
        if not token:
            continue
        start = text.find(token, pos)
        end = start + len(token)
        pos = end
        if start >= 0 and not _is_matched(start, end):
            unparsed.append(token)
    return unparsed
