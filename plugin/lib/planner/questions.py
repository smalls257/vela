"""Which questions a vault owes. Pure: reads the Vault and its catalogue, returns data.

A catalogue entry is a template with a scope. Code applies it once per subject its trigger
matches, so the copies multiply and nobody has to remember them. A copy's ID is
`<entry>@<subject>`: it stays the same while the subject keeps its ID, so a renamed file
carries its questions with it. The same vault always gives the same copies in the same order.
"""
import re
from dataclasses import dataclass

from planner import catalog, schema
from planner.model import meta_line

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
