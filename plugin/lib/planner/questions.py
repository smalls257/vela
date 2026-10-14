"""Which questions a vault owes. Pure: reads the Vault and its catalog, returns data.

A catalog entry is a template with a scope. Code applies it once per subject its trigger
matches, so the copies multiply and nobody has to remember them. A copy's ID is
`<entry>@<subject>`: it stays the same while the subject keeps its ID, so a renamed file
carries its questions with it. The same vault always gives the same copies in the same order.
"""
import re
from dataclasses import dataclass

from planner import catalog, ledger, schema
from planner.model import Finding, meta_line
from planner.parse import CODE_SPAN, WIKILINK, links_in, split_frontmatter

SUBJECT_ID_RE = {
    "initiative": schema.INITIATIVE_RE,
    "app": schema.PAGE_ID_RE["app-building-blocks"],
    "contract": re.compile(r"^CON-\d{3}$"),
    "capability": schema.PAGE_ID_RE["capability"],
    "party": re.compile(r"^PTY-\d{2,}$"),
    "stored-value": re.compile(r"^SV-\d{2,}$"),
}
SUBJECT_PREFIX = {"initiative": "INI-", "app": "APP-", "contract": "CON-", "capability": "CAP-", "party": "PTY-",
                  "stored-value": "SV-"}
PAGE_KINDS = {"app-building-blocks": "app", "capability": "capability", "decision": "decision", "epic": "epic"}
EPIC_LISTS = ("apps", "delivers", "consumes", "flows", "depends_on")


@dataclass(frozen=True)
class Subject:
    id: str
    kind: str  # one of catalog.SCOPES
    title: str
    page: object  # the page it is, or the page its heading sits on; None for the initiative
    line: int  # where check points for it: the heading, the `change:` line, or 1
    facts: tuple  # sorted (field, lower-case text) pairs a trigger may test

    def fact_map(self):
        return dict(self.facts)


@dataclass(frozen=True)
class Copy:
    id: str  # <entry id>@<subject id>
    entry: object  # catalog.Entry
    subject: Subject


def low(value):
    """A frontmatter or fact value as a trigger compares it, or "" when it is not text."""
    return " ".join(value.split()).lower() if isinstance(value, str) else ""


def title(page):
    value = page.meta.get("title")
    return " ".join(value.split()) if isinstance(value, str) and value.strip() else page.name


def _facts(**values):
    return tuple(sorted((k, low(v)) for k, v in values.items()))


def subjects(vault):
    """Every subject in the vault, in scope order and then by ID. A subject whose ID does not fit
    its kind is left out here, and the check already reports it (E107, E208)."""
    if "subjects" in vault.cache:
        return vault.cache["subjects"]
    out, seen = [], set()

    def add(subject):
        if subject.id not in seen and SUBJECT_ID_RE[subject.kind].match(subject.id):
            seen.add(subject.id)
            out.append(subject)

    initiative = vault.config.get("initiative")
    if isinstance(initiative, str):
        name = vault.config.get("title")
        add(Subject(initiative, "initiative", name if isinstance(name, str) and name else initiative, None, 1, ()))
    for app in vault.apps:
        meta = app.meta
        add(Subject(app.id, "app", title(app), app, meta_line(app, "change"),
                    _facts(change=meta.get("change"), state=meta.get("state"), stage=meta.get("stage"))))
    for contract in vault.contracts:
        add(Subject(contract.id, "contract", contract.name, contract.page, contract.line,
                    _facts(change=contract.fact("Change"), state=contract.fact("State"),
                           provider="external" if contract.fact("Provider") else "app")))
    for cap in sorted(vault.of_type("capability"), key=lambda p: p.id):
        meta = cap.meta
        add(Subject(cap.id, "capability", title(cap), cap, meta_line(cap, "change"),
                    _facts(change=meta.get("change"), state=meta.get("state"), origin=meta.get("origin"),
                           domain=meta.get("domain"))))
    for party in vault.parties:
        add(Subject(party.id, "party", party.name, party.page, party.line,
                    _facts(relationship=party.fact("Relationship"))))
    for stored in vault.stored_values:
        add(Subject(stored.id, "stored-value", stored.name, stored.page, stored.line, ()))
    vault.cache["subjects"] = tuple(out)
    return vault.cache["subjects"]


def subject(vault, subject_id):
    return next((s for s in subjects(vault) if s.id == subject_id), None)


def owed(vault):
    """Every owed copy, sorted by copy ID: each catalog entry applied once per subject of its
    scope whose facts its trigger matches."""
    if "owed" in vault.cache:
        return vault.cache["owed"]
    by_kind = {}
    for found in subjects(vault):
        by_kind.setdefault(found.kind, []).append(found)
    copies = [Copy(f"{entry.id}@{found.id}", entry, found)
              for entry in vault.catalog.entries
              for found in by_kind.get(entry.scope, [])
              if entry.trigger.matches(found.fact_map())]
    vault.cache["owed"] = tuple(sorted(copies, key=lambda c: c.id))
    return vault.cache["owed"]


# ------------------------------------------------------------------ what an open copy holds up

def _units(vault):
    """{kind: [(unit id, page, item or None)]} for every unit a copy may block."""
    if "units" in vault.cache:
        return vault.cache["units"]
    out = {kind: [] for kind in catalog.BLOCK_KINDS}
    for page in sorted(vault.pages, key=lambda p: (p.id, p.path)):
        kind = PAGE_KINDS.get(page.type) if isinstance(page.type, str) else None
        if kind and page.id:
            out[kind].append((page.id, page, None))
    for contract in vault.contracts:
        out["contract"].append((contract.id, contract.page, contract))
    for fr in vault.requirements:
        out["requirement"].append((fr.id, fr.page, fr))
    vault.cache["units"] = out
    return out


