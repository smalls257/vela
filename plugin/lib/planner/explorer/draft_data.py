"""A reader's draft, for the page: what changed since the baseline they opened, and where it sits in the vault.

The Violation to prevent is a draft nobody can see (Black Box): the page shows N pages changed and, per page, the
lines. drafts.py computes the difference; this gives each change the key of its page so the view can link it.
Only a reader's workspace has a baseline; an owner has git for this.

After a re-open (replay.py) some pages are in conflict: the page holds the owner's version and the reader's sits
beside it. Those are listed first, as `conflicts`, each with the lines the reader's version has that the owner's page
does not, because an unsettled page is what the reader must see before any other draft. `merged` marks the pages the
replay joined, so a reader knows to read them once.
"""
import pathlib

from planner import drafts
from planner.edge import copies, replays
from planner.opening import OpenError

KIND_WORDS = {"both-edited": "You and the owner changed the same lines.", "both-added": "You and the owner both added this page.",
              "owner-deleted": "The owner deleted this page; you had changed it.", "you-deleted": "You deleted this page; the owner changed it, so it is back.",
              "binary": "A binary file you and the owner both changed."}


def conflict_card(root, conflict):
    """One open conflict as the page draws it: the page, where the reader's side is, and mine against the owner's page."""
    root = pathlib.Path(root)
    mine = (root / conflict["mine"]).read_bytes()
    page = (root / conflict["path"]).read_bytes() if (root / conflict["path"]).is_file() else None
    binary = drafts.is_binary(mine) or (page is not None and drafts.is_binary(page))
    card = {"path": conflict["path"], "mine": conflict["mine"], "kind": conflict["kind"], "why": KIND_WORDS.get(conflict["kind"], conflict.get("note", "")),
            "ranges": conflict.get("lines", []), "binary": binary, "status": "conflict", "lines": [], "truncated": False, "added": 0, "removed": 0}
    if not binary and conflict["kind"] != "you-deleted":
        change = drafts.text_change(conflict["path"], "changed", drafts.collapse_generated((page or b"").decode("utf-8")), drafts.collapse_generated(mine.decode("utf-8")))
        card.update(lines=change["lines"], truncated=change["truncated"], added=change["added"], removed=change["removed"])
    return card


def for_workspace(root, vault, keys):
    """{"count", "pages", "conflicts", "merged", "problem"} for the reader workspace at `root`; `problem` says why nothing was compared.
    `count` is the changed pages (conflicts are separate: their page holds the owner's version, so it differs from nothing)."""
    root = pathlib.Path(root)
    baseline_dir = root / copies.BASELINE
    if not baseline_dir.is_dir():
        return {"count": 0, "pages": [], "conflicts": [], "merged": [], "problem": f"{baseline_dir} is missing, so there is nothing to compare your pages with"}
    try:
        changes = drafts.compare(copies.read_tree(baseline_dir, skip_published=True), copies.read_tree(root, skip_published=True))
        record, open_conflicts = replays.read_record(root), replays.open_conflicts(root)
    except OpenError as exc:
        return {"count": 0, "pages": [], "conflicts": [], "merged": [], "problem": str(exc)}
    by_path = {p.path: p for p in vault.pages}

    def label(page, path):
        return keys.page(page) if page is not None else "", str(page.meta.get("title") or page.name) if page is not None else path

    merged = set(record.get("merged", []))
    for change in changes:
        change["key"], change["title"] = label(by_path.get(change["path"]), change["path"])
        change["merged"] = change["path"] in merged
    conflicts = []
    for conflict in open_conflicts:
        card = conflict_card(root, conflict)
        card["key"], card["title"] = label(by_path.get(conflict["path"]), conflict["path"])
        conflicts.append(card)
    return {"count": len(changes), "pages": changes, "conflicts": conflicts, "merged": sorted(merged), "problem": ""}
