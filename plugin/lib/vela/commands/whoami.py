"""`vela whoami [--set HANDLE]`: the lead's handle, for every bullet that names them (`**Override:** ... by @<handle>`,
`Pending approval: @<handle>`, a capture's origin). Overhaul Task 6b.

START told the model to run `gh api user -q .login`, fall back to the first line of `.vela/handle`, and else ask once
and write it there; skills repeated it, and a model that skipped a step asked the lead again, or wrote a handle it
guessed. Here the order is code: the cached `.vela/handle` first (no network, and the lead is never asked twice),
then `gh`, whose answer is cached. When neither knows, exit 3 says "ask the lead once", and `--set` writes their
answer. A reader copy never runs `gh`. `.vela/` is not committed, so the handle stays on this machine.

`--role <role>` keeps the person's own role (lead, exec, product, qa, eng or mgr) in `.vela/role`, beside the handle; `role` in the
output is it, or "" when never set (the /vela:onboard skill then asks once). The lead's record in `.vela.yaml` (`roles:`) wins over it.

Exit codes: 0 the handle is printed; 1 `--set` got something that isn't a handle; 2 the cache couldn't be written;
3 ask the lead once (nothing changed).
"""
import pathlib
import re

from vela import commands, onboarding, say
from vela.edge import sessiongit

NAME = "whoami"
ROLE_FILE = ".vela/role"  # the person's own choice of role, kept beside their handle
HANDLE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")  # a GitHub login's shape
QUESTION = "What's your GitHub handle, the short name after the @? I'll remember it on this machine."


def register(sub):
    who = sub.add_parser("whoami", help="the lead's handle: cached in .vela/handle, else from gh, else ask them once")
    who.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    who.add_argument("--set", default="", metavar="HANDLE", help="write the handle the lead gave (after an exit 3)")
    who.add_argument("--role", default="", metavar="ROLE", help="write your role, one of lead, exec, product, qa, eng, mgr (or say it: engineer, QA lead); it shows as `role` and defaults onboarding")
    say.add_output_flags(who)
    who.set_defaults(func=cmd_whoami)


def cmd_whoami(args, out):
    root = pathlib.Path(args.vault).resolve()
    try:
        result = set_role(root, args.role) if args.role and not args.set else set_handle(root, args.set) if args.set else find_handle(root)
    except OSError as exc:
        result = say.Result(NAME, exit=say.FAILED, lines=[
            say.Line(f"vela: couldn't write {sessiongit.HANDLE_FILE}: {exc}",
                     plain=f"I couldn't save your handle on this machine: {exc}")])
    return commands.emit(result, args, out)


def read_role(root):
    """The role `vela whoami --role` kept, or "". A file that holds something else is not a role."""
    try:
        text = (pathlib.Path(root) / ROLE_FILE).read_text(encoding="utf-8").split("\n", 1)[0].strip()
    except (FileNotFoundError, UnicodeDecodeError):
        return ""
    return text if text in onboarding.AUDIENCES else ""


def set_role(root, given):
    role = onboarding.ROLE_WORDS.get(given.strip().casefold())
    if role is None:
        return say.Result(NAME, exit=say.REFUSED, refusals=[say.Refusal(
            "role", f"'{given}' isn't one of the roles.", "use one of: " + ", ".join(onboarding.AUDIENCES))])
    wrote = sessiongit.write_text(root, ROLE_FILE, role + "\n")
    label = onboarding.AUDIENCE_LABELS[role]
    return say.Result(NAME, wrote=[wrote], data={"role": role}, lines=[say.Line(role, plain=f"You're set as {label}.")])


def known(handle, source, wrote=(), role=""):
    return say.Result(NAME, wrote=list(wrote), data={"handle": handle, "source": source, "role": role},
                      lines=[say.Line(handle, plain=f"You're @{handle}.")])


def set_handle(root, given):
    handle = given.strip().lstrip("@")
    if not HANDLE.match(handle):
        return say.Result(NAME, exit=say.REFUSED, refusals=[say.Refusal(
            "handle", f"'{given}' isn't a GitHub handle: letters, digits and hyphens, up to 39.",
            "ask the lead for the name after the @ on their GitHub profile")])
    return known(handle, "set", [sessiongit.write_text(root, sessiongit.HANDLE_FILE, handle + "\n")], read_role(root))


def find_handle(root):
    cached = sessiongit.read_handle(root)
    if cached:
        return known(cached, "cache", role=read_role(root))
    why = "this is a read copy, which never runs gh"
    if not sessiongit.is_read_copy(root):
        ran = sessiongit.gh(root, "api", "user", "-q", ".login")
        login = ran.out.strip() if ran.how == "ok" else ""
        if HANDLE.match(login):
            return known(login, "gh", [sessiongit.write_text(root, sessiongit.HANDLE_FILE, login + "\n")], read_role(root))
        why = f"gh didn't say ({ran.how}{': ' + ran.first_line() if ran.first_line() else ''})"
    return say.Result(NAME, exit=say.NEEDS_LEAD, needs_lead=[{"ask": "handle", "question": QUESTION,
                                                              "answer_with": "--set <handle>"}],
                      lines=[say.Line(f"handle unknown: {why}, and {sessiongit.HANDLE_FILE} is empty. Ask the lead "
                                      f"once, then run vela whoami --set <handle>.", plain=QUESTION)])
