"""Opening a published copy as a private reader workspace. Pure: no disk, clock or network.

Two failures decide the shape. A workspace inside a OneDrive or SharePoint folder is synced while it is being
written, which is the corruption this whole design avoids, so the location is refused rather than warned about.
And a copy edited after it was published would be read as the owner's word, so the stamp's tree_hash is checked
and a mismatch stops the open, naming the files.

edge/copies.py reads the source and writes the workspace; cli.py orchestrates.
"""
import posixpath
import re

from planner import publish

SYNCED = re.compile(r"onedrive|sharepoint", re.IGNORECASE)
# Files a sync client or an operating system adds to a folder; none is part of a published copy.
OS_JUNK = {".DS_Store", "desktop.ini", "Thumbs.db"}
OS_JUNK_DIRS = ("__MACOSX/",)
DEFAULT_FOLDER = "PlannerWorkspaces"
COWORK_FOLDER = "planner-workspaces"
LAYOUT = (".planner/baseline", ".planner/workspace.json")


class OpenError(Exception):
    """The copy cannot be opened as asked; the message says what to change."""


def refuse_synced(parts, shown):
    """OneDrive and SharePoint folders sync while we write. `parts` are the path's folders; the first synced one is named."""
    for part in parts:
        if SYNCED.search(part):
            raise OpenError(f"{shown} is inside a synced folder ('{part}'). A synced workspace is the corruption this design avoids. "
                            "Pass --into with a folder that is not synced, or set PLANNER_WORKSPACES to one.")


def location_rule(into, workspaces_env, in_cowork):
    """Which rule picks the workspace folder: --into, then $PLANNER_WORKSPACES, then Cowork's working folder, then the home default."""
    if into:
        return "into"
    if workspaces_env:
        return "env"
    return "cowork" if in_cowork else "home"


def is_junk(path):
    return posixpath.basename(path) in OS_JUNK or any(path.startswith(d) or f"/{d}" in path for d in OS_JUNK_DIRS)


def check_names(names):
    """Every name in a source vault-relative with forward slashes, before anything is extracted."""
    for name in names:
        try:
            publish.check_name(name)
        except publish.PublishError as exc:
            raise OpenError(f"the source holds a name that would write outside the workspace, so I did not open it: {exc}") from exc


def content_files(files):
    """The copy's own files: no stamp, no OS junk."""
    return {path: data for path, data in files.items() if path != publish.STAMP_PATH and not is_junk(path)}


def verify_tree(files, stamp):
    """Stop when the files are not the ones the stamp hashed. The stamp may lack a hash (format drift): say so, do not guess."""
    want = stamp.get("tree_hash")
    if not want:
        raise OpenError("the stamp in this copy has no tree_hash, so I cannot tell whether it was changed after it was published.")
    if publish.tree_hash(content_files(files)) != want:
        raise OpenError("the files in this copy are not the ones the owner published (the stamp's tree_hash does not match). "
                        "Ask the owner for a fresh copy rather than opening one that was edited after publishing.")


def workspace_record(stamp, source, source_path, opened, author, planner_path):
    """The .planner/workspace.json content. `source_path` serves freshness only and never enters a proposal."""
    return {"role": "reader", "initiative": stamp["initiative"], "source": source, "source_path": source_path,
            "base_commit": stamp["commit"], "base_date": stamp["date"], "base_tree_hash": stamp.get("tree_hash", ""),
            "opened": opened, "author": author, "planner_path": planner_path}


def opened_message(stamp, folder):
    owner = stamp.get("owner", {})
    who = owner.get("name") or owner.get("contact") or "the owner"
    check = stamp.get("check", {})
    lines = [f"Opened {stamp['title']} at {stamp['short']}, published {stamp['date']} by {who}. "
             f"Check at publish: {check.get('errors', '?')} errors, {check.get('warnings', '?')} warnings.",
             f"  Your private copy is {folder}."]
    if stamp.get("dirty"):
        lines.append("  The owner published with uncommitted changes, so their latest pages may not be in this copy.")
    return lines


def reopen_message(existing, stamp):
    """What to say when the folder already holds a workspace. Phase 3 replays drafts onto a newer copy; until then, stop."""
    same = existing.get("initiative") in (None, stamp["initiative"])
    base = existing.get("base_commit", "")[:7] or "an unknown commit"
    if not same:
        return (f"That folder already holds a workspace for {existing.get('initiative')}, not {stamp['initiative']}. "
                "Pass --into with a different folder.")
    return (f"You already have this workspace open at {base}. I stopped so your drafts are not overwritten. "
            "Opening a newer copy onto it, which keeps your drafts and replays them over the new pages, is not built yet. "
            "Until it is, work on in this workspace, or open the newer copy into a different folder with --into.")
