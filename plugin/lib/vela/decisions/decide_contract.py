"""`vela decide CON-nnn`: a contract decided, on its provider's page (grill's "File each decision as its branch closes"; CONVENTIONS "Fact bullets"). Pure.

The Violation this kind exists to prevent is a Paper Tiger contract: decided on the consumer's word while nobody asked
the side that has to build it. So, beyond what every decision writes (`decide_writes`):

- **Where the provider stands is on record** (`--provider ^cP`): a capture saying the provider was present, answered
  async (channel and date), was asked in the PR, or "not consulted: <reason>". Grill section 4 asked for it in prose
  and nothing checked it; now a contract with no such capture is refused, unless the lead sets the rule aside
  (`PROVIDER_RULE`, a quoted skill rule, with their reason).
- **Who tests it** (`**Tested by:**`) is required once decided (E318), so a contract the check would turn red the
  moment it is written is refused here first, unless the lead overrides E318 with an end date.
- The case table with an error case, the open questions that block it and the stage of its app are the grill gate's
  (`gates.verdict`), which `decide_writes.gate_refusals` runs for every kind.

Its state is the `**State:**` bullet under `### CON-nnn <name>`; the Decision and Why go under `#### CON-nnn` in the
page's `## History`. Reopened, it goes back to `assumption`.
"""
from vela.decisions import consent, decide_writes

KIND = "contract"
TO, REOPEN_TO, DECISION = "decided", "assumption", True
PROVIDER_RULE = '"a decided contract records where the provider stands"'
FIELDS = {"provider": "the capture saying where the provider stands: present, async (channel and date), asked in "
                      "the PR, or not consulted: <reason>"}


def claims(view, ident):
    item = view.model.item(ident)
    return item is not None and item.kind == "contract"


def target(view, ident):
    return decide_writes.item_target(view, ident, KIND)


def refusals(item, view, record, found):
    out = []
    named = decide_writes.rules_set_aside(item)
    if item.get("provider"):
        missing = consent.exists(item["provider"], record)
        if missing is not None:
            out.append(missing)
    elif PROVIDER_RULE not in named:
        out.append(decide_writes.refusal(
            "decide-provider-stands", f"I haven't written down where the team that provides {found.name} stands yet.",
            "Capture where the provider stands (present, async with channel and date, asked in the PR, or not "
            "consulted: <reason>), then give it as --provider.",
            override=f"--override '{PROVIDER_RULE}' --reason-from <the lead's reason>"))
    contract = view.model.item(found.id)
    if not contract.fact("Tested by") and "E318" not in named:
        out.append(decide_writes.refusal(
            "decide-tested-by", f"Nobody has said yet who tests {found.name} from each side.",
            "Ask who tests it on each side and write - **Tested by:** under the contract, then decide again.",
            override="--override E318 --reason-from <the lead's reason> --until <date>"))
    return out


def set_state(text, found, state):
    return decide_writes.set_item_state(text, found.id, state)
