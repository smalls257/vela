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
answers every question in one turn. Exit codes:

0  started (or, with `--resume`, back on the open session's branch);
1  refused: a reader copy asked for an owner's mode, a host with no working git (the reader path is said), an unknown
   mode, or `--answer` found none or several open challenge PRs (what `gh` returned is printed; never a guessed
   branch);
2  git or `gh` failed (their words are printed), or main couldn't be brought up to date;
3  needs the lead, nothing changed: open sessions exist (resume, close or `--new`), uncommitted changes the pull
   would overwrite, or the initiative has no name yet (the one naming question; `--title` answers it, `--unnamed`
   records that the lead declined).

`session brief` is START steps 3 and 4, read-only: review comments on PRs merged since the last closed session (as
candidate captures, in `--json`), the overdue open questions, `vela next`, and how much is still open. A `gh` failure
is a printed line and exit 2, and `review_comments` is null, never an empty list that reads as "no comments"
(Silent Fallback). Everything else in the brief still runs.
"""
import argparse
import datetime
import io
import pathlib

from vela import commands, progress, records, say, sessions
from vela.edge import hostprobe, sessiongit
from vela.edge.vaultgit import GitUnavailable

NAME = "session open"
START, BRIEF = "session start", "session brief"
READ_COPY = "This is a read copy, so I will not use git: your work stays in this folder and nothing is committed or sent."


def register(sub):
    session = sub.add_parser("session", help="the session record: start one, find the open one, brief the lead")
    verbs = session.add_subparsers(dest="session_command", metavar="{open,start,brief}")
    verbs.required = True
    opener = verbs.add_parser("open", help="the open session record(s), each with its branch, modes and date")
    opener.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    opener.add_argument("--switch", action="store_true",
                        help="switch to the open record's branch when exactly one is open (never guesses among several)")
    opener.add_argument("--id", default="", help="pick this open record among several (after an exit 3)")
    say.add_output_flags(opener)
    opener.set_defaults(func=cmd_open)
    register_start(verbs)
    register_brief(verbs)


def register_start(verbs):
    starter = verbs.add_parser("start", help="pull main, open the session's branch and record, and commit it; stops "
                                             "with the choices when open sessions, unsaved work or an unnamed "
                                             "initiative need the lead")
    starter.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    starter.add_argument("--mode", action="append", default=[], choices=sorted(sessions.MODE_NAMES),
                         help="the session's mode; repeat for a session that runs several (the first names it)")
    starter.add_argument("--topic", default="", help="two to four words from the lead's first message: the id's slug")
    starter.add_argument("--answer", default="", metavar="PR|ID",
                         help="answer a challenge: its PR number, or the challenged ID (matched by exact title suffix)")
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
    today = cli.parse_today(args.today)[0]
    resolver = lead_resolver(root) if say.mode_of(args) == "for-lead" else None
    plain = words(resolver)
    try:
        result = start(root, args, today, plain)
    except Stop as stop:
        result = stop.result
    except GitUnavailable as exc:
        result = say.Result(START, exit=say.FAILED, lines=[
            say.Line(f"vela: {exc}", plain=plain(f"Git failed while starting the session. Git said: {exc}"))])
    except OSError as exc:  # atomic.WriteFailed among them
        result = say.Result(START, exit=say.FAILED, lines=[
            say.Line(f"vela: couldn't write: {exc}", plain=f"I couldn't write the session's files: {exc}")])
    return commands.emit(result, args, out, resolver)


def start(root, args, today, plain):
    """START steps 1, 2 and 5 in order; every stop before the first change."""
    reader = sessiongit.is_read_copy(root)
    modes = requested_modes(args)
    refuse_request(args, modes, reader)
    try:
        host = sessiongit.read_json(root, hostprobe.HOST_FILE)
    except ValueError as exc:
        raise failed(f"vela: {exc}", "The record of what this host can do is broken, so I haven't started. Run "
                                     "/vela:where to check the host again.") from exc
    row, sentence = hostprobe.stance(host) if host is not None else ("", "")
    if not reader and row in ("no-git", "git-broken"):
        raise refused("no working git", sentence, "open the vault's own clone in Claude Code, or work as a reader "
                      "here (read, ask, find, explore, draft, then /vela:propose)",
                      "run /vela:where again if git works here now")
    said = [say.Line(f"host: {row}: {sentence}", plain=sentence)] if row == "no-send" else []
    if reader:
        return start_in_copy(root, args, today, modes, plain, said)
    return start_in_repo(root, args, today, modes, plain, said, host or {})


def requested_modes(args):
    asked = (["answer"] if args.answer else []) + list(args.mode)
    return list(dict.fromkeys(asked))


def refuse_request(args, modes, reader):
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
                      "pull request, which a read copy can't do. Send a proposal (/vela:propose) and the owner "
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
    lines = [say.Line(f"{count}; nothing changed. Resume one with --resume <id>, close it with /vela:close, or start "
                      "another with --new:",
                      plain=f"{count}, so I haven't started a new one. Resume it, close it now, or leave it open "
                            "and start a new one?")]
    for record, ask in zip(records, asks):
        old = " (more than 14 days old)" if ask["stale"] else ""
        lines.append(say.Line(f"- {describe(record)}{old}",
                              plain=f"- {spoken(record, plain, today_date(today))}"
                                    f"{', more than two weeks ago' if old else ''}."))
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
                    "changed.", plain=f"Bringing {base_words} up to date would overwrite your uncommitted changes to "
                                      f"{shown}. Commit them first, set them aside, or drop them?")
    return ask, line


def resume(root, found, wanted, reader, lines, today, plain):
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
    if result.exit == say.DONE:
        text = (root / record.path).read_text(encoding="utf-8")
        result.wrote.append(write_state(root, record.id, record.path, record.branch, list(record.modes), record.date,
                                        max(records.numbers_in(text), default=0)))
        result.data.update(id=record.id, path=record.path, branch=record.branch)
    return result


def write_state(root, record_id, path, branch, modes, started, last_capture=0):
    """`.vela/session.json`: which record `record add` writes to, and the highest capture number it handed out."""
    return sessiongit.write_state(root, {"id": record_id, "path": path, "branch": branch, "modes": modes,
                                         "started": started, "last_capture": last_capture})


def problem_lines(problems):
    return [say.Line(f"unreadable: {why}", plain="A session record has frontmatter that can't be read, so it isn't "
                                                 "counted.") for why in problems]


def config_of(root):
    from vela import cli
    try:
        return cli.load_config(root)
    except cli.ToolError as exc:
        raise failed(f"vela: {exc}", f"The vault's settings file can't be read, so I haven't started: {exc}") from exc


def start_in_copy(root, args, today, modes, plain, said):
    """A reader copy: the record is written in place and nothing runs git (START, "Owner or reader")."""
    open_records, problems = sessions.find_open(sessiongit.folder_records(root))
    lines = said + [say.Line(f"read copy: {READ_COPY}", plain=READ_COPY)] + problem_lines(problems)
    if args.resume:
        return resume(root, open_records, args.resume, True, lines, today, plain)
    if open_records and not args.new:
        asks, asked = open_choices(open_records, today, plain)
        raise Stop(say.Result(START, exit=say.NEEDS_LEAD, needs_lead=asks, lines=lines + asked))
    if args.title or sessions.is_unnamed(config_of(root)):
        lines.append(say.Line("read copy: naming the initiative is the owner's; .vela.yaml not changed.",
                              plain="The owner names the initiative, so I haven't changed its name here."))
    record_id = sessions.new_id(today, args.topic, lambda i: (root / "sessions" / f"{i}.md").exists())
    rel = f"sessions/{record_id}.md"
    wrote = [sessiongit.write_text(root, rel, sessions.record_text(record_id, sessions.title_for(modes, args.topic),
                                                                    today, modes))]
    wrote.append(write_state(root, record_id, rel, None, modes, today))
    lines.append(say.Line(f"started: {record_id} in this folder, modes: {', '.join(modes)}",
                          plain=f"Calling this one {record_id}."))
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
                  f"GitHub's command line failed ({why}), so I haven't started: an answer never starts on a guessed "
                  "branch.")


def not_one_challenge(why, prs, plain):
    shown = [say.Line(f"- #{pr.get('number')} {pr.get('title', '')} ({pr.get('headRefName', '?')})",
                      plain=plain(f"- {pr.get('title', '')}")) for pr in prs if isinstance(pr, dict)]
    return Stop(say.Result(START, exit=say.REFUSED, data={"gh_returned": prs}, lines=[
        say.Line(f"{why}; nothing changed. gh returned:" if shown else f"{why}; nothing changed. gh returned nothing.",
                 plain="I couldn't find exactly one open challenge for that, so I haven't started: an answer never "
                       "starts on a guessed branch." + (" GitHub listed:" if shown else ""))] + shown))


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
                        plain=f"This vault has no shared copy set up, so the session starts from this machine's "
                              f"{base_words}.")
    if how == "offline":
        return say.Line(f"host can't reach origin (.vela/host.json): {base_words} not pulled",
                        plain=f"The shared copy can't be reached from here, so this session starts from this "
                              f"machine's {base_words}, which may be behind.")
    return say.Line(f"git fetch origin failed: {words_}; starting from this machine's {base_words}",
                    plain=f"I couldn't reach the shared copy, so this session starts from this machine's "
                          f"{base_words}, which may be behind. Git said: {words_}")


def move_to(root, base, upstream, base_words):
    """Switch to `base` and fast-forward it to `upstream` (START step 1's `git switch main` and `git pull`)."""
    if sessiongit.current_branch(root) != base:
        local = sessiongit.ref_exists(root, f"refs/heads/{base}")
        ok, said = sessiongit.switch(root, base, remote_only=not local)
        if not ok:
            raise failed(f"git switch {base} failed: {said}",
                         f"I couldn't switch to {base_words}, so I haven't started. Git said: {said}")
    if upstream:
        ok, said = sessiongit.fast_forward(root, upstream)
        if not ok:
            raise failed(f"git merge --ff-only {upstream} failed: {said}; on {base} now, nothing else changed",
                         f"I couldn't bring {base_words} up to date, so I haven't started: the session would start "
                         f"from an old copy. Git said: {said}")


def start_in_repo(root, args, today, modes, plain, said, host):
    """The owner's start: every check, then the pull, the branch, the record and its commit."""
    config = config_of(root)
    pr, challenged = find_challenge(root, args.answer, plain) if args.answer else (None, "")
    open_records, problems = sessions.find_open(sessiongit.branch_records(root))
    lines = said + problem_lines(problems)
    if args.resume:
        return resume(root, open_records, args.resume, False, lines, today, plain)
    asks, asked = [], []
    if open_records and not args.new:
        asks, asked = open_choices(open_records, today, plain)
    if not args.title and not args.unnamed and sessions.is_unnamed(config):
        ask, line = naming_choice()
        asks.append(ask)
        asked.append(line)
    base = pr["headRefName"] if pr else "main"
    base_words = "the challenge's branch" if pr else "main"
    how, fetch_words = bring_in(root, host)
    upstream = f"origin/{base}" if how == "fetched" and sessiongit.ref_exists(root, f"refs/remotes/origin/{base}") \
        else ""
    known = [ref for ref in (f"refs/heads/{base}", f"refs/remotes/origin/{base}") if sessiongit.ref_exists(root, ref)]
    target = upstream or (known[0] if known else "")  # origin's copy from an earlier fetch still serves offline
    if not target:
        raise failed(f"no branch {base} here or on origin; nothing changed",
                     f"I can't find {base_words} here or in the shared copy, so I haven't started.", lines)
    lost = sessions.clobbered(sessiongit.dirty_paths(root), sessiongit.incoming_paths(root, target))
    if lost:
        ask, line = clobber_choice(lost, base_words)
        asks.append(ask)
        asked.append(line)
    if asks:
        raise Stop(say.Result(START, exit=say.NEEDS_LEAD, needs_lead=asks, lines=lines + asked))
    fresh = freshness_line(how, fetch_words, base_words)
    lines += [fresh] if fresh else []
    move_to(root, base, upstream, base_words)
    carried = sessions.carried(sessiongit.dirty_paths(root), [])
    return open_record(root, args, today, modes, challenged, base if pr else "", lines, carried)


def open_record(root, args, today, modes, challenged, on_branch, lines, carried):
    """START step 5: the id, the branch (an answer stays on its challenge's), the record, `Open session <id>`, then
    the initiative's name when the lead gave one, and `.vela/session.json`."""
    def taken(candidate):
        on_disk = (root / "sessions" / f"{candidate}.md").exists()
        return on_disk or (not on_branch and sessiongit.branch_taken(root, f"session/{candidate}"))

    record_id = sessions.answer_id(today, challenged, taken) if challenged else sessions.new_id(today, args.topic, taken)
    branch = on_branch or f"session/{record_id}"
    if not on_branch:
        ok, said = sessiongit.create_branch(root, branch)
        if not ok:
            raise failed(f"git switch -c {branch} failed: {said}",
                         f"I couldn't make the session's branch, so I haven't started. Git said: {said}", lines)
    rel = f"sessions/{record_id}.md"
    title = sessions.title_for(modes, args.topic, challenged)
    wrote = [sessiongit.write_text(root, rel, sessions.record_text(record_id, title, today, modes))]
    sessiongit.commit(root, f"Open session {record_id}", [rel])
    where = "on the challenge's branch, so the answer lands in the challenge's pull request" if on_branch else ""
    lines.append(say.Line(f"started: {record_id} on {branch}, modes: {', '.join(modes)}",
                          plain=f"Calling this one {record_id}" + (f"; it's {where}." if where else ".")))
    if carried:
        lines.append(say.Line(f"carried, unstaged: {', '.join(carried)}",
                              plain=f"Your edits to {', '.join(carried)} come with us, unstaged."))
    if args.title:
        yaml_text = (root / ".vela.yaml").read_text(encoding="utf-8")
        wrote.append(sessiongit.write_text(root, ".vela.yaml", sessions.with_title(yaml_text, args.title)))
        sessiongit.commit(root, "Name the initiative", [".vela.yaml"])
        lines.append(say.Line(f"named: title: {args.title}", plain=f"The initiative is called {args.title} now."))
    elif args.unnamed:
        lines.append(say.Line("unnamed: the lead declined to name the initiative",
                              plain='The dashboard will read "New initiative" until you give it a name.'))
    wrote.append(write_state(root, record_id, rel, branch, modes, today))
    return say.Result(START, lines=lines, wrote=wrote, data={"id": record_id, "path": rel, "branch": branch,
                                                             "modes": modes, "reader": False})


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
                                     plain="Review comments aren't checked in a read copy."))
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
                                     plain=f"GitHub's command line failed ({why}), so review comments weren't "
                                           "checked."))
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
    for entry in found:
        spoken_name = entry["name"] or "An open question"
        when = sessions.date_in_words(entry["ask_by"], today_date(today))
        result.lines.append(say.Line(
            f"overdue: {entry['id']} {entry['name']}, owner {entry['owner'] or 'none'}, ask by {entry['ask_by']}",
            plain=f"{spoken_name} was due to be asked by {when}; {entry['owner'] or 'nobody'} owns it."))


