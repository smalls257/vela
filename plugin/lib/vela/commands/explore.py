"""`planner explore`: the parser, moved out of cli.py (Task 2) so Task 21c (`explore --for-lead`) edits this file and
not cli.py. The command itself is `cli.cmd_explore`."""


def register(sub):
    from vela import cli  # cli builds the parser, so it is loaded by the time this runs
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
    explore.set_defaults(func=cli.cmd_explore)
