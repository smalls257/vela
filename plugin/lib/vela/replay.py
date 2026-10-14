"""Replaying a reader's drafts onto a newer published copy. Pure: no disk, clock, network or git.

Three trees decide every page: B, the baseline the reader opened; D, their working copy; N, the newer copy the
owner published. The Violation to prevent is a Silent Fallback in the merge: a reader's week of drafting lost
because "take the newest" looked tidy, or an owner's correction undone because "keep mine" did. So a page is
settled silently only when one side did not touch it. When both did, the lines are merged only if their changes
do not touch; otherwise the page becomes N, the reader's whole version is written beside it, and the conflict is
listed. Nothing a person wrote is dropped without a file to find it in.

There is no git on a reader's machine, so the merge is a line-based three-way over `difflib`, deliberately as
cautious as git: hunks that merely touch are a conflict, because a reader's edit beside an owner's edit is
the likeliest place for two sentences to stop agreeing.

edge/replays.py writes the outcome to the workspace; cli.py orchestrates.
"""
import difflib
import re
from dataclasses import dataclass

from vela import drafts, schema

KEPT, TOOK, MERGED, CONFLICT = "kept", "took", "merged", "conflict"
# Why a page is in conflict.
BOTH_EDITED, BOTH_ADDED, OWNER_DELETED, YOU_DELETED, BINARY = "both-edited", "both-added", "owner-deleted", "you-deleted", "binary"

MINE_RE = re.compile(r"\.mine(-\d+)?(\.md)?$")
MARKER_RE = re.compile(rf"^\s*-\s+\*\*Pending approval:\*\*\s+(?P<by>{schema.HANDLE}),\s+(?P<date>\d{{4}}-\d{{2}}-\d{{2}})\s*$")
CREDIT_RE = re.compile(rf"\*\*Credit:\*\* (?P<by>{schema.HANDLE}) proposed this on (?P<date>\d{{4}}-\d{{2}}-\d{{2}})")
YOU_DELETED_NOTE = ("You deleted this page. The owner changed it in the newer copy, so it has been put back.\n"
                    "Delete this note, and the page too if you still want it gone.\n")


def is_mine_file(path):
    """A reader's saved side of a conflict (`page.mine.md`). It is not a vault page, so check and drafts ignore it."""
    return bool(MINE_RE.search(path))


def mine_path(path, taken):
    """Where the reader's version of `path` goes: beside it, `page.mine.md` (`file.csv.mine` for a non-page), and
    numbered when an earlier conflict's file is still there, so one is never written over another."""
    stem, suffix = (path[:-3], ".md") if path.endswith(".md") else (path, "")
    for n in range(1, 1000):
        candidate = f"{stem}.mine{'' if n == 1 else f'-{n}'}{suffix}"
        if candidate not in taken:
            return candidate
    raise ValueError(f"{path} has a thousand saved conflicts beside it; delete some")


@dataclass(frozen=True)
class Conflict:
    path: str
    kind: str
    mine: str  # where the reader's version was written
    lines: tuple = ()  # (first, last) line ranges of the copy the reader opened that both sides changed
    note: str = ""

    def as_dict(self):
        return {"path": self.path, "kind": self.kind, "mine": self.mine, "lines": [list(r) for r in self.lines], "note": self.note}


@dataclass(frozen=True)
class Outcome:
    path: str
    action: str  # KEPT, TOOK, MERGED or CONFLICT
    detail: str


@dataclass
class Result:
    write: dict  # {path: bytes} the working copy must now hold
    delete: list  # paths the working copy must no longer hold
    mine: dict  # {path: bytes} reader versions written beside conflicted pages
    outcomes: list
    conflicts: list
    backups: dict  # {path: bytes} the reader's version of each merged page before the merge

    def by_action(self, action):
        return [o for o in self.outcomes if o.action == action]


# ------------------------------------------------------------------ the three-way merge

def _hunks(base, other):
    matcher = difflib.SequenceMatcher(None, base, other, autojunk=False)
    return [(i1, i2, other[j1:j2]) for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag != "equal"]


def _apply(base, lo, hi, hunks):
    """base[lo:hi] with these hunks (all inside it) applied."""
    out, pos = [], lo
    for i1, i2, new in sorted(hunks, key=lambda h: (h[0], h[1])):
        out += base[pos:i1] + new
        pos = i2
    return out + base[pos:hi]


