"""One fixed layout: where every app and outside party sits, pinned in a file so it never moves.

Spatial memory is the point (research note, 2026-10-10-visualizing-dependencies-and-flows): the reader learns that
Coach is top right, and every view, the cockpit, the line map, the minimap, the flow lanes, keeps it there. A
position never comes from a force layout or from the screen size.

    <vault>/.vela/explorer-pins.json   {node key: [col, row]}

A position is a pair of numbers, fractional where a reader dropped a box between cells: a box stays where it is put.
The one rule (check_move, and layout.js in the page) is that no box is drawn over another: two boxes, as drawn, keep
at least GAP pixels between their edges. The first layout, and a node the file lacks, take whole cells: the nearest
free cell to where the layout would put it. A pinned node is never moved unless it sits on another box (see
`settle`). A key that starts "grp:" is not a node: it places a cluster of the grouped map (view-map's drag), and is
not a box this rule checks.
The caller names the file: the vault's own, or a file kept elsewhere. When that file does not exist yet the caller
may name a seed to start from, so a layout a lead has already seen carries over. Ported from the gallery mockup's
maps/extract.py.
"""
import itertools
import json
import pathlib

PINS_FILE = ".vela/explorer-pins.json"
GROUP_PREFIX = "grp:"
# How a cell is drawn on the cockpit, the minimap and the releases view (they share this frame, so a box clear of its
# neighbors on one is clear on all): pixels per column and per row, and how far below its row an outside party is
# drawn (the parties' band). The page reads these numbers from the build (D.pins.frame); #selftest checks every
# view's boxes fit inside BOX.
FRAME = {"cw": 380, "rh": 128, "bandGap": 104}
BOX = {"w": 190, "h": 70}  # the largest box any of them draws: the minimap's 190 by 70 (the cockpit's is 176 by 66)
GAP = 20  # pixels kept clear between two boxes' edges, so two boxes never touch
SLACK = 0.5  # pixels: a box placed exactly GAP away, then rounded to the thousandth of a cell, still counts as clear
MIN_PARTY_ROW_WIDTH = 3  # outside parties wrap to a new row past this many columns, or the apps' width when wider
LIMIT = 10_000  # a column or row beyond this is a typo or an attack, not a layout


def is_node(key):
    return not key.startswith(GROUP_PREFIX)


def drawn(cell, kind):
    """Where a box's center is drawn, in the frame's pixels: an outside party a band below its row."""
    return cell[0] * FRAME["cw"], cell[1] * FRAME["rh"] + (FRAME["bandGap"] if kind != "app" else 0)


def clash(a, kind_a, b, kind_b):
    """True when two boxes, as drawn, come closer than GAP to one another."""
    (ax, ay), (bx, by) = drawn(a, kind_a), drawn(b, kind_b)
    return abs(ax - bx) < BOX["w"] + GAP - SLACK and abs(ay - by) < BOX["h"] + GAP - SLACK


