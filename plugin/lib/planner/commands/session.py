"""`planner session`: the session's own lifecycle commands (CLI/skill overhaul, Task 6). Task 6a builds `open`;
Task 6b adds `start` and `brief` to the same group here.

`session open [--switch] [--id ID]` finds the open session record and the branch it sits on, so close and START no
longer run a git recipe by hand. The rules (why two records share a branch, why origin's branches count) are in
`planner/sessions.py`; the reads in `planner/edge/sessiongit.py`. Exit codes:

0  exactly one open record (with `--switch`, now on its branch);
1  none open: "No session is open." (close then takes its no-session path), or `--id` names no open record;
2  git failed, a switch git refused (its words are printed), or a record that may be the open one can't be read;
3  several open. Nothing changed and `--switch` did not move: picking for the lead would file one session's captures
   into another's record. The choices are printed and `--json` carries them as `needs_lead`; the skill asks the lead
   and runs again with `--id`.

A reader copy has no branches: the records are read from its folder and no git runs; `--switch` says so and stops.
"""
import datetime
import pathlib

from planner import commands, say, sessions
from planner.edge import sessiongit
from planner.edge.vaultgit import GitUnavailable

NAME = "session open"


def register(sub):
    session = sub.add_parser("session", help="the session record: which one is open, and on which branch")
    verbs = session.add_subparsers(dest="session_command", metavar="{open}")
    verbs.required = True
    opener = verbs.add_parser("open", help="the open session record(s), each with its branch, modes and date")
    opener.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    opener.add_argument("--switch", action="store_true",
                        help="switch to the open record's branch when exactly one is open (never guesses among several)")
    opener.add_argument("--id", default="", help="pick this open record among several (after an exit 3)")
    say.add_output_flags(opener)
    opener.set_defaults(func=cmd_open)


def cmd_open(args, out):
    root = pathlib.Path(args.vault).resolve()
    reader = sessiongit.is_read_copy(root)
    resolver = lead_resolver(root) if say.mode_of(args) == "for-lead" else None
    try:
        found = sessiongit.folder_records(root) if reader else sessiongit.branch_records(root)
    except GitUnavailable as exc:
        return commands.emit(git_failed(str(exc)), args, out, resolver)
    records, problems = sessions.find_open(found)
    chosen = sessions.pick(records, args.id) if args.id else records
    result = report(records, chosen, problems, args.id, words(resolver), datetime.date.today())
    result.data.update(reader=reader, switched=None)
    if args.switch and result.exit == say.DONE:
        switch_to(result, chosen[0], root, reader)
    return commands.emit(result, args, out, resolver)


def lead_resolver(root):
    """A resolver over the vault when it loads, so a title naming an item is said by that item's name. A folder that
    is not a vault still gets the plain kind words ("a contract"), and the leak check runs either way."""
    from planner import cli  # cli builds the parser, so it is loaded by the time this runs
    try:
        return say.Resolver(cli.load_vault(root))
    except cli.ToolError:
        return say.Resolver()


def words(resolver):
    return resolver.plain if resolver is not None else (lambda text: text)


def describe(record):
    where = record.branch or "this folder"
    remote = " (only on origin)" if record.remote_only else ""
    return f"{record.id} on {where}{remote}, modes: {', '.join(record.modes) or 'none'}, date: {record.date or '?'}"


def spoken(record, plain, today):
    return f"{plain(record.title)}, started {sessions.date_in_words(record.date, today)}"


def report(records, chosen, problems, wanted, plain, today):
    """The say.Result for what was found, before any switch: `records` are all the open ones, `chosen` those `--id`
    kept (all of them without `--id`)."""
    lines = [say.Line(f"unreadable: {why}", plain="A session record has frontmatter that can't be read, so it isn't "
                                                  "counted.") for why in problems]
    data = {"open": [r.as_json() for r in records], "problems": problems}
    if wanted and not chosen:
        return say.Result(NAME, exit=say.REFUSED, data=data, lines=lines + [
            say.Line(f"No open session has the id {wanted}.", plain="The session you picked isn't open.")])
    records = chosen
    if not records:
        exit_code = say.FAILED if problems else say.REFUSED  # a record that can't be read may be the open one
        return say.Result(NAME, exit=exit_code, data=data, lines=lines + [say.Line("No session is open.")])
    if len(records) == 1:
        return say.Result(NAME, data=data, lines=lines + [
            say.Line(f"open: {describe(records[0])}",
                     plain=f"One session is open: {spoken(records[0], plain, today)}.")])
    choices = [{"id": r.id, "topic": r.title, "branch": r.branch, "modes": list(r.modes), "date": r.date}
               for r in records]
    lines.append(say.Line(f"{len(records)} sessions are open; nothing changed. Run again with --id <id> to pick one:",
                          plain=f"{len(records)} sessions are open, so I haven't picked one. Which is this?"))
    lines += [say.Line(f"- {describe(r)}", plain=f"- {spoken(r, plain, today)}.") for r in records]
    return say.Result(NAME, exit=say.NEEDS_LEAD, data=data, lines=lines, needs_lead=choices)


def switch_to(result, record, root, reader):
    """Move to the one open record's branch, adding what happened (or git's refusal, as exit 2) to `result`."""
    if reader:
        result.lines.append(say.Line("read copy: no branches, nothing switched.",
                                     plain="This is a read copy, so it has no branches to switch to."))
        return
    if not record.remote_only and sessiongit.current_branch(root) == record.branch:
        result.lines.append(say.Line(f"already on {record.branch}.", plain="You're already on its branch."))
        result.data["switched"] = record.branch
        return
    ok, git_words = sessiongit.switch(root, record.branch, record.remote_only)
    if not ok:
        result.exit = say.FAILED
        result.lines.append(say.Line(f"git switch {record.branch} failed: {git_words}",
                                     plain=f"I couldn't switch to its branch. Git said: {git_words}"))
        return
    tracking = " (a new local branch tracking origin)" if record.remote_only else ""
    result.lines.append(say.Line(f"switched to {record.branch}{tracking}.", plain="Switched to its branch."))
    result.data["switched"] = record.branch


def git_failed(why):
    return say.Result(NAME, exit=say.FAILED, lines=[
        say.Line(f"planner: {why}", plain="Git couldn't read the session branches, so I can't tell which session is "
                                          "open.")])

