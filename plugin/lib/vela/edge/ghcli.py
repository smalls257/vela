"""What leaves the machine at close: the push, and the `gh` calls that open or comment on a pull request (Task 12).

The periphery for `commands/close_push.py`. Every call is timed and never prompts (a credential prompt with no terminal
would hang the session), and each comes back as what happened, never raising.

The Violation this module's shape prevents is the Silent Fallback a model falls into after `gh` misbehaves: saying "the
PR is open" because the command exited 0. A pull request exists only when `gh` printed its URL, so `Sent.url` is set
from the printed URL alone, and a `gh` that exits 0 without one is a failure with that reason (plan 3.1, a hard stop:
never say a PR exists unless `gh` printed its URL).
"""
import json
import re
import shlex
from dataclasses import dataclass

from vela.edge import hostprobe
from vela.edge.vaultgit import NO_PROMPT, GitUnavailable, run_git

PUSH_TIMEOUT = 120  # a first push of a large vault over a slow link; long enough for that, never a hang
GH_TIMEOUT = 60  # a PR create with several reviewers is a few API calls
URL = re.compile(r"https?://\S+/pull/(?P<number>\d+)\S*")


@dataclass(frozen=True)
class Sent:
    """How one send went. `url` and `number` are set only from a URL the program printed."""
    ok: bool
    command: str
    why: str = ""
    url: str = None
    number: int = None
    added: bool = False  # the body went onto a pull request the branch already had


def push_args(branch, track):
    """The push close names: `-u` for a session's own branch; an answer pushes to its challenge's branch as it is."""
    return ["push", "-u", "origin", branch] if track else ["push", "origin", branch]


def push(root, branch, track=True):
    command = "git " + " ".join(push_args(branch, track))
    try:
        code, out, err = run_git(root, *push_args(branch, track), timeout=PUSH_TIMEOUT, env=NO_PROMPT)
    except GitUnavailable as exc:
        return Sent(False, command, str(exc))
    if code != 0:
        return Sent(False, command, (err or out or f"git push exited {code}").strip())
    return Sent(True, command)


def url_in(text):
    """(url, number) of the first pull request URL in `text`, or (None, None)."""
    found = URL.search(text or "")
    return (found.group(0), int(found.group("number"))) if found else (None, None)


def _gh(root, args):
    command = shlex.join(["gh", *args])
    ran = hostprobe.run(["gh", *args], root, GH_TIMEOUT)
    if ran.how == "missing":
        return ran, Sent(False, command, "gh isn't installed")
    if ran.how == "timeout":
        return ran, Sent(False, command, f"gh gave no answer within {GH_TIMEOUT} seconds")
    if ran.how != "ok":
        return ran, Sent(False, command, ran.first_line() or "gh failed")
    return ran, None


def _sent_with_url(root, args):
    ran, failed = _gh(root, args)
    if failed is not None:
        return failed
    url, number = url_in(ran.out)
    command = shlex.join(["gh", *args])
    if url is None:
        return Sent(False, command, "gh printed no pull request URL" + (f": {ran.first_line()}" if ran.first_line()
                                                                         else ""))
    return Sent(True, command, url=url, number=number)


def create_args(head, title, body_file, reviewers, base="main"):
    args = ["pr", "create", "--base", base, "--head", head, "--title", title, "--body-file", str(body_file)]
    for handle in reviewers:
        args += ["--reviewer", handle]
    return args


def pr_create(root, head, title, body_file, reviewers, base="main"):
    return _sent_with_url(root, create_args(head, title, body_file, reviewers, base))


def comment_args(number, body_file):
    return ["pr", "comment", str(number), "--body-file", str(body_file)]


def pr_comment(root, number, body_file):
    return _sent_with_url(root, comment_args(number, body_file))


def open_prs_for(root, branch):
    """([{number, url}], why): the open PRs whose head is `branch`. `why` is gh's words when it failed."""
    ran, failed = _gh(root, ["pr", "list", "--head", branch, "--state", "open", "--json", "number,url"])
    if failed is not None:
        return None, failed.why
    try:
        found = json.loads(ran.out or "[]")
    except ValueError:
        return None, f"gh printed something that isn't JSON: {ran.out.strip()[:200]}"
    return [p for p in found if isinstance(p, dict)] if isinstance(found, list) else [], ""


NO_PR = "no pull requests found"


def open_pr_on(root, branch):
    """({number, url}, why): the open pull request whose head is `branch`, or (None, "") when it has none. `why` is gh's
    words when it failed for any other reason; a failure is never read as "no pull request" (that would open a second)."""
    ran, failed = _gh(root, ["pr", "view", branch, "--json", "number,url,state"])
    if failed is not None:
        return (None, "") if NO_PR in failed.why.lower() else (None, failed.why)
    try:
        found = json.loads(ran.out or "null")
    except ValueError:
        return None, f"gh printed something that isn't JSON: {ran.out.strip()[:200]}"
    if isinstance(found, dict) and str(found.get("state", "")).upper() == "OPEN" and found.get("number"):
        return found, ""
    return None, ""