def crowded(taken, col, row, kind):
    """True when a box of `kind` at (col, row) would come too close to one already placed; `taken` is
    [(col, row, kind)]."""
    return any(clash((col, row), kind, (c, r), k) for c, r, k in taken)


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
    neighbors = {k: set() for k in keys}
    for c in contracts:
        for consumer in c["consumers"]:
            if consumer != c["provider"] and consumer in neighbors and c["provider"] in neighbors:
                neighbors[c["provider"]].add(consumer)
                neighbors[consumer].add(c["provider"])
    row = {}
    for k in sorted(by_col):
        members = by_col[k]
        if k == 0:
            for i, a in enumerate(members):
                row[a] = i
            continue
        bary = {a: sum(row[n] for n in neighbors[a] if n in row) / max(1, len([n for n in neighbors[a] if n in row]))
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
        near = [col[n] for n in neighbors[p] if n in col]
        want[p] = sum(near) / len(near) if near else max_col + 1
    for p in partners:
        col[p] = max(0, int(want[p] + 0.5))  # whole columns: a half column is narrower than the box drawn on it
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


def check_move(pins, kinds):
    """Why this layout cannot be drawn without overlap, or "" when it can. `pins` is {key: [col, row]} and `kinds`
    {node key: "app" | "partner"}; keys beyond `kinds` (clusters) are not boxes. Two boxes, as drawn, keep GAP
    pixels between their edges; an outside party is drawn a band below its row, so it is measured there."""
    boxes = sorted(((v[0], v[1], k) for k, v in pins.items() if k in kinds), key=lambda x: (x[0], x[1], x[2]))
    reach = (BOX["w"] + GAP) / FRAME["cw"]  # columns: past this, nothing further right can touch
    for i, (c1, r1, k1) in enumerate(boxes):
        for c2, r2, k2 in itertools.islice(boxes, i + 1, None):
            if c2 - c1 >= reach:
                break
            if clash((c1, r1), kinds[k1], (c2, r2), kinds[k2]):
                return f"{k1} and {k2} would overlap: boxes keep {GAP} px apart as drawn"
    return ""


# The rule's cases, played by tests/test_explorer_layout.py against check_move and by #selftest against the page's
# copy of the rule (a selftest build carries them, with check_move's answer, as D.pins.cases): one table, so the two
# copies cannot drift apart without a test saying so.
MOVE_KINDS = {"APP-a": "app", "APP-b": "app", "PTY-01": "partner"}
MOVE_CASES = (
    ("two apps in one place", {"APP-a": [0, 0], "APP-b": [0, 0]}),
    ("two apps half a column apart in one row", {"APP-a": [0, 0], "APP-b": [0.5, 0]}),
    ("two apps 0.6 of a column apart in one row", {"APP-a": [0, 0], "APP-b": [0.6, 0]}),
    ("two apps 0.6 of a row apart in one column", {"APP-a": [0, 0], "APP-b": [0, 0.6]}),
    ("two apps 0.75 of a row apart in one column", {"APP-a": [0, 0], "APP-b": [0, 0.75]}),
    ("two apps close on a diagonal", {"APP-a": [0, 0], "APP-b": [0.5, 0.6]}),
    ("two apps just clear on a diagonal", {"APP-a": [0, 0], "APP-b": [0.5, 0.75]}),
    ("a party pinned in an app's own cell, drawn a band below it", {"APP-a": [0, 0], "PTY-01": [0, 0]}),
    ("a party a quarter row above an app", {"APP-a": [0, 1], "PTY-01": [0, 0.75]}),
    ("a party above every app, clear of them", {"APP-a": [0, 2], "APP-b": [1, 2], "PTY-01": [0, 0]}),
    ("whole cells, with a cluster key", {"APP-a": [0, 0], "APP-b": [1, 0], "PTY-01": [0, 1], "grp:x": [0, 0]}),
)


def move_cases():
    """MOVE_CASES with check_move's answer to each, as the page's selftest reads them."""
    return [{"name": name, "pins": pins, "kinds": MOVE_KINDS, "says": check_move(pins, MOVE_KINDS)} for name, pins in MOVE_CASES]


def validate(pins, allowed):
    """A browser's pins as {key: [col, row]} of finite numbers, or a ValueError saying what is wrong. `allowed` is the
    set of keys already in the file: a page can move what is pinned and order clusters, it cannot invent a node."""
    if not isinstance(pins, dict) or not pins or len(pins) > 2000:
        raise ValueError("pins must be a map of key to [column, row] with at least one key")
    out = {}
    for key, cell in pins.items():
        if not isinstance(key, str) or len(key) > 300 or not (key in allowed or key.startswith(GROUP_PREFIX)):
            raise ValueError(f"{str(key)[:60]!r} is not a node this vault has pinned")
        ok = (isinstance(cell, list) and len(cell) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in cell)
              and all(abs(x) <= LIMIT for x in cell) and cell[0] >= 0)
        if not ok:
            raise ValueError(f"{key} must be [column, row], numbers, column not below 0")
        out[key] = [int(x) if float(x).is_integer() else x for x in cell]
    return out


