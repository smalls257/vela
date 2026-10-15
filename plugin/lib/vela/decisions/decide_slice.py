"""`vela decide SLC-nnn`: a slice planned, not decided (grill section 2; CONVENTIONS "Slices"). Pure.

The Violation this kind exists to prevent is a Paper Tiger slice: planned while its flows have never been shown to run,
so teams build to a journey that breaks at the first join. So a slice goes to `planned` only when its recorded flow
check passed, and that is the grill gate's verdict (`gates.verdict`, which `decide_writes.gate_refusals` runs): every
contract its flows call has its case table with an error case, and the check's standing is `passed`. A finding is set
aside only by the dated flow-check override the checker itself reads under the slice page's `## Overrides`, which the
standing already applies; "not fully checked" has no override at all, because a check that did not finish proved
nothing to set aside. `--override` never covers the flow check here.

What it writes: `- **Status:** planned` among the slice's bullets and `- <today>: planned by @<lead>, in [[<session>]]`
under its `## History`, with no Decision bullet (a slice is planned, not decided). The Changes row is
`| SLC-nnn | - | planned | ... |`, `-` being "not planned yet". The later statuses are the teams' to set, so a planned
slice is never reopened here: changing the plan is the slice owner's edit, made with them.
"""
import re

from vela import slices
from vela.decisions import decide_writes, textedit

KIND = "slice"
TO, REOPEN_TO, DECISION = "planned", None, False
FIELDS = {}
STATUS = re.compile(r"^- \*\*Status:\*\*")


def claims(view, ident):
    pages = view.model.by_id.get(ident) or []
    return bool(pages) and pages[0].type == slices.PAGE_TYPE


def target(view, ident):
    found = decide_writes.page_target(view, ident, KIND)
    if found is None:
        return None
    page = view.model.by_id[ident][0]
    status = slices.read_page(page).status
    return decide_writes.Target(KIND, ident, found.path, found.name, status or "-", "", found.anchor, ident, ident)


def refusals(item, view, record, found):
    return []


def set_state(text, found, state):
    """The slice's `**Status:**` bullet set, or added after the last bullet above its first `##` section."""
    lines = text.rstrip("\n").split("\n")
    first = next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))
    for index in range(first):
        if STATUS.match(lines[index]):
            lines[index] = f"- **Status:** {state}"
            return "\n".join(lines) + "\n"
    bullets = [i for i in range(first) if lines[i].startswith("- **")]
    at = bullets[-1] + 1 if bullets else first
    lines[at:at] = [f"- **Status:** {state}"] if bullets else [f"- **Status:** {state}", ""]
    return "\n".join(lines) + "\n"


def extra(item, view, record, found, text):
    line = f"- {textedit.today(view)}: planned by {item['by']}, in [[{record.id}]]"
    return textedit.add_history(text, line)