def _clusters(mine, theirs):
    """[(lo, hi, our hunks, their hunks)] where each cluster is a run of hunks that overlap or touch."""
    tagged = sorted([(h, "ours") for h in mine] + [(h, "theirs") for h in theirs], key=lambda t: (t[0][0], t[0][1]))
    out, i = [], 0
    while i < len(tagged):
        lo, hi = tagged[i][0][0], tagged[i][0][1]
        group = [tagged[i]]
        i += 1
        while i < len(tagged) and tagged[i][0][0] <= hi:
            hi = max(hi, tagged[i][0][1])
            group.append(tagged[i])
            i += 1
        out.append((lo, hi, [h for h, side in group if side == "ours"], [h for h, side in group if side == "theirs"]))
    return out


def merge3(base, ours, theirs):
    """(merged lines, []) when the two sides' changes do not touch, else (None, [(first, last)]) with the line
    ranges of `base` (1-based, inclusive; last < first for a pure insertion) that both sides changed differently.
    A change both sides made identically is agreed, not a clash."""
    out, pos, clashes = [], 0, []
    for lo, hi, mine, theirs_ in _clusters(_hunks(base, ours), _hunks(base, theirs)):
        out += base[pos:lo]
        pos = hi
        mine_text, their_text = _apply(base, lo, hi, mine), _apply(base, lo, hi, theirs_)
        if mine and theirs_ and mine_text != their_text:
            clashes.append((lo + 1, hi))
            continue
        out += mine_text if mine else their_text
    out += base[pos:]
    return (None, clashes) if clashes else (out, [])


def contains_changes(base, ours, theirs):
    """Whether `theirs` already holds everything `ours` changed: each line ours added is in theirs, and each line
    ours removed is gone from it. True means the owner's page already says what the reader's did."""
    gone, added = set(), set()
    for _, i1, i2, j1, j2 in (op for op in difflib.SequenceMatcher(None, base, ours, autojunk=False).get_opcodes() if op[0] != "equal"):
        gone.update(base[i1:i2])
        added.update(ours[j1:j2])
    held = set(theirs)
    return added <= held and not (gone & (held - set(ours)))


def _lines(data):
    return data.decode("utf-8").splitlines(keepends=True)


def _reviewed_markers(ours, base, theirs):
    """Indexes of pending-approval lines the reader added that the owner has since reviewed: theirs holds the
    `**Credit:**` line that an accept or edit leaves, for the same handle and date."""
    credits = {(m["by"], m["date"]) for m in map(CREDIT_RE.search, theirs) if m}
    held = set(base)
    return [i for i, line in enumerate(ours)
            if line not in held and (m := MARKER_RE.match(line.rstrip("\r\n"))) and (m["by"], m["date"]) in credits]


# ------------------------------------------------------------------ one page, then the workspace

def _binary(*sides):
    return any(side is not None and drafts.is_binary(side) for side in sides)


def _text_both_changed(base, ours, theirs):
    """(action, merged bytes or None, clash ranges) for a text page both sides changed."""
    base_l, ours_l, theirs_l = _lines(base) if base is not None else [], _lines(ours), _lines(theirs)
    reviewed = set(_reviewed_markers(ours_l, base_l, theirs_l))
    view = [line for i, line in enumerate(ours_l) if i not in reviewed]
    if reviewed and contains_changes(base_l, view, theirs_l):
        return TOOK, theirs, []
    merged, clashes = merge3(base_l, view, theirs_l)
    if merged is None:
        return CONFLICT, None, clashes
    return MERGED, "".join(merged).encode("utf-8"), []


def _settle(path, base, ours, theirs, taken):
    """(action, detail, bytes the page should now hold or None, conflict or None) for a page that is not identical
    on both sides. One side may have left it alone."""
    if ours == base:
        return TOOK, "removed: the owner took it out and you had not changed it" if theirs is None else \
            "new from the owner" if base is None else "the owner's newer version (you had not changed it)", theirs, None
    if theirs == base:
        return KEPT, "your page removed; the owner left it alone" if ours is None else "your change; the owner left it alone", ours, None
    if ours is None:
        note = Conflict(path, YOU_DELETED, mine_path(path, taken), note="you deleted it, the owner changed it")
        return CONFLICT, note.note, theirs, note
    if theirs is None:
        note = Conflict(path, OWNER_DELETED, mine_path(path, taken), note="you changed it, the owner deleted it")
        return CONFLICT, note.note, None, note
    kind = BOTH_ADDED if base is None else BOTH_EDITED
    if _binary(base, ours, theirs):
        note = Conflict(path, BINARY, mine_path(path, taken), note="a binary file both of you changed")
        return CONFLICT, note.note, theirs, note
    action, merged, clashes = _text_both_changed(base, ours, theirs)
    if action == TOOK:
        return TOOK, "the owner reviewed your pending decision; their page already holds your change and wins", merged, None
    if action == MERGED:
        return MERGED, "your lines and the owner's merged (neither touched the other's)", merged, None
    note = Conflict(path, kind, mine_path(path, taken), () if base is None else tuple(clashes), "you and the owner both " + ("added this page" if base is None else "changed the same lines"))
    return CONFLICT, note.note, theirs, note


