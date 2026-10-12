"""An owner reading a reader's proposal back in, and answering it. Pure: no disk, clock, git or network.

Two failures decide the shape. A patch trusted without reading is an arbitrary file write on the owner's machine,
so every path is checked before git sees it and every hunk's counts are checked against its body; a damaged patch
stops with the file and hunk named. And a proposal answered by silence is a Silent Fallback for the reader: the
answer covers every group, a rejection or an edit says why in the owner's words, and a group left undecided stops
the answer rather than being written as accepted.

proposal.py writes what this module parses. edge/proposals.py reads the files; edge/reviewgit.py runs git.
"""
import re
from dataclasses import dataclass

from planner import drafts, parse, pending, proposal, schema, untrusted

HASH = re.compile(r"^[0-9a-f]{40}$")
HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@$")
CHANGES_BULLET = re.compile(r"^- Changes: `(?P<path>[^`]+)`(?: (?P<header>@@ .+? @@))?(?: \(also touches [^)]*\))?$")
CLAIM = re.compile(r"^- \*\*Check on this copy:\*\* (\d+) errors, (\d+) warnings")
OUTCOMES = ("accepted", "rejected", "edited")
NEEDS_REASON = ("rejected", "edited")


class ReviewError(Exception):
    """The proposal cannot be reviewed as given; the message says what is wrong and where."""


@dataclass(frozen=True)
class PatchHunk:
    header: str
    text: str


@dataclass(frozen=True)
class PatchFile:
    path: str
    status: str
    head: str
    hunks: tuple


@dataclass(frozen=True)
class ParsedPatch:
    base: str
    initiative: str
    files: tuple

    def hunk_keys(self):
        return {(f.path, h.header) for f in self.files for h in f.hunks}


def _file_path(line):
    rest = line[len("diff --git "):].rstrip("\n")
    size = (len(rest) - len("a/ b/")) // 2
    path = rest[2:2 + size]
    if size < 1 or rest != f"a/{path} b/{path}":
        raise ReviewError(f"'{line.strip()}' is not a plain a/<path> b/<path> header. A proposal carries no renames: a rename is a delete plus an add.")
    try:
        return proposal.check_path(path)
    except proposal.ProposalError as exc:
        raise ReviewError(str(exc)) from exc


def _status(head):
    if "\nnew file mode " in head:
        return drafts.ADDED
    return drafts.REMOVED if "\ndeleted file mode " in head else drafts.CHANGED


def _check_counts(path, hunk_lines):
    header, *body = hunk_lines
    match = HUNK_HEADER.match(header.rstrip("\n"))
    if not match:
        raise ReviewError(f"{path}: '{header.strip()}' is not a hunk header.")
    old = int(match[2]) if match[2] is not None else 1
    new = int(match[4]) if match[4] is not None else 1
    seen_old = sum(1 for line in body if line[:1] in (" ", "-"))
    seen_new = sum(1 for line in body if line[:1] in (" ", "+"))
    if (seen_old, seen_new) != (old, new):
        raise ReviewError(f"{path}: the hunk '{header.strip()}' says {old} old and {new} new lines but holds {seen_old} and {seen_new}. The patch is damaged; ask for it to be written again.")
    stray = next((line for line in body if line[:1] not in (" ", "-", "+", "\\")), None)
    if stray is not None:
        raise ReviewError(f"{path}: the hunk '{header.strip()}' holds a line that is not part of a diff: '{stray.strip()[:60]}'.")


def _split_hunks(path, lines):
    """(head lines, [hunk line lists]) of one file's section; the first '@@ ' line starts the hunks."""
    first = next((i for i, line in enumerate(lines) if line.startswith("@@ ")), len(lines))
    hunks, current = [], None
    for line in lines[first:]:
        if line.startswith("@@ "):
            current = [line]
            hunks.append(current)
        else:
            current.append(line)
    for hunk in hunks:
        _check_counts(path, hunk)
    return lines[:first], hunks


def parse_patch(data):
    """The ParsedPatch of a changes.patch, or ReviewError naming what is wrong. Nothing is trusted: size, UTF-8, base, paths,
    every header line (git obeys rename, copy and mode headers the path check never sees), counts."""
    if len(data) > untrusted.MAX_PATCH_BYTES:
        raise ReviewError(f"changes.patch is {len(data) // (1024 * 1024)} MB; the most I will read is {untrusted.MAX_PATCH_BYTES // (1024 * 1024)} MB.")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReviewError(f"changes.patch is not UTF-8 text ({exc.reason}), so it is not one this tool wrote.") from exc
    lines = proposal.split_lines(text)
    starts = [i for i, line in enumerate(lines) if line.startswith("diff --git ")]
    if not starts:
        raise ReviewError("changes.patch holds no 'diff --git' section, so there is nothing to apply. It may be empty or cut short.")
    fields = {}
    for line in lines[:starts[0]]:
        match = re.match(r"^# (base|initiative): (\S+)$", line.rstrip("\n"))
        if match:
            fields[match[1]] = match[2]
    if not HASH.match(fields.get("base", "")):
        raise ReviewError("changes.patch has no '# base: <full commit hash>' header, so I cannot tell which version of the vault it was written against.")
    files = []
    for n, start in enumerate(starts):
        section = lines[start:(starts[n + 1] if n + 1 < len(starts) else len(lines))]
        path = _file_path(section[0])
        head, hunks = _split_hunks(path, section)
        try:
            untrusted.check_patch_head(path, head)
        except untrusted.Refused as exc:
            raise ReviewError(str(exc)) from exc
        head_text = "".join(head)
        files.append(PatchFile(path, _status(head_text), head_text,
                               tuple(PatchHunk(h[0].rstrip("\n"), "".join(h)) for h in hunks)))
    paths = [f.path for f in files]
    if len(set(paths)) != len(paths):
        raise ReviewError("changes.patch holds the same file twice, which this tool never writes.")
    return ParsedPatch(fields["base"], fields.get("initiative", ""), tuple(files))


