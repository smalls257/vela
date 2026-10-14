"""`planner where`: the parser, moved out of cli.py (Task 2) so Task 7 (`where --probe`) edits this file and not
cli.py. The command itself is `cli.cmd_where`."""


def register(sub):
    from planner import cli  # cli builds the parser, so it is loaded by the time this runs
    where = sub.add_parser("where", help="which planner program a skill would run, and why other places were passed over")
    where.add_argument("--vault", default=".", help="vault root or reader workspace (default: current directory)")
    where.add_argument("--plugin-root", default="", help="the value ${CLAUDE_PLUGIN_ROOT} had when the skill loaded")
    where.add_argument("--skill-dir", default="", help="the value ${CLAUDE_SKILL_DIR} had when the skill loaded")
    where.set_defaults(func=cli.cmd_where)
