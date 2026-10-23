"""`vela check`: the parser, moved out of cli.py (Task 2) so tasks that extend it (13: `--for-lead` verdicts on
`--gate grill`; 21b: `--fix W326`) edit this file and not cli.py. The command itself is `cli.cmd_check`.

Task 13: `check --gate grill --item X [--item Y] --for-lead|--json` prints each item's grill verdict from `gates.py`
(ready, or not ready with the plain reason and the one fix) instead of the W807 list. The plain `--gate grill` output
and its exit codes stay exactly what the skills already read, so nothing that parses W807 moves. `--json` prints only
those verdicts: on any other check it would be a flag that silently changes nothing (Silent Fallback), so it is refused.

The shell reads what the pure gate may not: the vault, the open session record (`sessions/*.md` in this folder, so a
reader copy runs no git), and the flow checker's record for the flows and slices named. Exit 0 every item ready, 1 some
not ready, 2 the tool failed.

Task 21b: `check --fix W326 [--json|--for-lead]` sets each flagged page's frontmatter `state` as W326 says and prints
what changed (close section 6). Why it is code: a page whose rows have moved on but whose own state has not reads as
unsettled to everyone, and there is one right answer, so the model never hand-edits a state line. What to set is
`w326fix`'s (pure); this shell runs the check, writes through `edge/atomic.py`, runs no git (so a reader copy is the
same, and says the change reaches the owner through a proposal), and checks the vault again: a new state brings its
own duties (a fact lists its sources, E304; a decided page cites its Decision), and saying "fixed" over a page that
check now fails would be a Silent Fallback. Any other code after `--fix` is refused (exit 1): only W326 has one right
answer. Exit 0 set (or nothing to set); 1 refused, or the new state left an error on a page it changed; 2 the tool
failed.
"""
import pathlib

from vela import gates, plainwords, roles, rules, say, schema, sessions, w326fix
from vela.edge import atomic


def register(sub):
    check = sub.add_parser("check", help="read-only check of the vault")
    check.add_argument("--vault", default=".", help="vault root (default: current directory)")
    check.add_argument("--today", help="the date to judge overdue questions by, YYYY-MM-DD (default: today)")
    check.add_argument("--gate", choices=schema.GATES,
                       help="epics: before calling the epics finished, fail on anything no epic builds and on high-priority "
                            "questions nobody has dealt with; shape: as shaping ends, warn on questions still answered by "
                            "assumption; grill: before a grill, warn on open questions that hold up the items named with --item")
    check.add_argument("--item", action="append", help="with --gate grill: the ID of an item the grill will decide; repeat for each")
    check.add_argument("--all", action="store_true",
                       help="with --gate grill: gate every item still waiting to be decided (ready ones listed first), "
                            "instead of naming each with --item")
    check.add_argument("--app", help="with --gate epics: check only this app and the things on its handoff list (give its ID, "
                                     "like APP-booking); other apps, and the check that every requirement has an app, are skipped")
    check.add_argument("--fix", metavar="CODE",
                       help="W326 only: set each page's state as W326 says (a page whose rows have all moved on reads "
                            "as unsettled until its own state follows) and print what changed; any other code is refused")
    group = check.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true",
                       help="with --gate grill --item: each item's verdict as JSON (id, ready, reasons, fix, override, "
                            "overridden, owed), for the skill to reason over; with --fix W326: what changed")
    group.add_argument("--for-lead", action="store_true",
                       help="plain lines for the lead: each finding by page title, with no codes, no IDs and no fix lines; "
                            "with --gate grill --item, whether each item is ready to decide and the one thing that would "
                            "make it ready")
    say.add_more_flag(check)
    check.set_defaults(func=run)


