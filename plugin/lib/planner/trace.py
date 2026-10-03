"""Traceability: what the epics deliver against what the vault says must be delivered.

Pure. One computation feeds the T-rule findings in `rules` and the
`traceability` block in `render`, so the check and the page never disagree.
"""
import re
from dataclasses import dataclass

from planner import schema
from planner.parse import FENCE

AC_LINE = re.compile(r"^\s*\d+\.\s+(?P<body>.*?)(?P<markers>(?:\s*(?<!\[)\[[A-Za-z][A-Za-z0-9-]*\](?!\]))+)\.?\s*$")
SECTION_HEADING = re.compile(r"^##\s+(?P<text>.*?)\s*#*\s*$")
MARKER = re.compile(r"\[([A-Za-z][A-Za-z0-9-]*)\]")


@dataclass(frozen=True)
class Gap:
    rule: str  # "T1", "T2", "T4" or "T6"
    subject: str  # what the gap is about, for example "CAP-014" or "concern-data × APP-website"
    page: object  # the page the finding points at
    line: int  # 0 means "the line of `field` in the frontmatter"
    field: str
    anchor: str  # heading to link to, "" for the page
    message: str
    fix: str


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
    """Concern names marked on the page's numbered acceptance criteria, e.g. {"testing"}.

    Only the acceptance-criteria section counts, so a numbered line under "Out of scope"
    or "Rollout" cannot satisfy a concern. A struck-through criterion (its text starts
    with ~~) carries no markers. Lines inside code fences and generated blocks are skipped.
    """
    skip = set()
    for block in page.blocks:
        skip.update(range(block.start, block.end + 1))
    found, fence, in_criteria = set(), None, False
    for n, raw in enumerate(page.text.split("\n"), start=1):
        opening = FENCE.match(raw)
        if fence:
            if raw.strip().startswith(fence):
                fence = None
            continue
        if opening:
            fence = opening.group(1)
            continue
        if n in skip:
            continue
        section = SECTION_HEADING.match(raw)
        if section:
            in_criteria = section["text"].strip().lower().endswith("acceptance criteria")
            continue
        if not in_criteria:
            continue
        match = AC_LINE.match(raw)
        if match and not match["body"].lstrip().startswith("~~"):
            found.update(m.lower() for m in MARKER.findall(match["markers"]))
    return found


def report(vault):
    all_epics = epics(vault)
    gaps, checked = [], 0
    for rule in (_t1, _t2, _t4, _t6):
        found, count = rule(vault, all_epics)
        gaps.extend(found)
        checked += count
    return Report(tuple(gaps), checked)


def _t1(vault, all_epics):
    delivered = {v for e in all_epics for v in listed(e, "delivers")}
    caps = [c for c in sorted(vault.of_type("capability"), key=lambda p: p.id)
            if c.meta.get("change") in schema.ENUMS["change@capability"] and c.meta.get("change") != "unchanged"]
    gaps = [Gap("T1", c.id, c, 0, "change", "",
                f"No epic delivers {c.id} ({c.meta['change']}), so nobody is planned to build it.",
                f"Add {c.id} to delivers on the epic that builds it, or set change: unchanged if nothing changes.")
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
                                f"{contract.id} is {change} and its provider is outside this vault, but no epic delivers or consumes it.",
                                f"Add {contract.id} to consumes on the epic that builds the client."))
        elif contract.id not in delivered:
            gaps.append(Gap("T2", contract.id, contract.page, contract.line, "", contract.heading,
                            f"{contract.id} is {change}, but no epic delivers its provider side.",
                            f"Add {contract.id} to delivers on the provider team's epic."))
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
        waiver = waiver_state(cell.text)
        if waiver == "waiver":
            continue
        for_app = [e for e in all_epics if app.id in listed(e, "apps")]
        if waiver == "malformed":
            gaps.append(Gap("T4", subject, cell.concern, cell.line, "", "",
                            f"{subject} reads like a waiver, but not in the waiver form, so it covers nothing.",
                            "Write it as: no work (@handle, review YYYY-MM-DD): <reason>."))
        elif cell.concern.id == schema.OWNERSHIP_CONCERN:
            if not for_app:
                gaps.append(Gap("T4", subject, cell.concern, cell.line, "", "",
                                f"{subject} is addressed, but no epic lists {app.id} in apps, so no team is planned to own the work.",
                                f"Add {app.id} to apps on the epic its team owns, or write the cell as a waiver."))
        elif not any(name in markers[e.id] for e in for_app):
            gaps.append(Gap("T4", subject, cell.concern, cell.line, "", "",
                            f"{subject} is addressed, but no epic for {app.id} has an acceptance criterion marked [{name}].",
                            f"End the numbered acceptance criterion that does this work with [{name}] on an epic listing {app.id}, "
                            "or write a waiver: no work (@handle, review YYYY-MM-DD): <reason>."))
    return gaps, count


def _t6(vault, all_epics):
    gaps = [Gap("T6", e.id, e, 0, "delivers", "",
                f"{e.id} delivers nothing, so it traces to no capability, contract or goal.",
                "List what it builds or changes in delivers, or delete the epic.")
            for e in all_epics if isinstance(e.meta.get("delivers"), list) and not e.meta["delivers"]]
    return gaps, len(all_epics)
