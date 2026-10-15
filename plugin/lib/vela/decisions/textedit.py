"""The page edits every Task 15 apply kind makes, written once: escape the lead's words, find a section, add a table
row, a `## Changes` row, a `## History` bullet or a capture's mark, and number a new ID. Pure: text in, text out.

The Violation this exists to prevent is a Distributed Monolith across the kinds. Each kind (`add`, `marks`, `agenda`,
`override`, `defer`, `resolve`) writes into the same few places of the same pages; with its own copy of "append a
Changes row" or "put the mark before the block ID", one kind's fix would leave the others writing the old grammar.

Escaping (plan 9.1). The lead's words are copied verbatim, so a word that is also the vault's syntax would break the
page around it: a `|` splits a table cell (and the check then reads a row with the wrong columns), a newline ends a
bullet or a row, a `**` can be read as the start of a fact label. So, in a table cell, `|` becomes `\\|` (the escape
CONVENTIONS gives for a pipe in a table, which `parse.split_row` reads back); in a cell or a bullet a newline becomes
`<br>` and `**` becomes `\\*\\*`. A wikilink stays a link (its pipe escaped in a cell, as CONVENTIONS asks). Nothing else
changes: `unescape` gives back the words exactly as captured, which is what the tests pin.

Numbering. A new ID is `ids.next_id` over every text the vault view holds (each page as staged, so an ID an earlier
item of the same file took is counted) plus `branch_texts`, the IDs on `main` and every open session branch, which
the shell reads from git (`edge/idgit.py`) and attaches to the view with `attach`. In a reader copy there are no
branches and the list is empty; a view with no list attached at all is a vela bug, refused rather than numbered from
this tree alone, because a number another open branch holds is the collision this exists to prevent.
"""
import re

from vela import ids, parse, say

BR = "<br>"
_NEWLINE = re.compile(r"\r\n|\r|\n")
_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")
_BLOCK_ID = re.compile(r"\s\^c(?P<n>\d+)\s*$")
_HEADING = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.+?)\s*$")
HEADING_FORBIDDEN = set("#|^:%[]")
HEADING_MAX_WORDS = 6


# --- the view's context ---------------------------------------------------------------------------------------------

def attach(view, today, branch_texts):
    """Give a `decisions.Staged` view what the pure kinds can't read themselves: today's date and the texts of the
    other branches' IDs. The shell calls this before `decisions.plan`."""
    view.today = str(today)
    view.branch_texts = list(branch_texts)
    return view


def _bug(what):
    return say.Refusal("apply-context", "Something went wrong on my side, so I filed nothing.",
                       f"vela bug: the vault view has no {what} attached (textedit.attach); file it with vela apply "
                       "or vela add, which attach it.", override="none: this is a fault in vela, not a rule")


def context_refusals(view):
    missing = [name for name in ("today", "branch_texts") if getattr(view, name, None) is None]
    return [_bug(" or ".join(missing))] if missing else []


def today(view):
    return getattr(view, "today", None)


# --- escaping the lead's words --------------------------------------------------------------------------------------

def inline(words):
    """The words as a bullet value: one line, no `**` that could be read as a label."""
    return _NEWLINE.sub(BR, str(words)).replace("**", "\\*\\*")


def cell(words):
    """The words as a table cell: `inline`, and every pipe escaped (a link's label pipe too)."""
    return _UNESCAPED_PIPE.sub("\\\\|", inline(words))


def unescape(text):
    """The words as they were before `cell` or `inline` (and after `parse.split_row`, which reads `\\|` back)."""
    return str(text).replace("\\|", "|").replace("\\*\\*", "**").replace(BR, "\n")


def heading_problem(name):
    """Why `name` can't be an item heading's short name (CONVENTIONS "Links and headings"), or None."""
    name = (name or "").strip()
    if not name:
        return "it is empty"
    bad = sorted(HEADING_FORBIDDEN & set(name))
    if bad:
        return f"it holds {' '.join(bad)}, which a heading can't"
    if len(name.split()) > HEADING_MAX_WORDS:
        return f"it is {len(name.split())} words; a heading holds at most {HEADING_MAX_WORDS}"
    return None


