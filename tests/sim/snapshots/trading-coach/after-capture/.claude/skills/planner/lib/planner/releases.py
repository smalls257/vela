"""Releases: what each one delivers, and what the system looks like after it. Pure.

A release is a section on `04b-releases.md` listing the functional requirements it delivers, or some of each
one's acceptance criteria, so one epic or one requirement can span releases. Nothing else carries a release:
which apps change and which contracts exist after a release is computed from the requirements it delivers,
through each app's allocated share and the contracts that share goes through. "Today" is what exists before
the initiative: apps that are not new, and contracts whose change is not new.
"""
import re
from dataclasses import dataclass, field

from planner import allocation, schema

PAGE_ID = "releases"
HEADER = ("Delivers", "Criteria", "Note")
STATES = ("inkling", "assumption", "decided")
CRITERION = re.compile(r"^AC(\d+)$", re.I)
EXISTS_TODAY = ("changed", "integrated", "unchanged", "retire")  # an app with one of these is there before the initiative


@dataclass
class Row:
    requirement: str  # "CAP-002.FR2", or "" when the cell names none
    criteria: tuple  # () for "all", else the 1-based criterion numbers
    raw_criteria: str
    note: str
    line: int


@dataclass
class Release:
    name: str  # the section heading, "Release one: January board demo"
    line: int
    target: str
    state: str
    rows: list = field(default_factory=list)


def page(vault):
    found = vault.by_id.get(PAGE_ID) or []
    return found[0] if found else None


def criteria_of(raw):
    """(numbers, problem): "all" or "" is every criterion; "AC1, AC3" is those."""
    text = raw.strip()
    if text.lower() in ("", "all"):
        return (), ""
    numbers = []
    for part in re.split(r"[,\s]+", text):
        if not part:
            continue
        m = CRITERION.match(part)
        if not m:
            return (), f"'{part}' is not 'all' or ACn"
        numbers.append(int(m.group(1)))
    return tuple(numbers), ""


def releases(vault):
    """Every release on the releases page, in page order, outside History."""
    p = page(vault)
    if p is None:
        return []
    out, current, in_history = [], None, False
    lines = p.text.split("\n")
    tables = {t.row_lines[0] if t.row_lines else -1: t for t in p.tables if not t.generated}
    for n, line in enumerate(lines, 1):
        if line.startswith("## "):
            heading = line[3:].strip()
            in_history = heading.lower() == schema.HISTORY_HEADING.lower()
            current = None if in_history else Release(heading, n, "", "")
            if current:
                out.append(current)
        elif current and not in_history:
            m = re.match(r"^- \*\*(Target|State):\*\*\s*(.*)$", line)
            if m:
                setattr(current, m.group(1).lower(), m.group(2).strip())
    for table in p.tables:
        if table.generated or tuple(table.header)[:3] != HEADER or not table.row_lines:
            continue
        owner = next((r for r in reversed(out) if r.line < table.row_lines[0]), None)
        if owner is None:
            continue
        for cells, line in zip(table.rows, table.row_lines):
            padded = list(cells) + [""] * (3 - len(cells))
            found = allocation.REQUIREMENT_ID.search(padded[0])
            numbers, _ = criteria_of(padded[1])
            owner.rows.append(Row(found.group(0) if found else "", numbers, padded[1].strip(), padded[2].strip(), line))
    return out


def criteria_count(requirement):
    """How many acceptance criteria a requirement lists: the plain bullets under its heading, after its facts."""
    lines = requirement.page.text.split("\n")
    count = 0
    for line in lines[requirement.line:]:
        if line.startswith("#"):
            break
        if re.match(r"^- (?!\*\*[^*]+:\*\*)", line):
            count += 1
    return count


def snapshots(vault):
    """[{"name", "target", "state", "apps": {app id: status}, "contracts": {id: status}, "delivers": [FR ids]}]
    for Today and then after each release, cumulative. An app's status is "exists", "changes", "new" or "absent";
    a contract's is "exists", "new" or "absent"."""
    reqs = {r.id: r for r in allocation.requirements(vault)}
    carried = allocation.carried(vault)
    today_apps = {a.id: ("exists" if a.meta.get("change") in EXISTS_TODAY else "absent") for a in vault.apps}
    today_contracts = {c.id: ("absent" if c.fact("Change") == "new" else "exists") for c in vault.contracts}
    out = [{"name": "Today", "target": "", "state": "fact", "apps": dict(today_apps), "contracts": dict(today_contracts),
            "delivers": []}]
    apps, contracts, delivered = dict(today_apps), dict(today_contracts), []
    for release in releases(vault):
        for row in release.rows:
            if row.requirement not in reqs:
                continue
            if row.requirement not in delivered:
                delivered.append(row.requirement)
            for share in carried.get(row.requirement, []):
                apps[share.app.id] = "changes" if today_apps.get(share.app.id) == "exists" else "new"
                for cid in share.through:
                    if contracts.get(cid) == "absent":
                        contracts[cid] = "new"
        out.append({"name": release.name, "target": release.target, "state": release.state, "apps": dict(apps),
                    "contracts": dict(contracts), "delivers": list(delivered)})
    return out
