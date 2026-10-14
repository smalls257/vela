"""The question ledger's rows, read from the page text. Pure: no vault rules, no disk.

Every owed copy and every question a reviewer raises ends in a row, so a question that was
asked leaves a trace and one that was never asked shows as undisposed. Grammar, as
CONVENTIONS.md gives it under "Questions and the ledger":

    ## Question ledger                          (on 11-unknowns-and-risks.md)

    | Copy | State | Evidence | By | Date |
    |---|---|---|---|---|
    | Q-OPS-01@APP-* | answered | item: [[concern-operations|Operations]]; source: SRC-07 | @lead | 2026-11-19 |

The Copy cell is a copy ID (`Q-DAT-02@APP-booking`), a wildcard (`Q-OPS-01@APP-*`) or a
reviewer question (`R-FIN-01`). Evidence is `key: value` pairs separated by `;`. A `;` inside
double quotes or inside a [[wikilink]] does not split. Shape problems are collected on the row,
so one bad row never hides the others.
"""
import datetime
import re
from dataclasses import dataclass

from vela import schema

PAGE_ID = "unknowns-and-risks"
HEADING = "Question ledger"
HEADER = ("Copy", "State", "Evidence", "By", "Date")
STATES = ("open", "asked", "answered", "assumed", "unknown", "not-applicable")
KEYS = ("capture", "item", "source", "answer", "belief", "load-bearing", "signpost", "unknown", "reason", "question", "quote",
        "severity", "covers")
REVIEWER_KEYS = ("question", "quote", "severity")
# What each state may carry. `covers` is allowed on any copy row, and a reviewer row may also carry REVIEWER_KEYS.
STATE_KEYS = {"open": (), "asked": ("capture",), "answered": ("item", "source", "answer"),
              "assumed": ("belief", "load-bearing", "signpost"), "unknown": ("unknown",), "not-applicable": ("reason",)}
COPY_RE = re.compile(r"^(?P<entry>Q-[A-Z]{3}-\d{2})@(?P<subject>[A-Za-z0-9][A-Za-z0-9-]*?)(?P<wild>\*)?$")
WILD_ONLY_RE = re.compile(r"^(?P<entry>Q-[A-Z]{3}-\d{2})@(?P<wild>\*)$")
REVIEWER_RE = re.compile(r"^R-(?P<area>[A-Z]{3})-\d{2,}$")
KEY_RE = re.compile(r"^(?P<key>[A-Za-z-]+):\s*(?P<value>.*)$", re.S)
DATE_RE = schema.DATE_RE


@dataclass(frozen=True)
class Row:
    path: str
    line: int
    copy: str  # the Copy cell as written
    kind: str  # "copy", "wildcard", "reviewer", or "" when the cell fits none
    entry: str  # the entry ID, "" for a reviewer row
    subject: str  # the subject ID, or a wildcard's prefix without the *; "" for a reviewer row
    area: str  # a reviewer row's area code, "" otherwise
    state: str
    evidence: tuple  # ((key, value), ...) in the order written
    by: str
    date: str
    problems: tuple  # why the row's shape is wrong, each a phrase; empty when it is well formed

    def get(self, key):
        return next((v for k, v in self.evidence if k == key), "")

    def has(self, key):
        return any(k == key for k, _ in self.evidence)


