"""Where each flow starts, for the Flows view's "Starts from" picker. Pure: flow records and the flow checker's catalog in, data out.

A flow with more than one way in ("a customer browses page A" and "a customer calls in", both reaching app C) reads as
one long list unless the page can say which steps belong to which way in. This module names the starts and says which
numbered step belongs to which, so the page only reads it. Two sources, the first wins:

- The diagram. A strict sequence diagram whose first statement (after any GIVEN) is an `alt` names the flow's starts, one per alt/else
  option, labeled by the option's own words. The diagram is read once, by the flow checker's parser
  (`flowcheck.mermaid.parse_tree`); nothing here parses mermaid. Each option's calls are tied to the numbered steps the
  way branches_data.py ties the diagram to lanes (`participant_keys`): a step belongs to an option when it carries the
  same contract between the same two lanes. A step before an option's first tied step, back to the previous option's
  last, belongs to that option too (the customer picking a room on the website, before the website calls Booking).
- A guess. With no opening alt, a start is a lane that acts before anything sends to it, and the starts are the
  lanes whose first steps both reach one shared lane (the merge) before any step is shared. `guessed` is True when any
  step that rests on has an inferred direction (the contract's provider is drawn as the sender), so the page says so.

One start, or none, is no starts at all: the page shows nothing extra (None).

A start the diagram names that no numbered step carries stays in the record with no steps, and is listed under `unmatched`
so the page says so; the diagram's starts are never swapped for a guess.

The record on each flow (`flow["starts"]`, or None), and `step["start"]` on each step (the option's id, "" for a shared step):

    {"source": "diagram" | "guess", "guessed": bool,
     "options": [{"id": "S1", "label": "...", "lane": lane id, "steps": [step numbers]}],
     "merge": {"step": first shared step number, "lane": lane id or ""} | None,
     "unmatched": [labels of starts with no step]}

What it exists to prevent: a Paper Tiger flow page that lists both ways in as one numbered line of steps, so a reader
cannot tell "either" from "both"; and a second reading of the diagram that drifts from the checker's (a Leaky
Narrative). A guess that looked like a fact would be a Silent Fallback, so a guess is labeled.
"""
from . import branches_data

NO_STARTS = None


def annotate(vault, keys, flows, catalog, lanes):
    """Sets flow["starts"] and each step's "start" on every flow record (in place). `lanes` is the page's lane list, so a
    participant that is an outside party (not an app) still finds its lane by name."""
    pages = {keys.page(p): p for p in vault.of_type("flow")}
    by_name = {l["name"].lower(): l["id"] for l in lanes}
    names = {l["id"]: l["name"] for l in lanes}
    for flow in flows:
        page = pages.get(flow["key"])
        found = from_diagram(vault, keys, catalog, page, flow, by_name) or guess(flow["steps"], names)
        flow["starts"] = found
        owners = {n: o["id"] for o in (found or {"options": []})["options"] for n in o["steps"]}
        for step in flow["steps"]:
            step["start"] = owners.get(step["n"], "")


# --- from the diagram ----------------------------------------------------------------------------------------------

def tree_of(catalog, page):
    """The page's strict sequence diagram read by the flow checker's parser, or None when it draws none."""
    drawn = catalog.flows.get(page.id) if page is not None else None
    if drawn is None or not drawn.has_diagram:
        return None
    from vela.flowcheck import mermaid
    return mermaid.parse_tree(drawn, [])


def people_of(tree, catalog, vault, keys, by_name):
    """{participant name: lane id}: an app by the checker's own reading, anything else (an outside party) by its title."""
    people = branches_data.participant_keys(tree, catalog, vault, keys)
    for name, (title, _) in tree.participants.items():
        if name not in people and title.lower() in by_name:
            people[name] = by_name[title.lower()]
    return people


