"""The companions' files on disk, git and the two caches (Buffer: the pure modules never touch these).

Everything lives under `.vela/companion/` in the vault: like the rest of `.vela/` it stays on this machine and is
never staged. Nobody edits these files by hand; a file vela cannot read is said, never read as empty.
"""
import json
import pathlib

from vela import errors, pageindex
from vela.edge import atomic, vaultfiles

FOLDER = ".vela/companion"
INDEX = FOLDER + "/pages.json"


def folder(root):
    return pathlib.Path(root) / FOLDER


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic.write_atomic(path, json.dumps(data, indent=1, sort_keys=True) + "\n")


def _read_index(path):
    """(index, why): the stored index, or (None, the reason it can't be used). Missing is not an error."""
    if not path.is_file():
        return None, ""
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return None, f"the page index could not be read ({exc})"
    if not isinstance(stored, dict) or stored.get("version") != pageindex.VERSION or not isinstance(stored.get("pages"), dict):
        return None, "the page index was written by another version of vela"
    return stored, ""


def page_index(root):
    """{"version": 1, "pages": {rel: {"mtime_ns", "size", **pageindex.entries(...)}}}: stats every page, re-parses only
    new or changed ones, drops deleted ones, and writes the file back only when something changed. An index that can't
    be read, or of another VERSION, is rebuilt whole and returned with "rebuilt": "<why>" so the caller can say it;
    it is never read as an empty plan."""
    root = pathlib.Path(root)
    path = root / INDEX
    stored, why = _read_index(path)
    old = stored["pages"] if stored else {}
    current = vaultfiles.stats(root)
    pages, changed = {}, bool(why) or set(old) != {rel for rel in current if rel.endswith(".md")}
    for rel, (mtime, size) in current.items():
        if not rel.endswith(".md"):
            continue
        kept = old.get(rel)
        if kept and kept["mtime_ns"] == mtime and kept["size"] == size:
            pages[rel] = kept
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise errors.ToolError(f"Cannot read {rel}: {exc}") from exc
        pages[rel] = {"mtime_ns": mtime, "size": size, **pageindex.entries(rel, text)}
        changed = True
    index = {"version": pageindex.VERSION, "pages": pages}
    if changed:
        write_json(path, index)
    if why:
        index["rebuilt"] = why
    return index
