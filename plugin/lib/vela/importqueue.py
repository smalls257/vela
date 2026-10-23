"""The import's queue: what the documents say that only the lead can settle, handed to the session about four at a
time, each with a proposed answer. Pure: a state dict in, a new state or a batch out. `vela import`
(commands/importer.py) keeps the state in `.vela/import/<session>.json`, beside the topic map, and shares its store.

Three Violations shape it.

**Silent Fallback (the pile asked from memory).** An import reads a dozen documents and finds a dozen things to
confirm: decisions they state, two documents that disagree, a fact that may be out of date. Asked from the model's
memory, the ones in the middle drop, and a dropped clash looks exactly like two documents that agree. So every item is
written down as it is found, and `next` hands back what is still waiting, never what the model remembers.

**Paper Tiger (the batch nobody can judge).** Twelve confirmations in one turn meet "ask the lead" and fail the lead,
who can't hold twelve things and answers "yes" to all of them. So a batch is at most `BATCH` items (conversation voice
rule 7, `say.LEAD_LIMIT`), each with the proposed answer and why, and no new batch is handed out while one is still
waiting for its answers: `next` returns the open batch again.

**Leaky Narrative (the lead hears plumbing).** Every text on an item may be read to the lead, so it is cleaned by the
topic map's own `clean`, which refuses a path, a flag or an ID; sources are kept apart, as IDs the shell names by
title.

What each type is, and what can end it:

- `decision`: a decision a source states ("approved by the CTO on March 3"). The lead says yes, and it is decided
  citing the document (`vela decide --stated-in`); unsure, it stays an assumption with the document noted.
- `clash`: two sources that disagree. The lead picks which wins, the session proposing one with why; not knowing,
  both sides go down as one open question.
- `stale`: a fact that may be out of date (an old document, a later one that moved on). Still true, replaced, or open.
"""
from vela import say, topicmap, wording

VERSION = 1
FOLDER = ".vela/import"

DECISION, CLASH, STALE = "decision", "clash", "stale"
TYPES = (DECISION, CLASH, STALE)
# The order a batch is filled in: a clash first, because what wins changes what every later line says; then what may
# be out of date; then the decisions, which are asked last because they rest on the facts being settled.
ASK_ORDER = (CLASH, STALE, DECISION)

WAITING, ASKED = "waiting", "asked"
# How each type of item can end. `set-aside` is the lead's choice to leave it, said and kept, never a drop.
OUTCOMES = {
    DECISION: ("decided", "assumption", "set-aside"),
    CLASH: ("chosen", "open", "set-aside"),
    STALE: ("current", "replaced", "open", "set-aside"),
}
BATCH = say.LEAD_LIMIT

# What the lead hears an item as, by type.
SAID_AS = {DECISION: "{sources} says this was decided: {text}",
           CLASH: "{sources} disagree: {text}",
           STALE: "{sources} may be out of date: {text}"}

# The voice question, asked once in the import map: keep, voice, or the split the import proposes.
KEEP, SPLIT, VOICE = wording.KEEP, wording.SPLIT, wording.VOICE
WORDINGS = wording.WORDINGS
WORDING_KEY, WORDING_YES_KEY = wording.WORDING_KEY, wording.WORDING_YES_KEY
ALL_SOURCES = "*"
SPLIT_PROPOSAL = ("I'd keep the documents' exact words, quoted and cited, for requirements, contract and legal "
                  "terms, numbers and direct quotes, and write the page's own explaining sentences in the plan's "
                  "voice. Shall I do it that way, keep everything as written, or voice it all?")


class QueueRefused(topicmap.MapRefused):
    """The input can't go on the queue. The model's slip to fix, said as the map's refusals are."""


def new_state(session):
    return {"version": VERSION, "session": session, "items": [], "batches": 0, "wording": {}}


def parse(text):
    import json
    try:
        state = json.loads(text)
    except ValueError as exc:
        raise topicmap.MapUnreadable(f"the import queue is not JSON ({exc})") from exc
    if not isinstance(state, dict) or state.get("version") != VERSION or not isinstance(state.get("items"), list) \
            or not isinstance(state.get("wording"), dict):
        raise topicmap.MapUnreadable("the import queue is not one this vela wrote")
    return state


dumps = topicmap.dumps


def clean(text, what):
    try:
        return topicmap.clean(text, what)
    except topicmap.MapRefused as exc:
        raise QueueRefused(str(exc)) from exc


