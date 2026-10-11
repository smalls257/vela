"""What a reader has changed since the copy they opened. Pure: no disk, clock or network.

The Violation to prevent is a Black Box draft: a reader works for a week in a private copy and cannot see, in
words, what they have altered, so a proposal (or a forgotten edit) surprises them. So the explorer shows the
difference between the pristine baseline and the working pages, per page, as lines a person can read.

Two choices shape the data. Lines carry a kind ("add", "del", "ctx", "hunk") and the page draws the symbol as well
as the colour, so nothing rests on colour alone. And a generated block (the tables `planner render` writes) is
collapsed to one line on both sides, because its churn is not the reader's edit and would bury it.

edge/copies.py reads the two folders; explorer/draft_data.py gives each change its page key.
"""
import difflib

from planner import parse

MAX_DIFF_LINES = 600  # a page's diff beyond this is cut, and says so
CONTEXT = 3
ADDED, REMOVED, CHANGED = "added", "removed", "changed"


def is_binary(data):
    """Not text a person can read as a diff: a NUL byte, or not UTF-8 (the rule `propose` will use)."""
    if b"\x00" in data:
        return True
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def collapse_generated(text):
    """The page's lines with each generated block's body replaced by one line naming it, so render churn stays out."""
    out, open_name, hidden = [], None, 0  # `hidden` counts an unclosed block's lines
    for line in text.splitlines():
        if open_name is None:
            opened = parse.MARKER_OPEN.match(line)
            out.append(f"<!-- generated:{opened.group(1)} -->" if opened else line)  # the sha moves with the body
            if opened:
                open_name, hidden = opened.group(1), 0
        elif parse.MARKER_CLOSE.match(line):
            out.append(f"[generated block {open_name}, not shown]")
            out.append(line)
            open_name = None
        else:
            hidden += 1
    if open_name is not None:  # an unclosed block: show what it held, since check reports it as a fault
        out.append(f"[generated block {open_name} is not closed: {hidden} lines follow]")
    return out


def diff_lines(before, after):
    """[kind, text] rows of a unified diff with 3 lines of context, and whether it was cut."""
    rows = []
    for line in difflib.unified_diff(before, after, n=CONTEXT, lineterm=""):
        if line.startswith(("---", "+++")):
            continue
        kind = "hunk" if line.startswith("@@") else {"+": "add", "-": "del"}.get(line[:1], "ctx")
        rows.append([kind, line if kind == "hunk" else line[1:]])
    cut = len(rows) > MAX_DIFF_LINES
    return rows[:MAX_DIFF_LINES], cut


def text_change(path, status, before, after):
    lines, cut = diff_lines(before, after)
    if not lines:
        lines = [["hunk", "only line endings or the final newline differ"]]
    return {"path": path, "status": status, "binary": False, "lines": lines, "truncated": cut,
            "added": sum(1 for k, _ in lines if k == "add"), "removed": sum(1 for k, _ in lines if k == "del")}


def binary_change(path, status):
    return {"path": path, "status": status, "binary": True, "lines": [], "truncated": False, "added": 0, "removed": 0}


def compare(baseline, working):
    """The changes from {path: bytes} baseline to {path: bytes} working, by path: added, removed, changed."""
    out = []
    for path in sorted(set(baseline) | set(working)):
        old, new = baseline.get(path), working.get(path)
        if old == new:
            continue
        status = ADDED if old is None else REMOVED if new is None else CHANGED
        if any(side is not None and is_binary(side) for side in (old, new)):
            out.append(binary_change(path, status))
            continue
        before = collapse_generated(old.decode("utf-8")) if old is not None else []
        after = collapse_generated(new.decode("utf-8")) if new is not None else []
        if status == CHANGED and before == after and old.decode("utf-8").splitlines() != new.decode("utf-8").splitlines():
            continue  # only a generated block's body moved: render churn, not the reader's edit
        out.append(text_change(path, status, before, after))
    return out