def from_diagram(vault, keys, catalog, page, flow, by_name):
    """The starts an opening alt names, or None when the flow has none (or fewer than two that its steps show)."""
    tree = tree_of(catalog, page)
    if tree is None or len(tree.starts) < 2:
        return NO_STARTS
    people = people_of(tree, catalog, vault, keys, by_name)
    options = []
    for b in tree.starts:
        calls = calls_within(b.body, people)
        options.append({"label": " ".join(b.label.split()), "calls": calls, "lane": calls[0][0] if calls else ""})
    tail = calls_within(tree.tail, people)
    owner = tie_steps(flow["steps"], options, tail)
    fill_gaps(flow["steps"], owner, len(options))
    return record(flow["steps"], owner, list(range(len(options))), options, source="diagram")


def drawn_calls(vault, keys, catalog, page, by_name):
    """[(from lane, to lane, contract ID, words)] for every call the page's diagram draws, every start included, in order.
    The words are the diagram's own for the call ("capacity check"). Empty when the page draws no strict diagram."""
    tree = tree_of(catalog, page)
    if tree is None:
        return []
    people = people_of(tree, catalog, vault, keys, by_name)
    return [(people.get(n.parts[0], ""), people.get(n.parts[1], ""), n.parts[2], n.parts[3].strip())
            for n in call_nodes(tree.all_nodes()) if n.kind == "call"]


def default_groups(vault, keys, catalog, page, by_name, lane_ids):
    """([{"name": "Channels", "lanes": [lane ids]}], [sentences]) for the page's `box` blocks, in the diagram's order: the groups
    the page writes for the Flows view to open with, and what it could not draw of them, said (flowcheck.mermaid.plan_boxes, the
    one reading the checker's W407 shares). A box keeps the lanes the page's participants map to (an app by the checker's
    reading, an outside party by its title). The diagram is read by the flow checker's parser, never again here."""
    tree = tree_of(catalog, page)
    if tree is None or not tree.boxes:
        return [], []
    from vela.flowcheck import mermaid
    people = people_of(tree, catalog, vault, keys, by_name)
    groups, notes = mermaid.plan_boxes(tree, lambda name: people.get(name, "") if people.get(name, "") in lane_ids else "")
    return [{"name": name, "lanes": lanes} for name, lanes in groups], [words for _, words in notes]


def call_nodes(nodes):
    """Every call and event node in a block, in order, handling and branches included."""
    for node in nodes or ():
        if node.kind in ("call", "publish"):
            yield node
        yield from call_nodes(node.handling)
        yield from call_nodes(node.handler)
        for branch in node.branches or ():
            yield from call_nodes(branch.body)


def calls_within(nodes, people):
    """[(from lane, to lane, contract or event ID)] for every call and event in a block, in order, lanes as the page names them."""
    return [(people.get(n.parts[0], ""), people.get(n.parts[1], ""), n.parts[2]) for n in call_nodes(nodes)]


def tie_steps(steps, options, tail=()):
    """{step number: option index} for the steps that carry a call of exactly one option: the same contract between the
    same two lanes, either way round (a step whose direction is inferred may draw the pair reversed). A step two options
    claim goes to the one whose entry lane the step's text names, else to neither. The steps are read in order and the
    reading stops at the first step that carries a call of the shared steps after the alt, or that would take a step back
    to an earlier start: what follows is shared, even when it calls the same contract between the same lanes."""
    owner, last = {}, 0
    for step in steps:
        if any(carries(step, call) for call in tail):
            break
        claims = [i for i, o in enumerate(options) if any(carries(step, call) for call in o["calls"])]
        if len(claims) > 1:
            named = [i for i in claims if options[i]["calls"] and options[i]["calls"][0][0] in step.get("named", [])]
            claims = named if len(named) == 1 else []
        if len(claims) == 1:
            if claims[0] < last:
                break
            owner[step["n"]] = last = claims[0]
    return owner


def carries(step, call):
    frm, to, item = call
    ends = {frm, to}
    return bool(frm and to) and any(m["contract"] == item and {m["from"], m["to"]} == ends for m in step["messages"])


