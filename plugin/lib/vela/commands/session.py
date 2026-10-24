"""`vela session`: the session's own lifecycle commands (CLI/skill overhaul, Task 6). Task 6a built `open`; Task 6b
adds `start` (writes) and `brief` (reads), split so neither becomes a God Function that both changes the repo and
talks to GitHub (review S1, Shield). The rules are in `vela/sessions.py`; git, `gh` and the disk in
`vela/edge/sessiongit.py`; here is only the order of the steps and what each exit says.

`session open [--switch] [--id ID]` finds the open session record and the branch it sits on, so close and START no
longer run a git recipe by hand. Exit codes:

0  exactly one open record (with `--switch`, now on its branch);
1  none open: "No session is open." (close then takes its no-session path), or `--id` names no open record;
2  git failed, a switch git refused (its words are printed), or a record that may be the open one can't be read;
3  several open. Nothing changed and `--switch` did not move: picking for the lead would file one session's captures
   into another's record. The choices are printed and `--json` carries them as `needs_lead`; the skill asks the lead
   and runs again with `--id`.

A reader copy has no branches: the records are read from its folder and no git runs; `--switch` says so and stops.

`session start --mode M [--mode M2] --topic T [--answer PR|ID] [--resume ID|--new] [--title "..."|--unnamed]` is
START steps 1, 2 and 5 and ANSWER-A-CHALLENGE steps 1, 2 and 4. It reads `.vela/host.json` first, because a host
that can commit but can't send must be said at the start, not when the push fails at close (review M5, plan 7.3).
Every check that can stop it runs before anything changes, and all of them are reported at once, so the lead
answers every question in one turn. A new session opens on the branch the lead is on, whatever it is, main included:
it does not switch, pull or branch, and its record notes the branch and the commit it began at (`start_commit`, which
`close drafts` counts from). `--new-branch` makes a `session/...` branch from the current one, and is only for a lead
who asked for a fresh branch. A resumed session's branch, or a challenge's, has origin/main merged in by
`close sync-main`'s own code (`close_sync.bring_in_at_start`), so no session reads a plan older than the shared one
without hearing so. Exit codes:

0  started (or, with `--resume`, back on the open session's branch);
1  refused: a reader copy asked for an owner's mode, a host with no working git (the reader path is said), an unknown
   mode, `--answer` found none or several open challenge PRs (what `gh` returned is printed; never a guessed
   branch), or main changed lines the branch being resumed changed too (sync-main's lines; the merge is aborted);
2  git or `gh` failed (their words are printed), or main couldn't be brought up to date;
3  needs the lead, nothing changed: open sessions exist (resume, close or `--new`), uncommitted changes outside this
   plan (a plan that shares its repo), uncommitted changes a challenge's branch would overwrite, uncommitted edits on a resumed branch that main must be merged into (checkpoint them first), or
   the initiative has no name yet (the one naming question; `--title` answers it, `--unnamed` records that the lead
   declined).

`session branch` moves an open session that sits on the default branch onto its own `session/...` branch, for a lead
who said yes when `close push` explained that main can't be the head of a pull request. The session's commits go with
it and the local default branch goes back to where the session began.

`session brief` is START steps 3 and 4, read-only: review comments on PRs merged since the last closed session (as
candidate captures, in `--json`), the overdue open questions, `vela next`, and how much is still open. A `gh` failure
is a printed line and exit 2, and `review_comments` is null, never an empty list that reads as "no comments"
(Silent Fallback). Everything else in the brief still runs.

Where START.md's old prose went (the October 22 trim; START keeps one line, "on exit 3 ask what it asks, one at a time,
and run it again"): the choice a lead must make is printed here, every time, so it survives compaction.
- Which plan: a repository root that holds several plans exits 3 with `plans.which_plan` (the question, each plan by
  title, `--vault <folder>`). Never guess, never pick the first.
- No plan yet: `no_plan_yet` names `vela new`, says never to set a plan up by hand (no copied files, no `git init`) and
  to run `session start` again. A plan can go in a subfolder of a repository that holds others (`vela new --vault`).
  Documents that were in the folder land in the plan's inbox, where Discover reads them. `vela new` asks for the GitHub
  handle itself (`--handle`) and for the title (`--title`).
- Open sessions: resume (`--resume <id>`), close (`/vela:close`) or start another (`--new`); never close one the
  user hasn't asked to close.
- The initiative's name: asked once; `--title` answers it and `--unnamed` records that the lead declined (the
  dashboard then reads "New initiative").
"""
import argparse
import dataclasses
import datetime
import io
import json
import pathlib
import re

from vela import closestate, commands, guard, planscope, privaterecord, progress, records, recordsplit, say, sessions, titlecheck
from vela.commands import close_sync
from vela.edge import ghcli, hostprobe, mergegit, sessiongit, vaultgit
from vela.edge.vaultgit import GitUnavailable

NAME = "session open"
START, BRIEF = "session start", "session brief"
READ_COPY = ("This is your copy, so your work stays in this folder and nothing goes to the shared plan until "
             "you send a proposal.")
# Git's own words stay in the default line; the lead hears what it means (the October 14 voice audit).
GIT_DETAIL = "The details are in my notes."


def register(sub):
    session = sub.add_parser("session", help="the session record: start one, find the open one, brief the lead")
    verbs = session.add_subparsers(dest="session_command", metavar="{open,start,branch,brief}")
    verbs.required = True
    opener = verbs.add_parser("open", help="the open session record(s), each with its branch, modes and date")
    opener.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    opener.add_argument("--switch", action="store_true",
                        help="switch to the open record's branch when exactly one is open (never guesses among several)")
    opener.add_argument("--id", default="", help="pick this open record among several (after an exit 3)")
    say.add_output_flags(opener)
    opener.set_defaults(func=cmd_open)
    register_start(verbs)
    register_branch(verbs)
    register_brief(verbs)


def register_start(verbs):
    starter = verbs.add_parser("start", help="open the session's record on the current branch and commit it; stops "
                                             "with the choices when open sessions, unsaved work or an unnamed "
                                             "initiative need the lead")
    starter.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    starter.add_argument("--mode", action="append", default=[], choices=sorted(sessions.MODE_NAMES),
                         help="the session's mode; repeat for a session that runs several (the first names it)")
    starter.add_argument("--topic", default="", help="two to four words from the lead's first message: the id's slug")
    starter.add_argument("--answer", default="", metavar="PR|ID",
                         help="answer a challenge: its PR number, or the challenged ID (matched by exact title suffix)")
    starter.add_argument("--new-branch", action="store_true",
                         help="make a session branch from the current one, only when the lead asked for a fresh branch")
    which = starter.add_mutually_exclusive_group()
    which.add_argument("--resume", default="", metavar="ID", help="resume this open session (after an exit 3)")
    which.add_argument("--new", action="store_true", help="leave the open sessions open and start another")
    named = starter.add_mutually_exclusive_group()
    named.add_argument("--title", default="", help="the initiative's name, in the lead's words: written to .vela.yaml "
                                                   "and committed as 'Name the initiative'")
    named.add_argument("--unnamed", action="store_true",
                       help="the lead declined to name the initiative: start anyway, and say so once")
    starter.add_argument("--today", help="the session's date, YYYY-MM-DD (default: today)")
    say.add_output_flags(starter)
    starter.set_defaults(func=cmd_start)


