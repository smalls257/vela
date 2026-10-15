"""`vela close finish --summary "..." [--replace]` and `vela close dashboard [--branch]` (overhaul Task 11): file the
session in the one order close sections 7 and 9 name, and rebuild the dashboard with no session open.

The Violation this module's shape prevents is a God Method rebuilt inside the CLI: finishing a close touches the gate,
the allow-list staging, the handoff manifest and the explorer, and porting those mechanics here would give each of
them a second copy. So `close finish` *composes* them (Shield): it judges with `close_gate.observe` and
`closegate.ready`, then runs each write through the command that owns it, by its public command line (`vela close
stage --close --json`, `vela handoff <APP-id>`, `vela explore`), and commits only the two files those leave for it
(each manifest, then `dashboard.html`), each alone. The order is `closefinish.plan`'s, decided before the first write;
`closefinish.py` says why each step sits where it does.

`close finish` exit codes: 0 filed (the dashboard line says whether the dashboard was rebuilt: a dashboard that failed
never undoes the close, and its failure is said in every mode, never as "up to date"); 1 the gate says the session
isn't ready (run `vela close gate`), or no session is open; 2 the tool failed (git, or a step's own command; what was
already filed is said); 3 needs the lead, nothing written: several sessions are open, or a handoff record exists and
replacing it needs `--replace` and the app's team's own yes in the record.

`close dashboard` is the no-session path of close section 9: it rebuilds `dashboard.html` and never commits to main.
With no session open in an owner's copy and the page changed, it exits 3 offering a `dashboard/<date>` branch; nothing
is committed or pushed (the rebuilt page is the lead's view on this machine, not a change to the plan, so it is not in
`wrote`). `--branch` takes that offer: it creates `dashboard/<date>` from here and commits only `dashboard.html` on it
as `Rebuild dashboard`. Pushing it is `close push`'s job. With a session open it rebuilds and leaves the page for the
close. A reader copy runs no git in either command.
"""
import io
import json
import pathlib

from vela import closefinish, closegate, explorereport, handoffwarn, say, schema, sessions
from vela.edge import atomic, mergegit, sessiongit, stagegit, vaultgit

# The explore report lines the lead hears after the dashboard line (close section 9): what the build went on without.
RELAYED_KINDS = ("warning", "no design", "gitignore")


def register_close(steps):
    finish = steps.add_parser("finish", help="file the session: close the record, commit it, then each handoff "
                                             "record alone, then the dashboard alone")
    finish.add_argument("--vault", default=".", help="vault root (default: current directory)")
    finish.add_argument("--summary", required=True, help="the record's one-line summary, in plain words")
    finish.add_argument("--replace", action="store_true",
                        help="replace an app's existing handoff record; needs its team's own yes in the record")
    finish.add_argument("--today", help="the date check and the handoff record use, YYYY-MM-DD (default: system date)")
    say.add_output_flags(finish)
    finish.set_defaults(func=run_finish)
    board = steps.add_parser("dashboard", help="rebuild the dashboard with no session open; never commits to main")
    board.add_argument("--vault", default=".", help="vault root (default: current directory)")
    board.add_argument("--branch", action="store_true",
                       help="put the rebuilt dashboard on its own dashboard/<date> branch and commit it there")
    board.add_argument("--today", help="the date the dashboard counts from, YYYY-MM-DD (default: system date)")
    say.add_output_flags(board)
    board.set_defaults(func=run_dashboard)


def call(*argv):
    """(exit code, output) of one vela command, run in this process through its public command line."""
    from vela import cli
    out = io.StringIO()
    code = cli.main([str(a) for a in argv], out=out)
    return code, out.getvalue()


