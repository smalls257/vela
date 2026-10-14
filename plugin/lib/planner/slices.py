"""Slices: which flows make up each slice the flow checker proves. Pure: a vault in, slices out.

This is the one place that answers "which flows does this slice prove". check-slice and check's W391 both ask it, and
nothing else reads the bullets behind it, so when slices get pages of their own (`slices/SLC-nnn-*.md` with
`**Flows:**`, `**After:**`, `**Joins:**`, a status and overrides) only this module changes. A Shield against the
Distributed Monolith in which every caller parses the releases page its own way.

Today a slice is read from the releases page: release one's `**Tracer:**` flows are the tracer slice, and a later
release's `**Flows:**` bullet names its own. A release that names no flows is not a slice.
"""
from dataclasses import dataclass

from planner import releases


@dataclass(frozen=True)
class Slice:
    id: str  # "" while slices are read from releases; SLC-nnn once they have pages
    name: str  # the release heading today, "Release one: pilot"
    flows: tuple  # flow ids, in the order written
    path: str  # the page that names the flows
    line: int  # the bullet that names them
    order: int  # 0 for the first slice; slices before this one are the ones it may start from (F13)


def read_slices(vault):
    """Every slice in the vault, in order."""
    found = releases.releases(vault)
    page = releases.page(vault)
    out = []
    for n, release in enumerate(found):
        if n == 0 and release.tracer_flows:
            flows, line = release.tracer_flows, release.tracer_line
        elif release.flows:
            flows, line = release.flows, release.flows_line
        else:
            continue
        out.append(Slice("", release.name, tuple(flows), page.path if page else "", line, len(out)))
    return out
