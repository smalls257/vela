"""The git calls `vela voice settle` makes: does a page differ from HEAD, which blob HEAD holds for it, and restoring
one page to HEAD by exact path (overhaul Task 19).

Periphery (Buffer): `commands/voice_settle.py` decides from the texts these return and never runs git itself. Every
call goes through `vaultgit.run_git`, so a git that cannot answer raises `GitUnavailable` with its reason; nothing here
reads a failure as "no difference" (Silent Fallback), because that would skip the checkpoint a restore depends on.
Paths go with `GIT_LITERAL_PATHSPECS=1`, as in `stagegit`, so a page called `[draft] notes.md` is that file.
"""
from vela.edge import stagegit, vaultgit


def differs_from_head(root, page):
    """True when the working tree or the index holds a change to `page` that HEAD does not."""
    code, _, err = vaultgit.run_git(root, "diff", "--quiet", "HEAD", "--", page, env=stagegit.LITERAL)
    if code not in (0, 1):
        raise vaultgit.GitUnavailable(f"git diff HEAD -- {page} failed: {err}")
    return code == 1


def head_blob(root, page):
    """The blob HEAD holds for `page`, or None when HEAD has no such file."""
    code, out, err = vaultgit.run_git(root, "rev-parse", "--verify", "--quiet", vaultgit.at("HEAD", page))
    if code == 0:
        return out
    if code == 1 and not err:
        return None
    raise vaultgit.GitUnavailable(f"git rev-parse HEAD:{page} failed: {err}")


def head_text(root, page):
    """`page` as HEAD holds it, exactly, or None when HEAD has no such file."""
    code, out, err = vaultgit.run_git(root, "show", vaultgit.at("HEAD", page), binary=True)
    if code == 0:
        return out.decode("utf-8", "replace")
    if "does not exist" in err or "exists on disk, but not in" in err:
        return None
    raise vaultgit.GitUnavailable(f"git show HEAD:{page} failed: {err}")


def restore(root, page):
    """`page` back to HEAD in the index and the working tree, and no other file: a staged copy of a failed rewrite
    must not survive to be committed."""
    code, out, err = vaultgit.run_git(root, "restore", "--source=HEAD", "--staged", "--worktree", "--", page,
                                      env=stagegit.LITERAL)
    if code != 0:
        raise vaultgit.GitUnavailable(f"git restore -- {page} failed: {err or out}")
