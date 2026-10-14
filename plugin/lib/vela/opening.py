"""Opening a published copy as a private reader workspace. Pure: no disk, clock or network.

Three failures decide the shape. A workspace inside a folder a sync client (OneDrive, Dropbox, iCloud Drive, Google
Drive, Box) watches is rewritten while it is being worked in, which is the corruption this whole design avoids, so the
location is refused rather than warned about. A copy edited or damaged after it was published would be read as the
owner's word, so the stamp's tree_hash is checked and a mismatch stops the open; that catches accidents only, because
whoever edited a copy can recompute the hash, so it is never what makes opening safe. And a received copy is hostile
input (per-door checks once let a zip's .git/config run commands), so every name goes through untrusted.py before a
byte is written.

edge/copies.py reads the source and writes the workspace; cli.py orchestrates.
"""
import re

from vela import publish, untrusted

# Whole folder names a sync client creates. A name that merely contains "onedrive" (a repo called onedrive-migration) is not one.
SYNCED = (("OneDrive", re.compile(r"^onedrive( - .+)?$", re.IGNORECASE)),
          ("SharePoint", re.compile(r"^sharepoint( - .+)?$", re.IGNORECASE)),
          ("Dropbox", re.compile(r"^dropbox( \(.+\))?$", re.IGNORECASE)),
          ("Google Drive", re.compile(r"^(google ?drive|googledrive-.+|my drive)$", re.IGNORECASE)),
          ("iCloud Drive", re.compile(r"^(icloud ?drive|mobile documents|com~apple~clouddocs)$", re.IGNORECASE)),
          ("Box", re.compile(r"^box( sync)?$", re.IGNORECASE)))
OS_JUNK, OS_JUNK_DIRS = publish.OS_JUNK, publish.OS_JUNK_DIRS
DEFAULT_FOLDER = "PlannerWorkspaces"
COWORK_FOLDER = "planner-workspaces"
LAYOUT = (".planner/baseline", ".planner/workspace.json")


class OpenError(Exception):
    """The copy cannot be opened as asked; the message says what to change."""


def refuse_synced(parts, shown):
    """Folders a sync client watches change while we write. `parts` are the path's folders; the first synced one is named, with its tool."""
    for part in parts:
        for tool, pattern in SYNCED:
            if pattern.search(part):
                raise OpenError(f"{shown} is inside a synced folder ('{part}', which {tool} syncs). A synced workspace is the corruption this design avoids. "
                                "Pass --into with a folder that is not synced, or set PLANNER_WORKSPACES to one.")


def location_rule(into, workspaces_env, in_cowork):
    """Which rule picks the workspace folder: --into, then $PLANNER_WORKSPACES, then Cowork's working folder, then the home default."""
    if into:
        return "into"
    if workspaces_env:
        return "env"
    return "cowork" if in_cowork else "home"


is_junk = publish.is_junk


def check_names(names):
    """Every name in a source passes untrusted.py before anything is extracted: vault-relative, nothing in git's folder
    or the planner's private ones. A refusal names the file."""
    for name in names:
        kind, why = untrusted.verdict(name)
        if kind == untrusted.FORBIDDEN:
            raise OpenError(f"I did not open this copy: '{name}' is in it, and {why}.")


def content_files(files):
    """The copy's own files: no stamp, no OS junk."""
    return {path: data for path, data in files.items() if path != publish.STAMP_PATH and not is_junk(path)}


def admit(files):
    """({path: bytes} a reader workspace gets, [(path, why)] left out). Programs and tool settings (hooks, workflows, bin/,
    .claude/, editor plugins) are left out and reported, not written: a reader has no use for them and they run commands.
    The stamp stays. Any forbidden name refuses the whole copy."""
    candidates = {path: data for path, data in files.items() if path == publish.STAMP_PATH or not is_junk(path)}
    try:
        keep, left_out = untrusted.split_for_open(sorted(candidates))
    except untrusted.Refused as exc:
        raise OpenError(str(exc)) from exc
    return {path: candidates[path] for path in keep}, left_out


