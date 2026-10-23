"""`vela decide <page id>`: a page decided, its `state:` frontmatter (grill's "File each decision as its branch closes"). Pure.

The page kind is the fallback for any page with an `id` and a `state:` that no more specific kind claims (the strategy,
an app page, an initiative section). The Violation its shape prevents is a God Method in the dispatcher: an epic and a
slice are pages too, but each has rules of its own (a yes per criterion group; planned, not decided), so they are their
own kinds, tried first, and this one knows only frontmatter.

Its Decision, Why and the rest go directly under the page's `## History`, where CONVENTIONS puts page-level bullets.
Reopened, it goes back to `assumption`.
"""
from vela.decisions import decide_writes

KIND = "page"
TO, REOPEN_TO, DECISION = "decided", "assumption", True
FIELDS = {}


def claims(view, ident):
    pages = view.model.by_id.get(ident) or []
    return bool(pages) and pages[0].meta.get("state") is not None


def target(view, ident):
    return decide_writes.page_target(view, ident, KIND)


def refusals(item, view, record, found):
    return []


def set_state(text, found, state):
    return decide_writes.set_frontmatter_state(text, state)
