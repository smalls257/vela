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


def parse_porcelain(out):
    """Paths from `git status --porcelain=v1 -z`: each entry is `XY path`, and a rename or copy (`R`/`C` in either
    column) is followed by its old path as a field of its own, which is skipped: the new path is what changed."""
    paths, fields, i = [], out.split("\0"), 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if len(entry) < 4:
            continue
        status, path = entry[:2], entry[3:]
        paths.append(path)
        if "R" in status or "C" in status:
            i += 1
    return paths


def changed_paths(root):
    """Every path git status reports, tracked or untracked (each untracked file named, not its folder). Ignored files
    are not listed: git's own .gitignore already keeps them out of `git add` by path."""
    return parse_porcelain(_ok(root, "status", "--porcelain=v1", "-z", "--untracked-files=all"))


def staged_paths(root):
    """Paths the index would add or change in the next commit. Deletions are left out: removing an inbox file from the
    repository is the cure, not the problem. Honors GIT_INDEX_FILE, which git sets for a partial commit's hook."""
    return _fields(_ok(root, "diff", "--cached", "--name-only", "-z", "--no-renames", "--diff-filter=d"))


def stage(root, paths):
    """`git add` exactly these paths (a deleted one is staged as deleted). Never a folder, `.`, `-A` or `-u`."""
    if paths:
        _ok(root, "add", "--", *paths, env=LITERAL)


def commit(root, message, paths):
    """Commit exactly `paths` with `message` (`--only`: whatever else sits in the index stays out of this commit) and
    return the new commit's short hash. A failing pre-commit hook raises with the hook's own words."""
    _ok(root, "commit", "--quiet", "--only", "-m", message, "--", *paths, env=LITERAL)
    return _ok(root, "rev-parse", "--short", "HEAD").strip()