def write_pins(path, pins):
    """Write the pins file as the build does: sorted keys, two-space indent. Written beside and renamed, so a reader
    of the file never sees half of it."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    scratch = path.with_name(path.name + ".tmp")
    scratch.write_text(json.dumps(dict(sorted(pins.items())), indent=2) + "\n", encoding="utf-8")
    scratch.replace(path)


def settle(pins, kinds):
    """(pins, moved keys): the pins with every box that sits on another one moved to the nearest free cell. The
    first of two boxes (by column, row, key) keeps its place, so a lead's pins stay put and only the later of two
    overlapping boxes moves. Keys that are not nodes (clusters) pass through unchanged."""
    out = {k: list(v) for k, v in pins.items()}
    nodes = sorted((k for k in out if k in kinds), key=lambda k: (out[k][0], out[k][1], k))
    width = max(MIN_PARTY_ROW_WIDTH, 1 + max((round(out[k][0]) for k in nodes), default=0))
    moved, taken = [], []
    for k in nodes:
        c, r = out[k]
        if not crowded(taken, c, r, kinds[k]):
            taken.append((c, r, kinds[k]))
            continue
        # a party stays in its band, along the row and then onto the next; an app takes the nearest free cell in any direction
        spot = nearest_free(taken, round(c), round(r), kinds[k], width if kinds[k] == "partner" else None)
        out[k] = list(spot)
        taken.append((*spot, kinds[k]))
        moved.append(k)
    return out, moved


def nearest_free(taken, col, row, kind, width=None):
    """The free cell nearest (col, row) for a box of `kind`: ring by ring, or, with a width, along that row and then
    the rows below it (a row of parties wraps instead of running on without end)."""
    if width is not None:
        r = row
        while True:
            free = [c for c in range(0, width) if not crowded(taken, c, r, kind)]
            if free:
                return min(free, key=lambda c: (abs(c - col), c)), r
            r += 1
    ring = 0
    while True:
        free = [(col + dc, row + dr) for dc in range(-ring, ring + 1) for dr in range(-ring, ring + 1)
                if max(abs(dc), abs(dr)) == ring and col + dc >= 0 and row + dr >= 0 and not crowded(taken, col + dc, row + dr, kind)]
        if free:
            return sorted(free, key=lambda p: (abs(p[0] - col), abs(p[1] - row), p))[0]
        ring += 1


def pinned(path, nodes, contracts, seed=None):
    """({key: [col, row]}, added keys, stale keys, seed name used, moved keys). With a path, reads that pins file (else
    the seed's pins), settles any box that sits on another, places any new node at the nearest free cell and writes
    the file back. With no path the layout is computed and nothing is written."""
    path = pathlib.Path(path) if path else None
    seed = pathlib.Path(seed) if seed else None
    source = path if path and path.exists() else seed if seed and seed.exists() else None
    pins = read_pins(source) if source else {}
    ideal = ideal_layout(nodes, contracts)
    kinds = {n["key"]: n["kind"] for n in nodes}
    asked = {k: list(v) for k, v in pins.items()}
    pins.update(settle({k: v for k, v in pins.items() if k in kinds}, kinds)[0])
    taken = [(v[0], v[1], kinds[k]) for k, v in pins.items() if k in kinds]
    width = max(MIN_PARTY_ROW_WIDTH, 1 + max((c for k, (c, _) in ideal.items() if kinds[k] == "app"), default=0))
    added = []
    for key in sorted(ideal, key=lambda k: (ideal[k][0], ideal[k][1], k)):
        if key in pins:
            continue
        c, r = ideal[key]
        spot = nearest_free(taken, c, r, kinds[key], width if kinds[key] == "partner" else None)
        pins[key] = list(spot)
        taken.append((*spot, kinds[key]))
        added.append(key)
    moved = sorted(k for k in asked if k in kinds and list(pins[k]) != list(asked[k]))
    stale = sorted(k for k in pins if is_node(k) and k not in ideal)
    if path and (added or moved or not path.exists()):
        write_pins(path, pins)
    return pins, added, stale, (seed.name if source and source == seed else ""), moved
