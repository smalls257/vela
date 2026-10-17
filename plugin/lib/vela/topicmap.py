"""A session's running topic map: what the lead has said, tagged to the kinds a plan needs, the groups named and where
each stands, and the items waiting to be raised. Pure: a state dict and the catalog's kinds in, a new state or a
suggestion out. `vela map` (commands/map.py) keeps the state in `.vela/map/<session>.json`.

Two Violations shape it.

**Silent Fallback (the list kept in the model's memory).** The elicitation research of 16 October found that models
commit early and drop what was said in the middle turns (Laban et al., 2025: a 39% drop over several turns), and that a
parked item which quietly drops looks exactly like a finished interview. So nothing here lives in a prompt: every
note, group and waiting item is written to the session's working file, and the read-back says what is still waiting,
by state, and what was never touched ("nothing yet on money or dates").

**Black Box (conflicts never put side by side).** Positions arrive turns apart and nobody compares them. So each group
carries its stated position per topic, and `moves` says "put these side by side" the moment two groups hold different
positions on one topic, naming both holders, and "ask this group" for each group not yet heard on the current topic.

The timing rules come from the same research, section 7.1. Rule 11: with three or four items waiting, stop opening
new threads; the next turn is a summary that settles or retires them (`SUMMARIZE_AT`, Cowan's four chunks). Rule 7: a
group named goes on the roster at once and is asked about later. Rule 8: two positions on one concern get a linking
summary at the next pause, never while only one side is known. The map picks which question comes next; it is never
read aloud as a checklist.
"""
import json
from dataclasses import dataclass, field

from vela import say

VERSION = 1
FOLDER = ".vela/map"

# Section 7.1, rule 11: "Three or four items parked: stop opening new ones." Three is the first of those.
SUMMARIZE_AT = 3

GAP, CONFLICT, BELIEF, FACT = "gap", "conflict", "belief", "fact"
TYPES = (GAP, CONFLICT, BELIEF, FACT)
WAITING, SETTLED, RECORDED, SET_ASIDE = "waiting", "settled", "recorded", "set-aside"
OUTCOMES = (SETTLED, RECORDED, SET_ASIDE)  # settled in the talk; written into the plan as open; the lead set it aside
STATED, GUESS = "stated", "guess"  # a group's own position as the lead reports it, or the lead's guess at it
BASES = (STATED, GUESS)

SUMMARIZE, SIDE_BY_SIDE, ASK_GROUP, ASK_KIND, ASK_NEW_GROUP = (
    "summarize", "side-by-side", "ask-group", "ask-kind", "ask-new-group")

# How a waiting item is said in the read-back, by type.
SAID_AS = {GAP: "To check", CONFLICT: "Two views to settle", BELIEF: "To confirm", FACT: "To pin down"}


class MapRefused(ValueError):
    """The input can't go on the map (an unknown kind, a waiting item that isn't there). The model's slip to fix."""


class MapUnreadable(ValueError):
    """The map file exists but isn't one this version wrote. Said, never read as an empty map."""


def key(text):
    """How two spellings of one group or topic compare: case and spacing don't count."""
    return " ".join(str(text).split()).casefold()


def clean(text, what):
    """`text` with its spacing folded, or MapRefused when it is empty or would show the lead plumbing (a path, a
    flag, a command): everything on the map may be read back to the lead, so it is written in their words."""
    text = " ".join(str(text or "").split())
    if not text:
        raise MapRefused(f"the {what} is empty")
    leak = say.leak_in(say.Resolver().plain(text))
    if leak:
        raise MapRefused(f"the {what} holds {leak[0]} ({leak[1]}); write it the way the lead would say it")
    return text


def new_state(session):
    return {"version": VERSION, "session": session, "notes": [], "groups": [], "waiting": [],
            "last": {"kind": "", "topic": ""}, "raised": []}


def dumps(state):
    return json.dumps(state, indent=2, ensure_ascii=False) + "\n"


def parse(text):
    try:
        state = json.loads(text)
    except ValueError as exc:
        raise MapUnreadable(f"the topic map is not JSON ({exc})") from exc
    lists = ("notes", "groups", "waiting", "raised")
    if not isinstance(state, dict) or state.get("version") != VERSION or \
            not all(isinstance(state.get(k), list) for k in lists) or not isinstance(state.get("last"), dict):
        raise MapUnreadable("the topic map is not one this vela wrote")
    return state


def _kind(kinds, name):
    if name not in [k.name for k in kinds]:
        raise MapRefused(f"kind {name!r} is not one of {', '.join(k.name for k in kinds)}")
    return name


def _group(state, name):
    found = next((g for g in state["groups"] if key(g["name"]) == key(name)), None)
    if found is None:
        found = {"name": name, "named": 0, "positions": []}
        state["groups"].append(found)
    return found


def set_topic(state, topic):
    state["last"]["topic"] = clean(topic, "topic")


