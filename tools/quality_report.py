"""One finding per line, `<path>:<line>: <GATE-ID> <message ending in the fix>`, so every gate reports the same way
and a hook can hand the lines to an agent without parsing a second format."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    gate: str
    message: str


def render(findings: Iterable[Finding]) -> list[str]:
    """The findings as report lines, in path then line order so two runs on the same tree print the same text."""
    ordered = sorted(findings, key=lambda f: (f.path, f.line))
    return [f"{f.path}:{f.line}: {f.gate} {f.message}" for f in ordered]
