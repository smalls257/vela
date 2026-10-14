"""The git and disk side of `planner close sync-main`: fetch, compare, merge, abort, and the close state file.

This is the periphery (Buffer): `mergeplan` decides which hunks are safe from text alone, `closestate` says what a
record means, and this module only runs git and reads or writes files. Every git call goes through
`vaultgit.run_git`, which sets a timeout and raises `GitUnavailable` when git cannot answer (Black Box: a hung fetch
must not hang close). Nothing here turns a failure into an answer: a git that exits with an error raises
`MergeGitFailed` carrying git's own words, so the command prints them.

Two git rules live here because they decide whose writing survives:

- The generated-only re-merge is `git merge --no-edit -X ours origin/main`. `-X ours` decides only the hunks that
  conflict; every edit that merged cleanly, on either side, is kept. It is never `git checkout --ours/--theirs <file>`,
  which takes one side of the whole file and drops the other side's edits (one wrong `--theirs` loses the owner's
  writing).
- A merge that stopped is always aborted (`git merge --abort`) before the command returns, so the lead's copy is left
  as it was and the lines listed are lines of a file they can open.
"""
import pathlib

from vela import closestate, roles
from vela.edge import atomic, vaultgit

FETCH_TIMEOUT = 30  # a close may fetch a real remote; long enough for that, short enough to never look hung
MAIN = "origin/main"


class MergeGitFailed(Exception):
    """git ran and refused, or could not run: git's own message, for the command to print (exit 2)."""


def _git(root, *args, timeout=vaultgit.GIT_TIMEOUT, env=None):
    try:
        return vaultgit.run_git(root, *args, timeout=timeout, env=env)
    except vaultgit.GitUnavailable as exc:
        raise MergeGitFailed(str(exc)) from exc


def _out(root, *args):
    code, out, err = _git(root, *args)
    if code != 0:
        raise MergeGitFailed(f"git {' '.join(args)} failed: {err or out}")
    return out


def fetch_origin(root, timeout=FETCH_TIMEOUT):
    """"" when `git fetch origin` worked, else why it did not (a plain reason: the command asks the lead)."""
    try:
        code, out, err = vaultgit.run_git(root, "fetch", "--quiet", "origin", timeout=timeout, env=vaultgit.NO_PROMPT)
    except vaultgit.GitUnavailable as exc:
        return str(exc)
    return "" if code == 0 else ((err or out or "git fetch failed").splitlines() or ["git fetch failed"])[0]


def sha(root, ref):
    """The full commit sha of `ref`; MergeGitFailed naming the ref when it does not exist."""
    code, out, err = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if code != 0 or not out:
        raise MergeGitFailed(f"{ref} does not name a commit here{': ' + err if err else ''}")
    return out


def has_ref(root, ref):
    return _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")[0] == 0


def changed_paths(root, before, after):
    """Paths that differ between two commits (what a merge changed in the lead's copy)."""
    return [line for line in _out(root, "diff", "--name-only", before, after).splitlines() if line]


def current_branch(root):
    """The checked-out branch name, or "HEAD" when detached."""
    return _out(root, "rev-parse", "--abbrev-ref", "HEAD")


def is_ancestor(root, older, newer):
    """True when `older` is already in `newer`. git's exit 1 means "no"; any other failure raises."""
    code, out, err = _git(root, "merge-base", "--is-ancestor", older, newer)
    if code in (0, 1):
        return code == 0
    raise MergeGitFailed(f"git merge-base --is-ancestor {older} {newer} failed: {err or out}")


def tracked_changes(root):
    """Tracked files with uncommitted changes, staged or not. Untracked files are left out: a merge only refuses over
    one when main adds the same path, and then git's own error is printed."""
    out = _out(root, "status", "--porcelain", "--untracked-files=no")
    return [line[3:] for line in out.splitlines() if line.strip()]


def merge(root, ref=MAIN, ours_on_conflict=False):
    """(exit code, git's output). Exit 0 is a clean merge; anything else the caller reads with `conflicted_files`."""
    args = ["merge", "--no-edit"] + (["-X", "ours"] if ours_on_conflict else []) + [ref]
    code, out, err = _git(root, *args, timeout=120)
    return code, "\n".join(part for part in (out, err) if part)


def conflicted_files(root):
    out = _out(root, "diff", "--name-only", "--diff-filter=U")
    return [line for line in out.splitlines() if line]


def merging(root):
    """True while a merge is stopped part-way (MERGE_HEAD exists)."""
    return _git(root, "rev-parse", "--verify", "--quiet", "MERGE_HEAD")[0] == 0


def abort(root):
    _out(root, "merge", "--abort")


def conflicted_text(root, path):
    """The file's text with git's markers, or None when it is not there or not UTF-8 text (a modify/delete or binary
    conflict). None is not "no conflict": mergeplan counts such a file as outside."""
    try:
        return (pathlib.Path(root) / path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def state_path(root, key):
    return pathlib.Path(root) / closestate.FOLDER / f"{key}.json"


def write_state(root, key, rec):
    """Write the close state record whole, through edge/atomic, and return its path."""
    path = state_path(root, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic.write_atomic(path, closestate.dumps(rec))
    return path


def read_state(root, key):
    """The record for `key`, or None when there is none. An unreadable file raises closestate.StateUnreadable (the gate
    says so; it never reads it as a pass)."""
    path = state_path(root, key)
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise closestate.StateUnreadable(f"{path} could not be read ({exc})") from exc
    return closestate.parse(text)


def is_reader_copy(root):
    """True for a published read copy: `.planner/workspace.json` and no `.git`. Decided without running git, because a
    read copy must run no git at all."""
    root = pathlib.Path(root)
    facts = roles.Facts(git_here=(root / ".git").exists(), has_workspace=(root / ".planner" / "workspace.json").is_file())
    return roles.decide(facts).role == roles.READER


def sync_verdict(root):
    """What the close gate says about sync-main for this copy: closestate.verdict of this branch's record (None when
    sync-main never ran here). Raises closestate.StateUnreadable or MergeGitFailed; neither is ever a pass."""
    key = closestate.READER_KEY if is_reader_copy(root) else closestate.key_for(current_branch(root))
    return closestate.verdict(read_state(root, key))