def _links_to(vault, page, target, anchor=None):
    """Whether any link on `page` points at `target`, and at the heading `anchor` when one is given."""
    for link in page.links:
        if vault.resolve(link, page) is target and (anchor is None or link.anchor == anchor):
            return True
    return False


def _epic_lists(page):
    found = set()
    for key in EPIC_LISTS:
        values = page.meta.get(key)
        if isinstance(values, list):
            found.update(v for v in values if isinstance(v, str))
    return found


def _section_links(vault, found):
    """The units the bullets under a party or stored-value heading link to: (kind, id) pairs."""
    item = vault.item(found.id)
    out = set()
    for bullet in item.facts.values() if item is not None else ():
        for link in bullet.links:
            target = vault.resolve(link, item.page)
            if target is None:
                continue
            first = link.anchor.split()[0] if link.anchor.split() else ""
            linked = vault.item(first) if first else None
            if linked is not None and linked.page is target and linked.kind in ("contract", "requirement"):
                out.add((linked.kind, linked.id))
            elif PAGE_KINDS.get(target.type):
                out.add((PAGE_KINDS[target.type], target.id))
    return out


def _related(vault, unit, found):
    """Whether a unit (kind, id, page, item) is one an open copy about `found` holds up."""
    kind, unit_id, page, item = unit
    if found.kind == "initiative":
        return True
    if unit_id == found.id:
        return True
    if found.kind == "app":
        app = found.page
        if kind == "contract":
            return item.page is app or app in vault.consumers(item)
        if kind == "epic":
            return found.id in _epic_lists(page)
        if kind == "decision":
            return _links_to(vault, page, app)
        return False
    if found.kind == "contract":
        contract = vault.item(found.id)
        if kind == "epic":
            return found.id in _epic_lists(page)
        if kind == "decision":
            return _links_to(vault, page, contract.page, contract.heading)
        return False
    if found.kind == "capability":
        if kind == "requirement":
            return item.page is found.page
        if kind == "epic":
            return found.id in _epic_lists(page)
        if kind == "decision":
            return _links_to(vault, page, found.page)
        return False
    # a party or a stored value: what its own bullets link, and what links its heading
    if (kind, unit_id) in _section_links(vault, found):
        return True
    heading = vault.item(found.id)
    if kind == "epic":
        return found.id in _epic_lists(page)
    if kind == "decision" and heading is not None:
        return _links_to(vault, page, heading.page, heading.heading)
    return False


def blocks(vault, copy):
    """The IDs of the units this copy holds up while it is open, sorted: units of the kinds its
    entry lists in `blocks` that its subject touches. The initiative touches every unit."""
    key = ("blocks", copy.id)
    if key not in vault.cache:
        units = _units(vault)
        found = set()
        for kind in copy.entry.blocks:
            for unit_id, page, item in units[kind]:
                if _related(vault, (kind, unit_id, page, item), copy.subject):
                    found.add(unit_id)
        vault.cache[key] = tuple(sorted(found))
    return vault.cache[key]


# ------------------------------------------------------------------ the ledger: where each copy stands

@dataclass(frozen=True)
class Disposition:
    copy: Copy
    state: str  # the row's state, or "" when no row covers the copy
    row: object  # the ledger.Row that covers it, or None
    via: str  # "" for the copy's own row, else the covering row's Copy cell: a wildcard or an initiative row
    valid: bool = True  # False when the row has an error, so it disposes of nothing

    @property
    def undisposed(self):
        """No row says anything about it yet, its row says `open`, or its row is broken. A row that
        fails its checks is not a record of anything, so `planner questions` agrees with `planner check`."""
        return self.row is None or self.state == "open" or not self.valid

    @property
    def label(self):
        """Why it is undisposed, or how it stands: `no row`, `open`, `invalid (<state>)`, else its state."""
        return state_label(self.state, self.valid)

    @property
    def pending(self):
        """Undisposed, or asked and still waiting for its answer: what the gates hold up."""
        return self.undisposed or self.state == "asked"


def state_label(state, valid=True):
    if not valid:
        return f"invalid ({state})"
    return state or "no row"


def ledger_page(vault):
    pages = vault.by_id.get(ledger.PAGE_ID)
    return pages[0] if pages else None


def rows(vault):
    """Every ledger row on 11-unknowns-and-risks.md, in page order."""
    if "rows" not in vault.cache:
        page = ledger_page(vault)
        vault.cache["rows"] = tuple(ledger.rows(page)) if page is not None else ()
    return vault.cache["rows"]


def row_valid(vault, row):
    """True when the row has no shape, evidence or naming error. A warning does not break a row."""
    page = ledger_page(vault)
    if page is not None and row.line in ledger.misplaced_row_lines(page):
        return False
    return not any(f.is_error for f in _row_findings(vault).get(row.line, ()))


def reviewer_rows(vault):
    return [r for r in rows(vault) if r.kind == "reviewer" and r.state in ledger.STATES]


def _initiative_id(vault):
    value = vault.config.get("initiative")
    return value if isinstance(value, str) else ""


def _covers(vault, row, copy):
    """How well a readable row covers a copy: 3 its own row, 2 a wildcard (longer prefix first),
    1 an initiative row with `covers:` its scope, 0 not at all."""
    if row.entry != copy.entry.id:
        return 0
    if row.kind == "copy" and row.subject == copy.subject.id:
        return 3
    if row.kind == "wildcard" and copy.subject.id.startswith(row.subject) and \
            row.subject.startswith(SUBJECT_PREFIX[copy.entry.scope]):
        return 2
    if row.kind == "copy" and row.subject == _initiative_id(vault) and copy.entry.scope != "initiative" \
            and row.get("covers") == copy.entry.scope:
        return 1
    return 0