def add_note(state, kinds, kind, text, topic=""):
    """Tag one thing the lead said to a kind; it becomes the last kind, so `moves` looks near it next."""
    note = {"kind": _kind(kinds, kind), "text": clean(text, "note")}
    if topic:
        note["topic"] = clean(topic, "topic")
        state["last"]["topic"] = note["topic"]
    state["notes"].append(note)
    state["last"]["kind"] = kind
    return note


def name_group(state, name):
    """A group the lead named goes on the roster now (rule 7). Named twice, it ranks ahead of the kinds in `moves`:
    the conflict-assessment practice includes a name raised more than once."""
    group = _group(state, clean(name, "group"))
    group["named"] += 1
    return group


def add_position(state, name, topic, position, reason="", basis=STATED):
    """Where one group stands on one topic. A second position for the same group and topic replaces the first: the
    lead corrected it. The topic becomes the current one."""
    if basis not in BASES:
        raise MapRefused(f"basis {basis!r} is not one of {', '.join(BASES)}")
    group = name_group(state, name)
    topic = clean(topic, "topic")
    entry = {"topic": topic, "position": clean(position, "position"), "basis": basis}
    if reason:
        entry["reason"] = clean(reason, "reason")
    group["positions"] = [p for p in group["positions"] if key(p["topic"]) != key(topic)] + [entry]
    state["last"]["topic"] = topic
    return entry


def tag(state, kinds, text, kind_names=(), groups=(), topic="", position="", reason="", basis=STATED):
    """One answer onto the map: the lead's words under each kind, each group named on the roster, or one group's
    position on the topic. The one implementation behind `vela map add` and `vela record add --kind/--group`, so a
    capture and a map entry can't drift into two meanings of "tagged". Returns (what was added, said short; data)."""
    if position and (len(groups) != 1 or not topic):
        raise MapRefused("a --position needs the one --group that holds it and the --topic it is on")
    said, data = [], {"groups": [], "notes": []}
    if position:
        data["position"] = add_position(state, groups[0], topic, position, reason, basis)
        said.append(f"{groups[0]} on {topic}: {position}")
    else:
        for name in groups:
            group = name_group(state, name)
            data["groups"].append(group)
            said.append(f"group {group['name']} (named {group['named']})")
    for kind in kind_names:
        note = add_note(state, kinds, kind, text, topic)
        data["notes"].append(note)
        said.append(f"{kind}: {note['text']}")
    if topic and not kind_names and not position:
        set_topic(state, topic)
        said.append(f"topic: {topic}")
    return said, data


def open_item(state, kinds, kind_of_item, text, kind="", topic=""):
    """A waiting item (a gap, conflict, belief or fact to raise later). Always written, even past `SUMMARIZE_AT`:
    refusing would drop it, the Silent Fallback this map exists to stop; `moves` holds the timing instead. A conflict
    opened on a topic marks that topic's positions as already put side by side."""
    if kind_of_item not in TYPES:
        raise MapRefused(f"type {kind_of_item!r} is not one of {', '.join(TYPES)}")
    item = {"n": max([i["n"] for i in state["waiting"]], default=0) + 1, "type": kind_of_item,
            "text": clean(text, "item"), "state": WAITING}
    if kind:
        item["kind"] = _kind(kinds, kind)
    if topic:
        item["topic"] = clean(topic, "topic")
        if kind_of_item == CONFLICT and key(topic) not in [key(t) for t in state["raised"]]:
            state["raised"].append(item["topic"])
    state["waiting"].append(item)
    return item


def close_item(state, number, outcome=SETTLED, how=""):
    if outcome not in OUTCOMES:
        raise MapRefused(f"outcome {outcome!r} is not one of {', '.join(OUTCOMES)}")
    item = next((i for i in state["waiting"] if i["n"] == number), None)
    if item is None:
        raise MapRefused(f"no waiting item #{number} on this session's map")
    if item["state"] != WAITING:
        raise MapRefused(f"item #{number} is already {item['state']}")
    item["state"] = outcome
    if how:
        item["how"] = clean(how, "how it ended")
    return item


def waiting(state):
    return [i for i in state["waiting"] if i["state"] == WAITING]


def coverage(state, kinds):
    """{kind: how many things touch it}. A named group counts toward people: the roster is people's coverage."""
    counts = {k.name: 0 for k in kinds}
    for note in state["notes"]:
        if note["kind"] in counts:
            counts[note["kind"]] += 1
    for item in state["waiting"]:
        if item.get("kind") in counts:
            counts[item["kind"]] += 1
    if "people" in counts:
        counts["people"] += len(state["groups"])
    return counts


@dataclass(frozen=True)
class Move:
    """One suggested next move. `move` is one of the five; `text` is the model's line; `data` the details."""
    move: str
    text: str
    data: dict = field(default_factory=dict)

    def as_json(self):
        return {"move": self.move, "text": self.text, **self.data}


