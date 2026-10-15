"""`vela explore [--json|--for-lead]`: the parser, moved out of cli.py (Task 2), and the plain build report (Task 21c).

The build itself is `cli.cmd_explore`, unchanged: the default output is exactly what it prints, for the developer and
for tests. `--for-lead` and `--json` wrap it. The build's report lines name apps by ID, quote check codes and open the
summary with the initiative's ID; explore/SKILL.md used to ask the model to put each into plain words, so raw lines
reached the lead (a Leaky Narrative). `explorereport` holds those words now, and `--for-lead` prints them through
say's leak check, which fails the command (exit 2, "vela bug") if an ID or code survives.

`--serve` with `--for-lead` is refused (exit 1, nothing built): serving keeps the run going and prints as it goes, so
there is no finished report to put into words. Build with `--for-lead`, then serve without it.
"""
import io
import pathlib

from vela import commands, explorereport, say


def register(sub):
    explore = sub.add_parser("explore", help="build the vault explorer, one offline HTML page of the whole initiative")
    explore.add_argument("vault", nargs="?", default=".", help="vault root (default: current directory)")
    explore.add_argument("-o", "--out", help="HTML file to write (default: <vault>/dashboard.html)")
    explore.add_argument("--today", help="the date due windows count from, YYYY-MM-DD (default: system date)")
    explore.add_argument("--theme", default="console", help="the theme the page opens in: console, graphite, daylight or vaporwave")
    explore.add_argument("--design", action="append", default=[], metavar="APP-x=PATH",
                         help="a team's technical design for an app, shown in its 'Inside this app' view; repeat for each app")
    explore.add_argument("--breakdown", action="append", default=[], metavar="APP-x=PATH",
                         help="a team's work breakdown (docs/plan/<slug>-breakdown.md) for an app, for its Build plan; repeat for each app")
    explore.add_argument("--assets", help="an assets.config.json whose provider's art is inlined (default: the builtin art)")
    explore.add_argument("--selftest", action="store_true",
                         help="for developers: bundle the dashboard's own checks, so opening it with #selftest runs them (about 120 KB)")
    explore.add_argument("--serve", action="store_true",
                         help="then serve the page on this machine only, with Ask Claude on; opens the browser, Ctrl-C stops")
    explore.add_argument("--port", type=int, default=None, help="with --serve, the port (default: one derived from the vault, so the browser finds what it saved; 0 asks for any free one)")
    explore.add_argument("--model", choices=["haiku", "sonnet"], default="haiku",
                         help="with --serve, the model that answers questions (default: haiku; the page's Think harder asks sonnet)")
    explore.add_argument("--no-open", action="store_true", help="with --serve, do not open the browser")
    say.add_output_flags(explore)
    explore.set_defaults(func=cmd_explore)


SERVE_REFUSAL = say.Refusal(  # the model's own slip in how it asked: never the lead's to hear
    rule="serve-for-lead", audience=say.MODEL,
    plain=("Serving the page keeps this run going, so there's no finished build report to put into plain words. "
           "Build it with --for-lead first, then serve it without --for-lead."),
    fix="Build with `vela explore --for-lead` and relay it, then serve with `vela explore --serve` and relay its lines.",
    override="`vela explore --serve` alone serves the page and prints the raw build lines.")


def lead_resolver(root):
    """A resolver over the vault when it loads; a folder that is not a vault still gets the kind words."""
    from vela import cli
    try:
        return say.Resolver(cli.load_vault(root))
    except cli.ToolError:
        return say.Resolver()


def cmd_explore(args, out):
    from vela import cli  # cli builds the parser, so it is loaded by the time this runs
    if say.mode_of(args) == "default":
        return cli.cmd_explore(args, out)
    if args.serve:
        return commands.emit(say.Result("explore", exit=say.REFUSED, refusals=[SERVE_REFUSAL]), args, out)
    printed = io.StringIO()
    code = cli.cmd_explore(args, printed)
    resolver = lead_resolver(pathlib.Path(args.vault).resolve())
    report = [{"kind": explorereport.kind_of(entry), "text": entry, "plain": explorereport.lead_line(entry, resolver)}
              for entry in explorereport.entries(printed.getvalue())]
    summary = next((r["plain"] for r in report if r["kind"] == "summary"), "")
    result = say.Result("explore", exit=code, lines=[say.Line(r["text"], r["plain"]) for r in report],
                        data={"report": report}, answer=summary)  # the answer first: the page is built
    return commands.emit(result, args, out, resolver)
