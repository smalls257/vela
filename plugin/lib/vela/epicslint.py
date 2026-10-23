"""The boundary test on an epic's acceptance criteria, and the rewrite of a first-shape epic to the template (CLI/skill
overhaul, Task 21e). Pure: pages and a built vault in, findings or new text out. No disk, git or clock.

**The boundary test** (the epics skill, section 4) was three steps a model ran by eye on every criterion. Each step is
countable, so it is code; the rewrite at the boundary stays the skill's, because that is judgment. Why each step holds:

1. The criterion's `- Trace:` line holds a contract (`CON-`) or a flow (`FLO-`). A tester can only check behavior they
   can see, and the contracts and flows are where an app's behavior shows. A criterion traced to a requirement alone
   has no place to be tested from (`no-boundary`).
2. It names none of the app's containers or components (from the Containers table on its building-blocks page). Inside
   the app is the senior's design, not the solution lead's: a criterion that names a component decides the design the
   handoff gave away (`component`).
3. It names no technology or product, and none of the generic words database, table, queue, Redis or Kafka, for the same
   reason: a store or a product is how the team builds it, not what a tester sees (`technology`). The vault's tech and
   ADR pages carry no list of product names a reader could take, so the products are the fixed list below.

Two more lines the skill already holds: an ID never goes in a criterion's sentence or heading, only on its Trace line
(`id-in-sentence`), because the lead reads the sentence and the ID means nothing aloud; and more than about seven
criteria on one epic is a cut to split (`too-many`, section 3): a tester can't hold more, and W364 only warns past nine.

**The shape rewrite** (`--fix-shape`): an epic written before the template (numbered criteria under `## Epic acceptance
criteria`, markers ending the sentence) becomes `## Done when` with one `###` heading per criterion and its number
written on the Trace line as `AC<n>`. The Violation it exists to prevent is Forensic Coding in the vault: other pages
cite `EPC-nnn.AC3`, and a rewrite that renumbered by counting would leave every citation pointing at a different
criterion with nothing to show it moved (Anchor). So the number is the one written, struck criteria keep theirs, and
the new text is read back through `criteria.read` before anything is returned: a rewrite that would change any number,
trace, marker, group or strike raises `ShapeLost` instead of being written (Sensor, never a quiet renumbering).
The headings are drafted from each criterion's first words; the skill rewords them with the lead.
"""
import re
from dataclasses import dataclass, field

from vela import criteria, parse, schema, say
from vela.parse import FENCE, closes_fence
from vela.reading import TRACE_LINE

MAX_CRITERIA = 7
GENERIC_STORE_WORDS = ("database", "table", "queue", "Redis", "Kafka")
# Products a criterion should never name. Fixed, because the tech and ADR pages hold no structured list of products.
KNOWN_PRODUCTS = ("PostgreSQL", "Postgres", "MySQL", "SQL Server", "SQLite", "Oracle", "MongoDB", "DynamoDB",
                  "Cosmos DB", "Cassandra", "RabbitMQ", "SQS", "SNS", "S3", "Elasticsearch", "OpenSearch",
                  "Kubernetes", "Docker", "AWS Lambda", "Azure Functions", "Service Bus", "Event Hubs", "BigQuery",
                  "Snowflake", "Memcached", "GraphQL", "gRPC")
BOUNDARY_PREFIXES = ("CON-", "FLO-")
WHO_HEADING = "Who this is for and what changes"
WHO_STUB = "To be written at close."
DONE_HEADING = "Done when"
HEADING_WORDS = 10
TRAILING_SMALL_WORDS = {"a", "an", "the", "of", "for", "to", "over", "and", "or", "with", "in", "on", "at", "by",
                        "from", "that", "is", "are"}

_WIKILINK = re.compile(r"\[\[([^\]|]+?)(?:\\?\|([^\]]+))?\]\]")
_GENERIC = re.compile(r"(?<![\w-])(database|table|queue)s?(?![\w-])|(?<![\w-])(Redis|Kafka)(?![\w-])", re.I)
_SECTION = re.compile(r"^##\s+(?P<text>.*?)\s*#*\s*$")
_GROUP = re.compile(r"^(?P<hashes>#{3,6})\s+(?P<text>.*?)\s*#*\s*$")


@dataclass(frozen=True)
class Finding:
    epic: str
    epic_title: str
    path: str
    line: int
    kind: str  # "no-boundary", "component", "technology", "id-in-sentence" or "too-many"
    ac: int = 0  # 0 for an epic-wide finding
    criterion: str = ""  # the heading, or the first words of a numbered criterion
    words: tuple = ()  # what it named
    count: int = 0  # for too-many

    def as_json(self):
        return {"epic": self.epic, "path": self.path, "line": self.line, "kind": self.kind, "ac": self.ac,
                "criterion": self.criterion, "words": list(self.words), "count": self.count}