# ------------------------------------------------------------------ the note

@dataclass(frozen=True)
class GroupRef:
    key: str
    hunks: tuple  # (path, header)
    pending: bool


@dataclass(frozen=True)
class Note:
    title: str
    author: str
    claim: object  # (errors, warnings) or None
    groups: tuple


def parse_note(markdown):
    """Title, author, the reader's check claim and the groups with their hunks, from proposal.md."""
    title = author = ""
    claim = None
    groups, section, key, hunks = [], "", None, []

    def close():
        if key is not None:
            groups.append(GroupRef(key, tuple(hunks), section == "pending"))

    for raw in markdown.split("\n"):
        line = raw.rstrip()
        if line.startswith("# Proposal:") and not title:
            title = line[len("# Proposal:"):].strip()
        elif line.startswith("- **Author:**"):
            author = line.split(":**", 1)[1].strip()
        elif CLAIM.match(line):
            claim = tuple(int(n) for n in CLAIM.match(line).groups())
        elif line.startswith("## "):
            close()
            key, hunks = None, []
            section = "pending" if line.startswith("## Pending decisions") else "other" if line.startswith("## Other changes") else ""
        elif line.startswith("### ") and section:
            close()
            heading = line[4:].strip()
            key = proposal.NO_ID if heading.startswith(proposal.NO_ID) else heading.split()[0]
            hunks = []
        elif key is not None and CHANGES_BULLET.match(line):
            found = CHANGES_BULLET.match(line)
            hunks.append((found["path"], found["header"] or ""))
    close()
    return Note(title, author, claim, tuple(groups))


def groups_for(parsed, note):
    """([GroupRef], [problem]) covering every hunk in the patch exactly once.

    A hunk the note does not name goes to 'Not tied to an ID' (so nothing is hidden); one it names that the patch
    lacks is reported (so a stale note is noticed). With no note, each file is a group.
    """
    present = parsed.hunk_keys() | {(f.path, "") for f in parsed.files if not f.hunks}
    if note is None or not note.groups:
        return [GroupRef(f.path, tuple((f.path, h.header) for h in f.hunks) or ((f.path, ""),), False) for f in parsed.files], []
    problems, named, kept = [], set(), []
    for group in note.groups:
        real = tuple(h for h in group.hunks if h in present)
        problems += [f"proposal.md names {path} {header} but changes.patch has no such change." for path, header in group.hunks if (path, header) not in present]
        named.update(real)
        if real:
            kept.append(GroupRef(group.key, real, group.pending))
    loose = tuple(sorted(present - named))
    if loose:
        problems.append(f"{len(loose)} change(s) in changes.patch are not listed in proposal.md; they are shown under '{proposal.NO_ID}'.")
        existing = next((i for i, g in enumerate(kept) if g.key == proposal.NO_ID), None)
        if existing is None:
            kept.append(GroupRef(proposal.NO_ID, loose, False))
        else:
            kept[existing] = GroupRef(proposal.NO_ID, kept[existing].hunks + loose, False)
    return kept, problems


def subpatch(parsed, group):
    """The patch text holding only this group's hunks, for `git apply -R` to take them back out."""
    wanted = set(group.hunks)
    out = []
    for file in parsed.files:
        chosen = [h for h in file.hunks if (file.path, h.header) in wanted]
        if chosen or (not file.hunks and (file.path, "") in wanted):
            out.append(file.head + "".join(h.text for h in chosen))
    if not out:
        raise ReviewError(f"'{group.key}' holds no change in the patch.")
    return "".join(out)


# ------------------------------------------------------------------ accepting a pending decision

def _eol(text):
    return "\r\n" if "\r\n" in text else "\n"


def _last_content_index(lines, upto):
    """Index just past the last non-blank line before `upto`, so an insert does not land after a run of blanks."""
    i = upto
    while i > 0 and not lines[i - 1].strip():
        i -= 1
    return i