def register_branch(verbs):
    mover = verbs.add_parser("branch", help="move the open session's commits from the default branch onto a new "
                                            "session branch, after the lead's yes")
    mover.add_argument("--vault", default=".", help="vault root (default: current directory)")
    say.add_output_flags(mover)
    mover.set_defaults(func=cmd_branch)


def register_brief(verbs):
    brief = verbs.add_parser("brief", help="read-only: review comments since the last session, overdue questions, the "
                                           "next step and how much is open")
    brief.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    brief.add_argument("--today", help="the date overdue is judged by, YYYY-MM-DD (default: today)")
    say.add_output_flags(brief)
    brief.set_defaults(func=cmd_brief)


def cmd_open(args, out):
    root = pathlib.Path(args.vault).resolve()
    reader = sessiongit.is_read_copy(root)
    resolver = lead_resolver(root) if say.mode_of(args) == "for-lead" else None
    try:
        found = sessiongit.folder_records(root) if reader else sessiongit.branch_records(root)
    except GitUnavailable as exc:
        return commands.emit(git_failed(str(exc)), args, out, resolver)
    records, problems = sessions.find_open(found, vaultgit.plan_scope(root) if not reader else "")
    chosen = sessions.pick(records, args.id) if args.id else records
    result = report(records, chosen, problems, args.id, words(resolver), datetime.date.today())
    result.data.update(reader=reader, switched=None)
    if args.switch and result.exit == say.DONE:
        switch_to(result, chosen[0], root, reader)
    return commands.emit(result, args, out, resolver)


def lead_resolver(root):
    """A resolver over the vault when it loads, so a title naming an item is said by that item's name. A folder that
    is not a vault still gets the plain kind words ("a contract"), and the leak check runs either way."""
    from vela import cli  # cli builds the parser, so it is loaded by the time this runs
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
    """'Grill: calendar entries, started October 14'. A record whose title is only its slug is said by its modes."""
    title = plain(record.title)
    if say.leak_in(title):
        modes = [sessions.MODE_NAMES.get(m, m) for m in record.modes]
        title = f"the {say.names_said(modes) or 'untitled'} session"
    return f"{title}, started {sessions.date_in_words(record.date, today)}"


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
                                     plain="This is your copy, so it has no branches to switch to."))
        return
    if not record.remote_only and sessiongit.current_branch(root) == record.branch:
        result.lines.append(say.Line(f"already on {record.branch}.", plain="You're already on its branch."))
        result.data["switched"] = record.branch
        return
    ok, git_words = sessiongit.switch(root, record.branch, record.remote_only)
    if not ok:
        result.exit = say.FAILED
        result.lines.append(say.Line(f"git switch {record.branch} failed: {git_words}",
                                     plain=f"I couldn't switch to that session. {GIT_DETAIL}"))
        return
    tracking = " (a new local branch tracking origin)" if record.remote_only else ""
    result.lines.append(say.Line(f"switched to {record.branch}{tracking}.", plain="Switched to its branch."))
    result.data["switched"] = record.branch


def git_failed(why):
    return say.Result(NAME, exit=say.FAILED, lines=[
        say.Line(f"vela: {why}", plain="Git couldn't read the session branches, so I can't tell which session is "
                                          "open.")])


# ------------------------------------------------------------------------------------------------- session start

class Stop(Exception):
    """A step ended the start early; `result` says why, with its exit code."""

    def __init__(self, result):
        super().__init__(result.command)
        self.result = result


def refused(rule, plain, fix, override=""):
    return Stop(say.Result(START, exit=say.REFUSED, refusals=[say.Refusal(rule, plain, fix, override)]))


def failed(text, plain, lines=()):
    return Stop(say.Result(START, exit=say.FAILED, lines=list(lines) + [say.Line(text, plain=plain)]))


def cmd_start(args, out):
    from vela import cli  # cli builds the parser, so it is loaded by the time this runs
    root = pathlib.Path(args.vault).resolve()
    if not (root / ".vela.yaml").is_file():
        return commands.emit(no_plan_here(root), args, out)
    today = cli.parse_today(args.today)[0]
    resolver = lead_resolver(root) if say.mode_of(args) == "for-lead" else None
    plain = words(resolver)
    try:
        result = start(root, args, today, plain)
    except Stop as stop:
        result = stop.result
    except GitUnavailable as exc:
        result = say.Result(START, exit=say.FAILED, lines=[
            say.Line(f"vela: {exc}", plain=f"Git failed while starting the session. {GIT_DETAIL}")])
    except sessiongit.PrivateMissing as exc:
        result = say.Result(START, exit=say.FAILED, lines=[say.Line(f"vela: {exc}", plain=str(exc))])
    except OSError as exc:  # atomic.WriteFailed among them
        result = say.Result(START, exit=say.FAILED, lines=[
            say.Line(f"vela: couldn't write: {exc}", plain="I couldn't write the session's files to disk, so I "
                                                           "haven't started.")])
    return commands.emit(result, args, out, resolver)


def no_plan_here(root):
    """A folder with no `.vela.yaml`: the plan it sits in, the plans a repo's root holds (the lead says which), or none."""
    from vela.commands import plans as plans_command
    from vela.edge import plans
    top = plans.repo_root(root)
    above = plans.plan_above(root)
    if above is not None and above != root:
        name = plans_command.said_name(plans_command.describe(above, top or above))
        return say.Result(START, exit=say.REFUSED, refusals=[say.Refusal(
            "inside-plan", f"This folder is inside the plan {name}, but a session starts from the plan's own folder.",
            f"run the command with --vault {above}", "", recommend="I'd start it from the plan's own folder.", waiver="")])
    held = [plans_command.describe(folder, top) for folder in plans.plans_in(top)] if top == root else []
    if held:
        return plans_command.which_plan(held)
    return no_plan_yet()


def no_plan_yet():
    """A folder with no `.vela.yaml` isn't a plan yet. Git would fail there and say so in its own words (Black Box for
    the lead), so the start stops first and names the way forward: `vela new` starts one."""
    question = "There's no plan in this folder yet. Want me to start one? I'll need the initiative's name."
    return say.Result(START, exit=say.NEEDS_LEAD, needs_lead=[{
        "ask": "start a plan", "question": question, "answer_with": 'vela new --title "<initiative name>"',
        "then": "run session start again"}], lines=[
        say.Line("vela: no plan here yet; `vela new` starts one, never a plan set up by hand (no copied files, no git "
                 "init). In a subfolder of a repository that holds other plans: `vela new --vault <folder>`. Then run "
                 "session start again.", plain=question)])


def start(root, args, today, plain):
    """START steps 1, 2 and 5 in order; every stop before the first change."""
    reader = sessiongit.is_read_copy(root)
    modes = requested_modes(args)
    refuse_request(args, modes, reader)
    try:
        host = sessiongit.read_json(root, hostprobe.HOST_FILE)
    except ValueError as exc:
        raise failed(f"vela: {exc}", "I can't read my last check of this machine, so I haven't started. Want me to "
                                     "run the check again?") from exc
    row, sentence = hostprobe.stance(host) if host is not None else ("", "")
    if not reader and row in ("no-git", "git-broken"):
        raise Stop(say.Result(START, exit=say.REFUSED, refusals=[say.Refusal(
            "no working git", sentence, "open the vault's own clone in Claude Code, or work as a reader here (read, "
            "ask, find, explore, draft, then /vela:propose)", "run /vela:where again if git works here now",
            recommend="I'd open the plan's own folder in Claude Code to run the session.",
            waiver="If git works here now, I can check the machine again and go on.")]))
    said = [say.Line(f"host: {row}: {sentence}", plain=sentence)] if row == "no-send" else []
    if reader:
        return start_in_copy(root, args, today, modes, plain, said)
    return start_in_repo(root, args, today, modes, plain, said, host or {})


