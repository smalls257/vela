"""`vela close sync-main` (Task 8): bring in what changed on main before render and check, so they see what will merge.

This replaces the six-step merge recipe the close skill carried in prose (fetch, is-ancestor, checkpoint, merge,
classify hunks, abort, `-X ours`). It was the riskiest prose in the plugin: one wrong `--theirs` loses the owner's
edits. The steps are the same every time, so they are code (plan section 1); the lead is asked only where a person
must choose.

- Fetch fails: exit 3, nothing changed. The lead chooses to try again or go on; `--accept-not-compared` records the
  go-on, so `close gate` lists it instead of blocking (Silent Fallback: going on without main must be on record).
- origin/main already in HEAD: up to date, exit 0.
- Tracked files with uncommitted edits: exit 3, nothing changed. A merge over uncommitted edits can mix them into a
  conflict nobody can untangle. This command never stages or commits the session's files (one capability per
  subcommand): `vela close stage --checkpoint` does that.
- A clean merge: exit 0.
- Conflicts: `mergeplan` reads every hunk. Any hunk outside a generated block: the merge is aborted and the files and
  lines are listed, exit 1; main changed writing this branch changed too, and only the lead may choose between them.
  Every hunk inside a generated block: abort, then `git merge --no-edit -X ours origin/main`. Render rebuilds generated
  blocks from the pages, so which side's block survives does not matter; `-X ours` decides only the conflicting hunks,
  so every clean edit on either side is kept. Never `git checkout --ours/--theirs` on a file: that drops the other
  side's edits to the whole file.

Every outcome writes `.vela/close/<branch key>.json` (see `closestate`), so the gate can tell "brought in" from
"never tried". That file is vela's own untracked state, not a change to the lead's copy, so it is reported as
`state_file` and not in `wrote` (which an exit 3 promises is empty). A reader copy runs no git at all.
"""
import pathlib

from vela import closestate, commands, mergeplan, say
from vela.edge import mergegit

COMMAND = "close sync-main"
CHECKPOINT = "vela close stage --checkpoint"
ACCEPT = "vela close sync-main --accept-not-compared"


def register_close(steps):
    sync = steps.add_parser("sync-main", help="bring in what changed on main; stop and list the lines when main changed "
                                              "the same writing this branch did")
    sync.add_argument("--vault", default=".", help="vault root (default: current directory)")
    sync.add_argument("--today", help="the date to record, YYYY-MM-DD (default: today)")
    sync.add_argument("--timeout", type=int, default=mergegit.FETCH_TIMEOUT,
                      help=f"seconds to wait for git fetch (default: {mergegit.FETCH_TIMEOUT})")
    sync.add_argument("--accept-not-compared", action="store_true",
                      help="the lead chose to go on without main after a failed fetch: record it, so close gate lists it")
    say.add_output_flags(sync)
    sync.set_defaults(func=cmd_sync_main)


def cmd_sync_main(args, out):
    from vela import cli  # cli resolves the date once; the core never reads the clock
    today, _ = cli.parse_today(args.today)
    return commands.emit(sync_main(pathlib.Path(args.vault), today, args.accept_not_compared, args.timeout), args, out)


class _Run:
    """One sync-main run: where it is, which branch, and how each outcome is recorded and said."""

    def __init__(self, root, today):
        self.root, self.today, self.branch, self.main, self.head = root, today, "", "", ""

    def finish(self, status, exit_code, lines, reason="", files=(), refusals=(), needs_lead=(), wrote=()):
        key = closestate.key_for(self.branch) if status != closestate.READER else closestate.READER_KEY
        rec = closestate.record(status, self.branch, self.main, self.head, self.today, reason, files)
        path = mergegit.write_state(self.root, key, rec)
        data = {"status": status, "reason": reason, "branch": self.branch, "main": self.main, "head": self.head,
                "files": rec["files"], "state_file": path.relative_to(self.root).as_posix()}
        return say.Result(COMMAND, exit_code, list(lines), list(refusals), list(needs_lead), list(wrote), data)


def sync_main(root, today, accept=False, timeout=mergegit.FETCH_TIMEOUT):
    run = _Run(root, today)
    if mergegit.is_reader_copy(root):
        return run.finish(closestate.READER, say.DONE, [say.Line(
            "sync-main: a read copy has no main to bring in; no git was run.",
            "This is a read copy, so there is no main to bring in.")])
    try:
        return _sync_owner(run, accept, timeout)
    except mergegit.MergeGitFailed as exc:
        return _git_failed(run, str(exc))


def _sync_owner(run, accept, timeout):
    root = run.root
    run.branch = mergegit.current_branch(root)
    run.head = mergegit.sha(root, "HEAD")
    if accept:
        run.main = mergegit.sha(root, mergegit.MAIN) if mergegit.has_ref(root, mergegit.MAIN) else ""
        return run.finish(closestate.ACCEPTED, say.DONE, [say.Line(
            "sync-main: not compared with origin/main; the lead chose to go on. close gate will list it.",
            "Going on without comparing with main, as you said. The final check will list it.")])
    why = mergegit.fetch_origin(root, timeout)
    if why:
        return _fetch_failed(run, why)
    run.main = mergegit.sha(root, mergegit.MAIN)
    if mergegit.is_ancestor(root, run.main, "HEAD"):
        return run.finish(closestate.UP_TO_DATE, say.DONE, [say.Line(
            f"sync-main: up to date: origin/main {run.main[:7]} is already in {run.branch}.",
            "This branch already has everything on main.")])
    dirty = mergegit.tracked_changes(root)
    if dirty:
        return _uncommitted(run, dirty)
    return _merge(run)


