"""`vela check`: the parser, moved out of cli.py (Task 2) so tasks that extend it (13: `--for-lead` verdicts on
`--gate grill`; 21b: `--fix W326`) edit this file and not cli.py. The command itself is `cli.cmd_check`."""
from vela import schema


def register(sub):
    from vela import cli  # cli builds the parser, so it is loaded by the time this runs
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
    check.add_argument("--for-lead", action="store_true",
                       help="plain lines for the lead: each finding by page title, with no codes, no IDs and no fix lines")
    check.set_defaults(func=cli.cmd_check)