def requested_modes(args):
    asked = (["answer"] if args.answer else []) + list(args.mode)
    return list(dict.fromkeys(asked))


def refuse_request(args, modes, reader):
    if args.new_branch and (args.resume or args.answer or reader):
        raise refused("new branch", "A new branch is for a fresh session in the plan's own clone; a resumed session "
                      "and an answer keep the branch they are on, and a copy has no branches.",
                      "leave --new-branch off")
    if args.resume:
        return
    if not modes:
        raise refused("no mode", "I need to know which mode this session runs.", "pass --mode <mode>")
    if not args.answer and not sessions.slug(args.topic):
        raise refused("no topic", "I need a few words on what the session is for, to name it.",
                      'pass --topic "<two to four words from the lead>"')
    owner_only = [m for m in modes if m in sessions.OWNER_ONLY]
    if reader and owner_only:
        raise refused("owner-only mode", f"A {sessions.MODE_NAMES[owner_only[0]].lower()} session opens or updates a "
                      "pull request, which your copy can't do. Send a proposal (/vela:propose) and the owner "
                      "decides.", "run a reader mode here, or the owner runs this one in the vault's clone",
                      "the owner runs it in the vault's own clone")


def today_date(today):
    return datetime.date.fromisoformat(today)


def open_choices(records, today, plain):
    """(needs_lead entries, lines) for the open sessions: resume, close, or leave open and start another."""
    asks = [{"ask": "open session", "id": r.id, "topic": r.title, "branch": r.branch, "date": r.date,
             "stale": sessions.is_stale(r, today_date(today)),
             "choices": [f"--resume {r.id}", "/vela:close", "--new"]} for r in records]
    count = f"{len(records)} session{'s are' if len(records) != 1 else ' is'} open"
    newest = max(records, key=lambda r: (r.date or "", r.id))
    if len(records) == 1:
        asked = (f"A session is still open: {spoken(newest, plain, today_date(today))}. I'd pick it up. Pick it up, "
                 "close it, or leave it open and start a new one?")
    else:
        asked = (f"{say.count_words(len(records), capital=True)} sessions are still open. I'd pick up "
                 f"{spoken(newest, plain, today_date(today))}, since it's the newest. Pick one up, close one, or "
                 "start fresh?")
    lines = [say.Line(f"{count}; nothing changed. Resume one with --resume <id>, close it with /vela:close, or start "
                      "another with --new:", plain=asked)]
    for record, ask in zip(records, asks):
        old = " (more than 14 days old)" if ask["stale"] else ""
        lines.append(say.Line(f"- {describe(record)}{old}",
                              plain=f"- {spoken(record, plain, today_date(today))}"
                                    f"{', more than two weeks ago' if old else ''}." if len(records) > 1 else ""))
    return asks, lines


def naming_choice():
    ask = {"ask": "initiative name", "question": sessions.NAMING_QUESTION, "answer_with": '--title "<their words>"',
           "declined": "--unnamed"}
    line = say.Line(f"W718: the initiative is still called '{sessions.schema.PLACEHOLDER_TITLE}'; nothing changed. Ask "
                    f"the lead, then run again with --title \"...\" (or --unnamed if they decline): "
                    f"{sessions.NAMING_QUESTION}", plain=sessions.NAMING_QUESTION)
    return ask, line


def clobber_choice(paths, base_words):
    ask = {"ask": "uncommitted changes", "paths": paths, "choices": ["commit them", "set them aside", "drop them"]}
    shown = ", ".join(paths)
    line = say.Line(f"uncommitted changes that bringing {base_words} up to date would overwrite: {shown}; nothing "
                    "changed.", plain="Bringing in the shared plan would wipe your unsaved edits to {pages}. I'd "
                                      "save them first. Save them, set them aside, or drop them?")
    return ask, line


def with_pages(line, paths, plain):
    """A line whose plain says `{pages}`, filled with the pages' titles (never their paths)."""
    return say.Line(line.text, plain=line.plain.replace("{pages}", pages_said(paths, plain)), audience=line.audience)


def pages_said(paths, plain):
    """'the Goals and Solution strategy pages': each path said by its page's title, a few at most."""
    names = []
    for path in paths:
        stem = path.rsplit("/", 1)[-1]
        stem = stem[:-3] if stem.endswith(".md") else stem
        said = plain(stem)
        names.append(said if said != stem and not say.leak_in(said) else "")
    known = [n for n in names if n]
    others = len(names) - len(known)
    shown = known[:3]
    rest = len(known) - len(shown) + others
    said = say.names_said(shown + ([f"{say.count_words(rest)} other {'file' if rest == 1 else 'files'}"] if rest else []))
    return said if not known else f"{said} {'page' if len(shown) == 1 and not rest else 'pages'}"


def one_ask_at_a_time(asked):
    """Every stop is reported at once, so the model can answer them all in one call; the lead hears the first question
    in full and that more follow (conversation voice rule 2: one question at a time). The default lines keep them all."""
    firsts = [i for i, line in enumerate(asked) if line.plain and not line.plain.startswith("- ")]
    if len(firsts) < 2:
        return asked
    later = len(firsts) - 1
    kept = [say.Line(line.text, plain="", audience=line.audience) if i >= firsts[1] else line
            for i, line in enumerate(asked)]
    return kept + [say.Line("", plain=f"And {say.count_words(later)} more {'thing' if later == 1 else 'things'} after "
                                      "that.")]


def resume(root, found, wanted, reader, lines, today, plain, host=None):
    chosen = sessions.pick(found, wanted)
    if not chosen:
        raise Stop(say.Result(START, exit=say.REFUSED, lines=lines + [
            say.Line(f"No open session has the id {wanted}.", plain="The session you picked isn't open.")]))
    if len(chosen) > 1:
        asks = [{"ask": "open session", "id": r.id, "branch": r.branch} for r in chosen]
        raise Stop(say.Result(START, exit=say.NEEDS_LEAD, needs_lead=asks, lines=lines + [
            say.Line(f"{wanted} is open on {len(chosen)} branches; nothing changed: "
                     f"{', '.join(r.branch or 'this folder' for r in chosen)}",
                     plain="That session is open on more than one branch, so I haven't picked one.")]))
    record = chosen[0]
    result = say.Result(START, lines=lines + [
        say.Line(f"resuming: {describe(record)}", plain=f"Picking up {spoken(record, plain, today_date(today))}.")])
    switch_to(result, record, root, reader)
    if result.exit == say.DONE and not reader:
        result.wrote += bring_main_in(root, today, host or {}, result.lines, "copy of the session's branch")
    if result.exit == say.DONE:
        text = sessiongit.private_text(root, record.id)
        part = privaterecord.part_of(text) if text is not None else claim_part(root, record, result.lines)
        result.wrote.append(write_state(root, record.id, record.branch, list(record.modes), record.date, part,
                                        max(records.numbers_in(text or ""), default=0)))
        result.data.update(id=record.id, path=privaterecord.private_path(record.id), branch=record.branch)
    return result


