"""The flow checker's periphery: what changed in git, the recorded results on disk, and the checker's own version.

The decisions are pure (flowcheck.impact, flowcheck.record, flowcheck.changed); this module only fetches facts and
writes the record. Git that cannot answer raises GitUnavailable, so the caller checks every slice and says why rather
than reading "no answer" as "nothing changed". A record that cannot be read or written is a warning the caller prints,
never a failure of the check and never silent: the record is advisory.
"""
import hashlib
import pathlib

from planner.edge import atomic, vaultgit
from planner.edge.vaultgit import GitUnavailable
from planner.flowcheck import record

PACKAGE = pathlib.Path(__file__).resolve().parents[1] / "flowcheck"


def checker_version():
    """A digest of the checker's own source: a recorded result from another checker is never reused, and nobody has to
    remember to bump a number when the semantics change."""
    digest = hashlib.sha256()
    for path in sorted(PACKAGE.glob("*.py")):
        digest.update(path.name.encode("utf-8") + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()[:16]


def read_store(root):
    """(text or None, warning). None when there is no record yet."""
    path = pathlib.Path(root) / record.PATH
    if not path.is_file():
        return None, ""
    try:
        return path.read_text(encoding="utf-8"), ""
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"{record.PATH} could not be read ({exc}), so every slice is checked afresh."


def read_record(root):
    """(store, warning): the record on disk as `record.read_store` reads it, for readers (the handoff, the dashboard).
    A file that does not read is an empty store with a warning saying so, so every slice reads "not checked"."""
    text, unreadable = read_store(root)
    store, corrupt = record.read_store(text)
    return store, unreadable or corrupt


def write_store(root, text):
    """Write the record whole or not at all. Returns a warning when it could not be written, "" when it was."""
    path = pathlib.Path(root) / record.PATH
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic.write_atomic(path, text)
    except OSError as exc:
        return f"the result could not be recorded in {record.PATH} ({exc}); the next --changed checks these slices again."
    return ""


def changed_files(root, revisions=None, since=None):
    """{vault-relative path: its text before the change, or None when it did not exist}, for every file that differs.

    revisions None and since None: the working tree (staged or not) against HEAD, plus untracked files.
    since X: the working tree against commit X, plus untracked files.
    revisions "A..B": what changed between A and B, read before as of A; "A" alone is the same as since A.
    Paths are relative to the vault root, which may sit inside a bigger repo."""
    code, _, err = vaultgit.run_git(root, "rev-parse", "--is-inside-work-tree")
    if code != 0:
        raise GitUnavailable(err or f"{root} is not inside a git repository")
    untracked = True
    if revisions and ".." in revisions:
        base, _, target = revisions.partition("..")
        if not base or not target or target.startswith("."):
            raise GitUnavailable(f"'{revisions}' is not a range of the form A..B")
        diff = ("diff", "--name-status", "--no-renames", "-z", "--relative", base, target)
        untracked = False
    else:
        base = since or revisions or "HEAD"
        diff = ("diff", "--name-status", "--no-renames", "-z", "--relative", base)
    code, _, err = vaultgit.run_git(root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    if code != 0:
        raise GitUnavailable(f"'{base}' names no commit" + (f" ({err})" if err else ""))
    code, out, err = vaultgit.run_git(root, *diff, binary=True)
    if code != 0:
        raise GitUnavailable(f"git diff failed: {err}")
    fields = out.decode("utf-8", "replace").split("\0")
    statuses = {}
    for status, path in zip(fields[0::2], fields[1::2]):
        if path:
            statuses[path] = status[:1]
    if untracked:
        code, out, err = vaultgit.run_git(root, "ls-files", "--others", "--exclude-standard", "-z", binary=True)
        if code != 0:
            raise GitUnavailable(f"git ls-files failed: {err}")
        for path in out.decode("utf-8", "replace").split("\0"):
            if path:
                statuses.setdefault(path, "A")
    before = {}
    for path, status in sorted(statuses.items()):
        if status == "A":
            before[path] = None
            continue
        code, data, err = vaultgit.run_git(root, "show", f"{base}:./{path}", binary=True)
        if code != 0:
            raise GitUnavailable(f"git cannot show {path} as of {base}: {err}")
        try:
            before[path] = data.decode("utf-8")
        except UnicodeDecodeError:
            before[path] = data.decode("utf-8", "replace")
    return before
