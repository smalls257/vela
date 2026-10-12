"""One fixed layout: where every app and outside party sits, pinned in a file so it never moves.

Spatial memory is the point (research note, 2026-10-10-visualizing-dependencies-and-flows): the reader learns that
Coach is top right, and every view, the cockpit, the line map, the minimap, the flow lanes, keeps it there. A
position never comes from a force layout or from the screen size.

    <vault>/.planner/explorer-pins.json   {node key: [col, row]}

A node the file lacks takes the nearest free cell to where the layout would put it; a pinned node is never moved.
The caller names the file: the vault's own, or a file kept elsewhere. When that file does not exist yet the caller
may name a seed to start from, so a layout a lead has already seen carries over. Ported from the gallery mockup's
maps/extract.py.
"""
import json
import pathlib

PINS_FILE = ".planner/explorer-pins.json"


def ideal_layout(nodes, contracts):
    """Where the layout would put each node: reader-facing apps left, providers right, outside parties in a band
    below. Column is the longest chain of "uses" from the most reader-facing app; cycles are broken by a score
    (provided-to-apps minus consumed-from-apps, then key), so the result is a pure function of the record."""
    apps = [n["key"] for n in nodes if n["kind"] == "app"]
    uses = {a: set() for a in apps}
    score = {a: 0 for a in apps}
    for c in contracts:
        if c["providerKind"] != "app" or c["provider"] not in uses:
            continue
        for consumer in c["consumers"]:
            if consumer != c["provider"] and consumer in uses:
                uses[consumer].add(c["provider"])
                score[c["provider"]] += 1
                score[consumer] -= 1
    order = {a: (score[a], a) for a in apps}
    col = {}

    def column(a, trail=()):
        if a in col:
            return col[a]
        before = [b for b in apps if a in uses[b] and order[b] < order[a] and b not in trail]
        col[a] = 0 if not before else 1 + max(column(b, trail + (a,)) for b in before)
        return col[a]

    for a in sorted(apps, key=lambda k: order[k]):
        column(a)
    max_col = max(col.values(), default=0)
    by_col = {}
    for a in sorted(apps, key=lambda k: (col[k], order[k])):
        by_col.setdefault(col[a], []).append(a)
    keys = [n["key"] for n in nodes]
    neighbours = {k: set() for k in keys}
    for c in contracts:
        for consumer in c["consumers"]:
            if consumer != c["provider"] and consumer in neighbours and c["provider"] in neighbours:
                neighbours[c["provider"]].add(consumer)
                neighbours[consumer].add(c["provider"])
    row = {}
    for k in sorted(by_col):
        members = by_col[k]
        if k == 0:
            for i, a in enumerate(members):
                row[a] = i
            continue
        bary = {a: sum(row[n] for n in neighbours[a] if n in row) / max(1, len([n for n in neighbours[a] if n in row]))
                for a in members}
        for i, a in enumerate(sorted(members, key=lambda m: (bary[m], m))):
            row[a] = i
        offset = (max(len(by_col[0]), 1) - len(members)) / 2
        for a in members:
            row[a] = round(row[a] + offset)
    partners = [n["key"] for n in nodes if n["kind"] != "app"]
    band = max(row.values(), default=0) + 1
    want = {}
    for p in partners:
        near = [col[n] for n in neighbours[p] if n in col]
        want[p] = round(2 * sum(near) / len(near)) / 2 if near else max_col + 1
    groups = {}
    for p in sorted(partners, key=lambda k: (want[k], k)):
        groups.setdefault(want[p], []).append(p)
    for spot, members in groups.items():
        for i, p in enumerate(members):
            col[p] = round(spot + (i - (len(members) - 1) / 2) * 0.6, 2)
            row[p] = band
    return {k: [col[k], row[k]] for k in col}


def read_pins(source):
    """The pins in a file, or a ValueError naming it when it is not a map of key to [col, row]. A pins file that
    cannot be read stops the build: laying the map out again would move every app the lead has learned."""
    try:
        pins = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot read pins file {source}: {exc}") from exc
    if not isinstance(pins, dict) or not all(isinstance(v, list) and len(v) == 2 for v in pins.values()):
        raise ValueError(f"pins file {source} is not a map of node key to [column, row]")
    return pins


def pinned(path, nodes, contracts, seed=None):
    """({key: [col, row]}, added keys, stale keys, seed name used). With a path, reads that pins file (else the
    seed's pins), places any new node at the nearest free cell and writes the file back. With no path the layout
    is computed and nothing is written."""
    path = pathlib.Path(path) if path else None
    seed = pathlib.Path(seed) if seed else None
    source = path if path and path.exists() else seed if seed and seed.exists() else None
    pins = read_pins(source) if source else {}
    ideal = ideal_layout(nodes, contracts)
    taken = {tuple(v) for v in pins.values()}
    added = []
    for key in sorted(ideal, key=lambda k: (ideal[k][0], ideal[k][1], k)):
        if key in pins:
            continue
        c, r = ideal[key]
        ring = 0
        while True:
            free = [(c + dc, r + dr) for dc in range(-ring, ring + 1) for dr in range(-ring, ring + 1)
                    if max(abs(dc), abs(dr)) == ring and (c + dc, r + dr) not in taken and c + dc >= 0]
            if free:
                spot = sorted(free, key=lambda p: (abs(p[0] - c), abs(p[1] - r), p))[0]
                break
            ring += 1
        pins[key] = list(spot)
        taken.add(spot)
        added.append(key)
    stale = sorted(k for k in pins if k not in ideal)
    if path and (added or not path.exists()):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(sorted(pins.items())), indent=2) + "\n", encoding="utf-8")
    return pins, added, stale, (seed.name if source and source == seed else "")