def last_words(output, code):
    """The one line that says why a command failed: its last non-empty line, without the `vela:` prefix."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return f"the command exited {code} without saying why"
    return lines[-1].split("vela: ", 1)[-1].rstrip(".")


def emit(result, args, out, resolver=None):
    from vela import commands
    return commands.emit(result, args, out, resolver)


# ------------------------------------------------------------------ the dashboard, shared by both commands

def build_dashboard(root, today, resolver):
    """(built, lines): rebuild dashboard.html with `vela explore`. A failure is said, never raised: the caller decides
    what it means."""
    code, output = call("explore", root, "--today", today)
    if code != 0:
        why = last_words(output, code)
        plain = resolver.plain(why)
        if say.leak_in(plain):
            plain = "the explorer stopped with an error, which the plain output shows"
        return False, why, plain, []
    relayed = [say.Line(f"vela explore: {entry}", explorereport.lead_line(entry, resolver))
               for entry in explorereport.entries(output) if explorereport.kind_of(entry) in RELAYED_KINDS]
    return True, "", "", relayed


def dashboard_changed(root):
    return closefinish.DASHBOARD in stagegit.changed_paths(root)


def commit_alone(root, path, message):
    stagegit.stage(root, [path])
    return stagegit.commit(root, message, [path])


# ------------------------------------------------------------------ close finish

def run_finish(args, out):
    from vela import cli
    try:
        summary = closefinish.checked_summary(args.summary)
    except closefinish.SummaryRefused as exc:
        raise cli.ToolError(str(exc)) from exc
    root = pathlib.Path(args.vault).resolve()
    today, _ = cli.parse_today(args.today)
    try:
        return finish_session(root, today, summary, args, out)
    except (vaultgit.GitUnavailable, mergegit.MergeGitFailed) as exc:
        raise cli.ToolError(f"close finish: git failed: {exc}") from exc


def one_open_record(root):
    """(record, None), or (None, a Result to emit instead)."""
    found, problems = sessions.find_open(sessiongit.folder_records(root))
    if len(found) == 1:
        return found[0], None
    if not found:
        why = f" ({'; '.join(problems)})" if problems else ""
        return None, say.Result("close finish", exit=say.REFUSED, lines=[say.Line(
            f"vela close finish: no session is open, so there is nothing to finish{why}. For the dashboard alone, run "
            "vela close dashboard.", "No session is open, so there's nothing to finish.")])
    return None, say.Result("close finish", exit=say.NEEDS_LEAD,
                            needs_lead=[{"id": r.id, "topic": r.title, "date": r.date} for r in found],
                            lines=[say.Line(f"vela close finish: {len(found)} sessions are open; finish on the branch "
                                            "of the one you are closing. Nothing was written.",
                                            f"{len(found)} sessions are open here, so I haven't filed either. Which "
                                            "one are we finishing?")])


def not_ready(readiness, resolver):
    n = len(readiness.problems)
    things = "one thing needs" if n == 1 else f"{n} things need"
    refusal = say.Refusal("close-gate", f"The session isn't ready to finish yet: {things} sorting first.",
                          "Run vela close gate --for-lead, sort out each line it lists with the lead, then finish "
                          "again.", "Each line close gate lists says how the lead can set it aside; finish has no "
                                    "override of its own.")
    lines = [say.Line(f"  not ready: {p.plain} ({p.detail})", resolver.plain(p.plain)) for p in readiness.problems]
    return say.Result("close finish", exit=say.REFUSED, refusals=[refusal], lines=lines,
                      data={"ready": False, "problems": [p.__dict__ for p in readiness.problems]})


def due_handoffs(root, vault, before, record_text):
    """The Handoffs this session made due: apps whose `handed_off` changed since the branch point."""
    if before is None:
        return ()
    due = closefinish.handoffs_due(closefinish.handed_off(before), closefinish.handed_off(vault))
    pages = {app.id: app for app in vault.apps}
    return tuple(closefinish.Handoff(app, vault.name_of(app), (root / schema.HANDOFF_DIR / f"{app}.md").is_file(),
                                     closefinish.team_yes(record_text, pages[app].meta)) for app in due)


def finish_session(root, today, summary, args, out):
    from vela import cli
    from vela.commands import close_gate
    record, early = one_open_record(root)
    if early is not None:
        return emit(early, args, out)
    text = (root / record.path).read_text(encoding="utf-8")
    vault = cli.load_vault(root)
    resolver = say.Resolver(vault)
    seen = close_gate.observe(root, vault, record, text, today)
    readiness = closegate.ready(vault, text, record.id, seen)
    if not readiness.ready:
        return emit(not_ready(readiness, resolver), args, out, resolver)
    try:
        closed = closefinish.with_closed(text, summary)
    except closefinish.SummaryRefused as exc:
        raise cli.ToolError(f"close finish: {exc}") from exc
    handoffs = due_handoffs(root, vault, seen.before, closed)
    plan = closefinish.plan(seen.reader, handoffs, args.replace)
    if plan.needs_lead:
        result = say.Result("close finish", exit=say.NEEDS_LEAD,
                            needs_lead=[{"app": app, "choice": words} for app, words in plan.needs_lead],
                            lines=[say.Line(f"vela close finish: {app}: {words} Nothing was written.", words)
                                   for app, words in plan.needs_lead])
        return emit(result, args, out, resolver)
    run = Finish(root, today, record, closed, vault, resolver, plan, seen.reader, say.mode_of(args))
    return emit(run.walk(), args, out, resolver)


class Finish:
    """One walk of a `closefinish.Plan`, step by step, collecting what each step did into one Result."""

    def __init__(self, root, today, record, closed, vault, resolver, plan, reader, mode):
        self.root, self.today, self.record, self.closed, self.reader = root, today, record, closed, reader
        self.lead = mode == "for-lead"
        self.vault, self.resolver, self.plan = vault, resolver, plan
        self.result = say.Result("close finish", data={"session": record.id, "commits": [], "manifests": []})
        self.built = False

    def say(self, text, plain=None):
        """A line in every mode; one with no `plain` is for the default and JSON modes only, so the lead hears what
        was done and never the commit hashes and paths."""
        if plain is None and self.lead:
            return
        self.result.lines.append(say.Line(text, plain))

    def walk(self):
        steps = {closefinish.RECORD: self.write_record, closefinish.CLOSE_COMMIT: self.close_commit,
                 closefinish.MANIFEST: self.manifest, closefinish.DASHBOARD_BUILD: self.dashboard,
                 closefinish.DASHBOARD_COMMIT: self.dashboard_commit}
        for step, argument in self.plan.steps:
            if not steps[step](argument):
                self.result.exit = say.FAILED
                break
        if self.reader:
            self.say("vela close finish: a read copy: the record is closed here; nothing was staged or committed.",
                     closefinish.READER_NOTHING_COMMITTED)
        return self.result

    def write_record(self, _):
        atomic.write_atomic(self.root / self.record.path, self.closed)
        self.result.wrote.append(self.record.path)
        self.say(f"vela close finish: {self.record.path}: status: closed, with its summary.",
                 None if self.reader else "I've closed the session record, with its summary.")
        return True

    def close_commit(self, _):
        code, output = call("close", "stage", "--close", "--session", self.record.id, "--vault", self.root, "--json")
        try:
            staged = json.loads(output)
        except ValueError:
            staged = {}
        commit = staged.get("commit") or ""
        if code not in (say.DONE, say.REFUSED) or not commit.startswith("committed"):
            why = last_words(output, code)
            self.say(f"vela close finish: the record says closed, but the close commit didn't happen: {why}",
                     "The record says closed, but I couldn't commit the session, so nothing is filed yet.")
            return False
        self.result.data["commits"].append(commit)
        self.say(f"vela close finish: {commit}", "I've committed the session on its branch.")
        for left in staged.get("left", []):
            self.say(f"  left out: {left['path']} ({left['reason']})")
        for never in staged.get("never", []):
            self.say(f"  never staged: {never['path']} ({never['reason']})")
        out_of_it = len(staged.get("left", [])) + len(staged.get("never", []))
        if out_of_it:
            self.say(f"vela close finish: {out_of_it} changed file(s) left out of the close commit, named above.",
                     f"{out_of_it} other changed file{'s' if out_of_it != 1 else ''} "
                     f"{'aren' if out_of_it != 1 else 'isn'}'t part of this session, so I've left "
                     f"{'them' if out_of_it != 1 else 'it'} out of the commit.")
        return True

    def manifest(self, app):
        name = self.vault.name_of(app)
        flags = ["--replace"] if app in self.plan.replace else []
        code, output = call("handoff", app, "--vault", self.root, "--today", self.today, *flags)
        if code != 0:
            why = last_words(output, code)
            self.say(f"vela close finish: the session is committed; the handoff record for {app} wasn't written: {why}",
                     f"The session is committed, but I couldn't write {name}'s handoff record.")
            return False
        path = f"{schema.HANDOFF_DIR}/{app}.md"
        sha = commit_alone(self.root, path, closefinish.MANIFEST_MESSAGE.format(app=app))
        self.result.data["commits"].append(f"committed {sha}: {closefinish.MANIFEST_MESSAGE.format(app=app)}")
        self.result.data["manifests"].append(path)
        self.say(f"vela close finish: committed {sha}: {closefinish.MANIFEST_MESSAGE.format(app=app)}",
                 f"I've written {name}'s handoff record and committed it on its own.")
        gaps = handoffwarn.lines(handoffwarn.gaps(self.vault, self.app_page(app)))
        if gaps:
            head = closefinish.NOT_SETTLED_HEAD.format(app=name)
            self.say(f"not settled at handoff for {app}:", head)
            for line in gaps:
                self.say(f"  {line}", self.resolver.plain(line))
        return True

    def app_page(self, app):
        return next(a for a in self.vault.apps if a.id == app)

    def dashboard(self, _):
        built, why, plain, relayed = build_dashboard(self.root, self.today, self.resolver)
        self.built = built
        self.result.data["dashboard"] = {"built": built, "message": why or None}
        if not built:
            self.say(f"vela close finish: the dashboard couldn't be rebuilt: {why}. The close is filed.",
                     closefinish.DASHBOARD_FAILED.format(message=plain))
            return True  # a dashboard failure never undoes or fails the close
        self.say(f"vela close finish: rebuilt {closefinish.DASHBOARD}.", closefinish.DASHBOARD_DONE)
        self.result.lines += relayed
        return True

    def dashboard_commit(self, _):
        if not self.built or not dashboard_changed(self.root):
            return True
        sha = commit_alone(self.root, closefinish.DASHBOARD, closefinish.DASHBOARD_MESSAGE)
        self.result.data["commits"].append(f"committed {sha}: {closefinish.DASHBOARD_MESSAGE}")
        self.say(f"vela close finish: committed {sha}: {closefinish.DASHBOARD_MESSAGE}")
        return True


# ------------------------------------------------------------------ close dashboard

def run_dashboard(args, out):
    from vela import cli
    root = pathlib.Path(args.vault).resolve()
    today, _ = cli.parse_today(args.today)
    try:
        resolver = say.Resolver(cli.load_vault(root))
    except cli.ToolError:
        resolver = say.Resolver()
    reader = mergegit.is_reader_copy(root)
    found, _ = sessions.find_open(sessiongit.folder_records(root))
    if args.branch and (reader or found):
        why = "a read copy has no git" if reader else "a session is open, and vela close finish commits the " \
                                                      "dashboard on its branch"
        raise cli.ToolError(f"close dashboard --branch: {why}.")
    result = say.Result("close dashboard")
    built, why, plain, relayed = build_dashboard(root, today, resolver)
    result.data["dashboard"] = {"built": built, "message": why or None}
    if not built:
        result.exit = say.FAILED
        result.lines.append(say.Line(f"vela close dashboard: the dashboard couldn't be rebuilt: {why}.",
                                     f"The dashboard couldn't be updated: {plain}."))
        return emit(result, args, out, resolver)
    try:
        lead_choice(root, today, reader, found, args.branch, result)
    except vaultgit.GitUnavailable as exc:
        raise cli.ToolError(f"close dashboard: git failed: {exc}") from exc
    result.lines += relayed
    return emit(result, args, out, resolver)


def lead_choice(root, today, reader, found, branch, result):
    """What the rebuilt page means here: a read copy keeps it; an open session takes it at its close; with no session
    the lead chooses whether it gets its own branch (exit 3), or has chosen (`--branch`)."""
    line = result.lines.append
    if reader:
        line(say.Line("vela close dashboard: rebuilt dashboard.html; a read copy commits nothing.",
                      "I've updated the dashboard on your machine only; a read copy doesn't commit anything."))
        return
    if found:
        line(say.Line("vela close dashboard: rebuilt dashboard.html; vela close finish commits it on the session's "
                      "branch.", "I've updated the dashboard. It goes in when you finish this session."))
        return
    if not dashboard_changed(root):
        line(say.Line("vela close dashboard: dashboard.html was already up to date; nothing to commit.",
                      closefinish.DASHBOARD_DONE))
        return
    name = f"dashboard/{today}"
    if not branch:
        result.exit = say.NEEDS_LEAD
        result.needs_lead = [{"choice": "branch", "branch": name, "run": "vela close dashboard --branch"}]
        line(say.Line(f"vela close dashboard: rebuilt dashboard.html, not committed: no session is open. Run vela close "
                      f"dashboard --branch to commit it on {name}.", closefinish.NO_SESSION_DASHBOARD))
        return
    code, _, err = vaultgit.run_git(root, "switch", "-c", name)
    if code != 0:
        raise vaultgit.GitUnavailable(f"could not create {name}: {err.decode('utf-8', 'replace').strip()}"
                                      if isinstance(err, bytes) else f"could not create {name}: {str(err).strip()}")
    sha = commit_alone(root, closefinish.DASHBOARD, closefinish.DASHBOARD_MESSAGE)
    result.wrote.append(closefinish.DASHBOARD)
    result.data["commit"] = f"committed {sha}: {closefinish.DASHBOARD_MESSAGE}"
    line(say.Line(f"vela close dashboard: on {name}, committed {sha}: {closefinish.DASHBOARD_MESSAGE}",
                  f"I've put the dashboard on its own branch, {name}, and committed it there. Main is untouched."))