CLAIM_TRIES = 3
NOT_CLAIMED = ("I couldn't tell the other machine I'm taking notes here, so I haven't started. Check the connection "
               "and say the word, and I'll try again.")


def another_machine(part):
    return (f"This session's notes are on the other machine and stay there. I'll keep new notes here as part {part}.")


def claim_part(root, record, lines):
    """Take the next part number for this machine, tell the other machines, and open its private file. Returns the
    part. The claim is committed and pushed first because two machines that both wrote part 2 would fingerprint two
    different files under one key (a Distributed Monolith in the record); a lost push takes the next number, and a
    push that fails for any other reason stops the start, never an unclaimed part (Silent Fallback)."""
    rel = privaterecord.stub_path(record.id)
    for _ in range(CLAIM_TRIES):
        stub = (root / rel).read_text(encoding="utf-8")
        part = privaterecord.next_part(privaterecord.stub_meta(stub))
        sessiongit.write_text(root, rel, privaterecord.with_part(stub, part, privaterecord.PENDING))
        if not record.branch:  # a reader copy has no git: the claim stays in this folder
            return opened_part(root, record, part, lines)
        try:
            sessiongit.commit(root, f"Take part {part} of {record.id}", [rel])
        except GitUnavailable:
            sessiongit.write_text(root, rel, stub)
            raise
        if not sessiongit.has_origin(root):
            return opened_part(root, record, part, lines)
        sent = ghcli.push(root, record.branch, track=False)
        if sent.ok:
            return opened_part(root, record, part, lines)
        if not lost_race(sent.why):
            dropped, said = sessiongit.drop_last_commit(root)  # a retry must claim this same number
            kept = "" if dropped else f"; and the claim commit stays, because git refused to undo it: {said}"
            raise failed(f"the claim of part {part} was not pushed: {sent.why}{kept}", NOT_CLAIMED, lines)
        take_back_claim(root, record, lines)
    raise failed(f"{CLAIM_TRIES} claims in a row lost the push", NOT_CLAIMED, lines)


def lost_race(why):
    return any(sign in why for sign in ("rejected", "non-fast-forward", "fetch first"))


def take_back_claim(root, record, lines):
    """Drop the claim that lost and bring in the one that won, so the next try numbers after it."""
    ok, said = sessiongit.drop_last_commit(root)
    fetched, said_fetch = sessiongit.fetch(root) if ok else (False, "")
    moved, said_move = sessiongit.fast_forward(root, f"origin/{record.branch}") if fetched else (False, "")
    if not (ok and fetched and moved):
        raise failed(f"couldn't catch up with {record.branch} after a lost claim: {said or said_fetch or said_move}",
                     NOT_CLAIMED, lines)


def opened_part(root, record, part, lines):
    sessiongit.write_text(root, privaterecord.private_path(record.id),
                          privaterecord.new_private(record.id, record.title, record.date, part))
    lines.append(say.Line(f"claimed part {part} of {record.id}", plain=another_machine(part)))
    return part


def write_state(root, record_id, branch, modes, started, part=1, last_capture=0):
    """`.vela/session.json`: which notes `record add` writes to (`path`, the private file), the committed `stub` whose
    status says whether the session is still open, the part this machine holds, and the highest capture number it
    handed out."""
    return sessiongit.write_state(root, {"id": record_id, "path": privaterecord.private_path(record_id),
                                         "stub": privaterecord.stub_path(record_id), "part": part, "branch": branch,
                                         "modes": modes, "started": started, "last_capture": last_capture})


def problem_lines(problems):
    return [say.Line(f"unreadable: {why}", plain="A session record has frontmatter that can't be read, so it isn't "
                                                 "counted.") for why in problems]


def config_of(root):
    from vela import cli
    try:
        return cli.load_config(root)
    except cli.ToolError as exc:
        raise failed(f"vela: {exc}", f"The vault's settings file can't be read, so I haven't started: {exc}") from exc


TITLE_ASKED = ".vela/title-asked.json"
TITLE_AGAIN = " If you want it anyway, say the same name again and I'll keep it and note that you chose it."


def check_title(root, topic, today):
    """Stop, before anything is written, when the session's name is a person's (exit 3). The name is committed
    with the stub, so it is the one place a private session would show who was in it. The lead may override the
    check: the same name a second time is kept, and the day goes in the stub as `title_override`. Returns that day,
    or "" when the name passed the check."""
    if not topic:
        return ""
    from vela import cli
    private = pathlib.Path(root) / privaterecord.PRIVATE_DIR
    origins = set()
    for path in sorted(private.glob("*.md")) if private.is_dir() else ():
        origins |= titlecheck.origins_in(path.read_text(encoding="utf-8"))
    known = titlecheck.people(cli.load_vault(root), sessiongit.read_handle(root), sessiongit.lead_names(root), origins)
    found = titlecheck.named(topic, known)
    if not found:
        return ""
    asked = sessiongit.read_json(root, TITLE_ASKED) or {}
    if str(asked.get("topic", "")).casefold() == topic.strip().casefold():
        return today
    sessiongit.write_text(root, TITLE_ASKED, json.dumps({"topic": topic.strip()}) + "\n")
    raise Stop(say.Result(START, exit=say.NEEDS_LEAD, needs_lead=[{
        "ask": "session name", "question": titlecheck.TITLE_QUESTION}], lines=[say.Line(
        f"vela: the session name '{topic}' has {', '.join(found)} in it, a person; nothing was written. "
        "Run start again with the same --topic to override; the stub records title_override.",
        plain=f"{titlecheck.TITLE_QUESTION} (I matched on {say.names_said(found)}.){TITLE_AGAIN}")]))


def start_in_copy(root, args, today, modes, plain, said):
    """A reader copy: the record is written in place and nothing runs git (START, "Owner or reader")."""
    open_records, problems = sessions.find_open(sessiongit.folder_records(root))
    lines = said + [say.Line(f"read copy: {READ_COPY}", plain=READ_COPY)] + problem_lines(problems)
    if args.resume:
        return resume(root, open_records, args.resume, True, lines, today, plain)
    if open_records and not args.new:
        asks, asked = open_choices(open_records, today, plain)
        raise Stop(say.Result(START, exit=say.NEEDS_LEAD, needs_lead=asks, lines=lines + asked))
    override = check_title(root, args.topic, today)
    if args.title or sessions.is_unnamed(config_of(root)):
        lines.append(say.Line("read copy: naming the initiative is the owner's; .vela.yaml not changed.",
                              plain="The owner names the initiative, so I haven't changed its name here."))
    record_id = sessions.new_id(today, args.topic, lambda i: (root / "sessions" / f"{i}.md").exists())
    title = sessions.title_for(modes, args.topic)
    rel = privaterecord.private_path(record_id)
    stub, size_lines = with_size_said(root, privaterecord.new_stub(record_id, title, today, modes, title_override=override))
    wrote = [sessiongit.write_text(root, privaterecord.stub_path(record_id), stub),
             sessiongit.write_text(root, rel, privaterecord.new_private(record_id, title, today, 1))]
    wrote.append(write_state(root, record_id, None, modes, today))
    lines.append(say.Line(f"started: {record_id} in this folder, modes: {', '.join(modes)}",
                          plain=f"I've opened the session: {plain(sessions.title_for(modes, args.topic))}."))
    lines += size_lines
    return say.Result(START, lines=lines, wrote=wrote, data={"id": record_id, "path": rel, "branch": None,
                                                             "modes": modes, "reader": True})


