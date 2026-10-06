"""Which questions a vault owes. Pure: reads the Vault and its catalogue, returns data.

A catalogue entry is a template with a scope. Code applies it once per subject its trigger
matches, so the copies multiply and nobody has to remember them. A copy's ID is
`<entry>@<subject>`: it stays the same while the subject keeps its ID, so a renamed file
carries its questions with it. The same vault always gives the same copies in the same order.
"""
import re
from dataclasses import dataclass

from planner import catalog, ledger, schema
from planner.model import Finding, meta_line
from planner.parse import links_in

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
    """Every owed copy, sorted by copy ID: each catalogue entry applied once per subject of its
    scope whose facts its trigger matches."""
    if "owed" in vault.cache:
        return vault.cache["owed"]
    by_kind = {}
    for found in subjects(vault):
        by_kind.setdefault(found.kind, []).append(found)
    copies = [Copy(f"{entry.id}@{found.id}", entry, found)
              for entry in vault.catalogue.entries
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

    @property
    def undisposed(self):
        """No row says anything about it yet, or its row says `open`."""
        return self.row is None or self.state == "open"

    @property
    def pending(self):
        """Undisposed, or asked and still waiting for its answer: what the gates hold up."""
        return self.undisposed or self.state == "asked"


def ledger_page(vault):
    pages = vault.by_id.get(ledger.PAGE_ID)
    return pages[0] if pages else None


def rows(vault):
    """Every ledger row on 11-unknowns-and-risks.md, in page order."""
    if "rows" not in vault.cache:
        page = ledger_page(vault)
        vault.cache["rows"] = tuple(ledger.rows(page)) if page is not None else ()
    return vault.cache["rows"]


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


def dispositions(vault):
    """One Disposition per owed copy, in copy order. The copy's own row wins, then the wildcard with
    the longest prefix, then an initiative row that `covers:` the copy's scope. Exceptions take
    their own row. A row whose shape is broken still counts here; check reports it as an error."""
    if "dispositions" in vault.cache:
        return vault.cache["dispositions"]
    readable = [r for r in rows(vault) if r.kind in ("copy", "wildcard") and r.state in ledger.STATES]
    out = []
    for copy in owed(vault):
        best, rank = None, 0
        for row in readable:
            score = _covers(vault, row, copy)
            if score and (score > rank or (score == rank == 2 and len(row.subject) > len(best.subject))):
                best, rank = row, score
        via = "" if best is None or rank == 3 else best.copy
        out.append(Disposition(copy, best.state if best else "", best, via))
    vault.cache["dispositions"] = tuple(out)
    return vault.cache["dispositions"]


def coverage_line(vault, owed_count, undisposed_count):
    """What every report says about coverage. Never "complete": the catalogue only finds what is written into it."""
    return f"{owed_count} owed, {undisposed_count} undisposed, against catalogue v{vault.catalogue.version}"


# ------------------------------------------------------------------ the ledger rules

QUOTE_RE = re.compile(r'^"(?P<text>[^"]+)"\s+in\s+\[\[(?P<page>[^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]$')
_QUOTE_MARKS = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})
_WIKILINK_TEXT = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")


def normal_text(text):
    """Text as a quote is compared: lower case, curly quotes straight, Markdown emphasis, code ticks and
    link brackets gone, runs of whitespace one space."""
    text = _WIKILINK_TEXT.sub(r"\1", text.translate(_QUOTE_MARKS)).replace("\\|", "|")
    return " ".join(re.sub(r"[*_`]", "", text).lower().split())


def quote_problem(vault, value, label):
    """Why `value` is not a quote that can be checked, or "" when it is on its page. A quote is
    `"<the words>" in [[<page>]]`, and the words must be on that page, so evidence cannot be made up."""
    match = QUOTE_RE.match(value)
    if not match:
        return f'{label} must be "<the words>" in [[<page>]], the words and the page they are on'
    page = vault.page(match["page"].strip())
    if page is None:
        return f'{label} cites [[{match["page"].strip()}]], which is not a page in this vault'
    if page.id == ledger.PAGE_ID:
        return f"{label} cites the ledger page itself, which cannot evidence its own rows"
    if normal_text(match["text"]) not in normal_text(page.text):
        return f'{label} "{match["text"]}" is not on [[{match["page"].strip()}]]'
    return ""
UNK_RE = re.compile(r"\bUNK-\d{3}\b")


def _f(row, code, message, fix):
    return Finding(row.path, row.line, code, message, fix)


def _evidence_problems(vault, row):
    """What the row's state needs and its evidence lacks, as phrases."""
    need = []
    state = row.state
    if state == "asked" and not any(l.anchor.startswith("^c") for l in _links(row.get("capture"), row)):
        need.append("asked needs capture: a link to the capture where it was asked, such as [[<session>#^c07]]")
    if state == "answered":
        if not _links(row.get("item"), row):
            need.append("answered needs item: a link to the item that holds the answer")
        source = row.get("source")
        tokens = schema.SOURCE_TOKEN_RE.findall(source)
        sources = {i for i in vault.row_ids if schema.SOURCE_ID_RE.match(i)}
        if not tokens:
            if not source:
                need.append('answered needs source: an SRC-nn from sources.md, or the answer quoted as "<the words>" in [[<page>]]')
            else:
                need.append(quote_problem(vault, source, "source") or "")
        for token in tokens:
            if token not in sources:
                need.append(f"source {token} is not a row in sources.md")
    if state == "assumed":
        if not row.get("belief"):
            need.append("assumed needs belief: what is believed")
        if row.get("load-bearing") not in ("yes", "no"):
            need.append("assumed needs load-bearing: yes or no")
        if not row.get("signpost"):
            need.append("assumed needs signpost: what would show the belief is failing")
    if state == "unknown":
        ids = UNK_RE.findall(row.get("unknown"))
        found = [vault.item(i) for i in ids]
        if not ids:
            need.append("unknown needs unknown: the UNK-nnn that asks it")
        for unknown_id, item in zip(ids, found):
            if item is None or item.kind != "unknown":
                need.append(f"{unknown_id} is not an unknown in this vault")
            elif not schema.OWNER_BULLET_RE.match(item.fact("Owner")):
                need.append(f"{unknown_id} has no owner handle")
    if state == "not-applicable" and not row.get("reason"):
        need.append("not-applicable needs reason: why the question does not apply")
    if row.kind == "reviewer":
        if not row.get("question"):
            need.append("a reviewer question needs question: the question the reviewer raised")
        if not row.get("quote"):
            need.append('a reviewer question needs quote: "<the words>" in [[<page>]]')
        else:
            need.append(quote_problem(vault, row.get("quote"), "quote") or "")
        if row.has("severity") and row.get("severity") not in catalog.SEVERITIES:
            need.append("severity is high or normal")
    return [n for n in need if n]


