"""`vela decide "<release name>"`: a release decided, on `04b-releases.md` (grill's "File each decision as its branch closes"; CONVENTIONS "Releases").
Pure.

A release is a `## <name>` section with no ID, so it is named by its heading, exactly as written. A Grill decides it by
setting that section's `**State:**` to `decided` and adding the receipt, `- **Decision:** [[<session>]] c07, @who`
(written by `decide_writes.history_bullets`), directly under the page's `## History`; without that Decision check reports E303 on the release's heading. The Violation this kind's shape
prevents is a Leaky Narrative in the dispatcher: every other kind is found by an ID, and a release is not, so finding it
by its heading lives here and nowhere else.

The grill gate (`gates.verdict`) has no view of a release (it judges IDs), so none of its rules run on one; a release
that names its flows rests on its slices, and each slice is planned through its own flow check. The record's Changes
row names the release by its heading. Reopened, it goes back to `assumption`.
"""
from vela import releases
from vela.decisions import decide_writes, textedit

KIND = "release"
TO, REOPEN_TO, DECISION = "decided", "assumption", True
FIELDS = {}


def _release(view, ident):
    return next((r for r in releases.releases(view.model) if r.name == ident), None)


def claims(view, ident):
    return _release(view, ident) is not None


def target(view, ident):
    found = _release(view, ident)
    page = releases.page(view.model)
    if found is None or page is None:
        return None
    return decide_writes.Target(KIND, ident, page.path, ident, found.state, "", ident, releases.PAGE_ID, "")


def refusals(item, view, record, found):
    return []


def set_state(text, found, state):
    lines = text.rstrip("\n").split("\n")
    start = textedit.find_heading(lines, found.id, 2)
    end = textedit.section_end(lines, start, 2)
    changed = decide_writes.set_bullet_state(lines, start, end, state)
    if changed is None:
        changed = lines[:start + 1] + ["", f"- **State:** {state}"] + lines[start + 1:]
    return "\n".join(changed) + "\n"