def find_challenge(root, wanted, plain):
    """(pr, challenged id): exactly one open challenge PR, by number or by exact title suffix, or Stop."""
    number = wanted.lstrip("#")
    if number.isdigit():
        pr, why = sessiongit.gh_json(root, "pr", "view", number, "--json", "number,headRefName,title,state")
        if why:
            raise gh_stopped(f"gh pr view {number}", why)
        ident = sessions.challenged_id(pr if isinstance(pr, dict) else {})
        if not ident:
            raise not_one_challenge(f"PR {number} isn't an open challenge PR", [pr], plain)
        return pr, ident
    prs, why = sessiongit.gh_json(root, "pr", "list", "--search", f"Challenge: {wanted}", "--state", "open",
                                  "--json", "number,headRefName,title")
    if why:
        raise gh_stopped("gh pr list", why)
    prs = prs if isinstance(prs, list) else []
    matches = sessions.challenge_matches(prs, wanted)
    if len(matches) != 1:
        found = "no open PR" if not matches else f"{len(matches)} open PRs"
        raise not_one_challenge(f"{found} has a title ending with exactly 'Challenge: {wanted}'", prs, plain)
    return matches[0], wanted


def gh_stopped(what, why):
    return failed(f"{what} failed: {why}. An answer never starts on a guessed branch; nothing changed.",
                  "I couldn't reach GitHub, so I haven't started: I need the challenge itself, not a guess at it.")


def not_one_challenge(why, prs, plain):
    shown = [say.Line(f"- #{pr.get('number')} {pr.get('title', '')} ({pr.get('headRefName', '?')})",
                      plain=plain(f"- {pr.get('title', '')}")) for pr in prs if isinstance(pr, dict)]
    return Stop(say.Result(START, exit=say.REFUSED, data={"gh_returned": prs}, lines=[
        say.Line(f"{why}; nothing changed. gh returned:" if shown else f"{why}; nothing changed. gh returned nothing.",
                 plain=("I found more than one challenge that could match, so I haven't started. Which one?" if
                        len(shown) > 1 else "I couldn't find that challenge open on GitHub, so I haven't started.")
                 + (" GitHub lists:" if shown else ""))] + shown))


def bring_in(root, host):
    """(how, git's words): `fetched`, `no-origin`, `offline` (host.json says the shared copy can't be reached, so
    no fetch is tried) or `failed`. Only a fetch: nothing local moves until every check has passed."""
    if not sessiongit.has_origin(root):
        return "no-origin", ""
    if host.get("network") == hostprobe.NO:
        return "offline", ""
    ok, words_ = sessiongit.fetch(root)
    return ("fetched" if ok else "failed"), words_


def freshness_line(how, words_, base_words):
    if how == "fetched":
        return None
    if how == "no-origin":
        return say.Line(f"no origin: starting from this machine's {base_words}",
                        plain="This plan isn't shared anywhere yet, so we start from what's on this laptop.")
    if how == "offline":
        return say.Line(f"host can't reach origin (.vela/host.json): {base_words} not pulled",
                        plain="I can't reach the shared plan from here, so we start from this laptop's copy, which "
                              "may be out of date.")
    return say.Line(f"git fetch origin failed: {words_}; starting from this machine's {base_words}",
                    plain="I couldn't reach the shared plan, so we start from this laptop's copy, which may be out "
                          "of date.")


def move_to(root, base, upstream, base_words):
    """Switch to `base` and fast-forward it to `upstream` (START step 1's `git switch main` and `git pull`)."""
    if sessiongit.current_branch(root) != base:
        local = sessiongit.ref_exists(root, f"refs/heads/{base}")
        ok, said = sessiongit.switch(root, base, remote_only=not local)
        if not ok:
            raise failed(f"git switch {base} failed: {said}",
                         f"I couldn't get the latest shared plan, so I haven't started. {GIT_DETAIL}")
    if upstream:
        ok, said = sessiongit.fast_forward(root, upstream)
        if not ok:
            raise failed(f"git merge --ff-only {upstream} failed: {said}; on {base} now, nothing else changed",
                         "I couldn't get the latest shared plan, so I haven't started; starting from an old copy "
                         f"would mislead us. {GIT_DETAIL}")


def start_in_repo(root, args, today, modes, plain, said, host):
    """The owner's start, with vela's own changed files set aside for its length and written back unchanged after
    (`set_aside_vela_files`): a dashboard `close dashboard` rebuilt and nobody committed stopped six sessions in a row
    on "uncommitted changes" that no command would commit."""
    try:
        aside, kept = set_aside_vela_files(root)
    except mergegit.MergeGitFailed as exc:
        raise GitUnavailable(str(exc)) from exc
    try:
        result = start_owner(root, args, today, modes, plain, said, host)
    finally:
        mergegit.put_back(root, kept)
    if aside:
        result.lines.append(say.Line(
            f"set aside and wrote back unchanged {', '.join(aside)}: none is the lead's unsaved work (vela rebuilds "
            "the dashboard at close; close stage never commits its own files), so none stopped the start.",
            audience=say.MODEL))
    return result


def set_aside_vela_files(root):
    """(paths, kept bytes): the tracked files with uncommitted changes that `guard.set_aside_unasked` says are not
    the lead's work, put back to HEAD's copy, as sync-main does before its merge. `.vela/` is left alone: start writes
    `.vela/session.json` itself, and writing an old copy back would undo that."""
    aside = [path for path in mergegit.tracked_changes(root)
             if not sessions.is_tool_state(path) and guard.set_aside_unasked(path)]
    return aside, mergegit.set_aside(root, aside)


def check_shared_repo(root):
    """A plan that shares its repo starts a session only when nothing outside this plan has unsaved changes: those are
    the owner's own work on something else, and a session's commits and branch moves must not sweep it up. HEAD may be
    on any branch (the session runs on it). Otherwise exit 3, nothing changed. A plan that is its own repo has nothing
    else to disturb."""
    if not vaultgit.plan_scope(root):
        return
    outside = vaultgit.changed_outside_plan(root)
    if outside:
        count = say.count_words(len(outside))
        question = (f"{count.capitalize()} file{'s' if len(outside) != 1 else ''} outside this plan {'have' if len(outside) != 1 else 'has'} "
                    "unsaved changes, and a session saves its work in the same repository. Save them or "
                    "set them aside first, then I'll start.")
        raise Stop(say.Result(START, exit=say.NEEDS_LEAD, lines=[say.Line(
            f"vela: uncommitted changes outside this plan ({', '.join(outside[:5])}); a session commits in the same "
            "repository. Commit or stash them, then run again.", plain=question)],
            needs_lead=[{"ask": "unsaved work outside the plan", "question": question, "paths": outside}]))