def _links(value, row):
    return links_in(value, row.line) if value else ()


def _copy_problem(vault, row):
    """(code, message) when a readable copy or wildcard row names nothing owed, else None."""
    entry = vault.catalogue.entry(row.entry)
    if entry is None:
        return "E803", f"{row.copy} names {row.entry}, which is not in catalogue v{vault.catalogue.version}"
    if row.kind == "wildcard":
        prefix = SUBJECT_PREFIX[entry.scope]
        if not row.subject.startswith(prefix):
            return "E803", f"{row.copy} is a wildcard for a {entry.scope} entry, so it must start {row.entry}@{prefix}"
        if not any(_covers(vault, row, c) == 2 for c in owed(vault)):
            return "W804", f"{row.copy} matches no owed copy, so it covers nothing now. It stays as a record."
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


def ledger_findings(vault):
    """E801 for a malformed row, E802 for a state without its evidence, E803 for a row that names
    nothing the catalogue can owe, and W804 for a row whose copy is orphaned or no longer owed."""
    page = ledger_page(vault)
    for other in vault.pages:
        if other is page:
            continue
        for table in ledger.ledger_tables(other):
            yield Finding(other.path, table.line, "E801", "A question ledger table belongs on 11-unknowns-and-risks.md, "
                          "so planner never reads this one.", "Move its rows under ## Question ledger on 11-unknowns-and-risks.md.")
    seen = {}
    areas = vault.catalogue.area_codes
    for row in rows(vault):
        problems = list(row.problems)
        if row.kind and row.copy in seen:
            problems.append(f"it is also a row at line {seen[row.copy]}")
        seen.setdefault(row.copy, row.line)
        if problems:
            yield _f(row, "E801", f"Question ledger row {row.copy or '(empty)'} is malformed: {'; '.join(problems)}.",
                     "Write | <copy> | <state> | <key: value; key: value> | @handle | YYYY-MM-DD |, as CONVENTIONS.md shows.")
            continue
        if row.kind == "reviewer" and row.area not in areas:
            yield _f(row, "E803", f"{row.copy} names area {row.area}, which catalogue v{vault.catalogue.version} does not have.",
                     f"Use one of: {', '.join(areas)}.")
        elif row.kind != "reviewer":
            problem = _copy_problem(vault, row)
            if problem:
                code, message = problem
                fix = ("Fix the copy ID, or remove the row." if code == "E803"
                       else "Leave it as a record, or remove the row once nobody needs it.")
                yield _f(row, code, message, fix)
        need = _evidence_problems(vault, row)
        if need:
            yield _f(row, "E802", f"{row.copy} is {row.state}, but {'; '.join(need)}.",
                     "Add the evidence, or set the state to open.")


# ------------------------------------------------------------------ planner questions

def copy_answer(vault, d):
    c = d.copy
    return {"id": c.id, "entry": c.entry.id, "area": c.entry.area, "severity": c.entry.severity,
            "question": c.entry.question, "subject": c.subject.id, "subject_kind": c.subject.kind,
            "state": d.state or "no row", "row": d.row.line if d.row else None, "via": d.via or None,
            "pending": d.pending, "blocks": list(blocks(vault, c))}


def reviewer_answer(row):
    severity = row.get("severity") if row.get("severity") in catalog.SEVERITIES else "normal"
    return {"id": row.copy, "entry": None, "area": row.area, "severity": severity, "question": row.get("question"),
            "subject": None, "subject_kind": "reviewer", "state": row.state, "row": row.line, "via": None,
            "pending": row.state in ("open", "asked"), "blocks": []}


def listing(vault, area=None, open_only=False, subject_id=None):
    """What `planner questions` reports, as data json.dumps can write. The counts cover the copies the
    area and subject filters keep; --open then keeps only the undisposed ones in the list."""
    kept = [d for d in dispositions(vault) if (area is None or d.copy.entry.area == area)
            and (subject_id is None or d.copy.subject.id == subject_id)]
    reviewers = [r for r in reviewer_rows(vault) if (area is None or r.area == area)] if subject_id is None else []
    undisposed = sum(1 for d in kept if d.undisposed)
    return {
        "catalogue": vault.catalogue.version,
        "coverage": coverage_line(vault, len(kept), undisposed),
        "owed": len(kept),
        "undisposed": undisposed,
        "reviewer_questions": len(reviewers),
        "reviewer_open": sum(1 for r in reviewers if r.state == "open"),
        "copies": [copy_answer(vault, d) for d in kept if d.undisposed or not open_only],
        "reviewer": [reviewer_answer(r) for r in reviewers if r.state == "open" or not open_only],
    }
