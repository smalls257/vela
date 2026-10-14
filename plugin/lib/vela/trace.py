"""Traceability: what the epics deliver against what the vault says must be delivered.

Pure. One computation feeds the T-rule findings in `rules` and the
`traceability` block in `render`, so the check and the page never disagree.
"""
import re
from dataclasses import dataclass

from vela import criteria, plainwords, schema
from vela.diagrams import external_name

SECTION_HEADING = re.compile(r"^##\s+(?P<text>.*?)\s*#*\s*$")


@dataclass(frozen=True)
class Gap:
    rule: str  # "T1", "T2", "T4", "T6" or "T7"
    subject: str  # what the gap is about, for example "CAP-014" or "concern-data × APP-website"
    page: object  # the page the finding points at
    line: int  # 0 means "the line of `field` in the frontmatter"
    field: str
    anchor: str  # heading to link to, "" for the page
    message: str
    fix: str
    label: str = ""  # what a reader calls the subject, "Hold a seat (CAP-014)"; subject stays the key rules.py matches on


@dataclass(frozen=True)
class Report:
    gaps: tuple
    checked: int  # how many capabilities, contracts, cells and epics the rules looked at

    @property
    def passed(self):
        return self.checked - len(self.gaps)


def epics(vault):
    return sorted(vault.of_type("epic"), key=lambda p: p.id)


def listed(epic, key):
    """An epic's frontmatter list, or [] when it is missing or malformed (E103 and E105 report those)."""
    values = epic.meta.get(key)
    return [v for v in values if isinstance(v, str)] if isinstance(values, list) else []


def ac_markers(page):
    """Concern names marked on the page's acceptance criteria, e.g. {"testing"}.

    Only the acceptance-criteria section counts (`## Epic acceptance criteria`, or `## Done when` in the epic template),
    so a numbered line under "Out of scope" or "Rollout" cannot satisfy a concern. A struck-through criterion carries no
    markers. Lines inside code fences and generated blocks are skipped. `criteria.read` is the one reader of both shapes.
    """
    return {marker for c in criteria.read(page) for marker in c.markers}


def _title(page):
    title = page.meta.get("title")
    return title.strip() if isinstance(title, str) and title.strip() else page.name


def named(name, item_id):
    """A name with its ID as a tag: "Consent check (CON-003)". The bare ID when there is no name."""
    name = (name or "").strip()
    return f"{name} ({item_id})" if name and name != item_id else item_id


# What a capability's `change` does, said as a verb: "which this initiative adds".
CHANGE_VERBS = {"new": "adds", "extend": "extends", "replace": "replaces", "narrow": "narrows", "retire": "retires"}


def _provider(contract):
    external = contract.fact("Provider")
    return external_name(external) if external else _title(contract.page)


def report(vault):
    all_epics = epics(vault)
    gaps, checked = [], 0
    for rule in (_t1, _t2, _t4, _t6, _t7):
        found, count = rule(vault, all_epics)
        gaps.extend(found)
        checked += count
    return Report(tuple(gaps), checked)


def _t1(vault, all_epics):
    delivered = {v for e in all_epics for v in listed(e, "delivers")}
    caps = [c for c in sorted(vault.of_type("capability"), key=lambda p: p.id)
            if c.meta.get("change") in schema.ENUMS["change@capability"] and c.meta.get("change") != "unchanged"]
    gaps = [Gap("T1", c.id, c, 0, "change", "",
                f"No epic delivers {named(_title(c), c.id)}, which this initiative "
                f"{CHANGE_VERBS.get(c.meta['change'], 'changes')}, so nobody is planned to build it.",
                f"Add {c.id} to delivers on the epic that builds it, or set change: unchanged if nothing changes.",
                named(_title(c), c.id))
            for c in caps if c.id not in delivered]
    return gaps, len(caps)


