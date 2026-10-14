"""Text to pages. Pure: takes a path and its text, returns a Page.

Nothing here reads the disk, the clock or the network.
"""
import datetime
import re
from dataclasses import dataclass, field

import yaml

from vela import schema

WIKILINK = re.compile(r"\[\[([^\]]+?)\]\]")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
BULLET = re.compile(r"^- \*\*([^*:]+):\*\*\s*(.*)$")
# A backtick fence has no backtick after its opening run, so "```a``` text" is a paragraph with inline code, not a fence.
FENCE = re.compile(r"^\s*(`{3,}(?=[^`]*$)|~{3,})\s*([A-Za-z]*)")
CODE_SPAN = re.compile(r"`[^`]*`")
BLOCK_ID = re.compile(r"\s\^([A-Za-z0-9-]+)\s*$")
TABLE_SEPARATOR = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
# The one copy of the marker's words. render.OPEN writes it, MARKER_OPEN reads it, and conventions and viewer match it:
# a writer and a reader holding two copies would drift apart silently, and every block would stop being a block.
MARKER_TEXT = "do not edit, run planner render"
MARKER_OPEN = re.compile(r"^<!-- generated:([a-z0-9-]+) sha=([0-9a-f]{8}): " + re.escape(MARKER_TEXT) + r" -->$")
MARKER_CLOSE = re.compile(r"^<!-- /generated:([a-z0-9-]+) -->$")
MARKER_ANY = re.compile(r"^\s*<!--\s*/?generated")


def closes_fence(raw, marker):
    """True when `raw` closes a fence opened with `marker`: nothing but that fence character, at least as many."""
    stripped = raw.strip()
    return len(stripped) >= len(marker) and stripped == marker[0] * len(stripped)


def normalize_text(text):
    """A page's text as every reader sees it: no byte-order mark, newlines as \\n."""
    return text.lstrip("\ufeff").replace("\r\n", "\n")


def lines_of(text):
    """The page's lines, split on newline alone. str.splitlines also breaks on form feed, NEL, U+2028 and U+2029,
    so a line number counted with it drifts from the one parse and the rules report."""
    return normalize_text(text).split("\n")


@dataclass(frozen=True)
class Link:
    target: str  # basename, "" for a same-page link
    anchor: str  # heading text or "^blockid", "" if none
    label: str
    line: int


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    line: int


@dataclass(frozen=True)
class Bullet:
    label: str
    value: str
    line: int
    links: tuple
    item: str  # ID of the enclosing ### item section, "" at page level
    generated: bool


@dataclass(frozen=True)
class Table:
    header: tuple
    rows: tuple  # tuple of tuples of cell text
    line: int  # line of the header row
    row_lines: tuple
    generated: bool


@dataclass(frozen=True)
class Diagram:
    kind: str
    lines: tuple
    line: int  # line of the opening fence


@dataclass(frozen=True)
class Block:
    name: str
    sha: str
    content: str
    start: int  # line of the opening marker
    end: int  # line of the closing marker


@dataclass(frozen=True)
class ParseError:
    code: str
    line: int
    message: str
    fix: str


@dataclass
class Page:
    path: str
    name: str
    text: str
    meta: dict = field(default_factory=dict)
    headings: list = field(default_factory=list)
    links: list = field(default_factory=list)
    bullets: list = field(default_factory=list)
    tables: list = field(default_factory=list)
    diagrams: list = field(default_factory=list)
    blocks: list = field(default_factory=list)
    block_ids: set = field(default_factory=set)
    errors: list = field(default_factory=list)

    @property
    def type(self):
        return self.meta.get("type", "")

    @property
    def id(self):
        value = self.meta.get("id")
        return str(value) if isinstance(value, (str, int)) and not isinstance(value, bool) else ""

    def page_bullets(self, label):
        """Page-level fact bullets with this label, outside generated blocks."""
        return [b for b in self.bullets if b.label == label and not b.item and not b.generated]


KNOWN_LABELS = {label.lower(): label for label in (
    schema.CONTRACT_REQUIRED + schema.CONTRACT_OPTIONAL + schema.UNKNOWN_REQUIRED + schema.UNKNOWN_OPEN_REQUIRED
    + schema.UNKNOWN_RESOLVED_REQUIRED + schema.UNKNOWN_OPTIONAL + schema.RISK_REQUIRED + schema.RISK_OPTIONAL
    + schema.PAGE_LABELS + schema.SUBJECT_LABELS + schema.READING_LABELS)}


def canonical_label(label):
    """A known label in any letter case becomes its CONVENTIONS.md spelling."""
    return KNOWN_LABELS.get(label.lower(), label)