def start_owner(root, args, today, modes, plain, said, host):
    """The owner's start: every check, then the record and its commit, on the branch the lead is on. A challenge's
    answer is the exception: it goes onto the challenge's branch, brought up to date first."""
    config = config_of(root)
    pr, challenged = find_challenge(root, args.answer, plain) if args.answer else (None, "")
    open_records, problems = sessions.find_open(sessiongit.branch_records(root), vaultgit.plan_scope(root))
    check_shared_repo(root)
    lines = said + problem_lines(problems)
    if args.resume:
        return resume(root, open_records, args.resume, False, lines, today, plain, host)
    override = check_title(root, "" if pr else args.topic, today)
    asks, asked = [], []
    if open_records and not args.new:
        asks, asked = open_choices(open_records, today, plain)
    if not args.title and not args.unnamed and sessions.is_unnamed(config):
        ask, line = naming_choice()
        asks.append(ask)
        asked.append(line)
    if pr:
        return start_on_challenge(root, args, today, modes, plain, host, pr, challenged, lines, asks, asked)
    current = sessiongit.current_branch(root)
    if not current:
        raise refused("no branch", "The plan's repository isn't on a branch (HEAD is detached), and a session's "
                      "work needs a branch to sit on.", "switch to a branch, then start the session")
    if asks:
        raise Stop(say.Result(START, exit=say.NEEDS_LEAD, needs_lead=asks, lines=lines + one_ask_at_a_time(asked)))
    lines += [review_needs_branch(current)] if current == sessiongit.default_branch(root) and not args.new_branch else []
    carried = sessions.carried(sessiongit.dirty_paths(root), [])
    return open_record(root, args, today, modes, "", "" if args.new_branch else current, lines, carried, plain,
                       title_override=override)


def review_needs_branch(current):
    """Said once, when a session starts on the default branch: close can't open a pull request from it."""
    return say.Line(f"on {current}: a review needs its own branch; with the lead's yes, run vela session branch "
                    "(the session is open now)",
                    plain=f"We're on {current}, and a review needs its own branch. If you want one for this session, "
                          "say so and I'll make it; otherwise the work stays here.")


def start_on_challenge(root, args, today, modes, plain, host, pr, challenged, lines, asks, asked):
    """An answer: the challenge's branch, brought up to date, then the record on it."""
    base = pr["headRefName"]
    how, fetch_words = bring_in(root, host)
    upstream = f"origin/{base}" if how == "fetched" and sessiongit.ref_exists(root, f"refs/remotes/origin/{base}") \
        else ""
    known = [ref for ref in (f"refs/heads/{base}", f"refs/remotes/origin/{base}") if sessiongit.ref_exists(root, ref)]
    target = upstream or (known[0] if known else "")  # origin's copy from an earlier fetch still serves offline
    if not target:
        raise failed(f"no branch {base} here or on origin; nothing changed",
                     "I can't find the challenge's branch here or in the shared copy, so I haven't started.", lines)
    lost = sessions.clobbered(sessiongit.dirty_paths(root), sessiongit.incoming_paths(root, target))
    if lost:
        ask, line = clobber_choice(lost, "the challenge's branch")
        asks.append(ask)
        asked.append(with_pages(line, lost, plain))
    if asks:
        raise Stop(say.Result(START, exit=say.NEEDS_LEAD, needs_lead=asks, lines=lines + one_ask_at_a_time(asked)))
    fresh = freshness_line(how, fetch_words, "the challenge's branch")
    lines += [fresh] if fresh else []
    move_to(root, base, upstream, "the challenge's branch")
    wrote = bring_main_in(root, today, host, lines, "copy of the challenge's branch") if how == "fetched" else []
    carried = sessions.carried(sessiongit.dirty_paths(root), [])
    result = open_record(root, args, today, modes, challenged, base, lines, carried, plain)
    result.wrote[:0] = wrote
    return result


PASSED = (closestate.UP_TO_DATE, closestate.MERGED, closestate.MERGED_GENERATED)


def bring_main_in(root, today, host, lines, base_words):
    """START step 1 for a branch the session already has (a resumed one, a challenge's): origin/main is merged in by
    close sync-main's own code, so a session never reads a branch that lacks the shared plan without saying so (S15
    of the 2026-10-14 run missed an allocation that way). Adds what happened to `lines` and returns the paths the merge
    changed. Stop when the lead must act first: uncommitted edits in the way, a clash, or git failing."""
    how = "no-origin" if not sessiongit.has_origin(root) else "offline" if host.get("network") == hostprobe.NO else ""
    if how:
        lines.append(freshness_line(how, "", base_words))
        return []
    synced = close_sync.bring_in_at_start(root, today)
    if synced.data["status"] in PASSED:
        lines += synced.lines
        return list(synced.wrote)
    if synced.data["reason"] == closestate.FETCH_FAILED:  # the same as a start that couldn't fetch: said, and go on
        lines.append(freshness_line("failed", synced.data["fetch_error"], base_words))
        return []
    raise Stop(say.Result(START, exit=synced.exit, lines=lines + synced.lines, refusals=synced.refusals,
                          needs_lead=synced.needs_lead))


def open_record(root, args, today, modes, challenged, on_branch, lines, carried, plain=lambda text: text,
                title_override=""):
    """START step 5: the id, the branch (an answer stays on its challenge's), the record, `Open session <id>`, then
    the initiative's name when the lead gave one, and `.vela/session.json`."""
    scope = vaultgit.plan_scope(root)

    def taken(candidate):
        on_disk = (root / "sessions" / f"{candidate}.md").exists()
        return on_disk or (not on_branch and sessiongit.branch_taken(root, planscope.session_branch(scope, candidate)))

    record_id = sessions.answer_id(today, challenged, taken) if challenged else sessions.new_id(today, args.topic, taken)
    branch = on_branch or planscope.session_branch(scope, record_id)
    if not on_branch:
        ok, said = sessiongit.create_branch(root, branch)
        if not ok:
            raise failed(f"git switch -c {branch} failed: {said}",
                         f"I couldn't set the session up, so I haven't started. {GIT_DETAIL}", lines)
    rel = privaterecord.stub_path(record_id)
    title = sessions.title_for(modes, args.topic, challenged)
    began = sessiongit.head_commit(root)
    challenges = [args.topic] if "challenge" in modes else []
    stub, size_lines = with_size_said(root, privaterecord.new_stub(record_id, title, today, modes, branch, began,
                                                                   challenges, title_override))
    wrote = [sessiongit.write_text(root, rel, stub),
             sessiongit.write_text(root, privaterecord.private_path(record_id),
                                   privaterecord.new_private(record_id, title, today, 1))]
    committed = [rel] + keep_notes_out_of_git(root, wrote)
    sessiongit.commit(root, f"Open session {record_id}", committed)  # the notes stay here; only the stub is committed
    where = ", and your answer goes onto the challenge itself" if challenged else ""
    lines.append(say.Line(f"started: {record_id} on {branch}, modes: {', '.join(modes)}",
                          plain=f"I've opened the session: {plain(title)}{where}."))
    if carried:
        lines.append(say.Line(f"carried, unstaged: {', '.join(carried)}",
                              plain=f"Your edits to {pages_said(carried, plain)} come with us."))
    if args.title:
        yaml_text = (root / ".vela.yaml").read_text(encoding="utf-8")
        wrote.append(sessiongit.write_text(root, ".vela.yaml", sessions.with_title(yaml_text, args.title)))
        sessiongit.commit(root, "Name the initiative", [".vela.yaml"])
        lines.append(say.Line(f"named: title: {args.title}", plain=f"The initiative is called {args.title} now."))
    elif args.unnamed:
        lines.append(say.Line("unnamed: the lead declined to name the initiative",
                              plain='The dashboard will read "New initiative" until you give it a name.'))
    lines += size_lines
    wrote.append(write_state(root, record_id, branch, modes, today))
    return say.Result(START, lines=lines, wrote=wrote, data={"id": record_id, "path": rel, "branch": branch,
                                                             "modes": modes, "reader": False})