def _assignments(vault):
    """(copy, row, rank) for each owed copy: its own row, else the wildcard with the longest prefix, else an
    initiative row that `covers:` its scope. Exceptions take their own row. A broken row is still the one
    assigned, so a bad exception is never quietly replaced by the wildcard it was an exception to."""
    if "assignments" in vault.cache:
        return vault.cache["assignments"]
    readable = [r for r in rows(vault) if r.kind in ("copy", "wildcard") and r.state in ledger.STATES]
    out = []
    for copy in owed(vault):
        best, rank = None, 0
        for row in readable:
            score = _covers(vault, row, copy)
            if score and (score > rank or (score == rank == 2 and len(row.subject) > len(best.subject))):
                best, rank = row, score
        out.append((copy, best, rank))
    vault.cache["assignments"] = tuple(out)
    return vault.cache["assignments"]


def dispositions(vault):
    """One Disposition per owed copy, in copy order."""
    if "dispositions" not in vault.cache:
        vault.cache["dispositions"] = tuple(
            Disposition(copy, best.state if best else "", best, "" if best is None or rank == 3 else best.copy,
                        best is None or row_valid(vault, best))
            for copy, best, rank in _assignments(vault))
    return vault.cache["dispositions"]


def coverage_line(vault, owed_count, undisposed_count, reviewer_open=0, asked=0):
    """What every report says about coverage. Never "complete": the catalog only finds what is written into it.
    Asked questions and open reviewer questions are named when there are any, so the line describes every row
    listed under it. An asked question is disposed of nothing yet, and it still holds the gates."""
    asked_text = f", {asked} asked" if asked else ""
    reviewers = f", {reviewer_open} open reviewer question{'' if reviewer_open == 1 else 's'}" if reviewer_open else ""
    return (f"{owed_count} owed, {undisposed_count} undisposed{asked_text}{reviewers}, "
            f"against catalog v{vault.catalog.version}")


def reviewer_open(vault, row):
    """A reviewer question nobody has disposed of: `open`, or a row with an error."""
    return row.state == "open" or not row_valid(vault, row)


def reviewer_pending(vault, row):
    """A reviewer question the gates still hold: open, invalid, or asked and waiting for its answer."""
    return reviewer_open(vault, row) or row.state == "asked"


def asked_count(vault, kept, reviewers):
    """Valid `asked` copies and reviewer questions: pending, but not undisposed, so the line names them apart."""
    return (sum(1 for d in kept if d.valid and d.state == "asked")
            + sum(1 for r in reviewers if r.state == "asked" and row_valid(vault, r)))


# ------------------------------------------------------------------ the ledger rules

QUOTE_RE = re.compile(r'^"(?P<text>[^"]+)"\s+in\s+\[\[(?P<page>[^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]$')
MIN_QUOTE_WORDS = 4
_QUOTE_MARKS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
_WIKILINK_TEXT = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
UNK_RE = re.compile(r"\bUNK-\d{3}\b")


def normal_text(text):
    """Text as a quote is compared: lower case, curly quotes straight, Markdown emphasis, code ticks and
    link brackets gone, runs of whitespace one space."""
    text = _WIKILINK_TEXT.sub(r"\1", text.translate(_QUOTE_MARKS)).replace("\\|", "|")
    return " ".join(re.sub(r"[*_`]", "", text).lower().split())


REVIEWS_HEADING = "Reviews"


def _section_span(page, heading):
    """The 1-based line range (first, last) of the first `## <heading>` section, or None."""
    start = next((h.line for h in page.headings if h.level == 2 and h.text == heading), 0)
    if not start:
        return None
    later = [h.line for h in page.headings if h.level == 2 and h.line > start]
    return start, (min(later) - 1 if later else len(page.text.split("\n")))


def quotable_text(page):
    """The hand-written body of a page: no frontmatter, no generated block, no HTML comment. On the ledger
    page the ledger section is left out, so a row cannot be evidenced by itself. On a session record the
    `## Reviews` section is left out: it holds the reviewers' own words and the quotes a merge already
    dropped, so neither can come back as evidence through a re-run or a ledger row."""
    lines = page.text.split("\n")
    _, body_start, _ = split_frontmatter(page.text)
    skip = set(range(1, max(body_start, 1)))
    for block in page.blocks:
        skip.update(range(block.start, block.end + 1))
    spans = [ledger.section_lines(page)] if page.id == ledger.PAGE_ID else []
    if page.type == "session":
        spans.append(_section_span(page, REVIEWS_HEADING))
    for span in spans:
        if span:
            skip.update(range(span[0], span[1] + 1))
    kept = "\n".join(line for n, line in enumerate(lines, start=1) if n not in skip)
    return _HTML_COMMENT.sub(" ", kept)


def quote_problem(vault, value, label):
    """Why `value` is not a quote that can be checked, or "" when it is on its page. A quote is
    `"<the words>" in [[<page>]]`, and the words must be hand-written text on that page, so evidence cannot
    be made up."""
    match = QUOTE_RE.match(value)
    if not match:
        return f'{label} must be "<the words>" in [[<page>]], the words and the page they are on'
    name = match["page"].strip()
    page = vault.page(name)
    if page is None:
        return f"{label} cites [[{name}]], which is not a page in this vault"
    words = normal_text(match["text"])
    if len(words.split()) < MIN_QUOTE_WORDS:
        return f'{label} "{match["text"]}" has fewer than {MIN_QUOTE_WORDS} words, too few to show where it came from'
    if words not in normal_text(quotable_text(page)):
        return f'{label} "{match["text"]}" is not in the written text of [[{name}]]'
    return ""


