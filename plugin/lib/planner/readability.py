"""Reading load: pages a person can hold in mind, and the Trace line that carries the IDs prose no longer shows.

Pure: a page and a name index in, findings out. People hold about four to seven things in mind at once (Cowan 2001;
Miller 1956). A criterion that ends "(CON-001, FLO-001). From CAP-001.FR2." asks a reader to look up three codes
before the sentence means anything, so the sentence names things in plain words and `- Trace: CAP-001.FR2, CON-001,
FLO-001` on the line beneath keeps the IDs for the machine. The five W36x warnings below are the Sensor on that:
a page that has drifted back to codes, long lists or a wall of text says so, with the plain-words rewrite.
"""
import re
from dataclasses import dataclass

from planner import criteria as criteria_reader
from planner import schema
from planner.parse import FENCE, split_frontmatter
from planner.reading import BREADCRUMB, TRACE_LINE, VAULT_ID, visible

BARE_VAULT_ID = re.compile(rf"(?<![\w-]){VAULT_ID}(?![\w-])")
WIKILINK = re.compile(r"\[\[[^\]]*\]\]")
CODE_SPAN = re.compile(r"`[^`]*`")
URL = re.compile(r"https?://\S+")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LIST_ITEM = re.compile(r"^( {0,1})(?:[-*]|\d+\.)\s+(.*)$")
FACT_BULLET = re.compile(r"^\s*[-*]\s+\*\*[^*]+:\*\*")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
GEN_OPEN = re.compile(r"^\s*<!--\s*generated:")
GEN_CLOSE = re.compile(r"^\s*<!--\s*/generated:")
SUMMARY_MIN_WORDS = 10  # a paragraph shorter than this is a label, not a summary
NO_PROSE_TYPES = ("session", "sources")  # a working log and a table: neither is read top to bottom


@dataclass(frozen=True)
class Entry:
    """What an ID is called, and where the thing lives."""
    id: str
    name: str
    page: object  # the Page that holds it
    anchor: str  # heading text on that page, "" for the page itself


class NameIndex:
    """ID to plain name for one vault, so a warning, a tooltip and a chip all say the same name."""

    def __init__(self, vault):
        self.entries = {}
        for page in vault.pages:
            if page.id:
                self.entries.setdefault(page.id, Entry(page.id, _title(page), page, ""))
        for item_id, items in vault.items.items():
            item = items[0]
            self.entries[item_id] = Entry(item_id, item.name or item_id, item.page, item.heading)

    def lookup(self, item_id):
        return self.entries.get(item_id)

    def name(self, item_id):
        entry = self.entries.get(item_id)
        return entry.name if entry else ""


def _title(page):
    title = page.meta.get("title")
    return title.strip() if isinstance(title, str) and title.strip() else page.name


def trace_ids(line):
    """The IDs on a `- Trace:` line, in the order written; [] when the line is not one. A comma or a space divides
    them, so `CAP-001.FR1, CON-001` and `CAP-001.FR1 CON-001` read the same. The AC id and the concern markers that
    the epic template puts after a middle dot are not IDs of the vault and are left out (`criteria.parse_trace`)."""
    found = TRACE_LINE.match(line)
    if not found:
        return []
    return list(criteria_reader.parse_trace(found["ids"]).ids)


def is_trace(line):
    return TRACE_LINE.match(line) is not None


def trace_by_line(page):
    """{line number: [ID, ...]} for every Trace line outside code fences and generated blocks."""
    found, fence = {}, None
    for n, raw in enumerate(page.text.split("\n"), 1):
        if fence:
            fence = None if raw.strip().startswith(fence) else fence
            continue
        opening = FENCE.match(raw)
        if opening:
            fence = opening.group(1)
            continue
        if is_trace(raw):
            found[n] = trace_ids(raw)
    return {n: ids for n, ids in found.items() if not _in_block(page, n)}


def _in_block(page, n):
    return any(block.start <= n <= block.end for block in page.blocks)