def slug(words):
    return re.sub(r"[^a-z0-9]+", "-", str(words).lower()).strip("-")[:60].strip("-") or "untitled"


# --- reading the view -----------------------------------------------------------------------------------------------

def texts(view):
    """{path: text} of every page as the view sees it (earlier items' writes included)."""
    found = {page.path: view.text(page.path) for page in view.model.pages}
    found.update(view.pending)
    return {path: text for path, text in found.items() if text is not None}


def next_id(view, prefix):
    return ids.next_id(prefix, list(texts(view).values()) + list(getattr(view, "branch_texts", None) or ()))


def page_path(view, name):
    """The path of the page with this basename (no `.md`), as the view sees it, or None."""
    for path in texts(view):
        if path.rsplit("/", 1)[-1][:-3].lower() == name.lower():
            return path
    return None


def basename(path):
    return path.rsplit("/", 1)[-1][:-3]


def meta_of(text):
    return parse.split_frontmatter(text)[0] or {}


def find(view, ident):
    """(path, heading text or None) for an ID: an item's `### <ID> <name>` heading anywhere, else a page whose `id`
    is it (heading None). None when the view holds neither."""
    pattern = re.compile(rf"^#{{2,4}} {re.escape(ident)}(?: .*)?$")
    pages = texts(view)
    for path, text in pages.items():
        for line in text.split("\n"):
            if pattern.match(line.strip()):
                return path, line.strip().lstrip("#").strip()
    for path, text in pages.items():
        if str(meta_of(text).get("id", "")) == ident:
            return path, None
    return None


def title_heading(text):
    """The page's `# ` heading text, the anchor a page-level mark links."""
    for line in text.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return str(meta_of(text).get("title") or "")


def link(view, ident, cell_link=False):
    """`[[page#heading|ID]]` (or `[[page|ID]]` for a page ID), None when the view doesn't hold it."""
    found = find(view, ident)
    if found is None:
        return None
    path, heading = found
    bar = "\\|" if cell_link else "|"
    return f"[[{basename(path)}#{heading}{bar}{ident}]]" if heading else f"[[{basename(path)}{bar}{ident}]]"


def name_of(view, ident):
    """What the lead hears an ID called: its heading's name, else its page's title, else a plain phrase."""
    found = find(view, ident)
    if found is None:
        return "that item"
    path, heading = found
    if heading:
        return heading[len(ident):].strip() or "that item"
    return str(meta_of(texts(view)[path]).get("title") or "that page")


def capture_link(record_id, ref):
    return f"[[{record_id}#^c{str(ref).lstrip('^c')}]]"


# --- editing text ---------------------------------------------------------------------------------------------------

def _lines(text):
    return text.rstrip("\n").split("\n")


def _join(lines):
    return "\n".join(lines).rstrip("\n") + "\n"


def section_end(lines, start, level):
    """The index after the last line of the section whose heading is at `start`."""
    for index in range(start + 1, len(lines)):
        found = _HEADING.match(lines[index])
        if found and len(found["hashes"]) <= level and not lines[index].startswith("<!--"):
            return index
    return len(lines)


def find_heading(lines, text, level):
    want = f"{'#' * level} {text}".strip().lower()
    return next((i for i, line in enumerate(lines) if line.strip().lower() == want), None)


