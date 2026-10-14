"""`vela check`: the parser, moved out of cli.py (Task 2) so tasks that extend it (13: `--for-lead` verdicts on
`--gate grill`; 21b: `--fix W326`) edit this file and not cli.py. The command itself is `cli.cmd_check`.

Task 13: `check --gate grill --item X [--item Y] --for-lead|--json` prints each item's grill verdict from `gates.py`
(ready, or not ready with the plain reason and the one fix) instead of the W807 list. The plain `--gate grill` output
and its exit codes stay exactly what the skills already read, so nothing that parses W807 moves. `--json` prints only
those verdicts: on any other check it would be a flag that silently changes nothing (Silent Fallback), so it is refused.

The shell reads what the pure gate may not: the vault, the open session record (`sessions/*.md` in this folder, so a
reader copy runs no git), and the flow checker's record for the flows and slices named. Exit 0 every item ready, 1 some
not ready, 2 the tool failed.
"""
import pathlib

from vela import gates, say, schema, sessions


def register(sub):
    check = sub.add_parser("check", help="read-only check of the vault")
    check.add_argument("--vault", default=".", help="vault root (default: current directory)")
    check.add_argument("--today", help="the date to judge overdue questions by, YYYY-MM-DD (default: today)")
    check.add_argument("--gate", choices=schema.GATES,
                       help="epics: before calling the epics finished, fail on anything no epic builds and on high-priority "
                            "questions nobody has dealt with; shape: as shaping ends, warn on questions still answered by "
                            "assumption; grill: before a grill, warn on open questions that hold up the items named with --item")
    check.add_argument("--item", action="append", help="with --gate grill: the ID of an item the grill will decide; repeat for each")
    check.add_argument("--app", help="with --gate epics: check only this app and the things on its handoff list (give its ID, "
                                     "like APP-booking); other apps, and the check that every requirement has an app, are skipped")
    group = check.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true",
                       help="with --gate grill --item: each item's verdict as JSON (id, ready, reasons, fix, override, "
                            "overridden, owed), for the skill to reason over")
    group.add_argument("--for-lead", action="store_true",
                       help="plain lines for the lead: each finding by page title, with no codes, no IDs and no fix lines; "
                            "with --gate grill --item, whether each item is ready to decide and the one thing that would "
                            "make it ready")
    check.set_defaults(func=run)


def run(args, out):
    from vela import cli
    grill_items = args.gate == "grill" and bool(args.item)
    if args.json and not grill_items:
        raise cli.ToolError("--json prints the grill verdicts, so it goes with --gate grill --item <ID>.")
    if grill_items and say.mode_of(args) != "default":
        return verdicts(args, out)
    return cli.cmd_check(args, out)


def open_record_text(root):
    """(record text or None, note): the one open session record in this folder. None with a note when there are
    several, so answers captured this session are listed again rather than guessed from the wrong record."""
    from vela.edge import sessiongit
    found, _ = sessions.find_open(sessiongit.folder_records(root))
    if len(found) == 1:
        return (root / found[0].path).read_text(encoding="utf-8"), ""
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