def _regions(page):
    """(line number, text, heading text above it, in History) for each line of the page's own words: no frontmatter,
    no code fence, no generated block. A heading line carries its own text."""
    _, body_start, _ = split_frontmatter(page.text)
    fence, in_history, heading = None, False, ""
    for n, raw in enumerate(page.text.split("\n"), 1):
        if n < body_start:
            continue
        if fence:
            fence = None if raw.strip().startswith(fence) else fence
            continue
        opening = FENCE.match(raw)
        if opening:
            fence = opening.group(1)
            continue
        if _in_block(page, n) or GEN_OPEN.match(raw) or GEN_CLOSE.match(raw):
            continue
        found = HEADING.match(raw)
        if found:
            heading = found.group(2)
            if len(found.group(1)) <= 2:
                in_history = heading.strip().lower() == schema.HISTORY_HEADING.lower()
        yield n, raw, heading, in_history


def _is_prose(raw):
    """A line a person reads as words: not a heading, table row, fact bullet, Trace line or quote marker."""
    stripped = raw.strip()
    if not stripped or stripped.startswith(("#", "|", "<!--")) or FACT_BULLET.match(raw) or is_trace(raw):
        return False
    return True


def _outside_links(text):
    """The text with wikilinks, code and URLs taken out: what is left is what is typed in the open."""
    return URL.sub(" ", CODE_SPAN.sub(" ", WIKILINK.sub(" ", text)))


def _sentences(text):
    return [s for s in SENTENCE_END.split(text) if s.strip()]


def _ids_in(text):
    return BARE_VAULT_ID.findall(text)


def _says_its_name(text, end, name):
    """True when the words right after an ID (past a bracket or a dash) are the item's name."""
    if not name:
        return False
    after = re.sub(r"^[\s(\[:,–—-]+", "", text[end:]).lower()
    return after.startswith(name.lower())


def findings(page, names):
    """(line, code, message, fix) for each place the page asks a reader to hold too much. `names` is a NameIndex."""
    if page.type in NO_PROSE_TYPES or not page.meta:  # no frontmatter: E101 or E102 has the page, and its header is not prose
        return []
    out = []
    prose = [(n, raw) for n, raw, _, history in _regions(page) if not history and _is_prose(raw)]
    out += _id_findings(prose, names)
    out += _list_findings(page)
    out += _summary_findings(page)
    out += _epic_findings(page)
    return sorted(out)


