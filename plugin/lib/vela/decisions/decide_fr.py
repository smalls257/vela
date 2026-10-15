"""`vela decide CAP-nnn.FRn`: a functional requirement decided, on its capability page (grill section 4). Pure.

A requirements session writes a requirement at `assumption` only; only a Grill makes it `decided`, through the same
gate as any item (an open unknown that lists it in `**Blocks:**` fails GATE-4 for it). The Violation this kind's shape
prevents is a Leaky Narrative between the kinds: a requirement has nothing of its own beyond where its state lives, so
it adds no flag, and a flag another kind takes (a provider capture, criterion groups) is refused by the dispatcher
rather than ignored, because an ignored answer looks filed.

Its state is the `**State:**` bullet under `### CAP-nnn.FRn <what it does>`; the Decision goes under `#### CAP-nnn.FRn`
in the capability page's `## History`. Reopened, it goes back to `assumption`.
"""
from vela.decisions import decide_writes

KIND = "fr"
TO, REOPEN_TO, DECISION = "decided", "assumption", True
FIELDS = {}


def claims(view, ident):
    item = view.model.item(ident)
    return item is not None and item.kind == "requirement"


def target(view, ident):
    return decide_writes.item_target(view, ident, KIND)


def refusals(item, view, record, found):
    return []


def set_state(text, found, state):
    return decide_writes.set_item_state(text, found.id, state)
