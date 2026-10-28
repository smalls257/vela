"""`vela decide CON-nnn`: a contract decided, on its provider's page (grill's "File each decision as its branch closes"; CONVENTIONS "Fact bullets"). Pure.

The Violation this kind exists to prevent is a Silent Fallback on the page: a decided contract whose `**Tested by:**` is
missing, which E318 turns red, or one that quietly claims a tester nobody named. So, beyond what every decision writes
(`decide_writes`), nothing is refused here:

- **Where the provider stands** (`--provider ^cP`) is optional. When the lead answers, the capture is filed with the
  decision; when they don't, nothing is asked of them and nothing is guessed.
- **Who tests it** (`**Tested by:**`) is written `not yet` when the contract has none (`extra`), so E318 stays
  satisfied and the page says plainly that nobody has said.
- The case table with an error case, the stage of its app and the flow check are the grill gate's
  (`gates.verdict`), which `decide_writes.gate_refusals` runs for every kind.

Its state is the `**State:**` bullet under `### CON-nnn <name>`; the Decision and Why go under `#### CON-nnn` in the
page's `## History`. Reopened, it goes back to `assumption`.
"""
from vela.decisions import consent, decide_writes

KIND = "contract"
TO, REOPEN_TO, DECISION = "decided", "assumption", True
FIELDS = {"provider": "the capture saying where the provider stands: present, async (channel and date), asked in "
                      "the PR, or not consulted: <reason>"}


def claims(view, ident):
    item = view.model.item(ident)
    return item is not None and item.kind == "contract"


def target(view, ident):
    return decide_writes.item_target(view, ident, KIND)


def refusals(item, view, record, found):
    if item.get("provider"):
        missing = consent.exists(item["provider"], record)
        if missing is not None:
            return [missing]
    return []


def extra(item, view, record, found, text):
    """`- **Tested by:** not yet` under the State bullet when the contract names no tester."""
    if view.model.item(found.id).fact("Tested by"):
        return text
    lines = text.rstrip("\n").split("\n")
    start, end = decide_writes.item_block(lines, found.id)
    state = next(i for i in range(start, end) if decide_writes.STATE_BULLET.match(lines[i]))
    lines.insert(state + 1, "- **Tested by:** not yet")
    return "\n".join(lines) + "\n"


def set_state(text, found, state):
    return decide_writes.set_item_state(text, found.id, state)
