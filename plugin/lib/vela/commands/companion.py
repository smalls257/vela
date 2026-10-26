"""`vela companion session|explain|prepare`: the panels beside a chat.

The Violation this exists to prevent is a Distributed Monolith of meaning: the terminal mod, the one-line band and the
Cowork artifact each deciding for themselves what a session decided. This command builds one dict and writes three
renders of it into `.vela/companion/` (the JSON a mod reads, the Markdown a terminal shows, the HTML Cowork
publishes). Nothing else in the plugin holds a plan rule or a word of wording for a panel.

It runs after every vault write, so it starts through `commands/fast.py` and never imports `vela.cli`.

Exit codes, as every vela command means them: 0 drawn; 1 nothing to draw (no session is open here; any old panel is
removed so it can't keep showing a closed session); 2 the notes or the tool failed (the files written say so); 3 the
lead picks (several sessions are open; `--json` carries `needs_lead`).
"""
import datetime
import json
import pathlib

from vela import companiondesign, companionexplain, companionplan, companionrender, companionseen, companionsession, errors
from vela.edge import companionstore, plans, vaultfiles

NO_SESSION = "No session is open in this folder."
NOT_EXPLAINED = "Nothing has been explained yet."
OLD_ANSWER = "The last answer was written by an older vela and can't be redrawn. Ask the question again."
NO_VIEW_GIVEN = "Say which view answers it, with --view."


def register(sub):
    top = sub.add_parser("companion", help="the panels beside a chat: what this session decided, and what a question needs")
    verbs = top.add_subparsers(dest="companion_command", metavar="{session,explain,prepare}")
    verbs.required = True
    session = verbs.add_parser("session", help="what this session is about, what it decided, what's open and what's next")
    common(session)
    session.set_defaults(func=cmd_session)
    explain = verbs.add_parser("explain", help="a question about the plan, answered from vela's own numbers, with what the plan doesn't know")
    explain.add_argument("--view", choices=companionexplain.VIEWS, help="which view answers it (not needed with --last)")
    explain.add_argument("--about", default="", help="the flow or page it is about, by name (with --view flow or page)")
    explain.add_argument("--as", dest="as_handle", default="", metavar="@HANDLE", help="who is asking, when vela can't tell")
    explain.add_argument("--last", action="store_true", help="answer the last question asked again, with today's code and numbers")
    common(explain)
    explain.set_defaults(func=cmd_explain)
    prepare = verbs.add_parser("prepare", help="make the plan digest the explain views read, without drawing the dashboard")
    prepare.add_argument("--vault", default=".", help="vault root (default: current directory)")
    prepare.add_argument("--today", help="today's date, YYYY-MM-DD (default: the system date)")
    prepare.set_defaults(func=cmd_prepare)


def common(parser):
    parser.add_argument("--vault", default=".", help="vault root (default: current directory)")
    parser.add_argument("--find-up", action="store_true", help="find the vault by walking up from --vault")
    parser.add_argument("--json", action="store_true", help="print the JSON")
    parser.add_argument("--md", action="store_true", help="print the Markdown (the default)")
    parser.add_argument("--html", nargs="?", const="", metavar="FILE",
                        help="the Cowork publish path: also write the HTML to FILE, and record which capture it drew")
    parser.add_argument("--today", help="today's date, YYYY-MM-DD (default: the system date)")
    parser.add_argument("--now", help="the time, HH:MM (default: the system clock)")


def clock(args):
    stamp = datetime.datetime.now()
    return args.today or stamp.date().isoformat(), getattr(args, "now", None) or stamp.strftime("%H:%M")


def root_of(args):
    start = pathlib.Path(args.vault).resolve()
    if not args.find_up:
        return start
    found = plans.plan_above(start)
    return found if found is not None else start


def render_forms(root, data):
    """(markdown, html) of the dict, after its band and drawings are filled in. The palette is the dashboard's, so the
    panel and the dashboard share one room."""
    companionrender.with_renders(data)
    return companionrender.markdown(data), companionrender.html(data, companionstore.palette())