def verify_tree(files, stamp):
    """Stop when the files are not the ones the stamp hashed. The stamp may lack a hash (format drift): say so, do not guess.

    This notices accidents (a file edited, a folder half copied). It cannot notice a deliberate change: the hash is in the
    same archive, so whoever changed a file can recompute it. Copies made before OS junk was left out of the hash
    included it, so both sets are accepted."""
    want = stamp.get("tree_hash")
    if not want:
        raise OpenError("the stamp in this copy has no tree_hash, so I cannot tell whether it was changed after it was published.")
    everything = {path: data for path, data in files.items() if path != publish.STAMP_PATH}
    if want not in (publish.tree_hash(content_files(files)), publish.tree_hash(everything)):
        raise OpenError("the files in this copy are not the ones the owner published (the stamp's tree_hash does not match). "
                        "That usually means a page was edited or damaged after publishing: ask the owner for a fresh copy. "
                        "The check cannot tell you who sent a copy, so open only copies that came from the owner.")


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


SAME, NEWER, OLDER, OTHER_INITIATIVE, SAME_DAY = "same", "newer", "older", "other-initiative", "same-day"


def reopen_verdict(existing, stamp, confirmed_newer=False):
    """How the copy being opened relates to the workspace already in the folder: the same publish, a newer one to
    replay onto, an older one (never replayed: it would turn the owner's corrections back), or another initiative.

    A stamp holds a date, not a time. Two different publishes on one day cannot be put in order from their stamps, and
    guessing "newer" would replay drafts over the owner's later correction, so that case stops and asks, unless the
    reader says (--newer) that the copy being opened is the later one."""
    if existing.get("initiative") not in (None, stamp["initiative"]):
        return OTHER_INITIATIVE
    same_hash = not existing.get("base_tree_hash") or existing["base_tree_hash"] == stamp.get("tree_hash")
    if existing.get("base_commit") == stamp["commit"] and same_hash:
        return SAME
    if stamp["date"] < (existing.get("base_date") or ""):
        return OLDER
    if stamp["date"] == existing.get("base_date") and not confirmed_newer:
        return SAME_DAY
    return NEWER


def reopen_refusal(existing, stamp, verdict):
    """Why a re-open stops, in plain words, or "" when it goes on (a newer copy)."""
    base = existing.get("base_commit", "")[:7] or "an unknown commit"
    if verdict == OTHER_INITIATIVE:
        return (f"That folder already holds a workspace for {existing.get('initiative')}, not {stamp['initiative']}. "
                "Pass --into with a different folder.")
    if verdict == OLDER:
        return (f"The copy you gave me was published {stamp['date']} ({stamp['short']}), before the one this workspace is on "
                f"({base}, {existing.get('base_date', 'an unknown date')}). Replaying onto an older copy would turn the owner's corrections back, so I stopped. "
                "Open the newest copy you were sent.")
    if verdict == SAME_DAY:
        return (f"Two copies were published on {stamp['date']}: the one this workspace is on ({base}) and the one you gave me ({stamp['short']}). "
                "A stamp holds a date, not a time, so I cannot tell which is later, and replaying onto the earlier one would turn the owner's "
                "corrections back. If the one you gave me is the one the owner sent last, run the same command again with --newer. Nothing was changed.")
    return ""


def workspace_record_after_replay(existing, stamp, source, source_path, replayed, author):
    """workspace.json once the drafts sit on the new copy: the base moves, who opened it and when do not."""
    record = {**existing, "source": source, "source_path": source_path, "base_commit": stamp["commit"], "base_date": stamp["date"],
              "base_tree_hash": stamp.get("tree_hash", ""), "replayed": replayed}
    if author:
        record["author"] = author
    return record