def said(text):
    """A criterion's words as a reader sees them: each link said by its label."""
    return _WIKILINK.sub(lambda m: (m.group(2) or m.group(1)).replace("\\", ""), text)


def short(c):
    """What to call a criterion: its heading, or its first words."""
    if c.heading:
        return said(c.heading)
    words = said(c.text).strip("~ ").split()
    return " ".join(words[:8]) + ("..." if len(words) > 8 else "")


def _cell(text):
    return said(text).replace("`", "").replace("*", "").strip()


def containers(page):
    """The names in the first column of an app page's Containers table."""
    for table in page.tables:
        if table.generated or tuple(table.header)[:2] != schema.CONTAINERS_HEADER:
            continue
        return [_cell(row[0]) for row in table.rows if row and _cell(row[0])]
    return []


def boundary_names(vault):
    """Names a criterion may say: apps, contracts and flows are the boundary, and capabilities are the business's
    words. A container that shares one of those names ("Booking API" serving the Booking API contract) is said as the
    boundary, so it is never flagged."""
    names = [a.meta.get("title") for a in vault.apps] + [c.name for c in vault.contracts]
    names += [p.meta.get("title") for kind in ("flow", "capability") for p in vault.of_type(kind)]
    return {str(n).strip().lower() for n in names if n}


def components_for(vault, epic):
    """The containers of every app the epic lists, less any that share a boundary's name."""
    listed = epic.meta.get("apps")
    ids = {str(a) for a in listed} if isinstance(listed, list) else set()
    apps = [a for a in vault.apps if a.id in ids]
    allowed = boundary_names(vault)
    return sorted({name for app in apps for name in containers(app) if name.lower() not in allowed})


def _named(name, text):
    flags = re.I if " " in name else 0  # one word only as written ("Schedule"), so the plain word "schedule" passes
    return re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text, flags) is not None


def technologies(text):
    found = [m.group(0) for m in _GENERIC.finditer(text)]
    found += [p for p in KNOWN_PRODUCTS if re.search(rf"(?<![\w-]){re.escape(p)}(?![\w-])", text, re.I)]
    return tuple(dict.fromkeys(w.lower() if w.lower() in ("database", "table", "queue") else w for w in found))


def boundary_findings(epic, c, components):
    """The boundary test on one criterion, in the skill's order."""
    base = dict(epic=epic.id, epic_title=str(epic.meta.get("title") or epic.id), path=epic.path, line=c.line, ac=c.n,
                criterion=short(c))
    words = said(f"{c.heading}\n{c.text}")
    out = []
    if not any(i.startswith(BOUNDARY_PREFIXES) for i in c.trace):
        out.append(Finding(kind="no-boundary", **base))
    named = tuple(n for n in components if _named(n, words))
    if named:
        out.append(Finding(kind="component", words=named, **base))
    tech = technologies(words)
    if tech:
        out.append(Finding(kind="technology", words=tech, **base))
    ids = tuple(dict.fromkeys(m.group(0) for m in say.LEAD_PATTERNS["item"].finditer(words)))
    if ids:
        out.append(Finding(kind="id-in-sentence", words=ids, **base))
    return out


def lint_epic(vault, epic):
    live = [c for c in criteria.read(epic) if not c.struck]
    components = components_for(vault, epic)
    out = [f for c in live for f in boundary_findings(epic, c, components)]
    if len(live) > MAX_CRITERIA:
        out.append(Finding(epic.id, str(epic.meta.get("title") or epic.id), epic.path, 1, "too-many",
                           count=len(live)))
    return out


def lint(vault, epics):
    return [f for e in epics for f in lint_epic(vault, e)]


# ------------------------------------------------------------------------------------------------ the shape rewrite

class ShapeRefused(ValueError):
    """The page can't be rewritten mechanically; `plain` says why, for the lead."""

    def __init__(self, plain):
        self.plain = plain
        super().__init__(plain)


class ShapeLost(RuntimeError):
    """The rewrite would have changed a criterion's number, trace, markers, group or strike. A vela bug: nothing is
    written."""


@dataclass
class Rewrite:
    text: str
    changed: bool
    numbers: list = field(default_factory=list)
    headings: list = field(default_factory=list)  # (n, drafted heading)


def _sections(lines):
    """[(start, end, heading text)] for each `##` section, outside code fences. `end` is exclusive."""
    found, fence = [], None
    for i, raw in enumerate(lines):
        if fence:
            fence = None if closes_fence(raw, fence) else fence
            continue
        opening = FENCE.match(raw)
        if opening:
            fence = opening.group(1)
            continue
        m = _SECTION.match(raw)
        if m:
            if found:
                found[-1][1] = i
            found.append([i, len(lines), m["text"]])
    return [tuple(s) for s in found]