def finish(args, out, root, data, exit_code):
    data["vault"] = str(root)
    markdown, html = render_forms(root, data)
    published = args.html is not None
    companionstore.write_forms(root, data["kind"], data, markdown, html, html_out=args.html or None, published=published)
    if args.json:
        print(json.dumps(data, indent=1, ensure_ascii=False), file=out)
    elif published:
        print(data["files"]["html"], file=out)
    else:
        print(markdown, end="", file=out)
    return exit_code


def cmd_session(args, out):
    root = root_of(args)
    today, now = clock(args)
    try:
        stub, notes, problems = companionstore.open_session(root)
    except companionstore.NoSession:
        return design_or_nothing(args, out, root, today, now)
    except companionstore.Several as several:
        return said_several(args, out, several.records)
    if notes is None:
        data = companionsession.unreadable(stub, " ".join(problems), today, now)
        return finish(args, out, root, data, 2)
    index = companionstore.page_index(root)
    inputs = gather(root, stub, notes, index, today, now)
    try:
        data = companionsession.build(inputs[0])
    except ValueError as exc:
        data = companionsession.unreadable(stub, f"The session's notes couldn't be read ({exc}).", today, now)
        return finish(args, out, root, data, 2)
    data["warnings"] += inputs[1] + problems
    return finish(args, out, root, data, 0)


def gather(root, stub, notes, index, today, now):
    """(Inputs, warnings): the edge reads a session panel needs, each failure said as a warning, never as nothing."""
    from vela.edge import vaultgit
    warnings = []
    try:
        touched = companionstore.touched(root, str(stub.get("start_commit", "")), session_started(root, stub))
    except vaultgit.GitUnavailable:  # git's own words carry hashes and paths a lead must not read; the panel says it plainly
        touched = None
    map_text, why = companionstore.map_next(root, str(stub.get("id", "")))
    if why:
        warnings.append(why)
    return companionsession.Inputs(stub, notes, index, touched, map_text, companionstore.plan_next(root), today, now), warnings


def session_started(root, stub):
    """When the session began, as seconds since the epoch: the stub's own file time, for a copy with no git."""
    path = pathlib.Path(root) / f"sessions/{stub.get('id', '')}.md"
    return path.stat().st_mtime if path.is_file() else 0.0


def said_several(args, out, records):
    listed = [{"id": r.id, "title": r.title, "date": r.date} for r in records]
    if args.json:
        print(json.dumps({"needs_lead": listed, "message": "More than one session is open here."}, indent=1), file=out)
    else:
        print("More than one session is open here. Which one is this?", file=out)
        for r in records:
            print(f"  {r.title}", file=out)
    return 3


def design_or_nothing(args, out, root, today, now):
    """No session record is open: on a `design/<slug>` branch the design session is the session (it opens no record);
    anywhere else there is nothing to draw, and an old panel is removed so it can't keep showing a closed session."""
    found = companionstore.design_session(root)
    if found is None:
        companionstore.clear_forms(root, "session")
        print(f"{NO_SESSION} {companionstore.why_no_design(root)}", file=out)
        return 1
    data = companiondesign.build(found["branch"], found["record"], found["doc_text"], found["design"], found["doc_rel"],
                                 found["touched"], today, now)
    return finish(args, out, root, data, 0)


def prepare(root, today):
    """Load the plan, run the dashboard's own extract (no page drawn) and write the digest. Seconds on a big plan, which
    is why it happens once per open and not once per question. Returns the digest."""
    from vela import cli
    from vela.explorer import build
    vault = cli.load_vault(root)
    data = build.extract(vault, root, today)
    return companionstore.prepare_digest(vault, root, today, data, head_of(root))


def head_of(root):
    from vela.edge import vaultgit
    try:
        return vaultgit.head_short(root, "HEAD")
    except vaultgit.GitUnavailable:
        return ""


def cmd_prepare(args, out):
    import time
    root = pathlib.Path(args.vault).resolve()
    today = clock(args)[0]
    started = time.perf_counter()
    prepare(root, today)
    print(f"Prepared the plan's data in {time.perf_counter() - started:.1f} s.", file=out)
    return 0


