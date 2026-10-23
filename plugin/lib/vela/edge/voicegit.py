"""The disk, git and `gh` for `vela voice` (overhaul Task 18): read the examples and records, ask `gh` about merged
session PRs, read a PR's commits and pages, and write examples whole.

The periphery for `voiceplan.py`, which decides. The Violation this module exists to prevent is the Silent Fallback
harvest had when a model ran it by hand: a `gh` that failed looked exactly like "no edits found". So every `gh` call
raises `GhFailed` carrying gh's own words and every git call raises `GitUnavailable`; nothing here returns an empty
list for a failure, and the caller says which call failed and what it left unchecked.

A PR's tip is read by its full SHA right after `git fetch origin pull/<n>/head`, never through `FETCH_HEAD` later,
because `FETCH_HEAD` holds only the last fetch. File contents are read as bytes (`git show` output must not be
stripped), so a paragraph's hash is the hash of what the page holds.
"""
import json
import pathlib
import subprocess

from vela import parse, privaterecord, voiceplan
from vela.edge import atomic
from vela.edge.vaultgit import GitUnavailable, at, git_out, run_git

GH_TIMEOUT = 30
FETCH_TIMEOUT = 60  # a PR's objects over the network
PR_LIMIT = 10  # HARVEST: the last 10 merged session PRs; the output says when older ones were not checked
HARVEST_DIR = ".vela/harvest"  # gitignored, so a paragraph's file is never staged


class GhFailed(Exception):
    """`gh` could not answer: missing, timed out, or refused. The message is gh's own words."""


def gh_json(root, *args):
    """Parsed JSON from a `gh` call that must succeed."""
    command = ["gh", *args]
    try:
        done = subprocess.run(command, cwd=str(root), capture_output=True, timeout=GH_TIMEOUT)
    except FileNotFoundError as exc:
        raise GhFailed("gh is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise GhFailed(f"gh {' '.join(args[:2])} did not finish in {GH_TIMEOUT} s") from exc
    out = done.stdout.decode("utf-8", "replace")
    if done.returncode != 0:
        err = done.stderr.decode("utf-8", "replace").strip() or out.strip()
        raise GhFailed(f"gh {' '.join(args[:2])} failed: {err}")
    try:
        return json.loads(out) if out.strip().startswith(("{", "[", '"')) else out.strip()
    except ValueError as exc:
        raise GhFailed(f"gh {' '.join(args[:2])} printed something that is not JSON: {out[:200]}") from exc


def login(root):
    return str(gh_json(root, "api", "user", "-q", ".login")).strip()


def merged_session_prs(root, limit=PR_LIMIT):
    return gh_json(root, "pr", "list", "--state", "merged", "--search", "head:session/", "--author", "@me",
                   "--json", "number,headRefName", "--limit", str(limit))


def pr_commits(root, number):
    """[{oid, messageHeadline, messageBody}] in the PR's order."""
    return gh_json(root, "pr", "view", str(number), "--json", "commits").get("commits", [])


def fetch_pr(root, number):
    """The full SHA of PR `number`'s head, fetched from origin."""
    git_out(root, "fetch", "-q", "origin", f"pull/{number}/head", timeout=FETCH_TIMEOUT)
    return git_out(root, "rev-parse", "FETCH_HEAD")


def pages_of(root, oid):
    return [p for p in git_out(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "--relative", oid).splitlines() if p]


def commits_touching(root, base, tip, page):
    """Non-merge commits after `base` up to `tip` that changed `page`, newest first."""
    return [c for c in git_out(root, "log", "--no-merges", "--format=%H", f"{base}..{tip}", "--", page).splitlines() if c]


def diff_u0(root, oid, page):
    return git_out(root, "diff", "-U0", f"{oid}^", oid, "--", page)


def show(root, ref, path):
    """The text of `path` at `ref`, exactly (not stripped), or None when it is not there."""
    code, out, err = run_git(root, "show", at(ref, path), binary=True)
    if code != 0:
        if "does not exist" in err or "exists on disk, but not in" in err:
            return None
        raise GitUnavailable(f"git show {ref}:{path} failed: {err}")
    return out.decode("utf-8", "replace")


def examples(root):
    """Every example in `voice/examples/` and `voice/local/`, retired ones included (numbering counts them)."""
    root = pathlib.Path(root)
    found = []
    for place, folder in voiceplan.FOLDERS.items():
        for path in sorted((root / folder).glob("*/*.md")):
            text = path.read_text(encoding="utf-8")
            meta, _, _ = parse.split_frontmatter(text)
            found.append(voiceplan.Example(path.relative_to(root).as_posix(), place, path.name, meta,
                                           voiceplan.stored_body(text) or ""))
    return found


def page_meta(root, page):
    text = (pathlib.Path(root) / page).read_text(encoding="utf-8")
    meta, _, error = parse.split_frontmatter(text)
    return meta if error is None else None


def record_metas(root):
    """The frontmatter of every session stub, for the lists it carries (`harvest_declined`)."""
    return [privaterecord.stub_meta(p.read_text(encoding="utf-8"))
            for p in sorted((pathlib.Path(root) / "sessions").glob("*.md"))]


def write_paragraph(root, pr, n, text):
    """`.vela/harvest/<pr>-<n>.txt`, the paragraph's fixed path every later step names."""
    path = pathlib.Path(root) / HARVEST_DIR / f"{pr}-{n}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic.write_atomic(path, text)
    return path.relative_to(root).as_posix()


def clear_harvest(root):
    folder = pathlib.Path(root) / HARVEST_DIR
    for path in folder.glob("*.txt") if folder.is_dir() else ():
        path.unlink()


def write_example(root, rel, text):
    """Write a new example whole, then read it back as bytes for the compare."""
    path = pathlib.Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic.write_atomic(path, text)
    return path.read_bytes()


def write_files(root, files):
    """{rel: text} written all or none (the retirements a save applies after its compare passed)."""
    atomic.write_all_atomic({pathlib.Path(root) / rel: text for rel, text in files.items()})
