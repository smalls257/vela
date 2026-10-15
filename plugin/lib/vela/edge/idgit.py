"""git for numbering a new item: the IDs written on `main` and on every session branch (overhaul Task 15).

The periphery for `vela.decisions.textedit.next_id`, which decides the number. Anchor: an ID is a promise other pages
and other open branches can link to, so a number an open session branch already holds must never be handed out again
(two UNK-026 in one vault). The working tree alone can't see those numbers; the branches can. What is read, and why:

- `refs/heads/session/*`, `refs/remotes/origin/session/*`: every open session, here or pushed from another machine
  (as far as the last fetch saw: nothing here fetches, so filing stays fast and works offline);
- `main`/`master`, local and on origin: a session branch that merged and was deleted leaves its numbers only there.

One `git grep -h -o` per ref prints only the ID-shaped tokens of its Markdown files, not the files, so a large vault
costs one call per branch. A reader copy (no `.git`) has no branches: the list is empty and nothing runs. A git that
fails raises GitUnavailable with git's words; it never reads as "no other branch holds a number".
"""
import pathlib

from vela.edge.vaultgit import GitUnavailable, git_out, run_git

PATTERNS = ("refs/heads/session/", "refs/remotes/origin/session/")
MAIN_REFS = ("refs/heads/main", "refs/heads/master", "refs/remotes/origin/main", "refs/remotes/origin/master")
ID_TOKENS = r"[A-Z]{1,4}-[0-9]+(\.[A-Z]+[0-9]+)?"


def branch_texts(root):
    """[text] per branch: the ID-shaped tokens written there, one per line. [] in a folder with no `.git`."""
    root = pathlib.Path(root)
    if not (root / ".git").exists():
        return []
    refs = git_out(root, "for-each-ref", "--format=%(refname)", *PATTERNS, *MAIN_REFS).split()
    found = []
    for ref in refs:
        code, out, err = run_git(root, "grep", "-h", "-E", "-o", ID_TOKENS, ref, "--", "*.md")
        if code not in (0, 1):  # 1 is git grep's "nothing matched"
            raise GitUnavailable(f"git grep over {ref} failed: {err or out}")
        found.append(out)
    return found