def draft_heading(text):
    """A short heading from a criterion's first words: up to the first sentence or clause break, at most ten words."""
    plain = said(text).replace("~~", "").strip()
    first = re.split(r"(?<=[.;:])\s|,\s", plain, maxsplit=1)[0]
    words = first.rstrip(".;:,").split()[:HEADING_WORDS]
    while len(words) > 1 and words[-1].lower() in TRAILING_SMALL_WORDS:  # a cut never ends on "for a"
        words.pop()
    phrase = " ".join(words).rstrip(".;:,") or "Criterion"
    return phrase[0].upper() + phrase[1:]


def _criterion_lines(level, c):
    heading = draft_heading(c["text"])
    shown = f"~~{heading}~~" if c["struck"] else heading
    parts = [", ".join(c["ids"])] if c["ids"] else []
    parts.append(f"AC{c['n']}")
    if c["markers"]:
        parts.append(" ".join(f"[{m}]" for m in c["markers"]))
    body = " ".join([c["text"]] + c["more"]).strip()
    return heading, [f"{'#' * level} {shown}", "", body, "", "- Trace: " + "  ·  ".join(parts), ""]


def _convert(lines):
    """The lines of an old criteria section, as the template's. Returns (lines, [(n, heading)])."""
    out, drafted, level, current = [], [], 3, None

    def flush():
        if current is not None:
            heading, written = _criterion_lines(level, current)
            drafted.append((current["n"], heading))
            out.extend(written)

    for raw in lines:
        group = _GROUP.match(raw)
        numbered = criteria.NUMBERED.match(raw)
        trace_line = TRACE_LINE.match(raw)
        if group:
            flush()
            current = None
            out.extend([raw.rstrip(), ""])
            level = min(len(group["hashes"]) + 1, 6)
        elif numbered and not raw.startswith((" ", "\t")):
            flush()
            body = numbered["body"]
            marked = criteria.TRAILING_MARKERS.match(body)
            text, markers = (marked["body"], marked["markers"]) if marked else (body, "")
            current = {"n": int(numbered["n"]), "text": text.strip(), "struck": body.lstrip().startswith("~~"),
                       "markers": [m.lower() for m in re.findall(r"\[([^\]]+)\]", markers)], "ids": [], "more": []}
        elif trace_line and current is not None:
            parts = criteria.parse_trace(trace_line["ids"])
            current["ids"] = list(parts.ids)
            current["markers"] += [m for m in parts.markers if m not in current["markers"]]
        elif not raw.strip():
            continue
        elif current is not None and raw.startswith((" ", "\t")):
            current["more"].append(raw.strip())
        else:
            flush()
            current = None
            out.extend([raw.rstrip(), ""])
    flush()
    return out, drafted


def _same(before, after):
    key = [(c.n, c.struck, c.markers, c.trace, c.group) for c in before]
    return key == [(c.n, c.struck, c.markers, c.trace, c.group) for c in after]


def is_first_shape(text):
    """True when the page keeps its criteria as numbered lines under `## Epic acceptance criteria`, the shape
    `fix_shape` rewrites."""
    return any(criteria.is_criteria_heading(s[2]) and s[2].strip().lower() != DONE_HEADING.lower()
               for s in _sections(text.split("\n")))


def fix_shape(path, text):
    """`text` with its first-shape criteria rewritten to the template, every AC number kept. Unchanged (with
    `changed=False`) when the page has no first-shape section."""
    lines = text.split("\n")
    sections = _sections(lines)
    old = [s for s in sections if criteria.is_criteria_heading(s[2]) and s[2].strip().lower() != DONE_HEADING.lower()]
    new = [s for s in sections if s[2].strip().lower() == DONE_HEADING.lower()]
    before = criteria.read(parse.parse_page(path, text))
    if not old:
        return Rewrite(text, False, [c.n for c in before])
    if new or len(old) > 1:
        raise ShapeRefused("This epic holds its criteria in more than one section, so moving them could merge two "
                           "lists. Move them under one heading by hand first.")
    start, end, _ = old[0]
    converted, drafted = _convert(lines[start + 1:end])
    has_who = any(s[2].strip().lower() == WHO_HEADING.lower() for s in sections)
    head = [] if has_who else [f"## {WHO_HEADING}", "", WHO_STUB, ""]
    replacement = head + [f"## {DONE_HEADING}", ""] + converted
    result = "\n".join(lines[:start] + replacement + lines[end:])
    after = criteria.read(parse.parse_page(path, result))
    if not _same(before, after):
        raise ShapeLost(f"vela bug: rewriting {path} to the template would have changed its criteria "
                        f"(numbers {[c.n for c in before]} became {[c.n for c in after]}); nothing was written.")
    return Rewrite(result, True, [c.n for c in after], drafted)