def insert_block(text, heading, block, level=2, before=None):
    """`block` (lines) added at the end of the `heading` section, a blank line apart. A missing section is made: before
    the first heading named in `before` that the page has, else at the end of the page."""
    lines = _lines(text)
    start = find_heading(lines, heading, level)
    if start is None:
        at = next((i for name in (before or ()) for i in [find_heading(lines, name, level)] if i is not None), None)
        new = [f"{'#' * level} {heading}", "", *block, ""]
        if at is None:
            return _join(lines + [""] + new)
        return _join(lines[:at] + new + lines[at:])
    end = section_end(lines, start, level)
    body_end = end
    while body_end > start + 1 and not lines[body_end - 1].strip():
        body_end -= 1
    tail = [""] if end < len(lines) else []
    return _join(lines[:body_end] + [""] + list(block) + tail + lines[end:])


def table_rows_end(lines, header_index):
    end = header_index + 1
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        end += 1
    return end


def find_table(lines, first_cells):
    """The index of the header row whose first cells are `first_cells`, or None."""
    want = [c.lower() for c in first_cells]
    for index, line in enumerate(lines):
        if line.lstrip().startswith("|"):
            cells = [c.lower() for c in parse.split_row(line)]
            if cells[:len(want)] == want:
                return index
    return None


def add_row(text, first_cells, row):
    """`text` with `row` appended to the table whose header starts with `first_cells`, or None when there is none."""
    lines = _lines(text)
    header = find_table(lines, first_cells)
    if header is None:
        return None
    end = table_rows_end(lines, header)
    return _join(lines[:end] + [row] + lines[end:])


def heading_above(text, first_cells):
    """The text of the nearest heading above the table whose header starts with `first_cells`."""
    lines = _lines(text)
    header = find_table(lines, first_cells) or 0
    for line in reversed(lines[:header]):
        found = _HEADING.match(line)
        if found:
            return found["text"]
    return title_heading(text)


def row(*cells):
    """A table row; an empty cell is written `| |`, as the vault's tables leave a column blank."""
    return "|" + "".join(f" {c} |" if str(c) else " |" for c in cells)


CHANGES = "Changes"


def add_change(record_text, ident, before, after, source):
    """The record with one `## Changes` row, `| ID | From | To | Source |`, the table made when the record has none."""
    line = row(ident, before or "-", after, source)
    added = add_row(record_text, ("ID", "From", "To", "Source"), line)
    if added is not None:
        return added
    return insert_block(record_text, CHANGES, ["| ID | From | To | Source |", "|---|---|---|---|", line])


def add_history(text, bullet, item_id=""):
    """`text` with `bullet` under `## History`: under `#### <item_id>` inside it for an item, directly under the heading
    for the page (CONVENTIONS "Pages", "History at the end")."""
    lines = _lines(text)
    start = find_heading(lines, "History", 2)
    if start is None:
        lines += ["", "## History"]
        start = len(lines) - 1
    end = section_end(lines, start, 2)
    if not item_id:
        at = start + 1
        while at < end and not lines[at].strip():
            at += 1
        if at < end and lines[at].startswith("- "):
            while at < end and lines[at].startswith("- "):
                at += 1
            return _join(lines[:at] + [bullet] + lines[at:])
        tail = [""] if at < len(lines) else []
        return _join(lines[:start + 1] + ["", bullet] + tail + lines[at:])
    sub = next((i for i in range(start + 1, end) if lines[i].strip() == f"#### {item_id}"), None)
    if sub is None:
        body_end = end
        while body_end > start + 1 and not lines[body_end - 1].strip():
            body_end -= 1
        tail = [""] if end < len(lines) else []
        return _join(lines[:body_end] + ["", f"#### {item_id}", "", bullet] + tail + lines[end:])
    sub_end = section_end(lines, sub, 4)
    body_end = sub_end
    while body_end > sub + 1 and not lines[body_end - 1].strip():
        body_end -= 1
    if body_end == sub + 1:
        return _join(lines[:sub + 1] + ["", bullet] + lines[sub + 1:])
    return _join(lines[:body_end] + [bullet] + lines[body_end:])