def add(state, kind, text, sources, proposal, why):
    """Queue one item. Every item carries the sources it rests on (two for a clash) and the answer the session would
    give, with why: a batch with no proposal makes the lead do the session's work."""
    if kind not in TYPES:
        raise QueueRefused(f"type {kind!r} is not one of {', '.join(TYPES)}")
    sources = [s.strip() for s in sources if s and s.strip()]
    if not sources:
        raise QueueRefused("an item needs the source it rests on (--source)")
    if kind == CLASH and len(set(sources)) < 2:
        raise QueueRefused("a clash needs both sources that disagree (--source twice)")
    item = {"n": max([i["n"] for i in state["items"]], default=0) + 1, "type": kind, "text": clean(text, "item"),
            "sources": sources, "proposal": clean(proposal, "proposal"), "why": clean(why, "reason"),
            "state": WAITING, "batch": 0}
    state["items"].append(item)
    return item


def open_batch(state):
    """The items handed to the lead and not yet settled, in the order they were asked."""
    return [i for i in state["items"] if i["state"] == ASKED]


def waiting(state):
    return [i for i in state["items"] if i["state"] == WAITING]


def settled(state):
    return [i for i in state["items"] if i["state"] not in (WAITING, ASKED)]


def next_batch(state):
    """(batch, reopened): the open batch again when one is still waiting for answers (reopened True), else the next
    `BATCH` waiting items in `ASK_ORDER`, marked asked under a new batch number. Empty when nothing waits."""
    still = open_batch(state)
    if still:
        return still, True
    order = sorted(waiting(state), key=lambda i: (ASK_ORDER.index(i["type"]), i["n"]))
    batch = order[:BATCH]
    if batch:
        state["batches"] += 1
        for item in batch:
            item["state"], item["batch"] = ASKED, state["batches"]
    return batch, False


def close(state, number, outcome, how=""):
    """Settle one item with the lead's answer. Only an item handed to the lead can be settled: one settled before it
    was asked was settled without the lead."""
    item = next((i for i in state["items"] if i["n"] == number), None)
    if item is None:
        raise QueueRefused(f"no item #{number} on this session's import queue")
    if item["state"] == WAITING:
        raise QueueRefused(f"item #{number} hasn't been asked yet; hand it to the lead with import next first")
    if item["state"] != ASKED:
        raise QueueRefused(f"item #{number} is already {item['state']}")
    allowed = OUTCOMES[item["type"]]
    if outcome not in allowed:
        raise QueueRefused(f"a {item['type']} ends as {', '.join(allowed)}, not {outcome!r}")
    item["state"] = outcome
    if how:
        item["how"] = clean(how, "how it ended")
    return item


def set_wording(state, choice, yes, source=ALL_SOURCES):
    """The lead's answer to the voice question, for every source or one. `yes` is the capture of their words; the
    shell checks it is a person's before it gets here."""
    if choice not in WORDINGS:
        raise QueueRefused(f"wording {choice!r} is not one of {', '.join(WORDINGS)}")
    if not yes:
        raise QueueRefused("the wording answer needs the capture of the lead's words (--yes)")
    state["wording"][source] = {"as": choice, "yes": yes}
    return state["wording"][source]


def wording_for(state, sources):
    """The wording a page drawn from `sources` takes, and the yes behind it: the answer for its source when the lead
    gave one, else their answer for all sources, else `keep` with no yes. Until the lead answers, the documents' words
    are kept as written; nothing is voiced on the session's own judgment. A page drawn from sources answered
    differently keeps the stricter answer, so one source's "keep" is never voiced because another's was."""
    chosen = []
    for source in sources or [ALL_SOURCES]:
        answer = state["wording"].get(source) or state["wording"].get(ALL_SOURCES)
        chosen.append(answer or {"as": KEEP, "yes": ""})
    strictest = min(chosen, key=lambda a: WORDINGS.index(a["as"]))
    return strictest["as"], strictest["yes"]


def said(item, source_names):
    """The plain line the lead hears for one item: what the documents say, then the proposed answer and why."""
    names = say.names_said(source_names) if len(source_names) > 1 else (source_names[0] if source_names else "document")
    head = SAID_AS[item["type"]].format(sources=names, text=item["text"].rstrip("."))
    return f"{head}. I'd say: {item['proposal'].rstrip('.')}, because {item['why'].rstrip('.')}."


def counts(state):
    """{type: {"waiting": n, "asked": n, "settled": n}} for the read-back."""
    out = {t: {"waiting": 0, "asked": 0, "settled": 0} for t in TYPES}
    for item in state["items"]:
        bucket = item["state"] if item["state"] in (WAITING, ASKED) else "settled"
        out[item["type"]][bucket] += 1
    return out
