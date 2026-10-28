"""The git calls `vela close stage` and `vela guard staged` make: what changed, what is staged, staging by exact
path, and a commit of exactly those paths.

This is the periphery (Buffer): `guard.py` decides from paths and never sees git. Every call goes through
`vaultgit.run_git`, so each has a timeout and a git that cannot answer raises `GitUnavailable` with its reason;
nothing here turns a failure into an empty list (Silent Fallback), because an empty list would read as "nothing to
stage" or "nothing forbidden is staged".

Paths are read with `-z`, so a name with spaces, quotes or non-ASCII letters arrives exactly as it is on disk, and are
passed back with `GIT_LITERAL_PATHSPECS=1`, so a page called `[draft] notes.md` is that file and never a glob.
"""
from vela.edge import vaultgit

LITERAL = {"GIT_LITERAL_PATHSPECS": "1"}


def _ok(root, *args, env=None):
    code, out, err = vaultgit.run_git(root, *args, env=env, binary=True)
    if code != 0:
        raise vaultgit.GitUnavailable(f"git {args[0]} failed: {err or out.decode('utf-8', 'replace').strip()}")
    return out.decode("utf-8")


def _fields(out):
    return [field for field in out.split("\0") if field]


def changed_paths(root):
    """Every path git status reports under the plan's folder, tracked or untracked (each untracked file named, not its
    folder), relative to that folder. Ignored files are not listed: git's own .gitignore already keeps them out of
    `git add` by path. Another plan's files in the same repo are never listed."""
    return vaultgit.status_paths(root, "--untracked-files=all")


def changed_paths_in_repo(root):
    """The same for the whole repository, repository-relative: for a proposal's worktree, which is made for one plan
    and judged as a whole before anything is committed."""
    return vaultgit.status_paths(root, "--untracked-files=all", pathspec=(":/",))


def staged_paths(root):
    """Paths under the plan's folder the index would add or change in the next commit, relative to that folder.
    Deletions are left out: removing an inbox file from the repository is the cure, not the problem. Honors
    GIT_INDEX_FILE, which git sets for a partial commit's hook."""
    return _fields(_ok(root, "diff", "--cached", "--name-only", "-z", "--no-renames", "--diff-filter=d", "--relative"))


def staged_paths_in_repo(root):
    """Every path the index would add or change anywhere in the repository, repository-relative. The pre-commit hook
    asks this, because a commit carries the whole index, whichever plan the files belong to."""
    return _fields(_ok(root, "diff", "--cached", "--name-only", "-z", "--no-renames", "--diff-filter=d"))


def committed_paths_since(root, since):
    """Every path any commit in `since..HEAD` added or changed anywhere in the repository, repository-relative. Not the
    net difference: a private file added in one commit and removed in the next is still in the history a push sends.
    Deletions are left out, as in `staged_paths_in_repo`."""
    return sorted(set(_fields(_ok(root, "log", "--name-only", "--format=", "-z", "--no-renames", "--diff-filter=d",
                                  f"{since}..HEAD"))))


def stage(root, paths):
    """`git add` exactly these paths (a deleted one is staged as deleted). Never a folder, `.`, `-A` or `-u`."""
    if paths:
        _ok(root, "add", "--", *paths, env=LITERAL)


def commit(root, message, paths):
    """Commit exactly `paths` with `message` (`--only`: whatever else sits in the index stays out of this commit) and
    return the new commit's short hash. A failing pre-commit hook raises with the hook's own words."""
    _ok(root, "commit", "--quiet", "--only", "-m", message, "--", *paths, env=LITERAL)
    return _ok(root, "rev-parse", "--short", "HEAD").strip()


def staged_deletions(root):
    """Paths whose deletion is already in the index (gone from disk and index alike), which `stage` can't name again:
    a pathspec that matches nothing makes the whole add fail."""
    return _fields(_ok(root, "diff", "--cached", "--name-only", "-z", "--no-renames", "--diff-filter=D", "--relative"))


def staged_deletions_in_repo(root):
    return _fields(_ok(root, "diff", "--cached", "--name-only", "-z", "--no-renames", "--diff-filter=D"))


def commit_index(root, message):
    """Commit the index as it stands with `message` and return the short hash. For a proposal's worktree, where a
    three-way apply left the reader's changes staged: the caller has checked the index against guard.py first."""
    _ok(root, "commit", "--quiet", "-m", message)
    return _ok(root, "rev-parse", "--short", "HEAD").strip()
