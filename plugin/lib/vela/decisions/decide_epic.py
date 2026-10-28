"""`vela decide EPC-nnn`: an epic decided, with a yes for every group of its criteria (epics section 6). Pure.

The Violation this kind exists to prevent is a Paper Tiger epic: decided on one yes the lead could not hold in
mind, so criteria nobody heard go to the teams as agreed. Epics section 6 asks for a yes per group of about five; "every criterion has a yes" is countable, so it is counted here:

- `groups` (`--group CRITERIA YES`, repeated): which criteria a yes covers (`AC1-AC5`, `AC1, AC3` or `all`) and the
  lead's yes capture. Each yes passes the same consent checks as the decision's own (a person's words, not a bare
  "ok"), and a group names at most `consent.GROUP_LIMIT`
  criteria, past which one yes no longer says what was agreed to.
- **Every live criterion is in a group** (a struck one keeps its number and needs no yes), or the lead overrides
  GATE-3, the agenda's yes, which waives the group yeses too, on record with their reason.

The epic's state is its `state:` frontmatter, from `draft` or `reopened` (the gate's GATE-2 says so for any other);
reopened, it goes back to `reopened`, which is the state an epic changed after its decision carries.
"""
import re

from vela import criteria
from vela.decisions import consent, decide_writes

KIND = "epic"
TO, REOPEN_TO, DECISION = "decided", "reopened", True
FIELDS = {"groups": "the criterion groups: [{\"criteria\": \"AC1-AC5\", \"yes\": \"^c11\"}, ...], one yes "
                    "per group"}
RANGE = re.compile(r"^AC(\d+)\s*-\s*(?:AC)?(\d+)$", re.I)
ONE = re.compile(r"^AC(\d+)$", re.I)


def claims(view, ident):
    pages = view.model.by_id.get(ident) or []
    return bool(pages) and pages[0].type == "epic"


def target(view, ident):
    return decide_writes.page_target(view, ident, KIND)


def numbers(text, live):
    """The AC numbers a group's `criteria` names, or None when it doesn't read."""
    text = str(text or "").strip()
    if text.lower() == "all":
        return set(live)
    out = set()
    for part in filter(None, (p.strip() for p in text.split(","))):
        span, one = RANGE.match(part), ONE.match(part)
        if span:
            out.update(range(int(span.group(1)), int(span.group(2)) + 1))
        elif one:
            out.add(int(one.group(1)))
        else:
            return None
    return out


def group_refusals(groups, record, live):
    out, covered = [], set()
    for group in groups:
        named = numbers(group.get("criteria"), live)
        if named is None:
            out.append(decide_writes.refusal("decide-epic-group", "I couldn't tell which criteria one of those yeses "
                                                                  "was for.",
                                             f"criteria {group.get('criteria')!r} must be AC1-AC5, AC1, AC3 or all.",
                                             override="none: name the criteria the yes covers"))
            continue
        too_many = consent.group_small_enough(len(named))
        found = too_many or consent.a_yes(group.get("yes"), record)
        if found is not None:
            out.append(found)
        covered |= named
    return out, covered


def refusals(item, view, record, found):
    page = view.model.by_id[found.id][0]
    live = [c.n for c in criteria.read(page) if not c.struck]
    out, covered = group_refusals(item.get("groups") or [], record, live)
    left = [n for n in live if n not in covered]
    if left and decide_writes.GATE_3 not in decide_writes.rules_set_aside(item):
        count = len(left)
        out.append(decide_writes.refusal(
            "decide-epic-criteria",
            f"{count} of {found.name}'s criteria {'has' if count == 1 else 'have'} no yes from you yet, so I'll ask "
            f"about {'it' if count == 1 else 'them'} first.",
            f"Ask about AC{', AC'.join(map(str, left))} (at most {consent.GROUP_LIMIT} at a time), capture each yes, "
            "and give each group as --group CRITERIA YES.",
            override="--override GATE-3 --reason-from <the lead's reason>"))
    return out


def set_state(text, found, state):
    return decide_writes.set_frontmatter_state(text, state)