def parse_link(inner, line):
    inner = inner.replace("\\|", "|")
    target, _, label = inner.partition("|")
    name, _, anchor = target.partition("#")
    return Link(name.strip(), anchor.strip(), label.strip(), line)


def links_in(text, line):
    text = CODE_SPAN.sub("", text)
    return tuple(parse_link(m.group(1), line) for m in WIKILINK.finditer(text))


LINK_IN_ROW = re.compile(r"\[\[[^\[\]\n]*\]\]")


def protect_link_pipes(body):
    """A table row with every pipe inside a [[link]] hidden as NUL. A link's label pipe should be written \\| in a table;
    one written bare is still part of its link, as Obsidian reads it, not a column break (W329 names it)."""
    return LINK_IN_ROW.sub(lambda m: m.group(0).replace("\\|", "\x00").replace("|", "\x00"), body)


def split_row(line):
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells = protect_link_pipes(body.replace("\\|", "\x00")).split("|")
    return tuple(c.strip().replace("\x00", "|") for c in cells)


class _UniqueKeyLoader(yaml.SafeLoader):
    """yaml.safe_load keeps the last of two equal keys without a word, while fact bullets keep the first. Refusing the
    page says which line is the second one."""

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=True)
            if key in seen:
                raise yaml.constructor.ConstructorError(None, None, f"found a second '{key}:' line (a key may appear once)",
                                                        key_node.start_mark)
            seen.add(key)
        return super().construct_mapping(node, deep)


def _normalize_meta(meta):
    out = {}
    for key, value in meta.items():
        if isinstance(value, (datetime.date, datetime.datetime)):
            value = value.isoformat()[:10]
        out[str(key)] = value
    return out


def split_frontmatter(text):
    """Return (meta, body_start_line, error). body_start_line is 1-based."""
    lines = lines_of(text)
    if not lines or lines[0].strip() != "---":
        return {}, 1, ParseError("E101", 1, "This page has no frontmatter block.",
                                 "Add a --- block at the top with id, type and title.")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            raw = "\n".join(lines[1:i])
            try:
                meta = yaml.load(raw, Loader=_UniqueKeyLoader) if raw.strip() else None  # noqa: S506 (a SafeLoader subclass)
            except yaml.YAMLError as exc:
                mark = getattr(exc, "problem_mark", None)
                line = mark.line + 2 if mark else 1
                return {}, i + 2, ParseError("E102", line, f"The frontmatter is not valid YAML ({getattr(exc, 'problem', exc)}).",
                                             "Fix the YAML. Quote any value that contains a colon or starts with @, for example owner: \"@hl-lead\".")
            except (ValueError, TypeError) as exc:
                return {}, i + 2, ParseError("E102", 1, f"The frontmatter has a value YAML cannot read ({exc}).",
                                             "Fix the date. Write it as YYYY-MM-DD with a real month and day, for example 2026-11-20.")
            if meta is None:  # nothing between the --- lines, or only comments: the page declares nothing
                return {}, i + 2, ParseError("E101", 1, "The frontmatter block is empty.",
                                             "Fill the --- block with id, type and title.")
            if not isinstance(meta, dict):
                return {}, i + 2, ParseError("E102", 1, "The frontmatter is not a YAML mapping.",
                                             "Write the frontmatter as key: value lines.")
            return _normalize_meta(meta), i + 2, None
    return {}, 1, ParseError("E101", 1, "The frontmatter block is never closed.",
                             "Add a closing --- line after the frontmatter.")


def history_items(page):
    """{item ID: (first line, line after the last)} for each "#### <ID>" under the page's "## History"."""
    out, in_history, open_id, start = {}, False, None, 0
    total = len(page.text.split("\n")) + 1
    for heading in page.headings:
        if open_id and heading.level <= 4:
            out[open_id] = (start, heading.line)
            open_id = None
        if heading.level <= 2:
            in_history = heading.text.strip().lower() == schema.HISTORY_HEADING.lower()
            continue
        first = heading.text.split()[0] if heading.text.split() else ""
        if in_history and heading.level == 4 and schema.ITEM_ID_RE.match(first):
            open_id, start = first, heading.line
    if open_id:
        out[open_id] = (start, total)
    return out


def parse_page(path, text):
    """Parse one Markdown file. `path` is vault-relative with / separators."""
    text = normalize_text(text)
    name = path.rsplit("/", 1)[-1][:-3] if path.endswith(".md") else path.rsplit("/", 1)[-1]
    page = Page(path=path, name=name, text=text)
    meta, body_start, error = split_frontmatter(text)
    page.meta = meta
    if error:
        page.errors.append(error)
    lines = text.split("\n")
    _parse_body(page, lines, body_start)
    return page


