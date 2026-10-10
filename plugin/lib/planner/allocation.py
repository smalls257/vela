"""Allocation: each functional requirement divided among the apps and contracts that deliver it. Pure.

A capability's requirements say what the business needs, naming no app. Each app page's `## Requirements allocated`
table says its share of each, and which contracts carry the part that crosses to another app. One computation feeds
the E330-E333 findings, T7 in the trace report, and the `allocation` block, so they never disagree.
"""
import re
from dataclasses import dataclass

from planner import schema

REQUIREMENT_ID = re.compile(r"\bCAP-\d{3}\.FR\d+\b")
CONTRACT_ID = re.compile(r"\bCON-\d{3}\b")
ALLOCATED_STATES = ("inkling", "assumption", "decided")
CARRIED_STATES = ("assumption", "fact", "decided")  # a requirement at one of these must be allocated


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
    """{requirement ID: [rows that carry it]}."""
    out = {}
    for row in rows(vault):
        if row.requirement:
            out.setdefault(row.requirement, []).append(row)
    return out


def unallocated(vault):
    """Requirements at assumption, fact or decided that no app's table carries."""
    have = carried(vault)
    return [r for r in requirements(vault) if r.fact("State") in CARRIED_STATES and r.id not in have]


def matrix(vault):
    """(apps that carry anything, [(requirement, {app id: share})]) for the allocation block."""
    have = carried(vault)
    apps = sorted({row.app.id: row.app for rows_ in have.values() for row in rows_}.values(), key=lambda p: p.id)
    out = []
    for req in requirements(vault):
        shares = {}
        for row in have.get(req.id, []):
            through = f" ({', '.join(row.through)})" if row.through else ""
            shares[row.app.id] = (shares.get(row.app.id, "") + "; " if row.app.id in shares else "") + row.share + through
        out.append((req, shares))
    return apps, out
