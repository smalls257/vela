"""A session record's capture lines: their grammar and their numbers (overhaul Task 6b, `vela record add`).

START.md told the model to "number block IDs `^c01`, `^c02` and so on, in order, never reused", and the model counted
by eye. Two failures followed from that. A capture deleted mid-session freed its number, the next capture took it, and
two lines then shared `^c12`: every `## Changes` row and consent check that cited `^c12` now pointed at a different
sentence than the one the lead said yes to (a Silent Fallback in the record itself: the link still resolves, to the
wrong words). And a line written slightly off the grammar (a `)` in the origin, a mark not before the number) is a line
close's parser does not see, so it is never marked.

So the number is the highest one the record has *ever* used, plus one. "Ever" is the union of what the caller can
see: every `^cNN` in the text now (captures, and the Changes rows and links that cite numbers whose lines are gone),
the high-water mark `.vela/session.json` keeps for this record. There is no history leg: the record is an untracked
private file, so git holds none of its versions. A deleted capture's number survives in one of those two. And the line is built here, from parts, and refused when it would
not read back.

Pure: text in, text out; the edge reads the session file.
"""
import re

CAPTURES = "## Captures"
_NUMBER = re.compile(r"\^c(\d+)\b")
_TAG = re.compile(r"^[a-z][a-z-]*$")


class CaptureRefused(ValueError):
    """The capture would not read back as a capture line; the message says which part and why."""


def numbers_in(text):
    """Every capture number the text mentions: on a capture line, in a Changes row, in a link."""
    return {int(n) for n in _NUMBER.findall(text or "")}


def next_number(*seen):
    """One more than the highest number in any of the `seen` sets, so a number once used is never handed out again."""
    return max((n for numbers in seen for n in numbers), default=0) + 1


def label(number):
    return f"^c{number:02d}"


def _single_line(part, what):
    if "\n" in part or "\r" in part:
        raise CaptureRefused(f"the {what} is more than one line; a capture is one line")


def capture_line(tag, origin, words, number, mark=""):
    """`- [<tag>] (<origin>) <words> → <mark> ^cNN`, as CONVENTIONS "Sessions" gives it. Refuses parts that would
    break the line: a tag that isn't one lower-case word, an origin with a parenthesis (it would end the origin
    early), empty words, and words that already end in a number or carry the mark arrow (close would read them as
    the line's own)."""
    tag, origin, words, mark = tag.strip(), origin.strip(), words.strip(), (mark or "").strip()
    for part, what in ((tag, "tag"), (origin, "origin"), (words, "text"), (mark, "mark")):
        _single_line(part, what)
    if not _TAG.match(tag):
        raise CaptureRefused(f"the tag '{tag}' isn't one lower-case word (idea, thought, unknown, wild, worry, ...)")
    if not origin or "(" in origin or ")" in origin:
        raise CaptureRefused(f"the origin '{origin}' must be a name, role or handle with no parentheses "
                             "(claude, or 'claude, from <name>', for Claude's own words)")
    if not words:
        raise CaptureRefused("the text is empty")
    if _NUMBER.search(words) or " → " in words:
        raise CaptureRefused("the text carries a capture number or a mark arrow; pass a mark with --mark")
    if mark and _NUMBER.search(mark):
        raise CaptureRefused("the mark carries a capture number; the number is added for you")
    return f"- [{tag}] ({origin}) {words}" + (f" → {mark}" if mark else "") + f" {label(number)}"


def append(text, line):
    """`text` with `line` after the last capture line of `## Captures` (or under its heading when it has none, after
    any harvest-decline lines), keeping one blank line before the next section."""
    lines = text.split("\n")
    try:
        start = next(i for i, row in enumerate(lines) if row.strip() == CAPTURES)
    except StopIteration:
        raise CaptureRefused("the record has no ## Captures section") from None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    body = [i for i in range(start + 1, end) if lines[i].strip()]
    at = (body[-1] + 1) if body else start + 1
    if at == start + 1:
        lines[at:at] = ["", line]
        at += 2
    else:
        lines[at:at] = [line]
        at += 1
    if at < len(lines) and lines[at].strip():
        lines[at:at] = [""]
    return "\n".join(lines)

