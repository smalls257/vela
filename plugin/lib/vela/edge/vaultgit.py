"""The vault's git repo and the disk around it, for the commands that must look outside the pages.

This is the periphery (Buffer): roles, publish and freshness decide in pure modules and ask here for facts.
Every subprocess has a timeout, and a git that cannot answer raises GitUnavailable so the caller says so;
nothing here turns a failure into an empty answer.
"""
import io
import os
import pathlib
import subprocess
import tarfile

import yaml

from vela import publish, roles

GIT_TIMEOUT = 20
FETCH_TIMEOUT = 8  # an owner's session start must not hang on a dead network
# A credential prompt would hang a tool with no terminal. The fetch fails fast instead.
NO_PROMPT = {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "true", "SSH_ASKPASS": "true"}


class GitUnavailable(Exception):
    """git is missing, timed out, or refused: the reason, in a form a person can read."""


def run_git(root, *args, timeout=GIT_TIMEOUT, env=None, binary=False):
    """(returncode, stdout, stderr). Raises GitUnavailable when git cannot run or does not finish in time."""
    command = ["git", "-C", str(root), "-c", "core.quotepath=false", *args]
    try:
        done = subprocess.run(command, capture_output=True, timeout=timeout, env={**os.environ, **(env or {})})
    except FileNotFoundError as exc:
        raise GitUnavailable("git is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitUnavailable(f"git {args[0]} did not finish in {timeout} s") from exc
    except OSError as exc:
        raise GitUnavailable(f"git {args[0]} could not run: {exc}") from exc
    out = done.stdout if binary else done.stdout.decode("utf-8", "replace").strip()
    return done.returncode, out, done.stderr.decode("utf-8", "replace").strip()


def git_out(root, *args, timeout=GIT_TIMEOUT):
    """stdout of a git command that must succeed; GitUnavailable carries git's own message otherwise."""
    code, out, err = run_git(root, *args, timeout=timeout)
    if code != 0:
        raise GitUnavailable(f"git {' '.join(args)} failed: {err or out}")
    return out


def commit_problem(root):
    """Why the user cannot commit here, or "" when they can."""
    for key in ("user.name", "user.email"):
        code, value, _ = run_git(root, "config", key)
        if code != 0 or not value:
            return f"git {key} is not set"
    git_dir = pathlib.Path(git_out(root, "rev-parse", "--absolute-git-dir"))
    if not os.access(git_dir, os.W_OK):
        return f"{git_dir} is not writable"
    return ""


def head(root):
    """(full commit, short commit) of HEAD; GitUnavailable when there is no commit yet."""
    full = git_out(root, "rev-parse", "HEAD")
    return full, git_out(root, "rev-parse", "--short", "HEAD")


def parse_porcelain(out):
    """Paths from `git status --porcelain=v1 -z`: each entry is `XY path`, and a rename or copy (`R`/`C` in either
    column) is followed by its old path as a field of its own, which is skipped: the new path is what changed.

    The one parser for git status. It reads `-z` output, never stripped text: a strip before `line[3:]` ate the first
    path's first letter (`ashboard.html`, `vela/flowcheck-cache.json`), a Sensor that misreported."""
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


def status_paths(root, *args):
    """The paths `git status --porcelain=v1 -z <args>` names, repository-relative and exactly as on disk."""
    code, out, err = run_git(root, "status", "--porcelain=v1", "-z", *args, binary=True)
    if code != 0:
        raise GitUnavailable(f"git status failed: {err or out.decode('utf-8', 'replace').strip()}")
    return parse_porcelain(out.decode("utf-8"))


def tracked_paths(root):
    """Vault-relative paths git tracks under the vault, exactly as on disk; [] when the folder is in no repository (a
    read copy, a vault never put in git). Any other failure raises GitUnavailable."""
    code, out, err = run_git(root, "ls-files", "-z", "--", ".", binary=True)
    if code == 0:
        return [path for path in out.decode("utf-8").split("\0") if path]
    if "not a git repository" in err.lower():
        return []
    raise GitUnavailable(f"git ls-files failed: {err or 'no message'}")


def uncommitted(root):
    """Files changed or untracked under the vault, as git status sees them (ignored files are not listed). The files the
    explorer build writes itself (the dashboard and the pinned layout, publish.KEPT) are left out: the build counts what
    is uncommitted and then writes them, so counting them would make a page built before a commit differ from the same
    page built after it."""
    return status_paths(root, "--", ".", *(f":(exclude){path}" for path in publish.KEPT))


def user_identity(root):
    """(name, email) from git config, each "" when unset."""
    return tuple(run_git(root, "config", key)[1] for key in ("user.name", "user.email"))


def committed_files(root):
    """({vault-relative path: bytes}, [skipped names], {path: executable}) from HEAD's blobs, never the work tree.

    The vault may be a folder inside a bigger repo. `git archive HEAD` run from that folder archives just it, with
    names relative to it. (Naming the folder again as `HEAD:<prefix>` looks safer and returns nothing at all: git
    applies the working directory's prefix a second time, inside the already-narrowed tree.) Symlinks and
    submodule stubs are not files a read copy can carry; their names are returned so the caller says so.
    """
    code, data, err = run_git(root, "archive", "--format=tar", "HEAD", timeout=120, binary=True)
    if code != 0:
        raise GitUnavailable(f"git archive HEAD failed: {err}")
    files, skipped, executable = {}, [], {}
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for member in tar.getmembers():
            if member.isdir():
                continue
            if not member.isfile():
                skipped.append(member.name)
                continue
            files[member.name] = tar.extractfile(member).read()
            executable[member.name] = bool(member.mode & 0o111)
    return files, skipped, executable


def has_origin(root):
    return run_git(root, "config", "--get", "remote.origin.url")[0] == 0


def commit_date(root, ref):
    """The committer date of a ref as YYYY-MM-DD, or "" when the ref does not exist."""
    code, out, _ = run_git(root, "log", "-1", "--format=%cs", ref)
    return out if code == 0 else ""


def head_short(root, ref):
    code, out, _ = run_git(root, "rev-parse", "--short", ref)
    return out if code == 0 else ""


def upstream(root):
    """The current branch's upstream (origin/main), or "" when it has none."""
    code, out, _ = run_git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    return out if code == 0 else ""


def fetch(root, timeout):
    """"" when git fetch worked, else why it did not. It never pulls or merges."""
    try:
        code, out, err = run_git(root, "fetch", "--quiet", timeout=timeout, env=NO_PROMPT)
    except GitUnavailable as exc:
        return str(exc)
    return "" if code == 0 else ((err or out or "git fetch failed").splitlines() or ["git fetch failed"])[0]


def behind_ahead(root, upstream_ref):
    """(commits behind, commits ahead) of the upstream, from the remote state git last saw."""
    left, _, right = git_out(root, "rev-list", "--left-right", "--count", f"{upstream_ref}...HEAD").partition("\t")
    return int(left), int(right)


def role_facts(root):
    """roles.Facts for a directory: what git, the disk and .vela.yaml say about access."""
    root = pathlib.Path(root)
    git_error, in_tree, has_origin, can_commit, why = "", False, False, False, ""
    try:
        code, out, _ = run_git(root, "rev-parse", "--is-inside-work-tree")
        in_tree = code == 0 and out == "true"
        if in_tree:
            has_origin = run_git(root, "config", "--get", "remote.origin.url")[0] == 0
            why = commit_problem(root)
            can_commit = not why
    except GitUnavailable as exc:
        git_error = str(exc)
    config_role, config_error = None, ""
    config = root / ".vela.yaml"
    if config.is_file():
        try:
            data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
            config_role = data.get("role") if isinstance(data, dict) else None
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            config_error = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
    return roles.Facts(in_work_tree=in_tree, git_here=(root / ".git").exists(), has_origin=has_origin,
                       can_commit=can_commit, commit_problem=why,
                       has_workspace=(root / ".vela" / "workspace.json").is_file(),
                       git_error=git_error, config_role=config_role, config_error=config_error)
