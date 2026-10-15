"""`vela handoff`: the parser, moved out of cli.py (Task 2), and `vela handoff preview APP` (Task 21h).

`vela handoff APP` and `vela handoff verify APP` are still `cli.cmd_handoff`, unchanged. `preview` is dispatched here:
it lists what handing the app over would leave unmet (the checklist, what is not settled, each slice's recorded flow
check; `handoffpreview.py` says why each comes from where) and writes nothing, so a reader copy can run it too.

The output flags (`--json`, `--for-lead`) belong to the preview and to verify (challenge relays what changed since an
app was accepted, so verify says it through say too). On the handoff itself they would be read and ignored, a Silent
Fallback where a skill asks for plain lines and gets IDs, so they are refused there instead; so are `--commit` and
`--replace` on the preview, which records nothing.
"""
import pathlib

from vela import say

HELP_WORDS = ("APP-id: the app to hand off, which writes its handoff record; "
              "verify APP-id: list what changed since that app was handed off; "
              "preview APP-id: list what handing it over would leave unmet, writing nothing")


def register(sub):
    from vela import cli  # cli builds the parser, so it is loaded by the time this runs
    hand = sub.add_parser("handoff", help="record what a team takes on when an app is handed over, list what changed "
                                          "since, or preview what a handoff would leave unmet")
    hand.add_argument("words", nargs="+", metavar="[verify|preview] APP-id", help=HELP_WORDS)
    hand.add_argument("--vault", default=".", help="vault root (default: current directory)")
    hand.add_argument("--today", help="date to record, YYYY-MM-DD (default: system date)")
    hand.add_argument("--commit", help="commit to record (default: git rev-parse --short HEAD)")
    hand.add_argument("--replace", action="store_true", help="replace the existing handoff record once the app's team accepts the changes")
    say.add_output_flags(hand)
    hand.set_defaults(func=run, handoff=cli.cmd_handoff)


def run(args, out):
    from vela import cli
    if args.words[0] == "preview":
        return preview(args, out)
    if args.words[0] == "verify" and (args.json or args.for_lead):
        if len(args.words) != 2:
            raise cli.ToolError("Write vela handoff verify <APP-id>.")
        from vela import commands
        root = pathlib.Path(args.vault).resolve()
        result, vault = cli.handoff_verify_result(root, args.words[1])
        return commands.emit(result, args, out, say.Resolver(vault))
    if args.json or args.for_lead:
        flag = "--json" if args.json else "--for-lead"
        raise cli.ToolError(f"{flag} is for vela handoff preview and verify only; the handoff prints its own lines.")
    return args.handoff(args, out)


def preview(args, out):
    """List the handoff's unmet checklist, its not-settled items and each slice's recorded flow check. Exit 0 when the
    checklist is met, 1 when it isn't, 2 when the tool failed."""
    from vela import cli, commands, handoffpreview, slices
    if len(args.words) != 2:
        raise cli.ToolError("Write vela handoff preview <APP-id>.")
    for flag, given in (("--commit", args.commit), ("--replace", args.replace)):
        if given:
            raise cli.ToolError(f"vela handoff preview writes nothing, so {flag} has nothing to do. Leave it off, or run "
                                f"vela handoff {args.words[1]} to write the record.")
    root = pathlib.Path(args.vault).resolve()
    today, _ = cli.parse_today(args.today)
    vault = cli.load_vault(root)
    app = cli.handoff_app(vault, args.words[1])
    taking_part = slices.for_app(vault, slices.read_slices(vault), app)
    standings, warning = cli.recorded_standings(root, vault, [s.key for s in taking_part], today)
    found = handoffpreview.preview(vault, app, taking_part, standings, warning)
    resolver = say.Resolver(vault)
    return commands.emit(handoffpreview.result(found, resolver), args, out, resolver)