def _history_range(page, lines):
    """(heading index, end index) of the page's ## History section in `lines`, or None."""
    headings = sorted(page.headings, key=lambda h: h.line)
    for n, heading in enumerate(headings):
        if heading.level == 2 and heading.text.strip().lower() == schema.HISTORY_HEADING.lower():
            end = next((h.line - 1 for h in headings[n + 1:] if h.level <= 2), len(lines))
            return heading.line - 1, end
    return None


def _content_end(lines):
    return len(lines) - 1 if lines and lines[-1] == "" else len(lines)


def _add_credit(path, text, item_id, credit):
    """text with `credit` in the page's History: under #### <ID>, or directly under ## History for the page itself."""
    eol = _eol(text)
    lines = text.split("\n")
    lines = [line[:-1] if line.endswith("\r") else line for line in lines]
    page = parse.parse_page(path, "\n".join(lines))
    where = _history_range(page, lines)
    end_of_text = _content_end(lines)
    if where is None:
        block = ["", "## History", "", *( [f"#### {item_id}", ""] if item_id else []), credit]
        lines[end_of_text:end_of_text] = block
    elif not item_id:
        lines[where[0] + 1:where[0] + 1] = ["", credit]
    elif item_id in (entries := parse.history_items(page)):
        at = _last_content_index(lines, min(entries[item_id][1] - 1, end_of_text))
        lines[at:at] = ["", credit]
    else:
        at = _last_content_index(lines, min(where[1], end_of_text))
        lines[at:at] = ["", f"#### {item_id}", "", credit]
    return eol.join(lines)


def accept_pending(path, text, item_id, owner):
    """text with the item's Pending approval marker turned into the owner's own decision, and the reader credited.

    Returns (new text, reader handle, proposed date). The marker bullet becomes `- **Decided by:** @owner` where it
    stood; the credit goes to History. Raises ReviewError when the item carries no well-formed marker.
    """
    if not re.match(rf"^{schema.HANDLE}$", owner):
        raise ReviewError(f"'{owner}' is not a handle. Write it as @name.")
    page = parse.parse_page(path, text)
    bullet = next((b for b in page.bullets if b.label == schema.PENDING_LABEL and b.item == item_id and not b.generated), None)
    if bullet is None:
        raise ReviewError(f"{path} has no **Pending approval:** marker on {item_id or 'the page'}.")
    found = pending.parse_pending(page, bullet)
    if found.problem:
        raise ReviewError(f"{path}:{bullet.line}: the marker {found.problem}; fix it before accepting.")
    lines = text.split("\n")
    cr = "\r" if lines[bullet.line - 1].endswith("\r") else ""
    lines[bullet.line - 1] = f"- **Decided by:** {owner}{cr}"
    credit = f"**Credit:** {found.by} proposed this on {found.date}"
    return _add_credit(path, "\n".join(lines), item_id, credit), found.by, found.date


# ------------------------------------------------------------------ answer.md

def check_decisions(refs, decisions):
    """Every group decided once, with a legal outcome and, for a rejection or an edit, the owner's reason."""
    by_key = {}
    for d in decisions:
        key = d.get("group", "")
        if d.get("outcome") not in OUTCOMES:
            raise ReviewError(f"'{key}': outcome must be one of {', '.join(OUTCOMES)}, not '{d.get('outcome')}'.")
        if d["outcome"] in NEEDS_REASON and not str(d.get("reason") or "").strip():
            raise ReviewError(f"'{key}' is {d['outcome']} and needs the owner's reason in their own words; the reader will read it.")
        if key in by_key:
            raise ReviewError(f"'{key}' is decided twice.")
        by_key[key] = d
    known = {g.key for g in refs}
    unknown = sorted(set(by_key) - known)
    if unknown:
        raise ReviewError(f"These are not groups in the proposal: {', '.join(unknown)}.")
    missing = [g.key for g in refs if g.key not in by_key]
    if missing:
        raise ReviewError(f"These groups have no decision yet: {', '.join(missing)}. Decide each one; an answer that skips a group reads as accepted.")
    return by_key


_WORDS = {"accepted": "Accepted.", "rejected": "Rejected.", "edited": "Accepted with the owner's edit."}


def answer_markdown(note, refs, decisions, reviewer, today, branch, commit, base_short):
    """answer.md: per group the outcome, the owner's reason and the commit, then what the reader does next."""
    by_key = check_decisions(refs, decisions)
    lines = [f"# Answer: {note.title}", "",
             f"- **Reviewed by:** {reviewer}",
             f"- **Date:** {today}",
             f"- **Against:** your copy at {base_short}",
             f"- **Kept on:** branch {branch}, commit {commit}", ""]
    for group in refs:
        decision = by_key[group.key]
        lines += [f"## {group.key}", "", _WORDS[decision["outcome"]]]
        reason = str(decision.get("reason") or "").strip()
        if reason:
            lines += ["", reason]
        if decision.get("commit"):
            lines += ["", f"Commit: {decision['commit']}"]
        lines.append("")
    lines += ["## Next", "", "Publish a new copy and re-open to continue. Your drafts are not changed by this answer.", ""]
    return "\n".join(lines)