def _merge(run):
    root, before = run.root, run.head
    code, said = mergegit.merge(root)
    if code == 0:
        return _merged(run, before, closestate.MERGED, [], say.Line(
            f"sync-main: merged origin/main {run.main[:7]} into {run.branch}.",
            "I brought in what changed on main; nothing clashed."))
    paths = mergegit.conflicted_files(root)
    if not paths:  # the merge failed for a reason that is not a conflict: git's words are the only explanation
        _abort_if_stopped(root)
        raise mergegit.MergeGitFailed(f"git merge --no-edit {mergegit.MAIN} failed: {said}")
    plans = [mergeplan.plan_file(path, mergegit.conflicted_text(root, path)) for path in paths]
    mergegit.abort(root)
    if not mergeplan.generated_only(plans):
        return _conflict(run, plans)
    code, said = mergegit.merge(root, ours_on_conflict=True)
    if code != 0:
        _abort_if_stopped(root)
        raise mergegit.MergeGitFailed(f"git merge --no-edit -X ours {mergegit.MAIN} failed after the generated-only "
                                      f"check: {said}")
    files = [{"path": p.path, "lines": [h.lines() for h in p.hunks]} for p in plans]
    return _merged(run, before, closestate.MERGED_GENERATED, files, say.Line(
        f"sync-main: merged origin/main {run.main[:7]} into {run.branch}; every conflict was inside a generated block "
        f"({', '.join(p.path for p in plans)}), settled with -X ours. Run vela render to rebuild them.",
        "I brought in what changed on main. The only overlaps were in generated summaries, which the render rebuilds, "
        "so nobody's writing was lost."))


def _merged(run, before, status, files, line):
    run.head = mergegit.sha(run.root, "HEAD")
    wrote = mergegit.changed_paths(run.root, before, run.head)
    return run.finish(status, say.DONE, [line], files=files, wrote=wrote)


def _abort_if_stopped(root):
    if mergegit.merging(root):
        mergegit.abort(root)


def _page_name(plan):
    """How the lead hears a file: its page title, else its path when the path holds no ID, else a plain stand-in."""
    if plan.title and not say.leak_in(plan.title):
        return f'"{plan.title}"'
    return plan.path if not say.leak_in(plan.path) else "a page whose title I couldn't read"


def _hunk_words(plan):
    if not plan.hunks:
        return "the whole file (git left no lines to compare, as when one side deleted it)"
    spans = [h.lines() for h in plan.outside]
    return spans[0] if len(spans) == 1 else ", ".join(spans[:-1]) + " and " + spans[-1]


def _conflict(run, plans):
    stopped = [p for p in plans if p.outside]
    files = [{"path": p.path, "title": p.title, "lines": [h.lines() for h in p.outside] if p.hunks else ["whole file"]}
             for p in stopped]
    lines = [say.Line(f"sync-main: {p.path}: {', '.join(f['lines'])} outside a generated block",
                      f"Main changed {_page_name(p)} while we worked on it, so I stopped the merge. "
                      f"The lines both sides changed: {_hunk_words(p)}.")
             for p, f in zip(stopped, files)]
    refusal = say.Refusal(
        rule="sync-main conflict",
        plain="Main changed writing this branch changed too, so I stopped the merge. Nothing in your copy changed.",
        fix="Show the lead both sides of each listed line range; the lead resolves; rerun vela close sync-main.",
        override=f"{ACCEPT} (go on without main; close gate lists it)")
    return run.finish(closestate.CONFLICT, say.REFUSED, lines, files=files, refusals=[refusal])


def _fetch_failed(run, why):
    choices = [{"choice": "retry", "plain": "Try again", "run": "vela close sync-main"},
               {"choice": "go-on", "plain": "Go on without main", "run": ACCEPT}]
    return run.finish(closestate.NOT_COMPARED, say.NEEDS_LEAD, [say.Line(
        f"sync-main: not compared: git fetch origin failed: {why}. Retry, or record the lead's go-on with {ACCEPT}.",
        "I couldn't reach the shared copy, so this branch isn't compared with main yet. Go on without it, or try again?")],
        reason=closestate.FETCH_FAILED, needs_lead=choices)


def _uncommitted(run, dirty):
    shown = ", ".join(dirty[:5]) + (f" and {len(dirty) - 5} more" if len(dirty) > 5 else "")
    choices = [{"choice": "checkpoint", "plain": "Save the session's edits in a checkpoint commit", "run": CHECKPOINT}]
    return run.finish(closestate.NOT_COMPARED, say.NEEDS_LEAD, [say.Line(
        f"sync-main: not compared: {len(dirty)} tracked files have uncommitted edits ({shown}). Commit them first with "
        f"{CHECKPOINT}, then rerun.",
        "This session's edits aren't saved in a commit yet, so I can't bring in main without risking them. "
        "They need a checkpoint commit first.")],
        reason=closestate.UNCOMMITTED, needs_lead=choices)


def _git_failed(run, error):
    return run.finish(closestate.NOT_COMPARED, say.FAILED, [say.Line(
        f"sync-main: git failed, nothing was merged: {error}",
        "Git failed while I was comparing with main, so nothing was merged. The error is in vela's output.")],
        reason=closestate.GIT_FAILED)