def run(args, out):
    from vela import cli
    if args.fix is not None:
        return fix(args, out)
    if args.all:
        everything(args)
    grill_items = args.gate == "grill" and bool(args.item)
    if args.json and not grill_items:
        raise cli.ToolError("--json prints the grill verdicts (or, with --fix W326, what changed), so it goes with "
                            "--gate grill --item <ID> or --fix W326.")
    if grill_items and say.mode_of(args) != "default":
        return verdicts(args, out)
    return cli.cmd_check(args, out)


def everything(args):
    """`--all`: fill --item with every candidate, so one call answers "what is ready to decide?"."""
    from vela import cli
    if args.gate != "grill" or args.item:
        raise cli.ToolError("--all gates every item waiting to be decided, so it goes with --gate grill and no --item.")
    vault = cli.load_vault(pathlib.Path(args.vault).resolve())
    args.item = gates.candidates(vault)
    if not args.item:
        raise cli.ToolError("No item is waiting to be decided, so there is nothing for a grill to gate.")


def open_record_text(root):
    """(record text or None, note): the notes of the one open session in this folder. None with a note when there are
    several, or when the notes are not on this machine, so answers captured this session are listed again rather than
    guessed from the wrong record or an empty one."""
    from vela.edge import sessiongit
    found, _ = sessions.find_open(sessiongit.folder_records(root))
    if len(found) == 1:
        text = sessiongit.private_text(root, found[0].id)
        if text is None:
            return None, "This session's notes are not on this machine, so questions answered this session are still listed."
        return text, ""
    if len(found) > 1:
        return None, (f"{len(found)} sessions are open here, so questions answered this session are still listed.")
    return None, ""


def verdicts(args, out):
    from vela import cli, commands
    root = pathlib.Path(args.vault).resolve()
    today, _ = cli.parse_today(args.today)
    vault = cli.load_vault(root)
    items = cli.gate_items(vault, args.gate, args.item)
    cli.gate_app(vault, args.gate, args.app)
    record, note = open_record_text(root)
    keys = sorted({key for item in items for key in gates.flow_keys(vault, item)})
    flows, warning = cli.recorded_standings(root, vault, keys, today) if keys else ({}, "")
    found = [gates.verdict(vault, record, item, today, flows=flows) for item in items]
    notes = [n for n in (note, warning and f"The flow check's record could not be read, so flows read as not checked "
                                           f"({warning}).") if n]
    return commands.emit(gates.report(vault, found, notes), args, out, say.Resolver(vault))


# ------------------------------------------------------------------------------------------------ --fix W326

def fix(args, out):
    from vela import cli, commands
    refused = fix_refusal(args)
    if refused is not None:
        return commands.emit(refused, args, out, say.Resolver())
    root = pathlib.Path(args.vault).resolve()
    today, _ = cli.parse_today(args.today)
    vault = cli.load_vault(root)
    resolver = say.Resolver(vault)
    before = rules.check(vault, today)
    try:
        changes = w326fix.plan(before, {page.path: (page.id, page.text) for page in vault.pages})
        files = w326fix.rewrite(changes, {page.path: page.text for page in vault.pages})
    except w326fix.FixDrift as exc:
        raise cli.ToolError(str(exc)) from exc
    except w326fix.NoStateLine as exc:
        raise cli.ToolError(f"check --fix W326: {exc}; set it by hand. Nothing was changed.") from exc
    result = say.Result("check --fix", data={"changed": [c.as_json() for c in changes], "left": []})
    if not changes:
        result.lines = [say.Line("vela check --fix W326: nothing to change; every page's state already follows its rows.",
                                 "Every page's status already matches what's on it, so I haven't changed anything.")]
        return commands.emit(result, args, out, resolver)
    try:
        atomic.write_all_atomic({root / path: text for path, text in files.items()})
    except atomic.WriteFailed as exc:
        written = ", ".join(str(p) for p in exc.written) or "none"
        print(f"vela check --fix W326: could not write: {exc}. Written: {written}.", file=out)
        return say.FAILED
    result.wrote = [c.path for c in changes]
    count = f"{len(changes)} page{'' if len(changes) == 1 else 's'}"
    said = f"{say.count_words(len(changes))} page{'' if len(changes) == 1 else 's'}"
    result.lines = [say.Line(f"vela check --fix W326: set the state of {count}.", f"I updated the status of {said}.")]
    result.lines += [changed_line(c, resolver) for c in changes]
    left = left_on(root, today, before, result.wrote)
    result.data["left"] = [{"path": f.path, "line": f.line, "code": f.code, "message": f.message} for f in left]
    if left:
        pages = len({f.path for f in left})  # voice audit row 223: a count before the list, not "a little more"
        result.lines.append(say.Line("Left on the pages it changed (the new state's own duties):",
                                     f"{say.count_words(pages, capital=True)} of those pages now "
                                     f"need{'s' if pages == 1 else ''} a little more. Each one says what:"))
        result.lines += [left_line(f, resolver) for f in left]
    if any(f.is_error for f in left):
        result.exit = say.REFUSED
    if is_reader_copy(root):
        result.lines.append(say.Line("This is a reader copy: no git runs here; the change reaches the owner through a "
                                     "proposal.", say.YOUR_COPY_PROPOSAL))  # voice audit row 215
    return commands.emit(result, args, out, resolver)