# A not-applicable reason that defers rather than rules out. "not-applicable means it does not apply, never not
# yet": a question waiting on something is an unknown or an assumption, and recording it as ruled out takes it off
# every gate. Each cue is narrow, because a ruling-out often says "until", "after" or "later" too: "out of scope
# until INI-004", "ruled out after reading the contract", "closed two years later". The tests hold both lists.
_PERIOD = r"(?<!years )(?<!months )(?<!weeks )(?<!days )(?<!year )(?<!month )(?<!week )(?<!day )"
_WHO = r"(?:we|they|someone|somebody|the \w+)"
_LEARN = r"(?:know|hear|decide|confirm|answer|see|get|agree)s?"
DEFERRAL_CUES = tuple(re.compile(p, re.I) for p in (
    r"\bfor (?:now|the moment|the time being)\b",
    r"\b(?:depends|depending|dependent) on\b",
    rf"\buntil (?:after\b|UNK-\d|{_WHO} {_LEARN}\b|(?:it|this|that) is (?:known|decided|confirmed|answered|settled)\b)",
    r"(?<!\bno )(?<!\bnot )\bpending\b",
    _PERIOD + r"\blater\b(?!\s+than)",
    r"\b(?:tbd|tbc)\b",
    r"\bto be (?:decided|confirmed|determined|agreed|checked|settled)\b",
    r"\b(?:revisit|decide|reconsider|review|confirm|check|look again|come back|wait)\b(?:\s+\S+){0,4}?\s+(?:after|once|when)\b",
    r"\bnot (?:yet|known yet|decided yet)\b|\byet to\b|\b(?:known|decided|confirmed|answered|settled|clear) yet\b",
    r"\b(?:defer(?:s|red|ring)?|parked|on hold)\b|\bwait(?:ing)? (?:for|on)\b",
    rf"\bonce {_WHO} {_LEARN}\b",
))


def deferral_cue(reason):
    """The words of a not-applicable reason that defer the question rather than rule it out, or ""."""
    if not isinstance(reason, str):
        return ""
    found = [m for m in (cue.search(reason) for cue in DEFERRAL_CUES) if m]
    return min(found, key=lambda m: m.start()).group(0) if found else ""


def _f(row, code, message, fix):
    return Finding(row.path, row.line, code, message, fix)


def _links(value, row):
    return links_in(value, row.line) if value else ()


def _source_problem(vault, source):
    """source: is exactly one SRC-nn that sources.md has, or exactly one verified quote. Nothing else, so an
    SRC-nn beside a made-up sentence can never switch the quote check off."""
    if not source:
        return 'answered needs source: one SRC-nn from sources.md, or the answer quoted as "<the words>" in [[<page>]]'
    if schema.SOURCE_ID_RE.match(source):
        known = {i for i in vault.row_ids if schema.SOURCE_ID_RE.match(i)}
        return "" if source in known else f"source {source} is not a row in sources.md"
    if not QUOTE_RE.match(source):
        return 'source must be exactly one SRC-nn, or exactly one quote as "<the words>" in [[<page>]]'
    return quote_problem(vault, source, "source")


def _unknown_problems(vault, row):
    ids = list(dict.fromkeys(UNK_RE.findall(row.get("unknown"))))
    if not ids:
        return ["unknown needs unknown: the UNK-nnn that asks it"]
    need = []
    for unknown_id in ids:
        item = vault.item(unknown_id)
        if item is None or item.kind != "unknown":
            need.append(f"{unknown_id} is not an unknown in this vault")
        elif not schema.OWNER_BULLET_RE.match(item.fact("Owner")):
            need.append(f"{unknown_id} has no owner handle")
        elif item.fact("State").lower() == "resolved":
            need.append(f"{unknown_id} is resolved; record the answer")
        elif item.fact("State").lower() != "open":
            need.append(f"{unknown_id} is {item.fact('State') or 'not open'}, so it is not asking the question")
    return need


def _evidence_problems(vault, row):
    """What the row's state needs and its evidence lacks, as phrases."""
    need = []
    state = row.state
    allowed = ledger.STATE_KEYS.get(state, ()) + (ledger.REVIEWER_KEYS if row.kind == "reviewer" else ("covers",))
    for key, _ in row.evidence:
        if key not in allowed:
            need.append(f"{key}: does not belong on a row that is {state}")
    if state == "asked" and not any(l.anchor.startswith("^c") for l in _links(row.get("capture"), row)):
        need.append("asked needs capture: a link to the capture where it was asked, such as [[<session>#^c07]]")
    if state == "answered":
        if not _links(row.get("item"), row):
            need.append("answered needs item: a link to the item that holds the answer")
        if not row.get("answer"):
            need.append("answered needs answer: the answer, in one line")
        need.append(_source_problem(vault, row.get("source")))
    if state == "assumed":
        if not row.get("belief"):
            need.append("assumed needs belief: what is believed")
        if row.get("load-bearing") not in ("yes", "no"):
            need.append("assumed needs load-bearing: yes or no")
        if not row.get("signpost"):
            need.append("assumed needs signpost: what would show the belief is failing")
    if state == "unknown":
        need += _unknown_problems(vault, row)
    if state == "not-applicable" and not row.get("reason"):
        need.append("not-applicable needs reason: why the question does not apply")
    if row.kind == "reviewer":
        if not row.get("question"):
            need.append("a reviewer question needs question: the question the reviewer raised")
        if not row.get("quote"):
            need.append('a reviewer question needs quote: "<the words>" in [[<page>]]')
        else:
            need.append(quote_problem(vault, row.get("quote"), "quote"))
        if row.has("severity") and row.get("severity") not in catalog.SEVERITIES:
            need.append("severity is high or normal")
    return [n for n in need if n]


