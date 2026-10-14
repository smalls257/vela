"""git (and, in a reader copy, the folder) for `planner session open`: read the candidate session records and switch.

The periphery for `sessions.py`, which decides. What is read, and why:

- `refs/heads/session/*` and `refs/remotes/origin/session/*`: a session opened on another machine has its branch only
  on origin, and it is still this lead's open session. Only what the last fetch saw is known; nothing here fetches,
  so `session open` stays fast and works offline.
- the current branch, whatever its name: an answer session's record sits on its challenge's branch, and a branch a
  lead renamed is still where the work is.
- one `git grep -l '^status: open'` over all those tips narrows the records to read. Every session branch carries
  every closed record merged from `main`, so reading each file of each branch would cost branches x records git
  calls. For a candidate on origin whose local branch also exists, the local copy is read too, so `sessions.py` can
  prefer it (the local branch may already say `closed`).

A reader copy (a published folder: `.planner/workspace.json`, no `.git`) has no branches. It is recognized from the
disk alone and its `sessions/*.md` are read in place; no git command runs there, so a machine with no git works, and a
copy that sits inside some other repo never reads that repo's history.

Every git call has a timeout (vaultgit.run_git) and a failure raises GitUnavailable with git's words; nothing here
turns a failure into "no session is open".
"""
import pathlib

from vela import roles
from vela.edge.vaultgit import GitUnavailable, git_out, run_git

SWITCH_TIMEOUT = 60  # a checkout of a large vault, with hooks, can take a while
PATTERNS = ("refs/heads/session/", "refs/remotes/origin/session/")


def is_read_copy(root):
    """True for a published copy, judged by the same access rule `planner role` uses, from the disk alone."""
    root = pathlib.Path(root)
    facts = roles.Facts(has_workspace=(root / ".planner" / "workspace.json").is_file(), git_here=(root / ".git").exists())
    return roles.decide(facts).role == roles.READER


def folder_records(root):
    """[("", path, text)] for every `sessions/*.md` in a reader copy's folder."""
    folder = pathlib.Path(root) / "sessions"
    return [("", f"sessions/{path.name}", path.read_text(encoding="utf-8"))
            for path in sorted(folder.glob("*.md")) if path.is_file()]


def session_refs(root):
    """Every local and origin `session/*` ref, plus the current branch, as full ref names."""
    listed = git_out(root, "for-each-ref", "--format=%(refname)", *PATTERNS).splitlines()
    code, current, _ = run_git(root, "symbolic-ref", "-q", "HEAD")
    refs = [ref for ref in listed if ref]
    if code == 0 and current and current not in refs:
        refs.append(current)  # detached HEAD (code 1) has no branch to report
    return refs


def _grep_open(root, prefix, refs):
    """[(ref, vault-relative path)] of `sessions/*.md` files with a `status: open` line, at each ref's tip. The
    pathspec is relative to the vault folder (git runs there); the paths git prints may carry the repo prefix."""
    code, out, err = run_git(root, "grep", "-l", "^status: open", *refs, "--", "sessions/*.md")
    if code == 1:  # git grep's "nothing matched"
        return []
    if code != 0:
        raise GitUnavailable(f"git grep over the session branches failed: {err or out}")
    hits = []
    for line in out.splitlines():
        ref, _, path = line.partition(":")
        hits.append((ref, path[len(prefix):] if prefix and path.startswith(prefix) else path))
    return hits


def _show(root, prefix, ref, path):
    return git_out(root, "show", f"{ref}:{prefix}{path}")


def _local_twin(root, prefix, ref, path):
    """The local branch's copy of a record found on origin, or None when there is no local branch or no such file."""
    if not ref.startswith(PATTERNS[1]):
        return None
    local = "refs/heads/" + ref[len("refs/remotes/origin/"):]
    if run_git(root, "cat-file", "-e", f"{local}:{prefix}{path}")[0] != 0:
        return None
    return local, path, _show(root, prefix, local, path)


def branch_records(root):
    """[(ref, path, text)] of every candidate open record on the session branches and the current branch. Paths are
    relative to the vault folder, as in a reader copy."""
    refs = session_refs(root)
    if not refs:
        return []
    prefix = git_out(root, "rev-parse", "--show-prefix")
    found, seen = [], set()
    for ref, path in _grep_open(root, prefix, refs):
        twin = _local_twin(root, prefix, ref, path)
        for entry in [(ref, path, _show(root, prefix, ref, path))] + ([twin] if twin else []):
            if entry[:2] not in seen:
                seen.add(entry[:2])
                found.append(entry)
    return found


def current_branch(root):
    code, out, _ = run_git(root, "symbolic-ref", "-q", "--short", "HEAD")
    return out if code == 0 else None


def switch(root, branch, remote_only):
    """(ok, git's words). A branch only on origin gets a local branch tracking it; git refusing (uncommitted changes
    the switch would overwrite) is returned as git said it, for the caller to relay."""
    args = ["switch", "--track", f"origin/{branch}"] if remote_only else ["switch", branch]
    code, out, err = run_git(root, *args, timeout=SWITCH_TIMEOUT)
    return code == 0, "\n".join(x for x in (err, out) if x)
