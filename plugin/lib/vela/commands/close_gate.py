"""`vela close gate [--consent-block] [--today D] [--json|--for-lead]`: is this session ready to finish? (overhaul
Tasks 10a and 10)

The Violation this command's shape prevents is the God Method it replaces: "is this ready?" used to be a checklist
spread through the close skill's prose, each item a sentence a model could skip. Here it is one list, in one place
(Shield), and each line is a Sensor for a failure that used to be silent. What blocks:

- **Main not brought in.** `close sync-main` records its outcome; a branch never compared with main is not ready
  unless the lead chose to go on without it, which the gate still says. The gate never runs sync-main itself, even
  when its record is missing (plan 9.2 said it would): a check that merges is a write hidden inside a read, a Black
  Box. It says which command to run instead.
- **A decision with no quoted yes.** Every item that went into or out of `decided` since the branch point must have a
  `## Changes` row citing the lead's own words (`closegate.py` says what counts). A hand-set `state: decided` written
  with the Edit tool, which no hook stops in Cowork, shows up here in both apps.
- **A capture with no mark.** Close files every capture; one left unmarked is something the lead said that would drop
  out of the plan with nobody choosing that.
- **An error with no recorded choice.** `vela check`'s errors, after the overrides: what's left has nobody's choice
  behind it, and would fail the merge anyway.
- **A ledger row or an override removed since the branch point.** Close section 6 says to fix errors with the lead and
  never delete the row or override to quiet the check. Deletion is detectable, so it is refused here, unless the record
  holds the lead's own words for the removal (a `| <ID> | ... | removed | [[record#^cNN]] |` Changes row).
- **A stray file.** A changed file the close's allow-list leaves out (`guard.plan`) would be left behind by the close
  commit; the lead deals with it first. The handoff manifest and the dashboard are not strays: `close finish` commits
  them itself, after the close commit.
- **A stale render.** The close commit carries what render writes, so render must have nothing left to rewrite.

What is said and does not block: the flow check's line for each slice this session's changes reach (a read-back,
plan 2.1; the record in `.vela/flowcheck-cache.json` is read, never written, so the gate stays read-only); "hooks did
not run in this session" when `.vela/hooks-active` is missing (a missing hook costs earlier feedback, never
correctness: every rule a hook holds, a command holds too); and the host's stance from `.vela/host.json`.

`--consent-block` prints the PR body's **Consent** list: each decision with the lead's exact words and the capture link,
so the reviewer reads what the record claims the lead said (the code can't prove the lead said it; plan 4.3).

Exit codes: 0 ready; 1 not ready (the plain list, each line with what would clear it); 2 the tool failed; 3 several
sessions are open (nothing judged). A reader copy runs no git: it has no branch point, so every Changes row into or out
of decided is judged as written, and removals, strays and the flow check are left out and the list says so.

`observe` and `closegate.ready` are the public pair `close finish` composes (Task 11): observe gathers, ready judges.
"""
import pathlib
import re
import time

from vela import closegate, closestate, model, parse, say, sessions
from vela.edge import flowstore, hostprobe, mergegit, sessiongit, stagegit, vaultgit


def register_close(steps):
    gate = steps.add_parser("gate", help="whether this session is ready to finish: one list of what stops it, each "
                                         "with what would clear it")
    gate.add_argument("--vault", default=".", help="vault root (default: current directory)")
    gate.add_argument("--consent-block", action="store_true",
                      help="print the PR body's Consent list: each decision with the lead's exact words")
    gate.add_argument("--today", help="the date check and overrides are judged by, YYYY-MM-DD (default: system date)")
    say.add_output_flags(gate)
    gate.set_defaults(func=run)


def open_record(root):
    """(record, text) of the one open record in this working tree, or a Result to return instead."""
    found, problems = sessions.find_open(sessiongit.folder_records(root))
    if len(found) == 1:
        text = (root / found[0].path).read_text(encoding="utf-8")
        return found[0], text, None
    if not found:
        said = "No session is open, so there is nothing to finish."
        line = said + (f" ({'; '.join(problems)})" if problems else "")
        return None, "", say.Result("close gate", exit=say.REFUSED, lines=[say.Line(line, plain=said)])
    choices = [{"id": r.id, "topic": r.title, "date": r.date} for r in found]
    lines = [say.Line(f"{len(found)} sessions are open in this folder; run close gate on the branch of the one you are "
                      "closing.", plain=f"{say.count_words(len(found), capital=True)} sessions are open here: "
                                        f"{say.names_said([r.title for r in found])}. Which one are we closing?")]
    return None, "", say.Result("close gate", exit=say.NEEDS_LEAD, lines=lines, needs_lead=choices)