def _copy_problem(vault, row):
    """(code, message) when a readable copy or wildcard row names nothing owed, else None."""
    entry = vault.catalog.entry(row.entry)
    if entry is None:
        return "E803", f"{row.copy} names {row.entry}, which is not in catalog v{vault.catalog.version}"
    if row.kind == "wildcard":
        prefix = SUBJECT_PREFIX[entry.scope]
        if not row.subject.startswith(prefix):
            return "E803", f"{row.copy} is a wildcard for a {entry.scope} entry, so it must start {row.entry}@{prefix}"
        if entry.scope == "initiative":
            return "W804", (f"{row.copy} is a wildcard on an initiative entry, which has one copy. "
                            f"Write {row.entry}@{_initiative_id(vault) or 'INI-001'} instead.")
        if not any(_covers(vault, row, c) == 2 for c in owed(vault)):
            return "W804", f"{row.copy} matches no owed copy, so it covers nothing now. It stays as a record."
        if not any(best is row for _, best, _ in _assignments(vault)):
            return "W804", f"{row.copy} is shadowed: every copy it matches has a row of its own or a longer wildcard. It stays as a record."
        return None
    initiative_cover = row.subject == _initiative_id(vault) and entry.scope != "initiative"
    if row.has("covers") and not initiative_cover:
        return "E803", f"{row.copy}: covers: belongs on an initiative row such as {row.entry}@{_initiative_id(vault) or 'INI-001'}"
    if initiative_cover:
        if row.get("covers") != entry.scope:
            return "E803", (f"{row.copy} is an initiative row for a {entry.scope} entry, so it needs covers: {entry.scope}")
        if not any(_covers(vault, row, c) == 1 for c in owed(vault)):
            return "W804", f"{row.copy} covers no owed copy now. It stays as a record."
        return None
    if not SUBJECT_ID_RE[entry.scope].match(row.subject):
        return "E803", f"{row.copy} names {row.subject}, which is not a {entry.scope} ID, the scope of {row.entry}"
    found = subject(vault, row.subject)
    if found is None:
        return "W804", f"{row.copy} is orphaned: {row.subject} is no longer in the vault. The row stays as a record."
    if not any(c.id == row.copy for c in owed(vault)):
        return "W804", (f"{row.copy} is no longer owed: {row.subject} no longer matches the trigger "
                        f"'{entry.trigger.text}'. The row stays as a record.")
    return None


def _row_findings(vault):
    """{row line: [Finding]} for every row: E801 malformed, E802 evidence, E803 and W804 naming. Cached, because
    dispositions need to know which rows are broken."""
    if "row_findings" in vault.cache:
        return vault.cache["row_findings"]
    found, seen = {}, {}
    areas = vault.catalog.area_codes
    vault.cache["row_findings"] = found  # a wildcard check reads assignments, which never read findings
    for row in rows(vault):
        out = found.setdefault(row.line, [])
        problems = list(row.problems)
        if row.kind and row.copy in seen:
            problems.append(f"it is also a row at line {seen[row.copy]}")
        seen.setdefault(row.copy, row.line)
        if problems:
            out.append(_f(row, "E801", f"Question ledger row {row.copy or '(empty)'} is malformed: {'; '.join(problems)}.",
                          "Write | <copy> | <state> | <key: value; key: value> | @handle | YYYY-MM-DD |, as CONVENTIONS.md shows."))
            continue
        if row.kind == "reviewer" and row.area not in areas:
            out.append(_f(row, "E803", f"{row.copy} names area {row.area}, which catalog v{vault.catalog.version} does not have.",
                          f"Use one of: {', '.join(areas)}."))
        elif row.kind != "reviewer":
            problem = _copy_problem(vault, row)
            if problem:
                code, message = problem
                fix = ("Fix the copy ID, or remove the row." if code == "E803"
                       else "Leave it as a record, or remove the row once nobody needs it.")
                out.append(_f(row, code, message, fix))
        need = _evidence_problems(vault, row)
        if need:
            out.append(_f(row, "E802", f"{row.copy} is {row.state}, but {'; '.join(need)}.",
                          "Correct the evidence so check can verify it." if row.state == "open"
                          else "Add the evidence, or set the state to open."))
        cue = deferral_cue(row.get("reason")) if row.state == "not-applicable" else ""
        if cue:
            out.append(_f(row, "E802", f"{row.copy} is not-applicable, but its reason defers the question rather than "
                          f"ruling it out (\"{cue}\"): not-applicable means it does not apply, never not yet.",
                          "If the answer is waiting on something, record the row as unknown, with unknown: an open "
                          "UNK-nnn that has an owner, or as assumed, with belief:, load-bearing: and signpost:. If it "
                          "truly does not apply, say why in reason: without deferring it."))
    return found


def _page_findings(vault):
    """E801 for ledger tables and headings planner cannot read as the ledger."""
    page = ledger_page(vault)
    for other in vault.pages:
        if other is not page:
            for table in ledger.ledger_tables(other):
                yield Finding(other.path, table.line, "E801", "A question ledger table belongs on 11-unknowns-and-risks.md, "
                              "so planner never reads this one.", "Move its rows under ## Question ledger on 11-unknowns-and-risks.md.")
    if page is None:
        return
    for table in ledger.lookalike_tables(page):
        yield Finding(page.path, table.line, "E801",
                      f"The table under ## {ledger.HEADING} is headed '{' | '.join(table.header)}', not exactly "
                      f"'{' | '.join(ledger.HEADER)}', so planner does not read its rows.",
                      f"Make the header exactly | {' | '.join(ledger.HEADER)} |.")
    for table in ledger.misplaced_tables(page):
        yield Finding(page.path, table.line, "E801", f"A ledger table must sit under ## {ledger.HEADING}, and this one does not.",
                      f"Move it under ## {ledger.HEADING}.")
    for heading in ledger.extra_headings(page):
        yield Finding(page.path, heading.line, "E801", f"## {ledger.HEADING} appears twice, and the ledger has one section.",
                      "Merge the rows under the first heading.")


