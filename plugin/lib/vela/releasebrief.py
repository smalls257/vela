"""What a releases session starts from, and which flow proves the most of the system first. Pure: a vault in, facts out
(CLI/skill overhaul, Task 21f).

The Violation this module's shape prevents is the Leaky Narrative: the releases skill told the model to read the
releases page, every slice page, every capability's requirements, the allocation block and the boundary session's
record, then count apps and new contracts per flow by hand and show a table. The reading and the count are a lookup;
done in prose, every session counted differently and the lead heard the IDs it counted with. So the skill asks
`vela releases brief` and `vela releases tracer-candidates` and keeps only the workshop (one question at a time, the
lead decides each cut). It does not re-read anything itself: releases, slices, allocation and flows are asked
through their public readers (`releases.releases`, `slices.read_slices`, `allocation.carried`, `flows.passes_through`),
so this module never holds a second idea of what a slice or a tracer is (a Shield against the Distributed Monolith
`slices.py` describes).

The rules it carries, with their reasons (from releases/SKILL.md):

- Prerequisites, in order. No functional requirements: offer `/vela:requirements`, because a release is a list of
  requirements and there is nothing to place. Requirements and none allocated: offer `/vela:allocate`, because which
  apps change after a release is computed from allocation, so without it nothing says what a release touches (the
  lead may go on anyway, on record as an override). No flow pages: the tracer is taken in plain words with no link,
  and a boundary session can draw it.
- The first thin path boundary recorded is the flow page whose opening says "the first thin path": boundary writes
  it there so releases starts from it and does not ask again.
- Tracer candidates rank by the apps a flow crosses, then the new contracts it crosses. The tracer is built first and
  kept so the joins between apps get proved early; the flow crossing the most of them proves the most. An outside
  party is never counted, as an app or as the provider of a contract, because the lead cannot build it. A contract is
  new when its Change is `new`; a changed one already runs somewhere. A tie on both counts is the lead's call, broken
  by what the first release's audience sees first, so the ranking reports the tie instead of picking by ID.
- A flow whose steps name no sender and receiver (`flows.steps` reads the pair) cannot be counted. It is listed last
  and said to be uncounted, never as "crosses no apps": a zero there would be a fake answer, and would quietly rank
  an old-form flow below every drawn one. Boundary redraws it in the strict form.
"""
import re
from dataclasses import dataclass

from vela import allocation, flows, parse, releases, slices

FLOW_TYPE = "flow"
_SENTENCE = re.compile(r"[^.!?]*first thin path[^.!?]*[.!?]?", re.I)


@dataclass(frozen=True)
class Missing:
    """A prerequisite the session lacks: which, what the lead hears, and the skill to offer."""
    key: str
    says: str
    offer: str


@dataclass(frozen=True)
class FirstPath:
    flow: str  # the flow page's id
    words: str  # the sentence that names the path, as boundary wrote it


@dataclass(frozen=True)
class Candidate:
    flow: str
    apps: tuple  # app ids the flow's steps cross, in step order
    new_contracts: tuple  # new contract ids its steps cross, outside providers left out
    recorded_first_path: bool
    in_slices: tuple  # keys of the slices that already name the flow
    countable: bool = True  # False when no step names a sender and receiver, so its apps cannot be counted


@dataclass(frozen=True)
class Brief:
    releases: list  # releases.Release, page order
    slices: list  # slices.Slice, After order
    tracer: object  # the tracer slice, or None
    requirements: list  # every functional requirement, item-ID order
    due: list  # those at assumption or later: the ones that must be allocated and placed
    unallocated: list  # due requirements no app carries
    undated: list  # due requirements no release delivers
    first_path: list  # [FirstPath]
    flow_count: int
    missing: list  # [Missing], in the order the session should offer them


def flow_pages(vault):
    return sorted(vault.of_type(FLOW_TYPE), key=lambda p: p.id)


def opening(page):
    """The prose between the page's title and its first section: where boundary writes the first thin path."""
    _, start, _ = parse.split_frontmatter(page.text)
    out = []
    for line in page.text.split("\n")[start - 1:]:
        if line.startswith("## "):
            break
        if line.strip() and not line.startswith(("#", "- **")):
            out.append(line.strip())
    return " ".join(out)


def first_path(vault):
    """The flow pages whose opening names the first thin path, with the sentence that does."""
    out = []
    for page in flow_pages(vault):
        found = _SENTENCE.search(opening(page))
        if found:
            out.append(FirstPath(page.id, found.group(0).strip()))
    return out


def missing(requirements, carried, flow_count):
    out = []
    if not requirements:
        out.append(Missing("requirements", "There are no functional requirements yet, so there is nothing to place on "
                                           "a release.", "/vela:requirements"))
    elif not any(r.id in carried for r in requirements):
        out.append(Missing("allocation", "No requirement is allocated to an app yet, so nothing says which apps a "
                                         "release changes. Go on only if the lead says so, as an override.",
                           "/vela:allocate"))
    if not flow_count:
        out.append(Missing("flows", "No flow is drawn yet, so the tracer can only be taken in plain words; a boundary "
                                    "session can draw it.", "/vela:boundary"))
    return out


def brief(vault):
    """Everything a releases session reads before its first question, and what it lacks."""
    found = releases.releases(vault)
    cut = slices.read_slices(vault)
    reqs = allocation.requirements(vault)
    carried = allocation.carried(vault)
    due = allocation.due(vault)
    placed = {row.requirement for r in found for row in r.rows}
    count = len(flow_pages(vault))
    return Brief(found, cut, slices.tracer(cut), reqs, due, [r for r in due if r.id not in carried],
                 [r for r in due if r.id not in placed], first_path(vault), count, missing(reqs, carried, count))


def new_contracts(vault, contract_ids):
    """The contracts among these that the initiative builds new: Change `new`, and kept by one of the vault's apps."""
    by_id = {c.id: c for c in vault.contracts}
    return tuple(cid for cid in contract_ids
                 if cid in by_id and by_id[cid].fact("Change").lower() == "new" and not by_id[cid].fact("Provider"))


def candidates(vault):
    """Every drawn flow as a tracer candidate, most apps first, then most new contracts; ties keep flow order."""
    recorded = {fp.flow for fp in first_path(vault)}
    cut = slices.read_slices(vault)
    paired = {step.page.path for step in flows.steps(vault) if step.pair}
    out = []
    for page in flow_pages(vault):
        apps, contracts = flows.passes_through(vault, [page.id])
        out.append(Candidate(page.id, tuple(apps), new_contracts(vault, contracts), page.id in recorded,
                             tuple(s.key for s in cut if page.id in s.flows), page.path in paired))
    return sorted(out, key=lambda c: (not c.countable, -len(c.apps), -len(c.new_contracts)))


def tied(ranked):
    """The flows that share the top place on both counts, when more than one does: the lead breaks that tie."""
    if len(ranked) < 2 or not ranked[0].countable:
        return []
    top = (len(ranked[0].apps), len(ranked[0].new_contracts))
    level = [c.flow for c in ranked if (len(c.apps), len(c.new_contracts)) == top]
    return level if len(level) > 1 else []