def plan(baseline, working, new, existing_mine=()):
    """The Result of replaying `working` (reader) over `new` (owner) from `baseline`, each {path: bytes}.
    `existing_mine` are mine files already on disk, so a second conflict on one page never overwrites the first."""
    result = Result({}, [], {}, [], [], {})
    taken = set(existing_mine)
    for path in sorted(set(baseline) | set(working) | set(new)):
        base, ours, theirs = baseline.get(path), working.get(path), new.get(path)
        if ours == theirs:
            continue
        action, detail, final, conflict = _settle(path, base, ours, theirs, taken)
        result.outcomes.append(Outcome(path, action, detail))
        if final is None:
            if ours is not None:
                result.delete.append(path)
        elif final != ours:
            result.write[path] = final
        if conflict is None and ours is not None and ours != base and final != ours:
            result.backups[path] = ours
        if conflict is not None:
            taken.add(conflict.mine)
            result.conflicts.append(conflict)
            result.mine[conflict.mine] = YOU_DELETED_NOTE.encode("utf-8") if ours is None else ours
    return result


# ------------------------------------------------------------------ what to tell the reader

def _range_words(ranges):
    words = [f"line {a}" if a == b else f"lines {a}-{b}" if b > a else ("the top of the page" if a == 1 else f"the gap after line {a - 1}") for a, b in ranges]
    return ", ".join(words)


def conflict_line(conflict):
    where = f" ({_range_words(conflict.lines)} of the copy you opened)" if conflict.lines else ""
    if conflict.kind == YOU_DELETED:
        return f"{conflict.path}: you deleted it and the owner changed it, so it is back as the owner's. A note is at {conflict.mine}; delete the page again if you still want it gone."
    if conflict.kind == OWNER_DELETED:
        return f"{conflict.path}: the owner deleted it and you had changed it. The page is gone; your version is saved as {conflict.mine}."
    return f"{conflict.path}: {conflict.note}{where}. The page is now the owner's; your version is saved as {conflict.mine}."


def report(result, old, new, stale):
    """Lines for the reader, conflicts first. `old`/`new` are (short commit, date); `stale` is the proposals now out of date."""
    lines = [f"Re-opened: your copy moves from {old[0]} ({old[1]}) to {new[0]} ({new[1]}). Your drafts were replayed onto it."]
    if result.conflicts:
        lines.append(f"  Conflicts, {len(result.conflicts)}. Nothing of yours was overwritten: the page holds the owner's version and yours sits beside it.")
        lines += [f"    {conflict_line(c)}" for c in result.conflicts]
        lines.append("  Open each pair, copy over what you want to keep, then delete the .mine file. You cannot propose until none is left.")
    for action, words in ((MERGED, "Merged (your lines and the owner's, neither touching the other's)"),
                          (KEPT, "Kept your changes (the owner did not touch these)"),
                          (TOOK, "Took the owner's version (you had not changed these)")):
        found = result.by_action(action)
        if found:
            shown = ", ".join(o.path for o in found[:5]) + (f" and {len(found) - 5} more" if len(found) > 5 else "")
            lines.append(f"  {words}, {len(found)}: {shown}.")
    if result.backups:
        lines.append("  Your version of each page the merge changed, as it was before, is kept in .planner/replay-backup/.")
    lines += stale
    if not result.outcomes:
        lines.append("  Nothing in your copy and the new one differed, so there was nothing to replay.")
    return lines


def stale_lines(paths, old_short):
    """What to say about proposals written against the baseline that has just been replaced."""
    if not paths:
        return []
    names = ", ".join(paths[:3]) + (f" and {len(paths) - 3} more" if len(paths) > 3 else "")
    return [f"  Stale proposal{'s' if len(paths) > 1 else ''}, {len(paths)}: {names}. "
            f"{'They were' if len(paths) > 1 else 'It was'} written against {old_short}, which is no longer the copy you work on. "
            "If you have not sent it, do not: run /planner:propose again (planner propose) for a fresh one from your drafts as they stand now. "
            "One you already sent is the owner's to apply against the old commit; nothing here deleted it."]

