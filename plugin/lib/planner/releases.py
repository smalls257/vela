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
FLOW_ID = re.compile(r"\bFLO-\d+\b")
ITEM_ID = re.compile(r"\b[A-Z]{3}-[A-Za-z0-9]+(?:\.FR\d+)?\b")
_LEADING_LINKS = re.compile(r"^\s*(?:\[\[[^\]]+\]\]\s*(?:,\s*|$))+")
_NONE = re.compile(r"^none\b\s*,?\s*(.*)$", re.I)


@dataclass
class Row:
    requirement: str  # "CAP-002.FR2", or "" when the cell names none
    criteria: tuple  # () for "all", else the 1-based criterion numbers
    raw_criteria: str
    note: str
    line: int


@dataclass(frozen=True)
class Left:
    """One piece a lead left out of the tracer: what, the IDs it names (an app, a contract, a requirement), and why."""
    text: str
    ids: tuple
    reason: str
    line: int


@dataclass
class Release:
    name: str  # the section heading, "Release one: January board demo"
    line: int
    target: str
    state: str
    rows: list = field(default_factory=list)
    declared: bool = False  # it carries a Target or State bullet, which is what makes a ## section a release
    tracer_line: int = 0
    tracer_given: bool = False  # it has a **Tracer:** bullet of any kind, including "none, reason" and plain words
    tracer_flows: tuple = ()  # flow ids in the order they run
    tracer_words: str = ""  # the thin version in plain words
    tracer_none: str = ""  # the reason, when the lead chose no tracer; "no reason given" if the bullet says only none
    not_in_tracer: list = field(default_factory=list)  # [Left]


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


def read_tracer(value):
    """(flow ids, words, none-reason) from a Tracer bullet's text. One or more flow links in the order they run, then
    an optional comma and plain words; or `none, <reason>`; or plain words with no link."""
    none = _NONE.match(value.strip())
    if none:
        return (), "", none.group(1).strip() or "no reason given"
    lead = _LEADING_LINKS.match(value)
    head, words = (value[:lead.end()], value[lead.end():]) if lead else ("", value)
    flows = []
    for found in FLOW_ID.findall(head):
        if found not in flows:
            flows.append(found)
    return tuple(flows), words.strip().lstrip(",").strip(), ""


def read_left(value, line):
    """A Not-in-the-tracer entry: the words before the first colon name the piece (IDs may sit in parentheses or
    links), the words after it give the reason."""
    head, colon, reason = value.partition(":")
    ids = tuple(dict.fromkeys(ITEM_ID.findall(head)))
    return Left(value.strip(), ids, reason.strip() if colon else "", line)


def first_release(vault):
    """Release one, the only release that carries a tracer, or None when there are no releases."""
    found = releases(vault)
    return found[0] if found else None


def releases(vault):
    """Every release on the releases page, in page order, outside History. A ## section is a release when it has a
    Target or State bullet or a Delivers table; any other section (Notes, Open questions) is prose and is left out."""
    p = page(vault)
    if p is None:
        return []
    out, current, in_history = [], None, False
    lines = p.text.split("\n")
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
                current.declared = True
            m = re.match(r"^- \*\*(Tracer|Not in the tracer):\*\*\s*(.*)$", line)
            if m and m.group(1) == "Tracer":
                current.tracer_given, current.tracer_line = True, n
                current.tracer_flows, current.tracer_words, current.tracer_none = read_tracer(m.group(2))
            elif m:
                current.not_in_tracer.append(read_left(m.group(2), n))
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
    return [r for r in out if r.declared or r.rows]


def reach(vault, release):
    """(app ids, contract ids) that carry a share of what this release delivers, in first-seen order: the apps whose
    allocation rows carry its requirements and the contracts those shares go through."""
    carried = allocation.carried(vault)
    apps, contracts = [], []
    for row in release.rows:
        for share in carried.get(row.requirement, []):
            if share.app.id not in apps:
                apps.append(share.app.id)
            contracts += [c for c in share.through if c not in contracts]
    return apps, contracts


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
    today_apps = {a.id: ("absent" if a.meta.get("change") == "new" else "exists") for a in vault.apps}
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