def is_date(value):
    if not DATE_RE.match(value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def split_evidence(text):
    """((key, value), ...) and a list of problems, for one Evidence cell."""
    parts, current, depth, quoted, i = [], [], 0, False, 0
    while i < len(text):
        if text.startswith("[[", i):
            depth += 1
            current.append("[[")
            i += 2
            continue
        if text.startswith("]]", i) and depth:
            depth -= 1
            current.append("]]")
            i += 2
            continue
        char = text[i]
        if char == '"':
            quoted = not quoted
        if char == ";" and not quoted and not depth:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
        i += 1
    parts.append("".join(current))
    problems = []
    if quoted:
        problems.append("its Evidence has a double quote that is never closed")
    pairs, seen = [], set()
    for part in (p.strip() for p in parts):
        if not part:
            continue
        match = KEY_RE.match(part)
        if not match:
            problems.append(f"Evidence part '{part}' is not 'key: value'")
            continue
        key, value = match["key"].lower(), " ".join(match["value"].split())
        if key not in KEYS:
            problems.append(f"Evidence key '{key}' is not one of {', '.join(KEYS)}")
            continue
        if key in seen:
            problems.append(f"Evidence key '{key}' appears twice")
            continue
        seen.add(key)
        pairs.append((key, value))
    return tuple(pairs), problems


def parse_copy(cell):
    """(kind, entry, subject, area) for a Copy cell; kind is "" when the cell fits no form."""
    match = REVIEWER_RE.match(cell)
    if match:
        return "reviewer", "", "", match["area"]
    match = COPY_RE.match(cell) or WILD_ONLY_RE.match(cell)
    if match:
        subject = match.groupdict().get("subject") or ""
        return ("wildcard" if match["wild"] else "copy"), match["entry"], subject, ""
    return "", "", "", ""


def parse_row(path, line, cells):
    problems = []
    if len(cells) != len(HEADER):
        problems.append(f"it has {len(cells)} cells, and a ledger row has {len(HEADER)}: {' | '.join(HEADER)}")
    cells = tuple(cells) + ("",) * (len(HEADER) - len(cells))
    copy, state, evidence_text, by, date = (c.strip() for c in cells[:5])
    kind, entry, subject, area = parse_copy(copy)
    if not kind:
        problems.append(f"'{copy}' is not a copy ID such as Q-DAT-02@APP-booking, a wildcard such as Q-OPS-01@APP-*, "
                        "or a reviewer question such as R-FIN-01")
    if state not in STATES:
        problems.append(f"state '{state}' is not one of {', '.join(STATES)}")
    if state != "open" or by or date:
        if not schema.OWNER_RE.match(by):
            problems.append(f"By '{by}' is not a handle such as @hl-solution-lead" if by else "By is empty")
        if not is_date(date):
            problems.append(f"Date '{date}' is not a real YYYY-MM-DD date" if date else "Date is empty")
    pairs, evidence_problems = split_evidence(evidence_text)
    problems += evidence_problems
    for key, _ in pairs:
        if key in REVIEWER_KEYS and kind != "reviewer":
            problems.append(f"Evidence key '{key}' belongs on a reviewer question row (R-FIN-01)")
    return Row(path, line, copy, kind, entry, subject, area, state, pairs, by, date, tuple(problems))


def ledger_tables(page):
    """The page's hand-kept tables whose header is exactly the ledger's."""
    return [t for t in page.tables if not t.generated and tuple(t.header) == HEADER]


def _under(page, table):
    """The last heading before a table, or None."""
    above = [h for h in page.headings if h.line < table.line]
    return max(above, key=lambda h: h.line) if above else None


def lookalike_tables(page):
    """Hand-kept tables directly under the first `## Question ledger` whose header is not exactly the ledger's:
    a typo, `Copy ID`, `**Copy**`, an extra column, a different order. Planner cannot read them as the ledger,
    so check reports them rather than let a misspelled header hide every row. Only this page and this section
    are looked at, so a glossary table headed `Copy` elsewhere is never taken for a ledger."""
    start = heading_line(page)
    return [t for t in page.tables if start and not t.generated and tuple(t.header) != HEADER
            and getattr(_under(page, t), "line", 0) == start]


def _well_placed(page, table):
    head = _under(page, table)
    return head is not None and head.level == 2 and head.text == HEADING and head.line == heading_line(page)


def misplaced_tables(page):
    """Ledger tables that do not sit under the first `## Question ledger`, the last heading before them."""
    return [t for t in ledger_tables(page) if not _well_placed(page, t)]


def misplaced_row_lines(page):
    """The row lines of misplaced tables. Their rows are read but dispose of nothing."""
    return {line for t in misplaced_tables(page) for line in t.row_lines}


def extra_headings(page):
    """Every `## Question ledger` heading after the first."""
    return [h for h in sorted(page.headings, key=lambda h: h.line) if h.level == 2 and h.text == HEADING][1:]


def section_lines(page):
    """The 1-based line range (first, last) of the `## Question ledger` section, or None."""
    start = heading_line(page)
    if not start:
        return None
    later = [h.line for h in page.headings if h.level == 2 and h.line > start]
    return start, (min(later) - 1 if later else len(page.text.split("\n")))


def heading_line(page):
    """The line of the `## Question ledger` heading, or 0."""
    return next((h.line for h in page.headings if h.level == 2 and h.text == HEADING), 0)


def rows(page):
    """Every ledger row on a page, in page order."""
    return [parse_row(page.path, line, cells) for table in ledger_tables(page)
            for cells, line in zip(table.rows, table.row_lines)]


def lines(page):
    """The heading line and every row line: where check reports on the ledger, so a page-level
    **Override:** on the ledger page can name a ledger code."""
    found = {heading_line(page)} - {0}
    for table in ledger_tables(page):
        found.update(table.row_lines)
        found.add(table.line)
    found.update(t.line for t in lookalike_tables(page))
    found.update(h.line for h in extra_headings(page))
    return found
