"""A reader's changes as a patch an owner can apply, and the note that explains them. Pure: no disk, clock, git or network.

Two failures decide the shape. A patch that only looks like a patch (no base commit, binary bytes mangled, line
endings normalised) fails on the owner's side with nothing to say why, so the writer is exact: the text is split on
newlines alone, CRLF and a missing final newline survive, every file carries the blob hashes `git apply --3way`
needs, and a file that is not UTF-8 text is listed and never patched. And an invented reason is a Silent Fallback:
a change the reader did not explain reads "no reason given", not a sentence the tool made up.

The changed-file list comes from drafts.changed_files, the same decision the Drafts view makes, so the chip a
reader sees and the proposal they send cannot disagree. review.py reads what this module writes.
"""
import difflib
import hashlib
import re
from dataclasses import dataclass

from planner import drafts, parse, publish, schema, untrusted

CONTEXT = 3
NO_ID = "Not tied to an ID"
NO_REASON = "no reason given"
NULL_SHA = "0" * 40
FILE_MODE = "100644"
MAGIC = "# planner proposal"
NO_NEWLINE = "\\ No newline at end of file\n"
UNUSUAL_PATH = re.compile(r'[\x00-\x1f"\\`]')  # git would quote these, and the reviewer reads them inside Markdown
# A home folder on any system, whoever's it is: Unix and macOS homes, /root, macOS temp folders (they carry a per-login id),
# Windows drives with either slash in any case, WSL mounts, and UNC shares. Unix names stay case-sensitive so "/users/42" in
# API prose is not a hit. Exact strings (this user's home, the workspace) are checked as well.
_NAME = r"[^\s/\\`'\"<>)]"
HOME_PATH = re.compile(rf"(?:/Users/|/home/|/private/var/folders/|/var/folders/|(?i:[A-Za-z]:[\\/]+users[\\/]+|/mnt/[a-z]/users/)){_NAME}+"
                       rf"|/root(?=[/\s]|$)|\\\\{_NAME}+\\{_NAME}+")
_PAGE_ID_FORMS = re.compile(r"^(EPC-\d{3}|CAP-\d{3}|FLO-\d{3}|ADR-\d{4})$")
_ID_FORMS = (schema.ITEM_ID_RE, schema.GOAL_ID_RE, schema.CONSTRAINT_ID_RE, schema.SOURCE_ID_RE, _PAGE_ID_FORMS)


class ProposalError(Exception):
    """The proposal cannot be written as asked; the message says what to change."""


def check_path(path):
    """A path a proposal may carry: pages and sources only (untrusted.py). Hooks, workflows, Claude settings, programs, links
    and git's own folder are never a reader's to send, and the owner's review would apply them as the owner."""
    try:
        untrusted.check_proposal_path(path)
    except untrusted.Refused as exc:
        raise ProposalError(str(exc)) from exc
    if UNUSUAL_PATH.search(path):
        raise ProposalError(f"'{path}' has a quote, backslash, backtick or control character in its name. Rename it and propose again.")
    return path


def blob_sha(data):
    """git's own hash of a file's bytes, so `git apply --3way` can find the base version in the owner's repo."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()  # an identifier, not a secret


def split_lines(text):
    """Lines that keep their own endings, split on newline alone (str.splitlines would also split on form feeds)."""
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def is_id(token):
    return any(form.match(token) for form in _ID_FORMS)


def ids_by_line(path, text):
    """[ID] with one entry per line (index n-1 for line n): the vault ID the line sits under, "" when none.

    An item's heading owns its lines until a heading of the same or higher level; before that, and under headings
    that are not items, a page's own ID owns them.
    """
    total = text.count("\n") + 1
    if not path.endswith(".md"):
        return [""] * total
    page = parse.parse_page(path, text)
    page_id = str(page.meta.get("id") or "")
    out, current, level, heading_at = [], page_id, 0, 0
    headings = sorted(page.headings, key=lambda h: h.line)
    for line_no in range(1, total + 1):
        while heading_at < len(headings) and headings[heading_at].line <= line_no:
            heading = headings[heading_at]
            heading_at += 1
            first = heading.text.split()[0] if heading.text.split() else ""
            if is_id(first):
                current, level = first, heading.level
            elif current != page_id and heading.level <= level:
                current, level = page_id, 0
        out.append(current)
    return out


@dataclass(frozen=True)
class Hunk:
    header: str  # "@@ -10,4 +10,5 @@"
    lines: tuple  # prefixed lines, each ending in a newline (a no-newline marker is its own entry)
    ids: tuple  # the vault IDs its changed lines sit under, in order

    def text(self):
        return self.header + "\n" + "".join(self.lines)


@dataclass(frozen=True)
class FilePatch:
    path: str
    status: str  # drafts.ADDED, REMOVED or CHANGED
    head: str  # the lines from `diff --git` to the last header line
    hunks: tuple

    def text(self):
        return self.head + "".join(hunk.text() for hunk in self.hunks)


def _range(start, length):
    """difflib's own range format, which is the one git writes."""
    beginning = start + 1
    if length == 1:
        return str(beginning)
    if not length:
        beginning -= 1
    return f"{beginning},{length}"