def clashes(state):
    """[(topic, [holder, ...])] for each topic two groups hold different positions on, not yet put side by side."""
    by_topic = {}
    for group in state["groups"]:
        for p in group["positions"]:
            by_topic.setdefault(key(p["topic"]), (p["topic"], []))[1].append({"group": group["name"], **p})
    raised = {key(t) for t in state["raised"]}
    out = []
    for k, (topic, holders) in by_topic.items():
        if k in raised or len(holders) < 2 or len({key(h["position"]) for h in holders}) < 2:
            continue
        out.append((topic, holders))
    return out


def _held(holder):
    reason = f" because {holder['reason']}" if holder.get("reason") else ""
    guess = " (the lead's guess)" if holder["basis"] == GUESS else ""
    return f"{holder['group']} wants {holder['position']}{reason}{guess}"


def _side_by_side(topic, holders):
    return Move(SIDE_BY_SIDE, f"Put these side by side on {topic}: " + "; ".join(_held(h) for h in holders)
                + ". Ask when both can't hold, then open it as a conflict naming both and ask who decides.",
                {"topic": topic, "holders": holders})


def _summarize(state, pairs):
    items = waiting(state)
    text = (f"{len(items)} items wait: summarize first, settling or setting aside each, before opening any new thread.")
    if pairs:
        text += " Fold in, side by side: " + " | ".join(f"{t}: " + "; ".join(_held(h) for h in hs) for t, hs in pairs)
    return Move(SUMMARIZE, text, {"waiting": items, "pairs": [{"topic": t, "holders": hs} for t, hs in pairs]})


def _kind_moves(state, kinds, counts):
    """Kinds near the last one, emptiest first, then every other empty kind (the sweep); catalog order breaks ties."""
    order = [k.name for k in kinds]
    last = next((k for k in kinds if k.name == state["last"]["kind"]), None)
    near = list(last.near) if last else order
    swept = [n for n in order if n not in near and n != (last.name if last else "") and counts[n] == 0]
    means = {k.name: k.means for k in kinds}
    out = []
    for name in sorted(near, key=lambda n: (counts[n], order.index(n))) + swept:
        how = "near the last topic" if last and name in near else "never touched"
        out.append(Move(ASK_KIND, f"Ask about {name} ({means[name]}): {counts[name]} so far, {how}.",
                        {"kind": name, "means": means[name], "count": counts[name], "near_last": bool(last) and name in near}))
    return out


def moves(state, kinds):
    """What to raise next, best first. With `SUMMARIZE_AT` or more items waiting, the only move is to summarize:
    no new kind, no new group, no new pair (rule 11); pairs ready to compare are folded into the summary."""
    pairs = clashes(state)
    if len(waiting(state)) >= SUMMARIZE_AT:
        return [_summarize(state, pairs)]
    out = [_side_by_side(t, hs) for t, hs in pairs]
    topic = state["last"]["topic"]
    unheard = [g for g in state["groups"] if topic and key(topic) not in [key(p["topic"]) for p in g["positions"]]]
    for g in sorted(unheard, key=lambda g: -g["named"]):
        out.append(Move(ASK_GROUP, f"Ask where {g['name']} stands on {topic}; not asked yet.",
                        {"group": g["name"], "topic": topic, "named": g["named"]}))
    never = sorted([g for g in state["groups"] if not g["positions"] and g not in unheard], key=lambda g: -g["named"])
    new_group = [Move(ASK_NEW_GROUP, f"Ask what {g['name']} needs; never asked (named {_times(g['named'])}).",
                      {"group": g["name"], "named": g["named"]}) for g in never]
    kind_moves = _kind_moves(state, kinds, coverage(state, kinds))
    twice = [m for m in new_group if m.data["named"] >= 2]
    once = [m for m in new_group if m.data["named"] < 2]
    return out + twice + kind_moves[:1] + once + kind_moves[1:]


def _times(n):
    return {1: "once", 2: "twice"}.get(n, f"{n} times")


def or_said(names):
    """['a', 'b', 'c'] -> 'a, b or c'."""
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + f" or {names[-1]}" if names else ""


@dataclass(frozen=True)
class Readback:
    covered: tuple  # kind names with something on them, catalog order
    empty: tuple  # kind names with nothing yet
    waiting: tuple  # waiting item dicts, in the order they were opened
    unheard: tuple  # group names never asked where they stand

    def answer(self):
        if not self.covered:
            return "Nothing's on the map yet."
        if not self.empty:
            return f"We've touched every part of a plan: {say.names_said(list(self.covered))}."
        return (f"So far we've covered {say.names_said(list(self.covered))}. "
                f"Nothing yet on {or_said(list(self.empty))}.")

    def items(self):
        said = [f"{SAID_AS[i['type']]}: {i['text']}" for i in self.waiting]
        if self.unheard:
            verb = "stands" if len(self.unheard) == 1 else "stand"
            said.append(f"We haven't heard where {say.names_said(list(self.unheard))} {verb} yet.")
        return said


def readback(state, kinds):
    counts = coverage(state, kinds)
    order = [k.name for k in kinds]
    return Readback(tuple(n for n in order if counts[n]), tuple(n for n in order if not counts[n]),
                    tuple(waiting(state)), tuple(g["name"] for g in state["groups"] if not g["positions"]))