def next_steps(result, root, today):
    """`vela next`'s lines, through its own command, so the brief never disagrees with it."""
    from vela import cli
    buffer = io.StringIO()
    cli.cmd_next(argparse.Namespace(vault=str(root), today=today), buffer)
    prefix = "vela next: "
    found = [line[len(prefix):] if line.startswith(prefix) else line.strip()
             for line in buffer.getvalue().splitlines() if line.strip()]
    result.data["next"] = found
    result.lines += [say.Line(f"next: {line}") for line in found]


def how_much(result, vault, today):
    """How much is still open, so the lead hears the size of the work before the first question (START step 5)."""
    rows = progress.grid(vault, today)
    mix = [sum(row.mix[i] for row in rows) for i in range(4)]
    questions = sum(1 for u in vault.unknowns if u.fact("State") == "open")
    result.data["open"] = {"apps": len(rows), "inkling": mix[0], "assumption": mix[1], "fact": mix[2],
                           "decided": mix[3], "open_questions": questions}
    result.lines.append(say.Line(
        f"open: {len(rows)} apps; inkling {mix[0]}, assumption {mix[1]}, fact {mix[2]}, decided {mix[3]}; "
        f"{questions} open questions",
        plain=f"{len(rows)} app{'s' if len(rows) != 1 else ''}, with {sum(mix[:3])} of their items not decided yet "
              f"and {mix[3]} decided; {questions} open question{'s' if questions != 1 else ''}."))