def branch_point(root):
    """The commit this branch left main at: merge-base with origin/main, else with main."""
    for ref in ("origin/main", "main"):
        code, out, _ = vaultgit.run_git(root, "merge-base", "HEAD", ref)
        if code == 0 and out:
            return out
    raise vaultgit.GitUnavailable("this branch shares no commit with main or origin/main")


def vault_before(vault, before):
    """The vault as of the branch point: today's pages with each changed one swapped for its old text (`before`, from
    `flowstore.changed_files`, the reader `check-slice --changed` uses), so both sides are parsed the same way."""
    pages = [p for p in vault.pages if p.path not in before]
    pages += [parse.parse_page(path, text) for path, text in sorted(before.items())
              if text is not None and path.endswith(".md")]
    return model.build(pages, vault.config, sorted(vault.other_names), vault.catalog, vault.template_lines)


def check_errors(vault, today):
    """Check's errors, after the overrides (`rules.check` applies them)."""
    from vela import rules
    return tuple(f for f in rules.check(vault, today) if f.is_error)


def stale_render(root, vault):
    """(pages render would still rewrite, problems that stop render)."""
    from vela import render
    texts, _, _, refusals = render.render_vault(vault)
    if refusals:
        return (), len(refusals)
    stale = [path for path, text in sorted(texts.items())
             if (root / path).read_text(encoding="utf-8").replace("\r\n", "\n").lstrip("﻿") != text]
    return tuple(stale), 0


def strays(root, record_id):
    """Changed paths the close's allow-list leaves out, less the two `close finish` commits on its own."""
    from vela import cli, guard
    changed = stagegit.changed_paths(root)
    pages = {p for p in changed if p.endswith(".md") and cli.page_kind(p) == "page"}
    plan = guard.plan(changed, pages, record_id)
    return tuple(path for path, why in plan.left if why not in (guard.HANDOFF, guard.DASHBOARD))


_SLICE_ID = re.compile(r"^[A-Z]+-\d+\s+")


def flow_lines(root, vault, before, today):
    """((default line, lead line), ...) for each slice the changes since the branch point reach, through the same
    public functions `check-slice --changed` runs. The record is read and never written: the gate is a read."""
    from vela import cli
    from vela.flowcheck import changed, readers
    specs = cli.spec_texts(root)
    catalog = readers.read_catalog(vault, specs)
    if not catalog.slices:
        return ()
    walk = cli.changes_walk(root, vault, specs, catalog, before)
    store, _ = flowstore.read_record(root)
    report = changed.check_slices(catalog, today, store, walk, clock=time.perf_counter,
                                  version=flowstore.checker_version())
    reached = set(walk.affected)
    out = []
    for line in report.lines:
        if walk.everything or line.key in reached:
            status = line.words()[len(line.label) + 2:].split(". ", 1)[0].rstrip(".")
            out.append((line.words(), slice_words(_SLICE_ID.sub('', line.label), status)))
    if not out:  # said, so "nothing reached" never reads like "never checked"
        none = "Nothing this session changed touches a slice, so there was nothing new to check end to end."
        out.append((none, none))
    return tuple(out)


def slice_words(name, status):
    """What the lead hears about one slice's flow check: whether it still runs end to end."""
    if status.startswith("passes"):
        return f"{name} still runs end to end."
    if "not fully checked" in status and not status.startswith("fails"):
        return f"{name} isn't fully checked yet, so I can't say it runs end to end."
    return f"{name} breaks somewhere along the way; the boundary session is where that gets fixed."


def observe(root, vault, record, text, today):
    """Everything `closegate.ready` judges, gathered from git and the disk. A reader copy runs no git at all."""
    reader = mergegit.is_reader_copy(root)
    stale, render_problems = stale_render(root, vault)
    host = hostprobe.read_json(root / hostprobe.HOST_FILE)
    common = dict(today=today, sync=mergegit.sync_verdict(root), errors=check_errors(vault, today), stale=stale,
                  render_problems=render_problems, hooks_ran=(root / hostprobe.ACTIVE_FILE).is_file(), host=host or None,
                  reader=reader)
    if reader:
        return closegate.Seen(**common)
    before = flowstore.changed_files(root, since=branch_point(root))
    return closegate.Seen(before=vault_before(vault, before), stray=strays(root, record.id),
                          flow=flow_lines(root, vault, before, today), **common)


