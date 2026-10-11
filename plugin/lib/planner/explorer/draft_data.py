"""A reader's draft, for the page: what changed since the baseline they opened, and where it sits in the vault.

The Violation to prevent is a draft nobody can see (Black Box): the page shows N pages changed and, per page, the
lines. drafts.py computes the difference; this gives each change the key of its page so the view can link it.
Only a reader's workspace has a baseline; an owner has git for this.
"""
import pathlib

from planner import drafts
from planner.edge import copies
from planner.opening import OpenError


def for_workspace(root, vault, keys):
    """{"count", "pages": [...], "problem"} for the reader workspace at `root`; `problem` says why nothing was compared."""
    root = pathlib.Path(root)
    baseline_dir = root / copies.BASELINE
    if not baseline_dir.is_dir():
        return {"count": 0, "pages": [], "problem": f"{baseline_dir} is missing, so there is nothing to compare your pages with"}
    try:
        changes = drafts.compare(copies.read_tree(baseline_dir, skip_published=True), copies.read_tree(root, skip_published=True))
    except OpenError as exc:
        return {"count": 0, "pages": [], "problem": str(exc)}
    by_path = {p.path: p for p in vault.pages}
    for change in changes:
        page = by_path.get(change["path"])
        change["key"] = keys.page(page) if page is not None else ""
        change["title"] = str(page.meta.get("title") or page.name) if page is not None else change["path"]
    return {"count": len(changes), "pages": changes, "problem": ""}
