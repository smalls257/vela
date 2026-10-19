"""The log of what a person typed, `.vela/said/<session or branch>.log` (the edge for `vela/said.py`).

`.vela/` is the tool's local state and `guard.py` never stages it, so a log of someone's messages is never committed.
Appends are one short line each, so two sessions writing at once don't interleave inside an entry.
"""
import pathlib
import re

from vela import said

FOLDER = ".vela/said"


def log_path(root, name):
    safe = re.sub(r"[^\w.-]+", "-", name).strip("-.") or "session"
    return pathlib.Path(root) / FOLDER / f"{safe}.log"


def append(root, name, at, text):
    path = log_path(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as out:
        out.write(said.log_line(at, text) + "\n")
    return path


def read_all(root):
    """The text of every log, or None when there is none (hooks never fired here): the caller must not read that as
    'nothing was typed'."""
    folder = pathlib.Path(root) / FOLDER
    if not folder.is_dir():
        return None
    logs = sorted(folder.glob("*.log"))
    if not logs:
        return None
    return [p.read_text(encoding="utf-8", errors="replace") for p in logs]


def typed_messages(root):
    """What the person typed, one string per message, or None when no log exists (nothing can be proven either way)."""
    logs = read_all(root)
    return None if logs is None else said.messages(logs)
