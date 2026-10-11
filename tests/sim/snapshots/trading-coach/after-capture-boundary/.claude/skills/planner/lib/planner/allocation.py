"""Allocation: each functional requirement divided among the apps and contracts that deliver it. Pure.

A capability's requirements say what the business needs, naming no app. Each app page's `## Requirements allocated`
table says its share of each, and which contracts carry the part that crosses to another app. One computation feeds
the E330-E333 findings, T7 in the trace report, and the `allocation` block. The block counts the same requirements
T7 does, so its "not allocated" number is T7's gap count.
"""
import re
from dataclasses import dataclass

from planner import schema

REQUIREMENT_ID = re.compile(r"\bCAP-\d{3}\.FR\d+\b")
CONTRACT_ID = re.compile(r"\bCON-\d{3}\b")
# A row at fact records a share an integrated app already carries; like a goal row at fact, its page needs sources.
ALLOCATED_STATES = ("inkling", "assumption", "fact", "decided")
CARRIED_STATES = ("assumption", "fact", "decided")  # a requirement at one of these must be allocated, by a row at one


@dataclass(frozen=True)
class Row:
    app: object  # the app's building-blocks page
    requirement: str  # "CAP-002.FR2", or "" when the cell names none
    share: str
    through: tuple  # contract IDs
    state: str
    line: int


def rows(vault):
    """Every allocation row on every app page, in page and line order."""
    out = []
    for app in sorted(vault.apps, key=lambda p: p.id):
        for table in app.tables:
            if table.generated or tuple(table.header)[:len(schema.ALLOCATION_HEADER)] != schema.ALLOCATION_HEADER:
                continue
            for cells, line in zip(table.rows, table.row_lines):
                padded = list(cells) + [""] * (4 - len(cells))
                found = REQUIREMENT_ID.search(padded[0])
                out.append(Row(app, found.group(0) if found else "", padded[1].strip(),
                               tuple(CONTRACT_ID.findall(padded[2])), padded[3].strip(), line))
    return out


def requirements(vault):
    """Functional requirements in item-ID order."""
    found = [items[0] for item_id, items in vault.items.items() if items and items[0].kind == "requirement"]
    return sorted(found, key=lambda i: (i.id.split(".")[0], int(i.id.split("FR")[1])))


def carried(vault):
    """{requirement ID: [rows that carry it]}. An inkling row, or one with no valid state, is a guess at a share,
    not an owner, so it carries nothing."""
    out = {}
    for row in rows(vault):
        if row.requirement and row.state in CARRIED_STATES:
            out.setdefault(row.requirement, []).append(row)
    return out


def unallocated(vault):
    """Requirements at assumption, fact or decided that no app's table carries."""
    have = carried(vault)
    return [r for r in due(vault) if r.id not in have]


def due(vault):
    """The requirements that must be allocated: those at assumption, fact or decided. T7 and the block both count these."""
    return [r for r in requirements(vault) if r.fact("State") in CARRIED_STATES]


def decided_rows(vault):
    """(subject, row) for each decided row, the subject named as `CAP-nnn.FRn@APP-x` for the decision rules."""
    return [(f"{r.requirement}@{r.app.id}", r) for r in rows(vault) if r.state == "decided" and r.requirement]


def matrix(vault):
    """(apps that carry anything, [(requirement, {app id: share})]) for the allocation block, over the due requirements."""
    have = carried(vault)
    apps = sorted({row.app.id: row.app for rows_ in have.values() for row in rows_}.values(), key=lambda p: p.id)
    out = []
    for req in due(vault):
        shares = {}
        for row in have.get(req.id, []):
            through = f" ({', '.join(row.through)})" if row.through else ""
            shares[row.app.id] = (shares.get(row.app.id, "") + "; " if row.app.id in shares else "") + row.share + through
        out.append((req, shares))
    return apps, out
