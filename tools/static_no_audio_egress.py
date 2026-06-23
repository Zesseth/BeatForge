"""Static linter: refuse to load audio and reach the network in the same function.

Scans every Python file under ``src/`` and ``tools/`` for any ``def``-block
that mentions BOTH an audio-loading symbol AND a network-egress symbol. A
match is allowed only if the body contains the literal comment
``# beatforge: no-audio-egress-exempt`` (followed by a justification).

Exit code 0 = clean, 1 = violation. Run on every PR via
``.github/workflows/privacy.yml``.

This is deliberately a regex linter (not an AST tool) so reviewers can read
it in two minutes. Determinism rules: same file → same verdict.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

AUDIO_PATTERNS = [
    r"librosa\.load\b",
    r"soundfile\.read\b",
    r"\bsf\.read\b",
    r"pretty_midi\.PrettyMIDI\([^)]*\.wav",
    r"pretty_midi\.PrettyMIDI\([^)]*\.flac",
    r"\bAudioSegment\.from_file\b",
    r"wave\.open\([^)]*['\"]rb['\"]",
]

NETWORK_PATTERNS = [
    r"\brequests\.",
    r"\bhttpx\.",
    r"\burllib\.",
    r"\bopenai\.",
    r"\banthropic\.",
    r"\bsocket\.",
    r"\bsmtplib\.",
    r"\bftplib\.",
    r"\bparamiko\.",
]

EXEMPT_MARKER = "# beatforge: no-audio-egress-exempt"

AUDIO_RE = re.compile("|".join(AUDIO_PATTERNS))
NETWORK_RE = re.compile("|".join(NETWORK_PATTERNS))
DEF_RE = re.compile(r"^(\s*)(?:async\s+)?def\s+\w+", re.MULTILINE)


def _scan_file(path: Path) -> list[str]:
    """Return a list of violation messages for ``path`` (empty if clean)."""
    text = path.read_text(encoding="utf-8")
    violations: list[str] = []

    def_starts = [(m.start(), len(m.group(1))) for m in DEF_RE.finditer(text)]
    if not def_starts:
        return violations
    def_starts.append((len(text), -1))

    for i in range(len(def_starts) - 1):
        start, indent = def_starts[i]
        # body ends at next def with same-or-lower indent
        end = len(text)
        for j in range(i + 1, len(def_starts) - 1):
            nxt_start, nxt_indent = def_starts[j]
            if nxt_indent <= indent:
                end = nxt_start
                break
        body = text[start:end]
        if AUDIO_RE.search(body) and NETWORK_RE.search(body):
            if EXEMPT_MARKER in body:
                continue
            line_no = text[:start].count("\n") + 1
            violations.append(
                f"{path}:{line_no}: function body references both audio loading "
                "and a network-egress symbol (privacy violation). "
                f"Add a justified ``{EXEMPT_MARKER}`` comment if intentional."
            )
    return violations


def main(roots: list[Path] | None = None) -> int:
    if roots is None:
        repo = Path(__file__).resolve().parents[1]
        roots = [repo / "src", repo / "tools"]

    violations: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for py in root.rglob("*.py"):
            if py.name == Path(__file__).name and py.resolve() == Path(__file__).resolve():
                # don't scan ourselves — we mention both kinds of symbols by design
                continue
            violations.extend(_scan_file(py))

    if violations:
        for v in violations:
            print(v, file=sys.stderr)
        print(f"{len(violations)} no-audio-egress violation(s)", file=sys.stderr)
        return 1
    print("no-audio-egress: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