def with_size_said(root, stub):
    """(the new stub carrying the plan's size, the size line to say). The size is read before the stub exists and
    recorded in it, so it travels in the opening commit and is said once."""
    from vela import cli
    from vela.commands import size
    due = size.due(cli.load_vault(root))
    if due is None:
        return stub, []
    line, value, kept = due
    return privaterecord.with_size(stub, size=value, kept=kept), [line]


def keep_notes_out_of_git(root, wrote):
    """A plan made before private notes lacks the `.gitignore` line for them until `records split` runs, so the first
    session would leave its notes showing as new files for a hand `git add .` to commit. Adds the line (creating the file)
    and returns the path to commit with the stub, else []."""
    path = root / ".gitignore"
    held = path.read_text(encoding="utf-8") if path.is_file() else ""
    wanted = recordsplit.with_ignore_line(held)
    if wanted == held:
        return []
    wrote.append(sessiongit.write_text(root, ".gitignore", wanted))
    return [".gitignore"]


# ------------------------------------------------------------------------------------------------- session branch

BRANCH = "session branch"


def cmd_branch(args, out):
    root = pathlib.Path(args.vault).resolve()
    resolver = lead_resolver(root) if say.mode_of(args) == "for-lead" else None
    try:
        result = move_to_own_branch(root)
    except Stop as stop:
        result = stop.result
    except GitUnavailable as exc:
        result = say.Result(BRANCH, exit=say.FAILED, lines=[
            say.Line(f"vela: {exc}", plain=f"Git failed while moving the session. {GIT_DETAIL}")])
    except sessiongit.PrivateMissing as exc:
        result = say.Result(BRANCH, exit=say.FAILED, lines=[say.Line(f"vela: {exc}", plain=str(exc))])
    return commands.emit(result, args, out, resolver)


def refuse_branch(text, plain):
    return Stop(say.Result(BRANCH, exit=say.REFUSED, lines=[say.Line(text, plain=plain)]))


def move_to_own_branch(root):
    """Give the open session on the default branch its own `session/...` branch, carrying its commits. The local default
    branch goes back to the session's start commit so main holds nothing of the session (never committed to main, never
    pushed from it); when some of those commits are already on origin's copy, main is left alone and that is said."""
    if sessiongit.is_read_copy(root):
        raise refuse_branch("vela session branch: a reader copy has no branches.", READ_COPY)
    scope = vaultgit.plan_scope(root)
    current, default = sessiongit.current_branch(root), sessiongit.default_branch(root)
    found, _ = sessions.find_open(sessiongit.branch_records(root), scope)
    here = [r for r in found if r.branch == current]
    if not here and current == default:  # finished on the default branch, never pushed: close push sent the lead here
        here = finished_unpushed(root, default)
    if len(here) != 1:
        raise refuse_branch(f"vela session branch: {len(here)} open sessions on {current or 'no branch'}; need exactly one.",
                            "I can't tell which session to move, so I haven't moved anything.")
    record = here[0]
    if current != default:
        raise refuse_branch(f"vela session branch: {record.id} is on {current}, not {default}; nothing to move.",
                            "This session already has a branch of its own, so there's nothing to move.")
    branch = planscope.session_branch(scope, record.id)
    if sessiongit.branch_taken(root, branch):
        raise refuse_branch(f"vela session branch: {branch} already exists; nothing changed.",
                            "A branch for this session already exists, so I haven't moved anything.")
    text = (root / record.path).read_text(encoding="utf-8")
    notes = sessiongit.private_text(root, record.id)
    if notes is None:
        raise sessiongit.PrivateMissing(record.id)
    began = sessions.start_commit_of(text)
    ok, said = sessiongit.create_branch(root, branch)
    if not ok:
        raise failed_branch(f"git switch -c {branch} failed: {said}", f"I couldn't make the branch. {GIT_DETAIL}")
    rel = record.path
    sessiongit.write_text(root, rel, sessions.with_branch(text, branch))
    sessiongit.commit(root, f"Move session {record.id} to {branch}", [rel])
    write_state(root, record.id, branch, list(record.modes), record.date, privaterecord.part_of(notes),
                max(records.numbers_in(notes), default=0))
    lines = [say.Line(f"moved {record.id} from {default} to {branch}",
                      plain="The session has its own branch now, with everything we did on it.")]
    lines += main_back(root, default, began, branch)
    return say.Result(BRANCH, lines=lines, wrote=[rel], data={"id": record.id, "branch": branch, "from": default})


def finished_unpushed(root, default):
    """The sessions on the default branch that `close finish` closed and whose commits origin's default branch lacks:
    what `close push` sends back to `session branch` once the open one is gone."""
    upstream = f"refs/remotes/origin/{default}"
    found = []
    for ref, path, text in sessiongit.folder_records(root):
        record, _ = sessions.read(ref, path, text)
        if (record is not None and record.status == "closed" and privaterecord.stub_meta(text).get("branch") == default
                and sessiongit.unshared_commits_touching(root, upstream, "HEAD", path)):
            found.append(dataclasses.replace(record, branch=default))
    return found


def failed_branch(text, plain):
    return Stop(say.Result(BRANCH, exit=say.FAILED, lines=[say.Line(text, plain=plain)]))


def main_back(root, default, began, branch):
    """The lines for what happened to the local default branch: put back where the session began, or left, and why."""
    if not began or not sessiongit.ref_exists(root, began):
        return [say.Line(f"{default} left as it is: the record has no start commit to put it back to",
                         plain=f"The session's first commits are still on {default} here too; I didn't move it back.")]
    own = sessiongit.commits_between(root, began, branch)
    upstream = f"refs/remotes/origin/{default}"
    unshared = sessiongit.commits_between(root, upstream, branch) if sessiongit.ref_exists(root, upstream) else own
    if own != unshared:
        return [say.Line(f"{default} left as it is: some of the session's commits are already on origin/{default}",
                         plain=f"Some of today's work is already on the shared {default}, so I left {default} alone.")]
    ok, said = sessiongit.move_branch(root, default, began)
    if not ok:
        return [say.Line(f"git branch -f {default} failed: {said}; {default} still holds the session's commits",
                         plain=f"The session is on its own branch, but I couldn't take it off {default}. {GIT_DETAIL}")]
    return [say.Line(f"{default} put back at {began[:7]}, where the session began",
                     plain=f"{default.capitalize()} is back to how it was before today's work.")]


# ------------------------------------------------------------------------------------------------- session brief

def cmd_brief(args, out):
    from vela import cli
    root = pathlib.Path(args.vault).resolve()
    today = cli.parse_today(args.today)[0]
    vault = cli.load_vault(root)
    resolver = say.Resolver(vault) if say.mode_of(args) == "for-lead" else None
    result = say.Result(BRIEF)
    review_comments(result, root, vault, sessiongit.is_read_copy(root))
    overdue_questions(result, vault, today)
    ready_to_decide(result, root, vault, today)
    next_steps(result, root, today)
    how_much(result, vault, today)
    return commands.emit(result, args, out, resolver)