def _t2(vault, all_epics):
    delivered = {v for e in all_epics for v in listed(e, "delivers")}
    consumed = {v for e in all_epics for v in listed(e, "consumes")}
    gaps, count = [], 0
    for contract in vault.contracts:
        change = contract.fact("Change")
        if change not in schema.TRACE_CONTRACT_CHANGES:
            continue
        count += 1
        if contract.fact("Provider"):  # external provider: the vault plans only the client side
            if contract.id not in delivered | consumed:
                gaps.append(Gap("T2", contract.id, contract.page, contract.line, "", contract.heading,
                                f"{named(contract.name, contract.id)} is a {change} contract with {_provider(contract)}, "
                                "outside this vault, but no epic builds the side that calls it.",
                                f"Add {contract.id} to consumes on the epic that builds the client.",
                                named(contract.name, contract.id)))
        elif contract.id not in delivered:
            gaps.append(Gap("T2", contract.id, contract.page, contract.line, "", contract.heading,
                            f"No epic builds {named(contract.name, contract.id)}, the {change} contract "
                            f"{_provider(contract)} must offer.",
                            f"Add {contract.id} to delivers on the provider team's epic.",
                            named(contract.name, contract.id)))
    return gaps, count


def waiver_state(text):
    """"waiver" for a well-formed waiver, "malformed" for text that starts like one, else ""."""
    if schema.WAIVER_RE.match(text):
        return "waiver"
    return "malformed" if text.lower().startswith("no work") else ""


def _t4(vault, all_epics):
    apps = {a.name.lower(): a for a in vault.apps}
    markers = {e.id: ac_markers(e) for e in all_epics}
    gaps, count = [], 0
    for cell in sorted(vault.cells, key=lambda c: (c.concern.id, c.line)):
        app = apps.get(cell.app.lower())
        if app is None or cell.state != "addressed":
            continue  # E201, E301 and E315 report broken and missing cells
        count += 1
        name = cell.concern.id[len("concern-"):]
        subject = f"{cell.concern.id} × {app.id}"
        label = f"{_title(cell.concern)} for {_title(app)}"
        waiver = waiver_state(cell.text)
        if waiver == "waiver":
            continue
        for_app = [e for e in all_epics if app.id in listed(e, "apps")]
        if waiver == "malformed":
            gaps.append(Gap("T4", subject, cell.concern, cell.line, "", "",
                            f"{label} reads like a waiver, but not in the waiver form, so it covers nothing.",
                            "Write it as: no work (@handle, review YYYY-MM-DD): <reason>.", label))
        elif cell.concern.id == schema.OWNERSHIP_CONCERN:
            if not for_app:
                gaps.append(Gap("T4", subject, cell.concern, cell.line, "", "",
                                f"{label} is covered, but no epic is for {_title(app)}, so no team is planned to own the work.",
                                f"Add {app.id} to apps on the epic its team owns, or write the cell as a waiver.", label))
        elif not any(name in markers[e.id] for e in for_app):
            gaps.append(Gap("T4", subject, cell.concern, cell.line, "", "",
                            f"{label} is covered, but no epic for {_title(app)} has a done-when check that does this work.",
                            f"End the numbered acceptance criterion that does this work with [{name}] on an epic listing {app.id}, "
                            "or write a waiver: no work (@handle, review YYYY-MM-DD): <reason>.", label))
    return gaps, count


def _t7(vault, all_epics):
    """A functional requirement nobody is allocated: every epic can pass while it goes unbuilt."""
    from vela import allocation
    gaps = [Gap("T7", r.id, r.page, r.line, "", r.heading,
                f"{named(r.name, r.id)} is {plainwords.state_word(r.fact('State'))}, but no app has taken it on "
                "(no Requirements allocated row), so no team owns it.",
                f"Run /planner:allocate {r.id.split('.')[0]}, or add a row for {r.id} to the app page that delivers it.",
                named(r.name, r.id))
            for r in allocation.unallocated(vault)]
    return gaps, len(allocation.due(vault))


def _t6(vault, all_epics):
    gaps = [Gap("T6", e.id, e, 0, "delivers", "",
                f"{named(_title(e), e.id)} delivers nothing, so it traces to no capability, contract or goal.",
                "List what it builds or changes in delivers, or delete the epic.", named(_title(e), e.id))
            for e in all_epics if isinstance(e.meta.get("delivers"), list) and not e.meta["delivers"]]
    return gaps, len(all_epics)
