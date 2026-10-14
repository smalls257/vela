"""The explorer: breadth-first search over any transition system. Pure apart from the clock it is handed.

It knows nothing about flows. It asks `system` for the initial state, the successors of a state (label, state,
violation), a canonical form (for symmetry) and whether a state breaks an invariant. Breadth-first means the trace
found to any state is a shortest one; sorted successors mean it is the same trace on every run.

A state is "cut" when it breaks an invariant: it is a finding and is not expanded. A transition with a violation (an
illegal change) is recorded and its target is not entered. The state budget is checked before the time budget, and
both stop the search with `complete` False: nothing found after that is claimed, and nothing missing is a pass.
"""
from array import array
from collections import deque
from dataclasses import dataclass, field


@dataclass
class Graph:
    states: list
    parent: array  # parent state id, -1 for the start
    label: list  # the transition from the parent
    flip: bytearray  # 1 when the state was swapped into canonical form from its parent's successor
    succ_count: dict  # expanded state id -> number of successors, legal and illegal
    src: array  # legal transitions as two parallel arrays, for reachability
    dst: array
    cut: dict  # state id -> violation
    violations: list  # [(src id, label, violation)]
    complete: bool = True
    stopped_by: str = ""
    transitions: int = 0
    expanded: int = 0
    by_state: dict = field(default_factory=dict)

    def path(self, sid):
        """[(label, parity of the frame the label was computed in)] from the start to `sid`."""
        chain = []
        while sid > 0:
            chain.append(sid)
            sid = self.parent[sid]
        parity, out = 0, []
        for node in reversed(chain):
            out.append((self.label[node], parity))
            parity ^= self.flip[node]
        return out

    def parity(self, sid):
        p = 0
        while sid > 0:
            p ^= self.flip[sid]
            sid = self.parent[sid]
        return p


def explore(system, max_states, max_seconds, clock):
    start, _ = system.canonical(system.initial())
    index = {start: 0}
    g = Graph([start], array("i", [-1]), [None], bytearray(1), {}, array("i"), array("i"), {}, [])
    broken = system.invariant_broken(start)
    if broken:
        g.cut[0] = broken
    began = clock()
    queue = deque([0])
    while queue:
        if (g.expanded & 255) == 0 and clock() - began > max_seconds:
            g.complete, g.stopped_by = False, "seconds"
            break
        sid = queue.popleft()
        if sid in g.cut:
            continue
        found = system.successors(g.states[sid])
        g.expanded += 1
        g.succ_count[sid] = len(found)
        for label, nxt, violation in found:
            g.transitions += 1
            if violation is not None:
                g.violations.append((sid, label, violation))
                continue
            nxt, flipped = system.canonical(nxt)
            nid = index.get(nxt)
            if nid is None:
                nid = len(g.states)
                index[nxt] = nid
                g.states.append(nxt)
                g.parent.append(sid)
                g.label.append(label)
                g.flip.append(flipped)
                broken = system.invariant_broken(nxt)
                if broken:
                    g.cut[nid] = broken
                queue.append(nid)
            g.src.append(sid)
            g.dst.append(nid)
        if len(g.states) > max_states:
            g.complete, g.stopped_by = False, "states"
            break
    g.by_state = index
    return g


def can_finish(g, finished):
    """Ids from which a state in `finished` is reachable over legal transitions (reverse reachability, AG EF)."""
    preds = {}
    for src, dst in zip(g.src, g.dst):
        preds.setdefault(dst, []).append(src)
    seen = set(finished)
    queue = deque(sorted(seen))
    while queue:
        node = queue.popleft()
        for src in preds.get(node, ()):
            if src not in seen:
                seen.add(src)
                queue.append(src)
    return seen


def shortest_onward(g, start, goal):
    """The shortest list of state ids from `start` to a state in `goal` over legal transitions, or None."""
    succ = {}
    for src, dst in zip(g.src, g.dst):
        succ.setdefault(src, []).append(dst)
    back = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node in goal:
            out = []
            while node is not None:
                out.append(node)
                node = back[node]
            return list(reversed(out))
        for nxt in succ.get(node, ()):
            if nxt not in back:
                back[nxt] = node
                queue.append(nxt)
    return None