def gather_comments(root, since):
    """(candidates, None), or (None, gh's words) when any gh call fails: a partial list would read as complete."""
    prs, why = sessiongit.gh_json(root, "pr", "list", "--state", "merged", "--search", f"merged:>={since}",
                                  "--json", "number,title,url", "--limit", "100")
    if why:
        return None, why
    found = []
    for pr in prs if isinstance(prs, list) else []:
        number = str(pr.get("number"))
        view, why = sessiongit.gh_json(root, "pr", "view", number, "--json", "comments,reviews")
        if why:
            return None, f"gh pr view {number}: {why}"
        line_comments, why = sessiongit.gh_json(root, "api", f"repos/{{owner}}/{{repo}}/pulls/{number}/comments")
        if why:
            return None, f"the line comments on PR {number}: {why}"
        found += sessions.review_candidates(pr, view, line_comments)
    return found, None


def review_comments(result, root, vault, reader):
    """START step 3. Not checked is said as not checked: `review_comments` is null then, never []."""
    result.data["review_comments"] = None
    if reader:
        result.lines.append(say.Line("review comments: not checked in a read copy (no gh)",
                                     plain="Review comments aren't checked in your copy."))
        return
    since = sessions.last_closed([page.meta for page in vault.sessions])
    if not since:
        result.data["review_comments"] = []
        result.lines.append(say.Line("review comments: no closed session yet, so no merged session PR to read",
                                     plain="No session has been closed yet, so there are no review comments to bring "
                                           "in."))
        return
    found, why = gather_comments(root, since)
    if why:
        result.exit = say.FAILED
        result.lines.append(say.Line(f"gh could not list merged PRs ({why}), so review comments were not checked.",
                                     plain="I couldn't reach GitHub, so I haven't checked for review comments since "
                                           "the last session."))
        return
    result.data.update(review_comments=found, review_comments_since=since)
    count = f"{len(found)} review comment{'s' if len(found) != 1 else ''}"
    result.lines.append(say.Line(f"review comments: {count} on PRs merged since {since} (--json lists them)",
                                 plain=f"{count} came in on pull requests merged since the last session; I'll offer "
                                       "each one as a note." if found else
                                       "No review comments came in since the last session."))


def overdue_questions(result, vault, today):
    """START step 4: each open question past its ask-by date, by its name, with its owner."""
    found = []
    for unknown in vault.unknowns:
        if unknown.fact("State") != "open" or not progress.overdue(unknown, today):
            continue
        name = vault.name_of(unknown.id)
        found.append({"id": unknown.id, "name": "" if name == unknown.id else name,
                      "owner": unknown.fact("Owner"), "ask_by": unknown.fact("Ask by")})
    result.data["overdue"] = found
    found.sort(key=lambda e: e["ask_by"] or "")
    grouped = len(found) > OVERDUE_SAID
    for n, entry in enumerate(found):
        spoken_name = entry["name"] or "An open question"
        when = sessions.date_in_words(entry["ask_by"], today_date(today))
        owner = say.person_words(entry["owner"]) if entry["owner"] else ""
        plain = f"{spoken_name} was due to be asked by {when}; {owner or 'nobody'} owns it."
        if grouped:  # one line for the lead: how many, and the oldest; the rest wait to be asked for
            plain = (f"{say.count_words(len(found), capital=True)} questions are past their ask-by date; the oldest is "
                     f"{spoken_name}, due {when}" + (f" with {owner}" if owner else ", and nobody owns it") +
                     f". Want the other {say.count_words(len(found) - 1)}?") if n == 0 else ""
        result.lines.append(say.Line(
            f"overdue: {entry['id']} {entry['name']}, owner {entry['owner'] or 'none'}, ask by {entry['ask_by']}",
            plain=plain))


def ready_to_decide(result, root, vault, today):
    """Items the lead said yes to in a session that can't decide (`decisions/ready.py`), not decided since: a grill
    opens with them."""
    from vela import decisions
    from vela.decisions import decide, ready, textedit
    from vela.edge import apply as disk
    staged = textedit.attach(decisions.Staged(vault, disk.reader(root)), today, [])
    found = ready.waiting([privaterecord.stub_meta(text) for _, _, text in sessiongit.folder_records(root)],
                          lambda ident: decide.already(staged, ident) is not None)
    for entry in found:
        entry["name"] = vault.name_of(entry["id"])
    result.data["ready_to_decide"] = found
    if found:
        names = [e["name"] if e["name"] != e["id"] else "an item" for e in found]
        one = len(found) == 1
        result.lines.append(say.Line(
            "ready to decide: " + ", ".join(f"{e['id']} (yes in {e['session']})" for e in found),
            plain=f"The lead already said yes to {join_names(names)}; a short grill can make "
                  f"{'it' if one else 'them'} decided, and a grill opens with {'it' if one else 'them'}."))


def join_names(names):
    return ", ".join(names[:-1]) + (" and " if len(names) > 1 else "") + names[-1]


OVERDUE_SAID = 2  # past this many overdue questions, the brief says how many and the oldest


def next_steps(result, root, today):
    """`vela next`'s lines, through its own command, so the brief never disagrees with it."""
    from vela import cli
    buffer = io.StringIO()
    cli.cmd_next(argparse.Namespace(vault=str(root), today=today), buffer)
    prefix = "vela next: "
    found = [line[len(prefix):] if line.startswith(prefix) else line.strip()
             for line in buffer.getvalue().splitlines() if line.strip()]
    result.data["next"] = found
    said = [_AS_OF.sub("", line).strip() for line in found]
    result.lines += [say.Line(f"next: {line}", plain=(f"Next I'd suggest this: {words_}" if n == 0 else f"Also: {words_}"))
                     for n, (line, words_) in enumerate(zip(found, said))]
    if said:
        result.answer = f"Next I'd suggest this: {said[0]}"


_AS_OF = re.compile(r"\s*As of \S+ \([^)]*\)\.")


def how_much(result, vault, today):
    """How much is still open, so the lead hears the size of the work before the first question (START step 5)."""
    rows = progress.grid(vault, today)
    mix = [sum(row.mix[i] for row in rows) for i in range(4)]
    questions = sum(1 for u in vault.unknowns if u.fact("State") == "open")
    result.data["open"] = {"apps": len(rows), "inkling": mix[0], "assumption": mix[1], "fact": mix[2],
                           "decided": mix[3], "open_questions": questions}
    parts = [f"{say.count_words(n)} {word}" for n, word in zip((mix[3], mix[1], mix[0], mix[2]),
                                                                ("decided", "assumed", "early ideas", "confirmed")) if n]
    apps = f"{say.count_words(len(rows), capital=True)} app{'s' if len(rows) != 1 else ''}"
    result.lines.append(say.Line(
        f"open: {len(rows)} apps; inkling {mix[0]}, assumption {mix[1]}, fact {mix[2]}, decided {mix[3]}; "
        f"{questions} open questions",
        plain=f"{apps}, with {say.names_said(parts) or 'nothing on them yet'}; {say.count_words(questions)} "
              f"question{'s are' if questions != 1 else ' is'} open."))