def fill_gaps(steps, owner, count):
    """Steps between the previous option's last tied step and this option's last tied step belong to this option, so a
    start's own steps ("The customer picks a room") travel with it."""
    floor = 0
    for i in range(count):
        mine = [n for n, o in owner.items() if o == i]
        if not mine:
            continue
        top = max(mine)
        for step in steps:
            if floor < step["n"] <= top:
                owner.setdefault(step["n"], i)
        floor = top


# --- the guess ------------------------------------------------------------------------------------------------------

def senders_of(step):
    """(lanes that act, lanes that are reached, direction inferred) for one step."""
    if step["messages"]:
        return ({m["from"] for m in step["messages"]}, {m["to"] for m in step["messages"]},
                any(m["direction"] == "inferred" for m in step["messages"]))
    return ({step["self"]} if step["self"] else set()), set(), False


def guess(steps, names=None):
    """The mockup rule: a lane that acts before anything sends to it is a start; the starts are the lanes whose own steps
    reach one shared lane before any step is shared. None unless at least two do."""
    acted, reached, acts = {}, {}, []
    for i, step in enumerate(steps):
        by, to, inferred = senders_of(step)
        acts.append((by, to, inferred))
        for lane in by:
            acted.setdefault(lane, i)
        for lane in to:
            reached.setdefault(lane, i)
    candidates = [lane for lane in sorted(acted, key=acted.get) if lane not in reached or acted[lane] < reached[lane]]
    sources = {lane: {lane} for lane in candidates}
    owner, merge_at = {}, None
    for i, (by, to, _) in enumerate(acts):
        here = set().union(*(sources.get(lane, set()) for lane in by)) if by else set()
        if len(here) >= 2 and merge_at is None:
            merge_at = i
        if len(here) == 1 and merge_at is None:
            owner[steps[i]["n"]] = next(iter(here))
        for lane in to:
            sources.setdefault(lane, set()).update(here)
    if merge_at is None or not owner:
        return NO_STARTS
    last = max(i for i, step in enumerate(steps) if step["n"] in owner)
    merge_lane = next(iter(acts[last][1]), "") if len(acts[last][1]) == 1 else ""
    starts = [lane for lane in candidates if lane != merge_lane and any(
        owner.get(step["n"]) == lane and merge_lane in acts[i][1] for i, step in enumerate(steps))]
    if len(starts) < 2:
        return NO_STARTS
    options = [{"label": (names or {}).get(lane, lane), "calls": [], "lane": lane} for lane in starts]
    tied = {n: starts.index(lane) for n, lane in owner.items() if lane in starts}
    used = [step for step in steps if step["n"] in tied]
    found = record(steps, tied, list(range(len(starts))), options, source="guess", merge_lane=merge_lane)
    found["guessed"] = any(senders_of(step)[2] for step in used)
    return found


# --- the record ------------------------------------------------------------------------------------------------------

def record(steps, owner, kept, options, source, merge_lane=None):
    out = []
    for i in kept:
        mine = [s["n"] for s in steps if owner.get(s["n"]) == i]
        lane = options[i].get("lane") or entry_lane(steps, mine)
        out.append({"id": f"S{i + 1}", "label": options[i]["label"], "lane": lane, "steps": mine})
    tied = [n for o in out for n in o["steps"]]
    shared = next((s for s in steps if tied and s["n"] > max(tied) and s["n"] not in owner), None)
    if merge_lane is None:
        merge_lane = common_target(options, kept)
    merge = {"step": shared["n"], "lane": merge_lane} if shared is not None else None
    # a start the diagram names that no numbered step carries is said, never dropped
    return {"source": source, "guessed": False, "options": out, "merge": merge, "unmatched": [o["label"] for o in out if not o["steps"]]}


def entry_lane(steps, numbers):
    """The lane the start's first step acts in."""
    first = next((s for s in steps if s["n"] == numbers[0]), None) if numbers else None
    if first is None:
        return ""
    return first["messages"][0]["from"] if first["messages"] else (first["self"] or "")


def common_target(options, kept):
    """The lane every option's last call reaches, or "" when they reach different ones."""
    ends = {options[i]["calls"][-1][1] for i in kept if options[i]["calls"]}
    return next(iter(ends)) if len(ends) == 1 else ""
