"""Which conflict hunks `vela close sync-main` may settle by itself, and which only the lead may. Pure: text in, hunks out.

The Violation this module exists to prevent is a Silent Fallback in the merge: a "resolve the conflict" step that
quietly takes one side and drops the other side's writing. The close skill used to carry the recipe as prose ("read
each hunk; if any sits outside a `<!-- generated:` block, stop"), and one wrong reading of where a hunk sits loses the
owner's edits. So the reading lives here, with one bias: **when in doubt, a hunk is outside**. An outside hunk costs
the lead one look at the lines; a hunk wrongly called inside costs someone's paragraph.

A hunk is inside a generated block only when every side of it (ours, theirs, and the base when git wrote one) sits
within the span of one block `name`, and that block closes later in the file:

- every side holds only block content, and the block was already open where the hunk starts; or
- every side starts with the opening marker of the same block `name` and holds only content after it. The opening
  marker carries the content's sha, so when both sides re-rendered a block the marker line itself differs; render
  rewrites that line, so a marker that differs only in its sha is still the block's own line.

Anything else is outside: a closing marker inside the hunk, another block's marker, a side that leaves the block or
enters it from hand-written text (a hunk that straddles a marker), a marker-like line that does not parse, a block
that never closes, a conflict hunk with no end, and a conflicted file with no hunks at all (git's modify/delete and
binary conflicts leave no markers to read, so there is nothing to show it is safe).

Line numbers are reported in our copy of the file, because after `git merge --abort` that is the file the lead opens.
"""
import re
from dataclasses import dataclass

from vela import parse

_START, _BASE, _MID, _END = "<<<<<<<", "|||||||", "=======", ">>>>>>>"
# Any line that looks like a generated marker. One that does not match parse's strict form is still treated as a
# marker, and so as outside: a hand-edited marker is exactly where a block's edges are in doubt.
_MARKERISH = re.compile(r"<!--\s*/?\s*generated:")


@dataclass(frozen=True)
class Hunk:
    """One conflict hunk. `first`..`last` are its lines in our copy (`last < first` when our side is empty, which
    means "inserted after line `last`"). `block` is the generated block it lies wholly inside, or None (outside)."""
    first: int
    last: int
    block: object = None

    @property
    def inside(self):
        return self.block is not None

    def lines(self):
        """'12-18', '12', or 'after 11' for a hunk whose our side is empty."""
        if self.last < self.first:
            return f"after {self.last}" if self.last > 0 else "at the start"
        return str(self.first) if self.first == self.last else f"{self.first}-{self.last}"


def _is_marker_start(line, token):
    return line == token or line.startswith(token + " ")


def _marker_of(line):
    """('open', name), ('close', name), ('unknown', None) for a marker-like line that does not parse, or None."""
    opening, closing = parse.MARKER_OPEN.match(line), parse.MARKER_CLOSE.match(line)
    if opening:
        return "open", opening.group(1)
    if closing:
        return "close", closing.group(1)
    return ("unknown", None) if _MARKERISH.search(line) else None


def _block_after(state, line):
    """The open block after `line`, outside conflicts: None when the line closes it or is not a marker."""
    marker = _marker_of(line)
    if marker is None:
        return state
    kind, name = marker
    return name if kind == "open" else None


def _side_block(state, side):
    """The block one side of a hunk lies wholly inside, given the block open where the hunk starts, or None."""
    if state is not None:
        return state if all(_marker_of(line) is None for line in side) else None
    if not side or _marker_of(side[0]) is None or _marker_of(side[0])[0] != "open":
        return None
    name = _marker_of(side[0])[1]
    return name if all(_marker_of(line) is None for line in side[1:]) else None


def _hunk_block(state, sides):
    """The one block every side lies inside, or None."""
    names = {_side_block(state, side) for side in sides}
    return names.pop() if len(names) == 1 else None


def _closes_later(lines, start, name):
    """True when block `name` closes in the lines after a hunk, before any other marker."""
    for line in lines[start:]:
        marker = _marker_of(line)
        if marker is not None:
            return marker == ("close", name)
    return False


def hunks(text):
    """Every conflict hunk in a conflicted file's text, in order. A file with no hunks returns []: the caller must treat
    a conflicted file with no hunks as outside (see `outside_files`)."""
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":  # the file's final newline ends the last line; it is not a line of its own
        lines.pop()
    found, state, ours_line, i = [], None, 0, 0
    while i < len(lines):
        line = lines[i]
        if not _is_marker_start(line, _START):
            state = _block_after(state, line)
            ours_line += 1
            i += 1
            continue
        sides, current, j = {"ours": [], "base": [], "theirs": []}, "ours", i + 1
        while j < len(lines) and not _is_marker_start(lines[j], _END):
            if _is_marker_start(lines[j], _BASE) and current == "ours":
                current = "base"
            elif lines[j] == _MID and current in ("ours", "base"):
                current = "theirs"
            else:
                sides[current].append(lines[j])
            j += 1
        ours = sides["ours"]
        first, last = ours_line + 1, ours_line + len(ours)
        if j >= len(lines):  # a hunk with no end: nothing after it can be read, so it runs to the end and is outside
            found.append(Hunk(first, max(last, first), None))
            return found
        present = [ours, sides["theirs"]] + ([sides["base"]] if current != "ours" and sides["base"] else [])
        block = _hunk_block(state, present)
        if block is not None and not _closes_later(lines, j + 1, block):
            block = None
        found.append(Hunk(first, last, block))
        for kept in ours:
            state = _block_after(state, kept)
        ours_line = last
        i = j + 1
    return found


@dataclass(frozen=True)
class FilePlan:
    """One conflicted file: its path, its hunks, and the page title to name it by (None when it has none)."""
    path: str
    hunks: tuple
    title: object = None

    @property
    def outside(self):
        """Hunks outside every generated block. A file with no readable hunk counts as wholly outside."""
        return tuple(h for h in self.hunks if not h.inside) if self.hunks else (Hunk(1, 0, None),)


def plan_file(path, text):
    """The FilePlan for one conflicted file. `text` is its content with git's markers, or None when it could not be
    read as text (deleted on one side, binary): such a file has no hunks and so counts as outside."""
    if text is None:
        return FilePlan(path, ())
    return FilePlan(path, tuple(hunks(text)), title_of(text))


def title_of(text):
    """The page's `title:` from its frontmatter, or None. Read from our side when the frontmatter itself conflicts."""
    ours = re.sub(r"(?ms)^<<<<<<<[^\n]*\n(.*?)^(?:\|\|\|\|\|\|\||=======)[^\n]*\n.*?^>>>>>>>[^\n]*$", r"\1", text)
    meta, _, error = parse.split_frontmatter(ours)
    title = meta.get("title") if error is None else None
    return str(title) if title else None


def generated_only(plans):
    """True when every hunk of every conflicted file lies inside a generated block, so `-X ours` loses nobody's
    writing. An empty list is not "generated only": a merge that conflicted with nothing to show is not understood."""
    return bool(plans) and all(not p.outside for p in plans)