def _id_findings(prose, names):
    out = []
    for n, raw in prose:
        shown = visible(re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", raw))
        crowded = next((s for s in _sentences(shown) if len(_ids_in(_outside_code(s))) >= schema.SENTENCE_ID_LIMIT), None)
        if crowded:
            ids = _ids_in(_outside_code(crowded))
            out.append((n, "W360", f"One sentence holds {len(ids)} IDs ({', '.join(ids[:4])}), more than a reader can keep in mind.",
                        "Say each thing by its plain name, and move the IDs to a '- Trace: ID, ID' line under the sentence."))
        bare = _bare_without_name(_outside_links(raw), names)
        if bare:
            first = bare[0]
            name = names.name(first)
            how = (f"Write '{name}' in the sentence and put {first} on a '- Trace:' line under it." if name else
                   f"Say in plain words what {first} is, and put {first} on a '- Trace:' line under the sentence.")
            more = f" (and {len(bare) - 1} more)" if len(bare) > 1 else ""
            out.append((n, "W361", f"{first}{more} is written in the open, outside a link and without its name.", how))
    return out


def _outside_code(text):
    return URL.sub(" ", CODE_SPAN.sub(" ", text))


CAPITALISED_NAME = re.compile(r"\s+[A-Z][a-z]")


def _bare_without_name(text, names):
    """The IDs written in the open with no name beside them. An ID the vault holds no name for (an initiative
    elsewhere, a constraint row) counts as named when a capitalised name follows it, as in "INI-005 Mainframe Exit"."""
    bare = []
    for found in BARE_VAULT_ID.finditer(text):
        name = names.name(found.group(0))
        named = _says_its_name(text, found.end(), name) if name else CAPITALISED_NAME.match(text, found.end())
        if not named:
            bare.append(found.group(0))
    return bare


def _list_findings(page):
    """W362: more than nine list items under one heading with no subheading to break them. Epic acceptance criteria
    answer to W364 instead, so one long list is not named twice."""
    out, section, items, first = [], "", 0, 0

    def close():
        if items > schema.LIST_LIMIT and not criteria_reader.is_criteria_heading(section):
            out.append((first, "W362", f"{items} list items sit under one heading, more than a reader can hold at once.",
                        "Group them under short subheadings of about five each, or fold the least important into an 'Also open (n)' section."))

    for n, raw, heading, history in _regions(page):
        found = HEADING.match(raw)
        if found:
            close()
            section, items, first = found.group(2), 0, 0
            continue
        if history or FACT_BULLET.match(raw) or is_trace(raw):
            continue
        if LIST_ITEM.match(raw):
            items += 1
            first = first or n
    close()
    return out


def _summary_findings(page):
    words = sum(len(raw.split()) for _, raw, _, history in _regions(page) if not history)
    if words <= schema.LONG_PAGE_WORDS or _has_opening_summary(page):
        return []
    return [(1, "W363", f"The page runs about {words} words and opens with no summary.",
             "Open with two or three plain sentences under the title: what the page says and what is still open.")]


def _has_opening_summary(page):
    """A paragraph of real words between the title and the first `##` heading."""
    for _, raw, _, _ in _regions(page):
        found = HEADING.match(raw)
        if found:
            if len(found.group(1)) >= 2:
                return False
            continue
        stripped = raw.strip()
        if not stripped or not _is_prose(raw) or LIST_ITEM.match(raw) or stripped.startswith(">") or BREADCRUMB.match(stripped):
            continue
        if len(visible(stripped).split()) >= SUMMARY_MIN_WORDS:
            return True
    return False


def criteria(page):
    """(line, text) for each acceptance criterion that is not struck through, in either shape."""
    return [(c.line, c.raw) for c in criteria_reader.read(page) if not c.struck]


def _epic_findings(page):
    if page.type != "epic":
        return []
    out = [(line, "W370", message, "Add 'AC<n>' to the criterion's '- Trace:' line, after the IDs and a middle dot, with a number no "
            "other criterion uses.") for line, message in criteria_reader.problems(page)]
    listed = criteria(page)
    if len(listed) <= schema.EPIC_CRITERIA_LIMIT:
        return out
    return out + [(listed[0][0], "W364", f"The epic lists {len(listed)} acceptance criteria, more than a team can hold as one piece of work.",
                   "Split it into two epics of about five criteria each. The epics session proposes the cut.")]


# --------------------------------------------------------- IDs shown as names

PROTECTED = re.compile(r"`[^`]*`|\[\[[^\]]*\]\]|<[^>\n]+>|https?://\S+")


def name_ids(text, names, render):
    """The text with each bare vault ID that has a name replaced by `render(entry)`. Code spans, wikilinks, tags and
    URLs are left alone, and an ID already followed by its name loses the ID: the reader sees the name once. This is
    the display half of the Trace convention; old pages that still write IDs in prose read the same way."""
    out, last = [], 0
    for fixed in list(PROTECTED.finditer(text)) + [None]:
        stop = fixed.start() if fixed else len(text)
        out.append(_name_run(text[last:stop], names, render))
        if fixed:
            out.append(fixed.group(0))
            last = fixed.end()
    return "".join(out)


def _name_run(run, names, render):
    out, last = [], 0
    for found in BARE_VAULT_ID.finditer(run):
        entry = names.lookup(found.group(0))
        if entry is None or found.start() < last:
            continue
        end = found.end()
        if _says_its_name(run, end, entry.name):
            after = re.match(r"[\s(\[:,–—-]*", run[end:])
            end += after.end() + len(entry.name)
        out.append(run[last:found.start()])
        out.append(render(entry))
        last = end
    out.append(run[last:])
    return "".join(out)


def chip_entries(ids, names):
    """The Entries a Trace line points at, in the order written; an ID the vault does not hold is left out."""
    return [entry for entry in (names.lookup(i) for i in ids) if entry is not None]