def run(args, out):
    """Judge the open session; git that can't answer is a tool failure (exit 2) with git's words, never a pass."""
    try:
        return judge_session(args, out)
    except (vaultgit.GitUnavailable, mergegit.MergeGitFailed, closestate.StateUnreadable) as exc:
        from vela import commands
        return commands.emit(say.Result("close gate", exit=say.FAILED, lines=[say.Line(
            f"vela close gate: could not judge the session: {exc}",
            plain="I couldn't check whether the session is ready; git didn't answer.")]), args, out)


# How the answer line names each kind of problem, counted: what holds the close up, in the lead's terms.
KIND_WORDS = {
    closegate.SYNC: ("main changed the same pages we did", "main changed the same pages we did"),
    closegate.CONSENT: ("one decision needs your yes", "{n} decisions need your yes"),
    closegate.UNMARKED: ("some of what you said isn't sorted yet", "some of what you said isn't sorted yet"),
    closegate.CHECK: ("one item can't be finished as it stands", "{n} items can't be finished as they stand"),
    closegate.REMOVED_ROW: ("one thing was taken out this session", "{n} things were taken out this session"),
    closegate.STRAY: ("some files changed outside this session", "some files changed outside this session"),
}
WAY_OUT = "You can also keep any of these as they are; I'll note why."


def problem_lines(readiness, resolver):
    """Every problem and note. The text line carries the detail and the clear (for the model); the lead hears the
    question only, and the steps Claude takes itself (render, sync-main, the hooks note) not at all."""
    lines = []
    for p in readiness.problems:
        clear = f" To clear: {p.clear}" if p.clear else ""
        lines.append(say.Line(f"not ready: {p.plain} ({p.detail}){clear}", plain=resolver.plain(p.plain),
                              audience=p.audience))
    for n in readiness.notes:
        shown = n.plain if n.detail == n.plain else f"{n.plain} ({n.detail})"
        lines.append(say.Line(f"Noted: {shown}", plain=resolver.plain(n.plain), audience=n.audience))
    return lines


def answer_words(readiness):
    """The lead's first line: ready, or what holds the close up, grouped by kind and counted (about four things)."""
    if readiness.ready:
        return "The session is ready to finish."
    theirs = [p for p in readiness.problems if p.audience == say.LEAD]
    if not theirs:
        return "I have a step of my own to take before I can finish; nothing needs you yet."
    counts = {}
    for p in theirs:
        counts[p.kind] = counts.get(p.kind, 0) + 1
    parts = []
    for kind in closegate.KINDS:
        if kind in counts and kind in KIND_WORDS:
            one, many = KIND_WORDS[kind]
            parts.append(one if counts[kind] == 1 else many.format(n=say.count_words(counts[kind])))
    things = say.count_words(len(theirs))
    head = "One thing before I can finish" if len(theirs) == 1 else f"{things.capitalize()} things before I can finish"
    return f"{head}: {say.names_said(parts)}." + (" Shall we take them one at a time?" if len(theirs) > 1 else "")


def today_date(today):
    import datetime
    return datetime.date.fromisoformat(today)


def judge_session(args, out):
    from vela import cli  # the shell loads the vault; this module wires it
    from vela import commands
    root = pathlib.Path(args.vault).resolve()
    record, text, early = open_record(root)
    if early is not None:
        return commands.emit(early, args, out)
    today, _ = cli.parse_today(args.today)
    vault = cli.load_vault(root)
    readiness = closegate.ready(vault, text, record.id, observe(root, vault, record, text, today))
    if args.consent_block:
        print("\n".join(closegate.consent_block(readiness.consent)), file=out)
        return 0
    resolver = say.Resolver(vault, today=today_date(today))
    n = len(readiness.problems)
    head = (say.Line(f"close gate: ready to finish {record.id}.", plain="") if not n
            else say.Line(f"close gate: {n} thing{'' if n == 1 else 's'} before {record.id} can finish:", plain=""))
    asks = any(p.audience == say.LEAD and p.kind in (closegate.CONSENT, closegate.CHECK) for p in readiness.problems)
    data = {"ready": readiness.ready, "consent": [c.__dict__ for c in readiness.consent],
            "problems": [p.__dict__ for p in readiness.problems], "notes": [p.__dict__ for p in readiness.notes]}
    result = say.Result("close gate", exit=say.DONE if readiness.ready else say.REFUSED,
                        lines=[head] + problem_lines(readiness, resolver), data=data,
                        answer=answer_words(readiness), closing=WAY_OUT if asks else "")
    return commands.emit(result, args, out, resolver)
