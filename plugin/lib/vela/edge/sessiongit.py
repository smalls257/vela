"""git (and, in a reader copy, the folder) for `vela session open`: read the candidate session records and switch.

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

The open session is its stub in `sessions/` plus the private notes in `sessions/private/` (`open_record`); a stub
with no notes here raises `PrivateMissing`.

A reader copy (a published folder: `.vela/workspace.json`, no `.git`) has no branches. It is recognized from the
disk alone and its `sessions/*.md` are read in place; no git command runs there, so a machine with no git works, and a
copy that sits inside some other repo never reads that repo's history.

Every git call has a timeout (vaultgit.run_git) and a failure raises GitUnavailable with git's words; nothing here
turns a failure into "no session is open".

Task 6b adds what `session start`, `session brief`, `record add` and `whoami` need from git, `gh` and the disk:
fetching (with the short timeout freshness uses, so a dead network costs seconds), what the switch to main and the
pull would change, branch and commit by exact path (through `stagegit`), `gh` through the probe's runner (every call timed and never prompting), and
`.vela/session.json` and `.vela/handle`, written through `atomic`. Paths are vault-relative everywhere, so a vault in
a subfolder of its repo compares the same paths git reports.
"""
import json
import pathlib

from vela import planscope, privaterecord, roles, sessions
from vela.decisions import record as open_records
from vela.edge import atomic, hostprobe, stagegit
from vela.edge.vaultgit import FETCH_TIMEOUT, NO_PROMPT, GitUnavailable, git_out, plan_scope, run_git

SWITCH_TIMEOUT = 60  # a checkout of a large vault, with hooks, can take a while
PATTERNS = ("refs/heads/session/", "refs/remotes/origin/session/")
STATE_FILE = ".vela/session.json"
HANDLE_FILE = ".vela/handle"
GH_TIMEOUT = 20  # a merged-PR listing with comments is a few calls; each still gets its own limit


def is_read_copy(root):
    """True for a published copy, judged by the same access rule `vela role` uses, from the disk alone."""
    root = pathlib.Path(root)
    facts = roles.Facts(has_workspace=(root / ".vela" / "workspace.json").is_file(), git_here=(root / ".git").exists())
    return roles.decide(facts).role == roles.READER


def folder_records(root):
    """[("", path, text)] for every `sessions/*.md` in a reader copy's folder."""
    folder = pathlib.Path(root) / "sessions"
    return [("", f"sessions/{path.name}", path.read_text(encoding="utf-8"))
            for path in sorted(folder.glob("*.md")) if path.is_file()]


class PrivateMissing(ValueError):
    """The stub says the session is open, and this machine has no private notes for it. The notes never leave the
    machine that wrote them, so the lead is told, never handed an empty record to write into (a Silent Fallback)."""

    def __init__(self, record_id):
        self.record_id = record_id
        super().__init__(f"This session's notes are not on this machine ({privaterecord.private_path(record_id)}). "
                         "They stay on the machine that wrote them.")


def private_text(root, record_id):
    """The private notes of a session, or None when this machine has none."""
    try:
        return (pathlib.Path(root) / privaterecord.private_path(record_id)).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def open_record(root):
    """(OpenRecord, None) for the one open session, else (None, Opened) saying why not. The stub in `sessions/` says
    which session is open; its words are read from the private file. Raises PrivateMissing when the stub is open and
    the notes are not here."""
    opened, problems = sessions.find_open(folder_records(root))
    if len(opened) != 1:
        return None, open_records.Opened(opened, problems)
    record_id = opened[0].id
    text = private_text(root, record_id)
    if text is None:
        raise PrivateMissing(record_id)
    return open_records.from_text(record_id, privaterecord.private_path(record_id), text,
                                  privaterecord.part_of(text)), None


def write_notes(root, record, new_text):
    """Write a record's new private text and, when the lists it carries (`ready`, `harvest_declined`) changed, the
    stub beside it, so the committed header never disagrees with the words under it. The paths written."""
    wrote = []
    if new_text != record.text:
        wrote.append(write_text(root, record.path, new_text))
    stub = (pathlib.Path(root) / record.stub).read_text(encoding="utf-8")
    synced = privaterecord.synced_stub(stub, new_text)
    if synced != stub:
        wrote.append(write_text(root, record.stub, synced))
    return wrote


def session_refs(root):
    """Every local and origin `session/*` ref that is this plan's, plus the current branch, as full ref names. A plan
    that shares its repo with others owns `session/<plan>/*` (and the old unscoped `session/<id>`), never another
    plan's sessions."""
    scope = plan_scope(root)
    listed = git_out(root, "for-each-ref", "--format=%(refname)", *PATTERNS).splitlines()
    code, current, _ = run_git(root, "symbolic-ref", "-q", "HEAD")
    refs = [ref for ref in listed if ref and planscope.owns_session_branch(scope, ref[ref.index("session/"):])]
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


def _words(err, out):
    return "\n".join(x for x in (err, out) if x)


def has_origin(root):
    return run_git(root, "remote", "get-url", "origin")[0] == 0


def fetch(root):
    """(ok, git's words) for `git fetch origin`. A timeout is a failure with its reason, never a hang."""
    try:
        code, out, err = run_git(root, "fetch", "--quiet", "origin", timeout=FETCH_TIMEOUT, env=NO_PROMPT)
    except GitUnavailable as exc:
        return False, str(exc)
    return code == 0, _words(err, out)