def _missing_heading(vault):
    """W813 when the ledger page exists without its heading while copies are owed: every answer would have
    nowhere to go, and a plain check would otherwise say nothing until the epics gate."""
    page = ledger_page(vault)
    count = len(owed(vault))
    if page is None or ledger.heading_line(page) or not count:
        return
    yield Finding(page.path, 1, "W813", f"{page.path} has no ## {ledger.HEADING} heading; {count} owed "
                  f"cop{'y has' if count == 1 else 'ies have'} nowhere to be recorded.",
                  f"Add ## {ledger.HEADING} after ## Risks, as CONVENTIONS.md shows under \"Questions and the ledger\".")


def ledger_findings(vault, today=None):
    """E801 for a malformed row or an unreadable ledger table, E802 for a state without its evidence, E803 for a
    row that names nothing the catalog can owe, W804 for a row whose copy is orphaned, no longer owed, or
    shadowed, W812 for a row dated after today, and W813 for a ledger page with no ledger heading."""
    yield from _page_findings(vault)
    yield from _missing_heading(vault)
    for row in rows(vault):
        yield from _row_findings(vault).get(row.line, ())
        if today and ledger.is_date(row.date) and row.date > today:
            yield _f(row, "W812", f"{row.copy} is dated {row.date}, which is after today ({today}).",
                     "Correct the date, or leave it if the decision is booked ahead.")


# ------------------------------------------------------------------ planner questions

def copy_answer(vault, d):
    c = d.copy
    return {"id": c.id, "entry": c.entry.id, "area": c.entry.area, "severity": c.entry.severity,
            "question": c.entry.question, "subject": c.subject.id, "subject_kind": c.subject.kind,
            "subject_page": c.subject.page.path if c.subject.page is not None else None,
            "state": d.state or "no row", "valid": d.valid, "row": d.row.line if d.row else None, "via": d.via or None,
            "pending": d.pending, "blocks": list(blocks(vault, c))}


def reviewer_answer(vault, row):
    severity = row.get("severity") if row.get("severity") in catalog.SEVERITIES else "normal"
    valid = row_valid(vault, row)
    return {"id": row.copy, "entry": None, "area": row.area, "severity": severity, "question": row.get("question"),
            "subject": None, "subject_kind": "reviewer", "subject_page": None, "state": row.state, "valid": valid, "row": row.line, "via": None,
            "pending": row.state in ("open", "asked") or not valid, "blocks": []}


def listing(vault, area=None, open_only=False, subject_id=None):
    """What `planner questions` reports, as data json.dumps can write. The counts cover the copies the
    area and subject filters keep; --open then keeps only the pending ones in the list: undisposed, or asked
    and still waiting, because both hold the gates. A row with an error counts as undisposed, the same as
    check says."""
    kept = [d for d in dispositions(vault) if (area is None or d.copy.entry.area == area)
            and (subject_id is None or d.copy.subject.id == subject_id)]
    reviewers = [r for r in reviewer_rows(vault) if (area is None or r.area == area)] if subject_id is None else []
    undisposed = sum(1 for d in kept if d.undisposed)
    opened = [r for r in reviewers if reviewer_open(vault, r)]
    asked = asked_count(vault, kept, reviewers)
    return {
        **catalog.version_keys(vault.catalog.version),
        "coverage": coverage_line(vault, len(kept), undisposed, len(opened), asked),
        "owed": len(kept),
        "undisposed": undisposed,
        "asked": asked,
        "reviewer_questions": len(reviewers),
        "reviewer_open": len(opened),
        "copies": [copy_answer(vault, d) for d in kept if d.pending or not open_only],
        "reviewer": [reviewer_answer(vault, r) for r in reviewers if reviewer_pending(vault, r) or not open_only],
    }


# ------------------------------------------------------------------ the digest and the counts

BAND_NAMES = {1: "high, and blocks something", 2: "high", 3: "the rest"}


def _band(severity, blocked):
    return 1 if severity == "high" and blocked else 2 if severity == "high" else 3


# A digest this long or shorter is shown whole: it reads in one go. Past it, as with the v3 full run's 48 lines,
# normal lines bury the high ones, so the text view counts them by area. It is a view, never a cap: --all, --open,
# --json and the ledger block still give every line.
DIGEST_READS_WHOLE = 10


def consequential(group):
    """A digest line the lead sees in full: high severity, or it blocks something. The rest are counted by
    area with the command that lists them, and every one stays in --open, --json and the ledger block."""
    return group["severity"] == "high" or bool(group["blocks"])


