"""git for reviewing a proposal: a worktree on its own branch, the patch applied there, decisions committed there.

The periphery for review. The owner's checkout is never switched or changed: the work happens in a git worktree
beside it. Every call has a timeout (vaultgit.run_git), nothing pushes, and nothing bypasses a hook. A failure
raises GitUnavailable with git's own words.
"""
import pathlib
import tempfile

from planner.edge.vaultgit import git_out, run_git

APPLY_TIMEOUT = 60
COMMIT_TIMEOUT = 120  # a repo's pre-commit hooks run inside this


def commit_exists(root, commit):
    return run_git(root, "cat-file", "-e", f"{commit}^{{commit}}")[0] == 0


def start_ref(root):
    """('main' or 'master' if the repo has one, else HEAD), so the branch starts from the owner's line of record."""
    for name in ("main", "master"):
        if run_git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}")[0] == 0:
            return name
    return "HEAD"


def commits_between(root, base, ref):
    """How many commits `ref` has that `base` does not."""
    return int(git_out(root, "rev-list", "--count", f"{base}..{ref}"))


def branch_exists(root, branch):
    return run_git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}")[0] == 0


def add_worktree(root, folder, branch, start):
    git_out(root, "worktree", "add", "-b", branch, str(folder), start, timeout=APPLY_TIMEOUT)


def prefix(root):
    """The vault's folder inside its repo ("" when the vault is the repo root)."""
    return git_out(root, "rev-parse", "--show-prefix")


def toplevel(root):
    return pathlib.Path(git_out(root, "rev-parse", "--show-toplevel"))


def _apply(worktree, patch_text, args, directory):
    """(returncode, stderr) of git apply with the patch written to a temp file outside every repo."""
    with tempfile.TemporaryDirectory() as folder:
        patch = pathlib.Path(folder) / "changes.patch"
        patch.write_bytes(patch_text.encode("utf-8"))
        extra = [f"--directory={directory.rstrip('/')}"] if directory else []
        code, out, err = run_git(worktree, "apply", *args, *extra, str(patch), timeout=APPLY_TIMEOUT)
    return code, "\n".join(x for x in (out, err) if x)


def apply_three_way(worktree, patch_text, directory):
    """(clean, unmerged paths, git's words). Conflicts are left in the files as markers; a refusal leaves nothing."""
    code, words = _apply(worktree, patch_text, ["--3way"], directory)
    unmerged = git_out(worktree, "diff", "--name-only", "--diff-filter=U").splitlines()
    return code == 0 and not unmerged, unmerged, words


def revert(worktree, patch_text, directory):
    """Take these hunks back out and stage the result. (ok, git's words)."""
    code, words = _apply(worktree, patch_text, ["-R", "--index"], directory)
    return code == 0, words


def discard_worktree(root, folder, branch):
    """Take back a worktree and its branch after a refusal, so a failed review leaves the repo as it found it."""
    git_out(root, "worktree", "remove", "--force", str(folder), timeout=APPLY_TIMEOUT)
    git_out(root, "branch", "-D", branch)


def changed_entries(worktree):
    """[(status, new mode, path)] for everything the applied patch changed, as git itself reports it (renames shown as a
    delete plus an add). The patch parser is one defence; what git really did is the one that counts."""
    out = git_out(worktree, "diff", "HEAD", "--raw", "-z", "--no-renames", "--no-abbrev")
    fields = [f for f in out.split("\0") if f]
    return [(meta.split()[-1][0], meta.split()[1], path) for meta, path in zip(fields[0::2], fields[1::2])]


def has_changes(worktree):
    return bool(git_out(worktree, "status", "--porcelain"))


def unmerged(worktree):
    return git_out(worktree, "diff", "--name-only", "--diff-filter=U").splitlines()


def commit_all(worktree, message):
    """Stage everything and commit with the owner's identity and hooks. Returns the short hash."""
    git_out(worktree, "add", "-A", timeout=COMMIT_TIMEOUT)
    git_out(worktree, "commit", "-q", "-m", message, timeout=COMMIT_TIMEOUT)
    return git_out(worktree, "rev-parse", "--short", "HEAD")


def head_short(worktree):
    return git_out(worktree, "rev-parse", "--short", "HEAD")


def branch_name(worktree):
    return git_out(worktree, "rev-parse", "--abbrev-ref", "HEAD")