def _row(prefix, line):
    return prefix + line if line.endswith("\n") else prefix + line + "\n" + NO_NEWLINE


def _hunk(group, old, new, old_ids, new_ids):
    first, last = group[0], group[-1]
    header = f"@@ -{_range(first[1], last[2] - first[1])} +{_range(first[3], last[4] - first[3])} @@"
    rows, ids = [], []
    for tag, i1, i2, j1, j2 in group:
        if tag == "equal":
            rows += [_row(" ", line) for line in old[i1:i2]]
            continue
        if tag in ("replace", "delete"):
            rows += [_row("-", line) for line in old[i1:i2]]
            ids += old_ids[i1:i2]
        if tag in ("replace", "insert"):
            rows += [_row("+", line) for line in new[j1:j2]]
            ids += new_ids[j1:j2]
    return Hunk(header, tuple(rows), tuple(dict.fromkeys(i for i in ids if i)))


def _head(path, status, old, new, with_hunks):
    shown = path + "\t" if " " in path else path  # git ends a name containing a space with a tab
    lines = [f"diff --git a/{path} b/{path}\n"]
    old_sha = blob_sha(old) if old is not None else NULL_SHA
    new_sha = blob_sha(new) if new is not None else NULL_SHA
    if status == drafts.ADDED:
        lines += [f"new file mode {FILE_MODE}\n", f"index {old_sha}..{new_sha}\n"]
    elif status == drafts.REMOVED:
        lines += [f"deleted file mode {FILE_MODE}\n", f"index {old_sha}..{new_sha}\n"]
    else:
        lines.append(f"index {old_sha}..{new_sha} {FILE_MODE}\n")
    if with_hunks:
        lines.append("--- /dev/null\n" if status == drafts.ADDED else f"--- a/{shown}\n")
        lines.append("+++ /dev/null\n" if status == drafts.REMOVED else f"+++ b/{shown}\n")
    return "".join(lines)


def file_patch(path, status, old, new):
    """The patch section for one text file; `old` and `new` are bytes or None (a new or a deleted file)."""
    check_path(path)
    old_text = old.decode("utf-8") if old is not None else ""
    new_text = new.decode("utf-8") if new is not None else ""
    before, after = split_lines(old_text), split_lines(new_text)
    hunks = ()
    if before or after:
        matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
        old_ids, new_ids = ids_by_line(path, old_text), ids_by_line(path, new_text)
        hunks = tuple(_hunk(group, before, after, old_ids, new_ids) for group in matcher.get_grouped_opcodes(CONTEXT))
    return FilePatch(path, status, _head(path, status, old, new, bool(hunks)), hunks)


def preamble(base_commit, initiative):
    return f"{MAGIC}\n# base: {base_commit}\n# initiative: {initiative}\n"


@dataclass(frozen=True)
class Built:
    patch: str
    files: tuple  # FilePatch, in path order
    binaries: tuple  # (status, path) of files that are not text and so are not patched


def build(baseline, working, base_commit, initiative):
    """The proposal's patch from {path: bytes} baseline and working copies, through drafts.changed_files."""
    files, binaries = [], []
    for path, status, old, new, binary in drafts.changed_files(baseline, working):
        check_path(path)
        if binary:
            binaries.append((status, path))
            continue
        files.append(file_patch(path, status, old, new))
    patch = preamble(base_commit, initiative) + "".join(f.text() for f in files)
    return Built(patch, tuple(files), tuple(binaries))


# ------------------------------------------------------------------ groups

@dataclass(frozen=True)
class Group:
    key: str  # a vault ID, or NO_ID
    hunks: tuple  # (path, header, also-touches IDs)
    pending: bool


def group_of(hunk, pending_ids):
    """The group a hunk belongs to: a pending item it touches first, else the first ID its changed lines sit under."""
    for item in hunk.ids:
        if item in pending_ids:
            return item
    return hunk.ids[0] if hunk.ids else NO_ID