def digest(vault, area=None, subject_id=None):
    """The pending copies (undisposed, or asked and still waiting) grouped by entry, so one answer can serve
    many, and the pending reviewer questions, ranked: high severity that blocks something first, then high,
    then the rest. Within a band the order is by entry ID, so it never changes between runs. Nothing is left out."""
    kept = [d for d in dispositions(vault) if (area is None or d.copy.entry.area == area)
            and (subject_id is None or d.copy.subject.id == subject_id)]
    groups = {}
    for d in kept:
        if d.pending:
            groups.setdefault(d.copy.entry.id, []).append(d)
    out = []
    for entry_id, found in groups.items():
        entry = found[0].copy.entry
        blocked = sorted({unit for d in found for unit in blocks(vault, d.copy)})
        why = {}
        for d in found:
            why[d.label] = why.get(d.label, 0) + 1
        out.append({"band": _band(entry.severity, blocked), "entry": entry_id, "area": entry.area,
                    "severity": entry.severity, "question": entry.question, "copies": [d.copy.id for d in found],
                    "why": why, "blocks": blocked})
    reviewers = [r for r in reviewer_rows(vault) if area is None or r.area == area] if subject_id is None else []
    for row in reviewers:
        if not reviewer_pending(vault, row):
            continue
        answer = reviewer_answer(vault, row)
        out.append({"band": _band(answer["severity"], []), "entry": row.copy, "area": row.area,
                    "severity": answer["severity"], "question": answer["question"], "copies": [row.copy],
                    "why": {state_label(row.state, answer["valid"]): 1}, "blocks": []})
    opened = sum(1 for r in reviewers if reviewer_open(vault, r))
    asked = asked_count(vault, kept, reviewers)
    out.sort(key=lambda g: (g["band"], g["entry"]))
    undisposed = sum(1 for d in kept if d.undisposed)
    return {**catalog.version_keys(vault.catalog.version), "coverage": coverage_line(vault, len(kept), undisposed, opened, asked),
            "owed": len(kept), "undisposed": undisposed, "asked": asked, "reviewer_open": opened, "groups": out}


def stats(vault, area=None):
    """For each entry, how many copies the vault owes and how each ended, and how often it ended
    not-applicable: the evidence for pruning an entry or tightening its trigger. Pruning is the user's call."""
    found = dispositions(vault)
    out = []
    for entry in vault.catalog.entries:
        if area is not None and entry.area != area:
            continue
        mine = [d for d in found if d.copy.entry.id == entry.id]
        states = {state: sum(1 for d in mine if d.valid and (d.state or "no row") == state)
                  for state in ("no row",) + ledger.STATES}
        states["invalid"] = sum(1 for d in mine if not d.valid)
        na = states["not-applicable"]
        out.append({"entry": entry.id, "area": entry.area, "owed": len(mine),
                    "states": {k: v for k, v in states.items() if v}, "not_applicable": na,
                    "not_applicable_share": round(na / len(mine), 2) if mine else 0.0})
    return {**catalog.version_keys(vault.catalog.version), "entries": out}


# ------------------------------------------------------------------ the gates

DISPOSE = "Answer it, rule it out with a reason, or record it as an unknown with an owner or as an assumption."


def _ledger_location(vault):
    """Where a gate reports a copy with no row: the `## Question ledger` heading, or line 1 of the page."""
    page = ledger_page(vault)
    if page is None:
        return "11-unknowns-and-risks.md", 1
    return page.path, ledger.heading_line(page) or 1


def _ledger_gap(vault):
    """What is missing for the ledger to exist, in words for a finding: the page, or its heading. "" when both are there."""
    page = ledger_page(vault)
    if page is None:
        return "The vault has no 11-unknowns-and-risks.md ledger page."
    if not ledger.heading_line(page):
        return "The page has no ## Question ledger heading."
    return ""


def _standing(d):
    return "has no ledger row" if d.row is None else f"is {state_label(d.state, d.valid)}" + (f" (by {d.via})" if d.via else "")


def epics_gate(vault):
    """E805 for each high-severity copy or reviewer question still open, asked or with no row. These
    are the questions whose silence costs most: lawful basis, partner clauses, stored-value liability."""
    path, heading = _ledger_location(vault)
    gap = _ledger_gap(vault)
    page = ledger_page(vault)
    adding = ("Add the page, with a ## Question ledger heading. " if page is None
              else "Add ## Question ledger to the page. " if gap else "")
    for d in dispositions(vault):
        if d.copy.entry.severity != "high" or not d.pending:
            continue
        message = f"{d.copy.id} is high severity and {_standing(d)}: {d.copy.entry.question}"
        yield Finding(path, d.row.line if d.row else heading, "E805",
                      f"{message} {gap}".strip() if d.row is None else message,
                      f"{adding}{DISPOSE} {schema.E805_OVERRIDE_HINT}")
    for row in reviewer_rows(vault):
        if row.get("severity") == "high" and reviewer_pending(vault, row):
            label = state_label(row.state, row_valid(vault, row))
            yield Finding(path, row.line, "E805", f"{row.copy} is high severity and is {label}: {row.get('question')}",
                          f"{DISPOSE} {schema.E805_OVERRIDE_HINT}")


def load_bearing_assumptions(vault):
    """The rows a passing epics gate rests on: `assumed`, `load-bearing: yes`, on a high-severity copy or
    reviewer question. The gate counts an assumption as disposed, so these are named, never hidden."""
    found = {d.row.copy: d.row.line for d in dispositions(vault) if d.valid and d.state == "assumed"
             and d.copy.entry.severity == "high" and d.row.get("load-bearing") == "yes"}
    found.update({r.copy: r.line for r in reviewer_rows(vault) if r.state == "assumed" and r.get("severity") == "high"
                  and r.get("load-bearing") == "yes" and row_valid(vault, r)})
    return sorted(found, key=lambda copy: found[copy])


def shape_gate(vault):
    """W806 for each row still `assumed`. An assumption clears into a decision, a requirement or a
    constraint before Shape closes (Volere), or it stays a belief nobody checked."""
    for row in rows(vault):
        if row.state == "assumed" and row.kind:
            yield Finding(row.path, row.line, "W806", f"{row.copy} is still assumed: {row.get('belief') or 'no belief given'}.",
                          "Once the plan holds it, set the row to answered with an item link, or record it as an unknown "
                          "with an owner. Say in the session why it stays assumed if it does.")