def ref_exists(root, ref):
    return run_git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")[0] == 0


def branch_taken(root, branch):
    """True when `branch` exists here or on origin (as the last fetch saw it)."""
    return ref_exists(root, f"refs/heads/{branch}") or ref_exists(root, f"refs/remotes/origin/{branch}")


def dirty_paths(root):
    """Every changed or untracked path under the plan's folder, vault-relative."""
    return stagegit.changed_paths(root)


def incoming_paths(root, target):
    """The vault-relative paths that differ between HEAD and `target`: what moving to `target` would rewrite."""
    if not ref_exists(root, "HEAD"):
        return []
    out = git_out(root, "diff", "--name-only", "--relative", "-z", "HEAD", target)
    return [path for path in out.split("\0") if path]


def fast_forward(root, upstream):
    """(ok, git's words) for `git merge --ff-only <upstream>`: the pull, after the fetch already ran."""
    code, out, err = run_git(root, "merge", "--ff-only", "--quiet", upstream, timeout=SWITCH_TIMEOUT)
    return code == 0, _words(err, out)


def default_branch(root):
    """The branch reviews go into: origin's HEAD when it says, else `main` or `master` as the repo has it, else `main`."""
    code, out, _ = run_git(root, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD")
    if code == 0 and out.startswith("origin/"):
        return out[len("origin/"):]
    for name in ("main", "master"):
        if ref_exists(root, f"refs/heads/{name}") or ref_exists(root, f"refs/remotes/origin/{name}"):
            return name
    return "main"


def head_commit(root):
    """The full sha HEAD points at, or "" in a repo with no commit yet."""
    code, out, _ = run_git(root, "rev-parse", "--verify", "--quiet", "HEAD^{commit}")
    return out if code == 0 else ""


def commits_between(root, base, tip):
    """How many commits `tip` has that `base` lacks."""
    return int(git_out(root, "rev-list", "--count", f"{base}..{tip}") or 0)


def move_branch(root, branch, target):
    """(ok, git's words): point the local `branch` at `target`. Only for a branch that is not checked out."""
    code, out, err = run_git(root, "branch", "-f", branch, target)
    return code == 0, _words(err, out)


def create_branch(root, branch):
    code, out, err = run_git(root, "switch", "-c", branch, timeout=SWITCH_TIMEOUT)
    return code == 0, _words(err, out)


def commit(root, message, paths):
    """Stage exactly `paths` and commit them with `message`; the short hash. Raises GitUnavailable with git's words."""
    stagegit.stage(root, paths)
    return stagegit.commit(root, message, paths)


def gh(root, *args):
    """One `gh` call through the probe's runner: timed, never prompting, a missing gh named. A `hostprobe.Ran`."""
    return hostprobe.run(["gh", *args], root, GH_TIMEOUT)


def gh_json(root, *args):
    """(value, None) for a gh call that printed JSON, or (None, why) in gh's own words."""
    ran = gh(root, *args)
    if ran.how == "missing":
        return None, "gh isn't installed"
    if ran.how == "timeout":
        return None, f"gh gave no answer within {GH_TIMEOUT} seconds"
    if ran.how != "ok":
        return None, ran.first_line() or f"gh {' '.join(args[:2])} failed"
    try:
        return json.loads(ran.out or "null"), None
    except ValueError:
        return None, f"gh printed something that isn't JSON: {ran.out.strip()[:200]}"


def read_json(root, rel):
    """The file's JSON object, or None when it is absent. One that can't be read or parsed raises ValueError: a
    broken state file is said, never read as "no session"."""
    path = pathlib.Path(root) / rel
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ValueError(f"{rel} can't be read: {exc}") from exc
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError(f"{rel} isn't JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{rel} isn't a JSON object")
    return data


def write_text(root, rel, text):
    """Write a vault-relative file whole (atomic), making its folder. Raises OSError (atomic.WriteFailed)."""
    path = pathlib.Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic.write_atomic(path, text)
    return rel


def write_state(root, state):
    return write_text(root, STATE_FILE, json.dumps(state, indent=2) + "\n")


NAME_FILE = ".vela/name"


def _first_line(path):
    """The first line of a small personal file, or "" when there is no such file (no name kept is no name)."""
    try:
        return path.read_text(encoding="utf-8").split("\n", 1)[0].strip()
    except (FileNotFoundError, UnicodeDecodeError):
        return ""


def lead_names(root):
    """The lead's display names, lower-cased: the first line of `.vela/name` (`vela whoami --name`) and git's
    `user.name`. A name the model typed as an origin ("Sim Lead", "Jo Smith") is the lead's own words under another
    spelling; the handle is what the checks compare, so these let it be rewritten to the handle."""
    found = {_first_line(pathlib.Path(root) / NAME_FILE)}
    if not is_read_copy(root):  # a reader copy runs no git
        code, value, _ = run_git(root, "config", "user.name")
        if code == 0:
            found.add(value.strip())
    return {n.casefold() for n in found if n}


def read_handle(root):
    """The first line of `.vela/handle`, or ""."""
    try:
        return (pathlib.Path(root) / HANDLE_FILE).read_text(encoding="utf-8").split("\n", 1)[0].strip()
    except FileNotFoundError:
        return ""
