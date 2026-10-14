"""`vela questions`: the parser, moved out of cli.py (Task 2) so Task 20 (`questions --digest --session`) edits
this file and not cli.py. The command itself is `cli.cmd_questions`."""


def register(sub):
    from vela import cli  # cli builds the parser, so it is loaded by the time this runs
    ques = sub.add_parser("questions", help="the questions the catalog says this vault owes, and where each stands")
    ques.add_argument("--vault", default=".", help="vault root (default: current directory)")
    ques.add_argument("--json", action="store_true", help="print JSON instead of text")
    ques.add_argument("--area", help="only this area of the catalog, such as FIN")
    ques.add_argument("--open", action="store_true", help="list only copies with no row, an open row, an invalid row or an asked row")
    ques.add_argument("--subject", help="only copies about this subject, such as APP-booking")
    view_of = ques.add_mutually_exclusive_group()
    view_of.add_argument("--digest", action="store_true",
                         help="the undisposed and asked copies grouped by entry and ranked, high and blocking first")
    ques.add_argument("--all", action="store_true",
                      help="with --digest: every line in full, not only the high and blocking ones")
    view_of.add_argument("--stats", action="store_true", help="how often each entry ends not-applicable in this vault")
    ques.set_defaults(func=cli.cmd_questions)
