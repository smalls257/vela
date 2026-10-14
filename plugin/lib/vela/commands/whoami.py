"""`vela whoami [--set HANDLE]`: the lead's handle, for every bullet that names them (`**Override:** ... by @<handle>`,
`Pending approval: @<handle>`, a capture's origin). Overhaul Task 6b.

START told the model to run `gh api user -q .login`, fall back to the first line of `.vela/handle`, and else ask once
and write it there; skills repeated it, and a model that skipped a step asked the lead again, or wrote a handle it
guessed. Here the order is code: the cached `.vela/handle` first (no network, and the lead is never asked twice),
then `gh`, whose answer is cached. When neither knows, exit 3 says "ask the lead once", and `--set` writes their
answer. A reader copy never runs `gh`. `.vela/` is not committed, so the handle stays on this machine.

Exit codes: 0 the handle is printed; 1 `--set` got something that isn't a handle; 2 the cache couldn't be written;
3 ask the lead once (nothing changed).
"""
import pathlib
import re

from vela import commands, say
from vela.edge import sessiongit

NAME = "whoami"
HANDLE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")  # a GitHub login's shape
QUESTION = "What's your GitHub handle, the short name after the @? I'll remember it on this machine."


def register(sub):
    who = sub.add_parser("whoami", help="the lead's handle: cached in .vela/handle, else from gh, else ask them once")
    who.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    who.add_argument("--set", default="", metavar="HANDLE", help="write the handle the lead gave (after an exit 3)")
    say.add_output_flags(who)
    who.set_defaults(func=cmd_whoami)


def cmd_whoami(args, out):
    root = pathlib.Path(args.vault).resolve()
    try:
        result = set_handle(root, args.set) if args.set else find_handle(root)
    except OSError as exc:
        result = say.Result(NAME, exit=say.FAILED, lines=[
            say.Line(f"vela: couldn't write {sessiongit.HANDLE_FILE}: {exc}",
                     plain=f"I couldn't save your handle on this machine: {exc}")])
    return commands.emit(result, args, out)


def known(handle, source, wrote=()):
    return say.Result(NAME, wrote=list(wrote), data={"handle": handle, "source": source},
                      lines=[say.Line(handle, plain=f"You're @{handle}.")])


def set_handle(root, given):
    handle = given.strip().lstrip("@")
    if not HANDLE.match(handle):
        return say.Result(NAME, exit=say.REFUSED, refusals=[say.Refusal(
            "handle", f"'{given}' isn't a GitHub handle: letters, digits and hyphens, up to 39.",
            "ask the lead for the name after the @ on their GitHub profile")])
    return known(handle, "set", [sessiongit.write_text(root, sessiongit.HANDLE_FILE, handle + "\n")])


def find_handle(root):
    cached = sessiongit.read_handle(root)
    if cached:
        return known(cached, "cache")
    why = "this is a read copy, which never runs gh"
    if not sessiongit.is_read_copy(root):
        ran = sessiongit.gh(root, "api", "user", "-q", ".login")
        login = ran.out.strip() if ran.how == "ok" else ""
        if HANDLE.match(login):
            return known(login, "gh", [sessiongit.write_text(root, sessiongit.HANDLE_FILE, login + "\n")])
        why = f"gh didn't say ({ran.how}{': ' + ran.first_line() if ran.first_line() else ''})"
    return say.Result(NAME, exit=say.NEEDS_LEAD, needs_lead=[{"ask": "handle", "question": QUESTION,
                                                              "answer_with": "--set <handle>"}],
                      lines=[say.Line(f"handle unknown: {why}, and {sessiongit.HANDLE_FILE} is empty. Ask the lead "
                                      f"once, then run vela whoami --set <handle>.", plain=QUESTION)])
