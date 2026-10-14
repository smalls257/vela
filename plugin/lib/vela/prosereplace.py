"""Keeping a merged paragraph word for word before it is rewritten: the pure half of `vela prose replace` (overhaul
Task 21d).

Why: merged prose belongs to the people who edited it. When a session makes a merged paragraph wrong as a whole,
house-voice ("Merged prose") and close section 4 say to rewrite it, and first to keep the old paragraph word for word
in the session record under `## Replaced prose`, with the page and the date, so whoever wrote it can find it. Copying
verbatim is what code does best and a model does worst: asked to copy, it tidies (a dropped `**`, a relabeled link, a
trailing space gone). The Violation this module's shape prevents is Forensic Coding of the owner's own words: a
"copy" that is a paraphrase leaves them reconstructing what they wrote from git. So the copy is taken here, as bytes:

- `paragraph_at` finds the paragraph by line number and returns its lines exactly as they are on the page, line
  endings and trailing whitespace included. It never normalizes.
- A line inside a generated block (between `<!-- generated:NAME ... -->` and `<!-- /generated:NAME -->`) is
  refused, not copied: those lines are `vela render`'s, not anyone's prose, and the next render rewrites them anyway.
- A blank line, a heading, a marker or the frontmatter is not a paragraph; nothing is guessed from its neighbors.
- `with_entry` adds `From <page>, <date>:` and the paragraph at the end of the record's `## Replaced prose` section,
  creating the heading (once) at the end of the record when it is missing. Every byte already in the record stays.

Pure: text in, text out. No disk, git or clock; the date is passed in.
"""
import re
from dataclasses import dataclass

from vela import parse

HEADING = "## Replaced prose"
_ANY_HEADING = re.compile(r"^#{1,6}\s")
_SECTION_END = re.compile(r"^#{1,2}\s")  # a heading at the section's level or above ends `## Replaced prose`


@dataclass(frozen=True)
class Paragraph:
    first: int  # 1-based line numbers on the page
    last: int
    text: str  # the lines exactly as on the page


@dataclass(frozen=True)
class Miss:
    """Why there is nothing to copy at that line. `rule` is a short tag for `--json`; `plain` is said to the lead."""
    rule: str
    plain: str


def _frontmatter_end(lines):
    """The 0-based index of the closing `---`, or -1 when the page has no frontmatter."""
    if not lines or lines[0].rstrip("\r\n") != "---":
        return -1
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r\n") == "---":
            return index
    return len(lines) - 1  # an unclosed frontmatter runs to the end: nothing in it is prose


def _generated_lines(lines):
    """The 0-based indexes of every line in a generated block, its two marker lines included."""
    inside, open_name = set(), None
    for index, raw in enumerate(lines):
        line = raw.rstrip("\r\n")
        opening, closing = parse.MARKER_OPEN.match(line), parse.MARKER_CLOSE.match(line)
        if open_name is None and opening:
            open_name = opening.group(1)
        if open_name is not None:
            inside.add(index)
        if closing and open_name == closing.group(1):
            open_name = None
    return inside


def _is_boundary(raw):
    line = raw.rstrip("\r\n")
    return not line.strip() or bool(_ANY_HEADING.match(line)) or bool(parse.MARKER_ANY.match(line))


def paragraph_at(text, line):
    """The Paragraph holding 1-based `line` of a page's `text`, or a Miss saying why there is none."""
    lines = text.splitlines(keepends=True)
    index = line - 1
    if index < 0 or index >= len(lines):
        return Miss("no paragraph", f"The page has no line {line}.")
    if index <= _frontmatter_end(lines):
        return Miss("no paragraph", f"Line {line} is in the page's frontmatter, not its prose.")
    generated = _generated_lines(lines)
    if index in generated:
        return Miss("generated block", f"Line {line} is in a block vela writes, not prose anyone edited, so there is "
                                       "nothing of theirs to keep.")
    if _is_boundary(lines[index]):
        return Miss("no paragraph", f"Line {line} is a blank line or a heading, not a paragraph.")
    stop = _frontmatter_end(lines)
    first = index
    while first - 1 > stop and first - 1 not in generated and not _is_boundary(lines[first - 1]):
        first -= 1
    last = index
    while last + 1 < len(lines) and last + 1 not in generated and not _is_boundary(lines[last + 1]):
        last += 1
    return Paragraph(first + 1, last + 1, "".join(lines[first:last + 1]))


def entry(page, date, paragraph):
    """One entry: where it came from and when, then the paragraph. A paragraph that ended the page without a newline
    gets one, so the next entry starts on its own line; no other byte is added."""
    body = paragraph if paragraph.endswith("\n") else paragraph + "\n"
    return f"From {page}, {date}:\n\n{body}"


def with_entry(record, page, date, paragraph):
    """The record's text with one more entry under `## Replaced prose`."""
    lines = record.splitlines(keepends=True)
    heading = next((i for i, raw in enumerate(lines) if raw.rstrip() == HEADING), None)
    added = entry(page, date, paragraph)
    if heading is None:
        head = record if not record or record.endswith("\n") else record + "\n"
        return f"{head}\n{HEADING}\n\n{added}"
    end = next((i for i in range(heading + 1, len(lines)) if _SECTION_END.match(lines[i])), len(lines))
    at = end
    while at - 1 > heading and not lines[at - 1].strip():
        at -= 1  # past the blank lines that end the section, so they stay between it and the next heading
    before = "".join(lines[:at])
    if not before.endswith("\n"):
        before += "\n"
    after = "".join(lines[at:])
    if at == end and end < len(lines):
        after = "\n" + after  # the section ran right up to the next heading: keep a blank line before it
    return f"{before}\n{added}{after}"
