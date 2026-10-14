"""`planner handoff`: the parser, moved out of cli.py (Task 2) so Task 21h (`handoff preview`) edits this file and
not cli.py. The command itself is `cli.cmd_handoff`."""


def register(sub):
    from vela import cli  # cli builds the parser, so it is loaded by the time this runs
    hand = sub.add_parser("handoff", help="record what a team takes on when an app is handed over, or list what changed since")
    hand.add_argument("words", nargs="+", metavar="[verify] APP-id", help="APP-id: the app to hand off, which writes its handoff record; "
                                                                          "verify APP-id: list what changed since that app was handed off")
    hand.add_argument("--vault", default=".", help="vault root (default: current directory)")
    hand.add_argument("--today", help="date to record, YYYY-MM-DD (default: system date)")
    hand.add_argument("--commit", help="commit to record (default: git rev-parse --short HEAD)")
    hand.add_argument("--replace", action="store_true", help="replace the existing handoff record once the app's team accepts the changes")
    hand.set_defaults(func=cli.cmd_handoff)