def fix_refusal(args):
    """A Result refusing this `--fix`, or None. Only W326 has one right answer; and --fix inside a gate or with items
    would leave unclear which check it answered."""
    code = args.fix.strip().upper()
    if code not in w326fix.FIXABLE:
        result = say.Result("check --fix", exit=say.REFUSED, data={"code": args.fix})
        result.refusals.append(say.Refusal(
            "fix", "I can only fix one kind of problem by myself: a page whose status hasn't caught up with what's on "
                   "it.",  # voice audit row 222
            f"--fix takes W326 only; fix {args.fix} by hand as its Fix line says.",
            "Edit the page by hand; nothing here stops that.", waiver=""))  # no rule to set aside, only a limit
        return result
    if args.gate or args.item or args.app:
        result = say.Result("check --fix", exit=say.REFUSED, data={"code": code})
        result.refusals.append(say.Refusal(
            "fix", "Setting page states runs on its own, not inside another check.",
            "Run `vela check --fix W326` with no --gate, --item or --app, then the gate you wanted.",
            "Run the two commands one after the other."))
        return result
    return None


def changed_line(change, resolver):
    title = resolver.page_title(pathlib.PurePosixPath(change.path).stem) or resolver.name(change.page)
    # voice audit row 214: not "rows", and the state said in words ("assumption" is "not decided yet")
    before, after = plainwords.state_word(change.before), plainwords.state_word(change.after)
    return say.Line(f"{change.path}:{change.line}: state: {change.before} -> {change.after} ({change.why})",
                    f"{title} is now marked {after}, to match what's on it. It said {before} before.")


def left_on(root, today, before, paths):
    """Findings on the changed pages that were not there before the fix, from a fresh read of the vault."""
    from vela import cli
    seen = {(f.path, f.code, f.message) for f in before}
    after = rules.check(cli.load_vault(root), today)
    return [f for f in after if f.path in paths and (f.path, f.code, f.message) not in seen]


def left_line(finding, resolver):
    page = resolver.vault.page(pathlib.PurePosixPath(finding.path).stem)
    title = resolver.page_title(page.name) if page is not None else None
    message = finding.message.replace(f"{title} ({page.id})", title) if title else finding.message
    plain = message if title and message.startswith(title) else f"{title or 'That page'}: {message}"
    return say.Line(f"  {finding.format()}", resolver.plain(plain))


def is_reader_copy(root):
    """The rule `roles` applies, from the disk alone: a reader copy has a workspace file and no git."""
    facts = roles.Facts(git_here=(root / ".git").exists(), has_workspace=(root / ".vela" / "workspace.json").is_file())
    return facts.has_workspace and not facts.git_here and roles.decide(facts).role == roles.READER
