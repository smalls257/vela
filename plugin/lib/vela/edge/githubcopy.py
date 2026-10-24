"""Fetching a plan from GitHub with the tools this computer has (the periphery for `githubsource.py`).

`gh` when it is installed and signed in, else plain `git`; both with the prompts turned off, so nothing ever waits on a
password nobody can type. A failure raises CloneFailed with its kind and git's own words: the words go to stderr for
whoever debugs, and the director hears only `githubsource.message`.
"""
import os
import shutil
import subprocess

from vela import githubsource
from vela.edge import vaultgit

CLONE_BASE = "https://github.com"  # tests replace it with a local address (file://...)


class CloneFailed(Exception):
    def __init__(self, kind, detail):
        super().__init__(detail)
        self.kind, self.detail = kind, detail


def has_git():
    return shutil.which("git") is not None


def gh_signed_in():
    """gh is installed and `gh auth status` exits 0 (5 s limit)."""
    gh = shutil.which("gh")
    if gh is None:
        return False
    try:
        return subprocess.run([gh, "auth", "status"], capture_output=True, timeout=5, env={**os.environ, **vaultgit.NO_PROMPT}).returncode == 0
    except (OSError, subprocess.TimeoutExpired):  # gh that can't answer in five seconds is as good as not signed in
        return False


def run(argv, timeout):
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env={**os.environ, **vaultgit.NO_PROMPT})
    except subprocess.TimeoutExpired as exc:
        raise CloneFailed(githubsource.UNREACHABLE, f"{argv[0]} did not finish in {timeout} s") from exc
    except OSError as exc:
        raise CloneFailed(githubsource.NO_GIT, str(exc)) from exc
    if done.returncode != 0:
        raise CloneFailed(githubsource.failure_kind(done.stderr), done.stderr.strip())
    return done.stdout


def clone(repo, dest, timeout=60):
    """A shallow clone of the repository's default branch into `dest`."""
    if gh_signed_in():
        run([shutil.which("gh"), "repo", "clone", repo.label, str(dest), "--", "--depth", "1"], timeout)
    else:
        run(["git", "clone", "--quiet", "--depth", "1", f"{CLONE_BASE}/{repo.owner}/{repo.name}.git", str(dest)], timeout)


def remote_head(repo, timeout):
    """The commit the repository's default branch is at now, for freshness."""
    out = run(["git", "ls-remote", f"{CLONE_BASE}/{repo.owner}/{repo.name}.git", "HEAD"], timeout)
    return out.split()[0] if out.split() else ""