def groups(files, pending_ids):
    """Groups keyed by the vault IDs the diff touches, pending decisions first, then in order of first appearance."""
    order, held = [], {}
    for patch in files:
        for hunk in patch.hunks:
            key = group_of(hunk, pending_ids)
            if key not in held:
                held[key] = []
                order.append(key)
            held[key].append((patch.path, hunk.header, tuple(i for i in hunk.ids if i != key)))
        if not patch.hunks:  # an empty file added or removed has no hunk; it still belongs somewhere
            held.setdefault(NO_ID, [])
            if NO_ID not in order:
                order.append(NO_ID)
            held[NO_ID].append((patch.path, "", ()))
    ranked = sorted(order, key=lambda key: (key not in pending_ids, order.index(key)))
    return [Group(key, tuple(held[key]), key in pending_ids) for key in ranked]


# ------------------------------------------------------------------ proposal.md

def check_phrase(check):
    errors, warnings = check["errors"], check["warnings"]
    text = f"{errors} errors, {warnings} warnings"
    new = check.get("new") or []
    return text + (f" (new: {', '.join(new)})" if new else "")


def _bullets(group):
    lines = []
    for path, header, also in group.hunks:
        where = f"`{path}` {header}".rstrip()
        lines.append(f"- Changes: {where}" + (f" (also touches {', '.join(also)})" if also else ""))
    return lines


def _group_block(group, why, heading, extra):
    block = [f"### {heading}", "", why or NO_REASON]
    if extra:
        block += ["", extra]
    return block + ["", *_bullets(group), ""]


def files_line(files, binaries):
    count = {s: sum(1 for f in files if f.status == s) for s in (drafts.CHANGED, drafts.ADDED, drafts.REMOVED)}
    tail = "; binary files not included" if binaries else ""
    return f"({count[drafts.CHANGED]} changed, {count[drafts.ADDED]} added, {count[drafts.REMOVED]} removed{tail})"


def render_markdown(note):
    """proposal.md from a dict holding title, author, base, written, check, pending, groups, whys, files, binaries.

    `pending` maps an item ID to {"heading", "by", "date", "session"}; `whys` maps a group key to the reader's reason.
    """
    check = note["check"]
    base = note["base"]
    flagged = " Errors are listed first; they did not stop this proposal." if check["errors"] else ""
    lines = [f"# Proposal: {note['title']}", "",
             f"- **Author:** {note['author']}",
             f"- **Base:** {base['initiative']} at {base['short']}, published {base['date']} by {base['owner']}",
             f"- **Written:** {note['written']}",
             f"- **Check on this copy:** {check_phrase(check)}.{flagged}", ""]
    if check["errors"]:
        lines += ["## Check errors on this copy", ""] + [f"- {e}" for e in check["error_lines"]] + [""]
    pending_groups = [g for g in note["groups"] if g.pending]
    other_groups = [g for g in note["groups"] if not g.pending]
    if pending_groups:
        lines += ["## Pending decisions (need your approval)", ""]
        for group in pending_groups:
            item = note["pending"][group.key]
            marker = f"Pending approval: {item['by']}, {item['date']}." + (f" Session: {item['session']}." if item.get("session") else "")
            lines += _group_block(group, note["whys"].get(group.key), f"{item['heading']}: decided", marker)
    if other_groups:
        lines += ["## Other changes and why", ""]
        for group in other_groups:
            lines += _group_block(group, note["whys"].get(group.key), group.key, "")
    lines += ["## Files", "", files_line(note["files"], note["binaries"]), ""]
    lines += [f"- {f.status}: {f.path}" for f in note["files"]]
    lines += [f"- binary file {'changed' if s == drafts.CHANGED else s}: {p}, not included" for s, p in note["binaries"]]
    return "\n".join(lines).rstrip() + "\n"


# ------------------------------------------------------------------ privacy

def privacy_hits(texts, forbidden):
    """[(name, line number, line)] where a text holds a forbidden string or any home folder path.

    `forbidden` is exact strings this proposal must never carry: this user's home folder, the workspace, the
    source it was opened from, the planner program. Empty strings are skipped, not matched everywhere.
    """
    needles = [f for f in forbidden if f]
    hits = []
    for name, text in texts.items():
        for number, line in enumerate(text.split("\n"), start=1):
            if any(needle in line for needle in needles) or HOME_PATH.search(line):
                hits.append((name, number, line.strip()[:200]))
    return hits


def hide_home(text, home):
    """The text with a home folder replaced by <home>, for the reader who agreed to it."""
    return text.replace(home, "<home>") if home else text