def current_digest(root, today):
    """(digest, warnings): the stored digest when it still matches the plan; otherwise prepared again, and said. It never
    serves an old digest as current, which would put stale numbers in the chat."""
    import time
    why = ""
    try:
        digest = companionstore.plan_digest(root)
    except errors.ToolError:
        digest, why = None, "the stored one couldn't be read"
    if digest is not None and digest.get("version") == companionplan.VERSION \
            and digest.get("fingerprint") == vaultfiles.fingerprint(root):
        return digest, []
    started = time.perf_counter()
    prepare(root, today)
    took = f"{time.perf_counter() - started:.1f} s"
    reason = why or ("there was none yet" if digest is None else "the plan had changed")
    return companionstore.plan_digest(root), [f"Prepared the plan's data again in {took}; {reason}."]


def explain_files():
    base = companionstore.FOLDER
    return {"json": f"{base}/explain.json", "md": f"{base}/explain.md", "html": f"{base}/explain.html"}


def ask_again(args, root):
    """Sets the view, flow or page and asker of the last question on `args` and returns "", or returns why it can't. The
    stored answer is never replayed: a file an older vela wrote has no blocks, and a panel drawn from it would be blank
    with nothing to say why (Silent Fallback). Asking again with the current code always gives current blocks."""
    last = companionstore.folder(root) / "explain.json"
    if not last.is_file():
        return NOT_EXPLAINED
    try:
        held = json.loads(last.read_text(encoding="utf-8"))
    except ValueError:
        return OLD_ANSWER
    if not isinstance(held, dict) or held.get("version") != companionexplain.VERSION or held.get("view") not in companionexplain.VIEWS:
        return OLD_ANSWER
    args.view, args.about = held["view"], held.get("about", "")
    args.as_handle = args.as_handle or held["viewer"]["handle"]
    return ""


def said_message(args, out, message):
    """A sentence from vela and nothing to draw (exit 1); with --json it is the `message` the mod shows as its problem."""
    print(json.dumps({"message": message}, indent=1, ensure_ascii=False) if args.json else message, file=out)
    return 1


def since_of(root, digest, today, warnings):
    """The "Since ..." line, and the rolled record written back. A record that can't be read starts over, and says so."""
    try:
        held = companionstore.seen(root)
    except errors.ToolError as exc:
        held = {}
        warnings.append(f"{exc} I started the comparison again.")
    rolled = companionseen.roll(held, companionseen.snapshot(digest, today))
    if rolled != held:
        companionstore.write_seen(root, rolled)
    return companionseen.since_line(rolled.get("previous"), rolled["current"])


def cmd_explain(args, out):
    root = root_of(args)
    today = clock(args)[0]
    if args.last:
        refused = ask_again(args, root)
        if refused:
            return said_message(args, out, refused)
    elif not args.view:
        return said_message(args, out, NO_VIEW_GIVEN)
    digest, warnings = current_digest(root, today)
    handle, role = companionstore.viewer(root)
    viewer = companionexplain.Viewer(("@" + args.as_handle.lstrip("@")) if args.as_handle else handle, role)
    since = since_of(root, digest, today, warnings)
    try:
        data = companionexplain.explain(digest, args.view, args.about, viewer, since, today)
    except companionexplain.Unknown as exc:
        return said_unknown(args, out, exc)
    except companionexplain.NeedsViewer:
        return said_needs_viewer(args, out)
    data["files"] = explain_files()
    data["warnings"] += warnings
    return finish(args, out, root, data, 0)


def said_unknown(args, out, exc):
    if args.json:
        print(json.dumps({"message": str(exc), "matches": exc.matches}, indent=1, ensure_ascii=False), file=out)
    else:
        print(str(exc), file=out)
        for name in exc.matches:
            print(f"  {name}", file=out)
    return 1


def said_needs_viewer(args, out):
    ask = {"ask": "handle", "question": companionexplain.NEEDS_WHO, "answer_with": "--as @handle"}
    if args.json:
        print(json.dumps({"needs_lead": [ask], "message": companionexplain.NEEDS_WHO}, indent=1), file=out)
    else:
        print(companionexplain.NEEDS_WHO, file=out)
    return 3