def capture_line(record_text, ref):
    """(index, line) of the capture `ref` names, or (None, None)."""
    number = str(ref).strip().lstrip("^").lstrip("c")
    lines = _lines(record_text)
    for index, line in enumerate(lines):
        found = _BLOCK_ID.search(line)
        if found and line.lstrip().startswith("- [") and int(found["n"]) == int(number or -1):
            return index, line
    return None, None


def existing_mark(line):
    found = re.match(r"^- \[[\w-]+\] \([^)]*\) .*? → (?P<mark>.*?) \^c\d+\s*$", line.strip())
    return found["mark"].strip() if found else None


def write_mark(record_text, ref, mark_text):
    """The record with ` → <mark_text>` written into capture `ref`'s line before its `^cNN` (CONVENTIONS "Sessions": the
    block ID is the last token on the line), or None when the capture is missing or already has a mark."""
    index, line = capture_line(record_text, ref)
    if index is None or existing_mark(line) is not None:
        return None
    found = _BLOCK_ID.search(line)
    lines = _lines(record_text)
    lines[index] = f"{line[:found.start()].rstrip()} → {mark_text} {line[found.start():].strip()}"
    return _join(lines)


def keep_mark(page, heading, ident, state):
    return f"keep: [[{page}#{heading}|{ident}]] ({state})"


def mark_if_unmarked(record_text, ref, mark_text):
    """`write_mark`, leaving a capture that already carries a mark as it is (an earlier mode's mark is kept)."""
    if not ref:
        return record_text
    marked = write_mark(record_text, ref, mark_text)
    return record_text if marked is None else marked


# --- refusals every type shares -------------------------------------------------------------------------------------

def refusal(rule, plain, fix, override="none: write it by hand in the grammar vela conventions prints, and tell the "
                                        "lead"):
    return say.Refusal(rule, plain, fix, override=override)


def id_refusal(view, ident, prefix):
    """A refusal when an item's own `id` is not a `<prefix>-n` ID, or is already used; None when it is free."""
    if not re.fullmatch(rf"{prefix}-\d+", str(ident)):
        return refusal("add-id", "That number isn't in the form I expect, so I filed nothing.",
                       f"id {ident!r} is not a {prefix}- ID; leave id out and vela numbers it.")
    used, _ = ids.used_numbers(prefix, list(texts(view).values()) + list(getattr(view, "branch_texts", None) or ()))
    if int(str(ident).split("-")[1]) in used:
        return refusal("add-id-taken", "That number is already taken, so I filed nothing.",
                       f"{ident} is used in this vault or on an open session branch; leave id out and vela numbers it.",
                       override="none: IDs are never reused")
    return None


def heading_refusal(name):
    problem = heading_problem(name)
    if problem is None:
        return None
    return refusal("add-heading", "That name won't work as a heading, so I filed nothing.",
                   f"The short name {name!r} can't be a heading: {problem}. Give at most six words with none of "
                   "# | ^ : % [ ].", override="none: rename it; the heading is the item's link target")


def quote(record, ref):
    """The words a capture quotes (all its words when it quotes none), or None when the record doesn't hold it."""
    capture = record.capture(ref) if ref else None
    return capture.quote if capture is not None else None


def capture_refusals(item, record, field="capture"):
    from vela.decisions import consent  # consent imports schema, which imports nothing of ours: no cycle, but late
    ref = item.get(field)
    if not ref:
        return []
    found = consent.exists(ref, record)
    return [found] if found else []


def new_id(item, view, prefix):
    return item.get("id") or next_id(view, prefix)


def record_writes(record, view, new_text):
    from vela.decisions.schema import Write
    return [Write(record.path, new_text)] if new_text != (view.text(record.path) or record.text) else []


def record_text(record, view):
    return view.text(record.path) or record.text


def yaml_value(text):
    """A frontmatter value, quoted when it holds a character YAML would read as syntax (CONVENTIONS "Frontmatter":
    quote any value that holds a colon or starts with `@`)."""
    text = str(text)
    if any(c in text for c in ':#"@{}[],&*!|>%\'') or text != text.strip():
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text
