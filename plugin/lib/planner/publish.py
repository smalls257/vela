"""The read copy an owner hands to people who have no git. Pure: no disk, clock or network.

Two failures decide the shape. A copy built from the working tree could ship half-finished pages as if they
were the owner's word, so callers pass committed blobs only, and the stamp says when the vault was dirty
anyway (publishing is never refused; the reader is told instead). And a copy that cannot be traced to a commit
leaves a proposal with nothing to be applied against, so the stamp carries the full hash `git apply --3way` needs.

edge/vaultgit.py reads the blobs; edge/copies.py writes the folder or zip.
"""
import hashlib
import io
import json
import posixpath
import re
import zipfile

STAMP_PATH = ".planner/published.json"
STAMP_FORMAT = 1
# The built explorer, at the vault root so a colleague finds it in git or OneDrive without building anything. A view of the
# pages, not a page: a publish rebuilds it from the published content, and a reader's drafts never count it as a change.
DASHBOARD_PATH = "dashboard.html"
# Generated output, a person's private voice material, and the vendored plugin (the reader's own plugin runs).
EXCLUDED = (".git/", ".planner/", "voice/local/", ".claude/skills/planner/", DASHBOARD_PATH)
# The files a team commits that sit under EXCLUDED: the pinned layout (the vault .gitignore un-ignores it), so a reader's map is
# laid out like the owner's, and the dashboard. Still "excluded" as far as a reader's drafts go: neither is a page, so comparing
# a workspace with its baseline skips them.
KEPT = (".planner/explorer-pins.json", DASHBOARD_PATH)
ZIP_TIME = (1980, 1, 1, 0, 0, 0)


class PublishError(Exception):
    """The copy cannot be made as asked; the message says what to change."""


def is_excluded(path):
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in EXCLUDED)


def check_name(path):
    """A copy's names are vault-relative with forward slashes; anything else would escape the folder it is unpacked into."""
    if not path or path.startswith("/") or "\\" in path or re.match(r"^[A-Za-z]:", path):
        raise PublishError(f"'{path}' is not a vault-relative path with forward slashes.")
    if ".." in path.split("/"):
        raise PublishError(f"'{path}' climbs out of the vault.")
    return path


def selected(files):
    """The committed files that belong in a read copy, by path."""
    return {check_name(path): data for path, data in files.items() if path in KEPT or not is_excluded(path)}


def tree_hash(files):
    """sha256 over the sorted path and content hash of each file, so a tampered copy is detectable. The dashboard is left
    out: it is stamped with the day it was built, so counting it would make every publish of one commit look like
    different content to a reader's freshness check."""
    digest = hashlib.sha256()
    for path in sorted(name for name in files if name != DASHBOARD_PATH):
        digest.update(f"{path}\0{hashlib.sha256(files[path]).hexdigest()}\n".encode("utf-8"))
    return digest.hexdigest()


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "initiative"


def copy_name(title, short):
    """The one top folder of a zip: <initiative-slug>-<short commit>."""
    return f"{slug(title)}-{short}"


def owner_contact(config, git_name, git_email, name_flag="", contact_flag=""):
    """{"name", "contact"} for the stamp: the flags, else .planner.yaml owner_contact, else git config.

    A published copy with no one to write to leaves a reader stuck, so nothing resolving is an error.
    """
    contact = contact_flag or str(config.get("owner_contact") or "") or git_email
    name = name_flag or git_name or contact
    if not contact:
        raise PublishError("I do not know who a reader should write to. Set owner_contact in .planner.yaml, "
                           "set git user.email, or pass --owner-contact.")
    return {"name": name, "contact": contact}


def build_stamp(config, commit, short, date, dirty, owner, counts, files):
    return {"format": STAMP_FORMAT, "initiative": config["initiative"], "title": config["title"],
            "commit": commit, "short": short, "date": date, "dirty": dirty, "owner": owner,
            "check": {"errors": counts[0], "warnings": counts[1]}, "tree_hash": tree_hash(files)}


def stamp_bytes(stamp):
    return (json.dumps(stamp, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def with_stamp(files, stamp):
    return {**files, STAMP_PATH: stamp_bytes(stamp)}


def zip_bytes(files, top, executable=()):
    """One zip, one top folder, forward-slash names, fixed timestamps: the same input gives the same bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo(posixpath.join(top, check_name(path)), date_time=ZIP_TIME)
            info.external_attr = (0o755 if path in executable else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[path])
    return buffer.getvalue()


def dirty_message(short, uncommitted):
    if not uncommitted:
        return ""
    noun = "file" if uncommitted == 1 else "files"
    return f"published HEAD {short}; your {uncommitted} uncommitted {noun} {'is' if uncommitted == 1 else 'are'} not in it."