def _parse_body(page, lines, body_start):
    in_fence, fence_kind, fence_start, fence_lines = None, "", 0, []
    item = ""
    in_history = False  # under the page's "## History": "#### <ID>" there gives the bullets below it to that item
    open_block = None  # (name, sha, start_line, content_lines)
    table = None  # (header, line, rows, row_lines, generated)
    i = body_start - 1
    while i < len(lines):
        raw = lines[i]
        n = i + 1
        i += 1
        if in_fence:
            if closes_fence(raw, in_fence):
                if fence_kind == "mermaid":
                    kind = next((l.split()[0] for l in fence_lines if l.strip() and not l.strip().startswith("%%")), "")
                    page.diagrams.append(Diagram(kind, tuple(fence_lines), fence_start))
                in_fence = None
            else:
                fence_lines.append(raw)
            if open_block:
                open_block[3].append(raw)
            continue
        fence = FENCE.match(raw)
        if fence:
            table = _close_table(page, table)
            in_fence, fence_kind, fence_start, fence_lines = fence.group(1), fence.group(2), n, []
            if open_block:
                open_block[3].append(raw)
            continue
        if MARKER_ANY.match(raw):
            table = _close_table(page, table)
            open_block = _marker(page, raw.strip(), n, open_block)
            continue
        if open_block:
            open_block[3].append(raw)
        generated = open_block is not None
        heading = HEADING.match(raw)
        if heading:
            table = _close_table(page, table)
            level, htext = len(heading.group(1)), heading.group(2)
            page.headings.append(Heading(level, htext, n))
            first = htext.split()[0] if htext.split() else ""
            if level <= 2:
                in_history = htext.strip().lower() == schema.HISTORY_HEADING.lower()
            if level == 3 and schema.ITEM_ID_RE.match(first):
                item = first
            elif level == 4 and in_history and schema.ITEM_ID_RE.match(first):
                item = first
            elif level <= 3:
                item = ""
            page.links.extend(links_in(htext, n))
            continue
        block_id = BLOCK_ID.search(raw)
        if block_id:
            page.block_ids.add(block_id.group(1))
        page.links.extend(links_in(raw, n))
        if raw.lstrip().startswith("|"):
            if table is None:
                table = [split_row(raw), n, [], [], generated, False]
            elif not table[5]:
                if TABLE_SEPARATOR.match(raw.strip()):
                    table[5] = True
                else:
                    table = [split_row(raw), n, [], [], generated, False]
            else:
                table[2].append(split_row(raw))
                table[3].append(n)
            continue
        table = _close_table(page, table)
        bullet = BULLET.match(raw)
        if bullet:
            label, value = canonical_label(bullet.group(1).strip()), bullet.group(2).strip()
            page.bullets.append(Bullet(label, value, n, links_in(value, n), item, generated))
    _close_table(page, table)
    if in_fence:
        page.errors.append(ParseError("E404", fence_start, "A code fence is never closed.",
                                      "Close the fence with a matching ``` line."))
    if open_block:
        page.errors.append(ParseError("E404", open_block[2], f"Generated block '{open_block[0]}' has no closing marker.",
                                      f"Add <!-- /generated:{open_block[0]} --> after the block."))


def _close_table(page, table):
    if table is not None and table[5]:
        page.tables.append(Table(table[0], tuple(table[2]), table[1], tuple(table[3]), table[4]))
    return None


def _marker(page, line, n, open_block):
    opening, closing = MARKER_OPEN.match(line), MARKER_CLOSE.match(line)
    if opening and open_block is None:
        return (opening.group(1), opening.group(2), n, [])
    if closing and open_block is not None and closing.group(1) == open_block[0]:
        name, sha, start, content = open_block
        page.blocks.append(Block(name, sha, "\n".join(content), start, n))
        return None
    if opening:
        page.errors.append(ParseError("E404", n, f"Generated block '{opening.group(1)}' opens inside block '{open_block[0]}'.",
                                      "Close the first block before opening another."))
        return open_block
    if closing and open_block is not None:
        page.errors.append(ParseError("E404", n, f"Closing marker '{closing.group(1)}' does not match open block '{open_block[0]}'.",
                                      f"Use <!-- /generated:{open_block[0]} -->."))
        return open_block
    if closing:
        page.errors.append(ParseError("E404", n, f"Closing marker '{closing.group(1)}' has no opening marker.",
                                      "Remove it, or add the opening marker above the block."))
        return open_block
    page.errors.append(ParseError("E404", n, "This generated-block marker is not in the current format.",
                                  f"Use <!-- generated:NAME sha=00000000: {MARKER_TEXT} --> "
                                  "and <!-- /generated:NAME -->, then run planner render."))
    return open_block
