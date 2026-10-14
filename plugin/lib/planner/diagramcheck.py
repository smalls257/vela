"""Every mermaid block in the vault must draw: E604 for each one mermaid cannot parse, W604 when nothing could check.

    blocks(pages) -> [Block]                     the mermaid blocks on parsed pages (vault pages and docs/ alike)
    findings(blocks, verdicts) -> [Finding]       E604 for each block whose verdict is not None
    unchecked(blocks, reason) -> [Finding]        one W604 when there were blocks and no mermaid to judge them

The Violation this exists to prevent is a Paper Tiger: a design passes every check while the explorer shows "Diagram
not drawn" where its flow should be. The judge is mermaid's own parser (planner.edge.mermaidjs), never a grammar of
ours, so the check and the drawing cannot disagree. A missing runtime is W604, never a quiet pass (Silent Fallback).
This module is pure: it turns blocks and verdicts into findings and never runs anything.
"""
import re
from dataclasses import dataclass

from planner.model import Finding

PARSE_LINE = re.compile(r"^Parse error on line (\d+)")
UNKNOWN_TYPE = "No diagram type detected"
# mermaid's names for what it found, in a reader's words
FOUND = {"NEWLINE": "the end of the line", "EOF": "the end of the diagram", "SEMI": "a ;"}
ARROWISH = re.compile(r"ARROW|CROSS|POINT|LINK|ARROWHEAD")
END_TOKENS = ("EOF", "1")  # jison names the end of input EOF, or by its number 1 when the grammar kept no names
SHOWN_AS_SOURCE = "until then the viewer and the explorer show its source, not a drawing."


@dataclass(frozen=True)
class Block:
    path: str  # vault-relative, / separators
    line: int  # line of the opening fence
    source: str  # the diagram text between the fences

    @property
    def first(self):
        """The diagram's first line that says something, which names its kind for a reader."""
        return next((l.strip() for l in self.source.split("\n") if l.strip() and not l.strip().startswith("%%")), "(empty)")


def blocks(pages):
    return [Block(page.path, d.line, "\n".join(d.lines)) for page in pages for d in page.diagrams]


def failing_line(verdict):
    """The diagram line mermaid stopped at (1 is the line under the fence), or None when it did not say."""
    match = PARSE_LINE.match(verdict.get("message") or "")
    return int(match.group(1)) if match else None


def expected_words(verdict):
    expected = [e.strip("'") for e in verdict.get("expected") or []]
    if expected and all(ARROWISH.search(e) for e in expected):
        return "an arrow, such as ->> or -->"
    named = [e.lower().replace("_", " ") for e in expected[:4]]
    return ("one of: " + ", ".join(named) + (" and more" if len(expected) > 4 else "")) if named else "something else"


def found_words(verdict):
    token = verdict.get("token") or ""
    if token in FOUND:
        return FOUND[token]
    text = (verdict.get("text") or "").strip()
    return f'"{text}"' if text else "something it cannot read"


def plain(block, verdict):
    """(page line, what went wrong, how to fix it), in a reader's words, from mermaid's own verdict."""
    message = verdict.get("message") or "mermaid gave no reason"
    lines = block.source.split("\n")
    at = failing_line(verdict)
    if message.startswith(UNKNOWN_TYPE):
        return unknown_type(block)
    if verdict.get("token") in END_TOKENS or (at is not None and at > len(lines)):
        return ran_out(block, verdict, lines)
    if at is None or at < 1:
        return block.line, f"mermaid cannot read it: {' '.join(message.split())}", "Correct the diagram; " + SHOWN_AS_SOURCE
    return bad_line(block, verdict, lines, at)


def unknown_type(block):
    return (block.line, f'mermaid does not know the diagram type "{block.first.split()[0]}", so it draws nothing.',
            "Start the block with a type mermaid draws, such as flowchart LR, sequenceDiagram or erDiagram.")


def ran_out(block, verdict, lines):
    """mermaid reached the end with something still open, most often a loop, alt, opt or par with no end."""
    expected = [e.strip("'") for e in verdict.get("expected") or []]
    if "end" in expected:
        return (block.line + len(lines), "mermaid reached the end of the diagram with a block still open: it expected an end line.",
                "Close each loop, alt, opt, par, rect and subgraph with its own end line.")
    return (block.line + len(lines), f"mermaid reached the end of the diagram still expecting {expected_words(verdict)}.",
            "Finish the last statement; " + SHOWN_AS_SOURCE)


def bad_line(block, verdict, lines, at):
    text = lines[at - 1].strip()
    what = (f'mermaid cannot read its line {at}, "{text}": it expected {expected_words(verdict)}, '
            f"and found {found_words(verdict)}.")
    if ";" in text:
        fix = ("A ; ends a statement in mermaid, so the words after it were read as a new line. "
               "Write a comma or \"then\" instead, or #59; where a semicolon must show.")
    else:
        fix = "Correct that line; " + SHOWN_AS_SOURCE
    return block.line + at, what, fix


def findings(blocks, verdicts):
    """E604 for each block whose verdict is not None. `verdicts` lines up with `blocks`, one each."""
    if len(blocks) != len(verdicts):
        raise ValueError(f"{len(blocks)} diagrams but {len(verdicts)} verdicts; the parser lost track of one")
    out = []
    for block, verdict in zip(blocks, verdicts):
        if verdict is None:
            continue
        line, what, fix = plain(block, verdict)
        out.append(Finding(block.path, line, "E604", f'The diagram at line {block.line} ("{block.first}") does not draw: {what}', fix))
    return out


def unchecked(blocks, reason):
    """One W604 for the whole run, on the first block, so a vault with diagrams is never passed unread."""
    if not blocks:
        return []
    first = blocks[0]
    return [Finding(first.path, first.line, "W604",
                    f"{len(blocks)} mermaid diagram{'' if len(blocks) == 1 else 's'} not checked: {reason}.",
                    "Install Node.js (node on the PATH, or PLANNER_NODE naming it) and run the check again; "
                    "a diagram mermaid cannot read shows as source, not a drawing.")]