def unit_location(vault, unit_id):
    """(path, line) where check reports on a unit: an item's heading, a page's state line, or a table row."""
    item = vault.item(unit_id)
    if item is not None:
        return item.page.path, item.line
    pages = vault.by_id.get(unit_id)
    if pages:
        return pages[0].path, meta_line(pages[0], "state")
    if unit_id in vault.row_ids:
        page, line = vault.row_ids[unit_id]
        return page.path, line
    return None


def can_be_blocked(vault, unit_id):
    """Whether any catalog entry blocks a unit of this ID's kind: a party, a stored value or a readme never is."""
    kinds = {kind for entry in vault.catalog.entries for kind in entry.blocks}
    return any(uid == unit_id for kind in kinds for uid, _page, _item in _units(vault)[kind])


def grill_gate(vault, items):
    """W807 for each copy still open, asked or with no row that blocks an item on the Grill's agenda.
    A warning, never an error: the lead may decide anyway. It prints only under --gate grill --item, so the
    Grill's capture "decided with <copy IDs> open (W807)" is what records that it was open."""
    for unit_id in items:
        where = unit_location(vault, unit_id)
        if where is None:
            yield Finding(*_ledger_location(vault), "W807", f"{unit_id} has no page or line to report on, so no open question can be shown against it.",
                          "Name an item the vault holds as a heading, a page or a table row.")
            continue
        if not can_be_blocked(vault, unit_id):
            yield Finding(where[0], where[1], "W807", f"No catalog question blocks {unit_id}: it is not a unit of any kind the catalog holds up.",
                          "A Grill on it gets no ledger warning. Name the app, contract, requirement, capability or concern it touches.")
            continue
        for d in dispositions(vault):
            if d.pending and unit_id in blocks(vault, d.copy):
                yield Finding(where[0], where[1], "W807",
                              f"{d.copy.id} {_standing(d)} and blocks {unit_id}: {d.copy.entry.question}",
                              "Put it on the agenda and settle it first, or decide anyway and capture "
                              "\"decided with <copy IDs> open (W807)\": that capture is the record, because W807 "
                              "prints only under this gate.")


# ------------------------------------------------------------------ a subject nobody typed

WORD_RE = re.compile(r"[A-Za-z]+")
KIND_NAMES = {"party": "party", "stored-value": "stored value"}


def _fact_texts(page):
    """(line, text) for the page's fact bullets and hand-kept table rows. Prose, generated blocks and
    the ledger itself are left out: a fact is where a subject would be typed."""
    for bullet in page.bullets:
        if not bullet.generated:
            yield bullet.line, bullet.value
    for table in page.tables:
        if table.generated or tuple(table.header[:len(ledger.HEADER)]) == ledger.HEADER:
            continue
        for cells, line in zip(table.rows, table.row_lines):
            yield line, " ".join(cells)


def _kinds_on(vault, page):
    """The subject kinds a page holds as headings or links to."""
    kinds = {i.kind for found in vault.items.values() for i in found if i.page is page}
    for link in page.links:
        first = link.anchor.split()[0] if link.anchor.split() else ""
        item = vault.item(first) if first else None
        if item is not None:
            kinds.add(item.kind)
    return kinds & set(KIND_NAMES)


def _exception_pattern(phrase):
    words = [re.escape(w[:-1]) + "[a-z]*" if w.endswith("*") else re.escape(w) for w in phrase.split()]
    return re.compile(r"\b" + r"\s+".join(words) + r"\b")


def mentioned(entry, text):
    """The entry's mention words in lower-case `text`, in the order they are written, once the phrases the
    entry says are not the subject ("credit card", "story point") are taken out."""
    for phrase in entry.mention_except:
        text = _exception_pattern(phrase).sub(" ", text)
    forms = set(entry.mentions)
    return [w for w in WORD_RE.findall(text) if w in forms]


def untyped_mentions(vault):
    """W809 where a fact says "points", "clause" or another word an existence question lists, the page
    neither holds nor links a subject of the kind that question creates, and that question has no answer
    yet. A missed extraction would otherwise leave the ledger looking clean. Once per page and question."""
    creators = [e for e in vault.catalog.entries if e.creates and e.mentions]
    initiative = _initiative_id(vault)
    settled = {d.copy.entry.id for d in dispositions(vault) if d.copy.subject.kind == "initiative" and not d.undisposed}
    for page in sorted(vault.pages, key=lambda p: p.path):
        if page.type == "session":
            continue  # captures are the raw record; close types what they name
        if page.type == "sources":
            continue  # a source's title names a document, not a subject
        kinds = _kinds_on(vault, page)
        told = set()
        for line, text in sorted(_fact_texts(page)):
            prose = WIKILINK.sub("", CODE_SPAN.sub("", text)).lower()
            for entry in creators:
                if entry.id in told or entry.id in settled or entry.creates in kinds:
                    continue
                hits = mentioned(entry, prose)
                if not hits:
                    continue
                told.add(entry.id)
                copy = f"{entry.id}@{initiative}" if initiative else entry.id
                kind = KIND_NAMES[entry.creates]
                yield Finding(page.path, line, "W809",
                              f"'{hits[0]}' may be an untyped subject: this page holds or links no {kind}, and {copy} "
                              f"has no answer yet ({entry.question})",
                              f"Type it as ### {SUBJECT_PREFIX[entry.creates]}nn on 03-context-and-scope.md and link it "
                              f"from here, or answer {copy} in the question ledger.")
