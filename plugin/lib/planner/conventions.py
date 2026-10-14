"""CONVENTIONS.md read one section at a time, and its check-codes table kept equal to `schema.CODES`.

Two Violations shape this module. A skill that says "read CONVENTIONS.md" for one rule makes the model carry a
21,000-word file into every session (Computational Friction in the reader's head), so `section` returns one heading
and what sits under it, and `near` offers a handful of headings instead of falling back to the whole file (that
fallback would be a Silent Fallback: the reader asked for one rule and quietly got all of them). And a hand-written
copy of the codes table drifts from `schema.CODES` (Fossil Comments in table form), so `with_codes_table` rewrites
the `check-codes` block from the schema and a test holds every copy to it.

Pure: text in, text out. `commands/conventions.py` reads the file and prints; `tools/conventions_codes.py` writes.
"""
import difflib
import re
from dataclasses import dataclass

from planner import render, schema

HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
CODES_BLOCK = "check-codes"
NEAR_LIMIT = 5
# Words too common to say which section a reader means ("the ledger" means the ledger).
COMMON = frozenset({"a", "an", "and", "the", "of", "in", "on", "to", "for", "or", "out", "by", "with"})


@dataclass(frozen=True)
class Section:
    title: str
    level: int
    line: int  # 1-based line of the heading
    text: str  # the heading line and everything under it, subsections included

    @property
    def words(self):
        return len(self.text.split())


def headings(text):
    """(line index, level, title) for each Markdown heading outside fenced code. CONVENTIONS shows example pages in
    fences, and their `# Title` and `## Overrides` lines are examples, not sections."""
    out, fence = [], None
    for index, line in enumerate(text.split("\n")):
        opened = FENCE.match(line)
        if fence:
            if opened and opened.group(1)[0] == fence[0] and len(opened.group(1)) >= len(fence) \
                    and not line.strip()[len(opened.group(1)):].strip():
                fence = None
            continue
        if opened:
            fence = opened.group(1)
            continue
        found = HEADING.match(line)
        if found:
            out.append((index, len(found.group(1)), found.group(2)))
    return out


def sections(text):
    """Every section, in file order. A section runs to the next heading of its level or higher, except the document
    title: its section is the opening paragraph only, because the title holds the whole file and printing the whole
    file is what reading by section exists to stop."""
    lines = text.split("\n")
    found = headings(text)
    out = []
    for at, (index, level, title) in enumerate(found):
        later = found[at + 1:]
        if level == 1:
            end = later[0][0] if later else len(lines)
        else:
            end = next((i for i, lvl, _ in later if lvl <= level), len(lines))
        out.append(Section(title, level, index + 1, "\n".join(lines[index:end]).rstrip()))
    return out


def key(name):
    """How a heading is compared: case and spacing ignored, and a leading `## ` a caller copied along with it."""
    return " ".join(name.strip().lstrip("#").split()).casefold()


def section(all_sections, name):
    """The section whose heading is exactly `name` (as `key` compares), or None."""
    wanted = key(name)
    return next((s for s in all_sections if key(s.title) == wanted), None)


def near(all_sections, name, limit=NEAR_LIMIT):
    """Up to `limit` headings close to `name`: spelling-close first, then headings that hold its words."""
    wanted = key(name)
    titles = {}
    for s in all_sections:
        titles.setdefault(key(s.title), s.title)
    close = difflib.get_close_matches(wanted, list(titles), n=limit, cutoff=0.6)
    words = [w for w in re.findall(r"[\w-]+", wanted) if w not in COMMON]
    holding = [k for k in titles if words and all(w in k.split() or w in k for w in words)]
    some = [k for k in titles if any(w in k.split() for w in words)]
    out = []
    for k in close + holding + some:
        if k not in out:
            out.append(k)
    return [titles[k] for k in out[:limit]]


# ------------------------------------------------------------ the check-codes block

def code_order(code):
    """E303 beside W303: a rule and its by-override warning are read together."""
    return int(code[1:]), code[0]


def codes_table(codes=None):
    """The `check-codes` block's content: one `| code | meaning |` row per code, in code order."""
    codes = schema.CODES if codes is None else codes
    rows = [render.row(code, render.cell(codes[code])) for code in sorted(codes, key=code_order)]
    return "\n".join(["| Code | Finding |", "|---|---|"] + rows)


def codes_block(codes=None):
    content = codes_table(codes)
    return "\n".join([render.OPEN.format(name=CODES_BLOCK, sha=render.block_hash(content)), content,
                      render.CLOSE.format(name=CODES_BLOCK)])


class NoCodesBlock(ValueError):
    """The file has no `check-codes` block to rewrite."""


def with_codes_table(text, codes=None):
    """`text` with its `check-codes` block rewritten from the schema. Raises NoCodesBlock when the markers are missing,
    rather than appending a table somewhere the reader does not look."""
    pattern = re.compile(r"^<!-- generated:" + CODES_BLOCK + r" sha=[0-9a-f]{8}: do not edit, run planner render -->\n"
                         r".*?^<!-- /generated:" + CODES_BLOCK + r" -->$", re.M | re.S)
    if not pattern.search(text):
        raise NoCodesBlock(f"no <!-- generated:{CODES_BLOCK} ... --> block")
    block = codes_block(codes)
    return pattern.sub(lambda _: block, text, count=1)
