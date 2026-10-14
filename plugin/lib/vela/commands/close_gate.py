"""`vela close gate [--consent-block] [--json|--for-lead]`: is this session ready to finish? (overhaul Task 10a)

The wave-1 gate holds two things, each a Sensor for a failure that used to be silent:

- **A decision with no quoted yes.** Every item that went into or out of `decided` since the branch point must have a
  `## Changes` row citing the lead's own words (`closegate.py` says what counts). A hand-set `state: decided` written
  with the Edit tool, which no hook stops in Cowork, shows up here in both apps.
- **Main not brought in.** `close sync-main` records its outcome; a branch never compared with main is not ready
  unless the lead chose to go on without it, which the gate still says.

`--consent-block` prints the PR body's **Consent** list: each decision with the lead's exact words and the capture link,
so the reviewer reads what the record claims the lead said (the code can't prove the lead said it; plan 4.3).

Exit codes: 0 ready; 1 not ready (the plain list); 2 the tool failed; 3 several sessions are open (nothing judged).
A reader copy has no branch point, so every Changes row into or out of decided in the record is judged as written.

Later tasks (10) add the other lines (unmarked captures, removed ledger rows or overrides, a dirty tree, a stale
render, the flow check, hooks that did not run) in this same module.
"""
import pathlib

from vela import closegate, closestate, model, parse, say, sessions
from vela.edge import flowstore, mergegit, sessiongit, vaultgit


def register_close(steps):
    gate = steps.add_parser("gate", help="whether this session is ready to finish: every decision has the lead's quoted "
                                         "yes, and main was brought in")
    gate.add_argument("--vault", default=".", help="vault root (default: current directory)")
    gate.add_argument("--consent-block", action="store_true",
                      help="print the PR body's Consent list: each decision with the lead's exact words")
    say.add_output_flags(gate)
    gate.set_defaults(func=run)


def open_record(root):
    """(record, text) of the one open record in this working tree, or a Result to return instead."""
    found, problems = sessions.find_open(sessiongit.folder_records(root))
    if len(found) == 1:
        text = (root / found[0].path).read_text(encoding="utf-8")
        return found[0], text, None
    if not found:
        line = "No session is open, so there is nothing to finish." + (f" ({'; '.join(problems)})" if problems else "")
        return None, "", say.Result("close gate", exit=say.REFUSED, lines=[say.Line(line)])
    choices = [{"id": r.id, "topic": r.title, "date": r.date} for r in found]
    lines = [say.Line(f"{len(found)} sessions are open in this folder; run close gate on the branch of the one you are "
                      "closing.", plain=f"{len(found)} sessions are open here, so I haven't judged either. Which one "
                                        "are we closing?")]
    return None, "", say.Result("close gate", exit=say.NEEDS_LEAD, lines=lines, needs_lead=choices)


def branch_point(root):
    """The commit this branch left main at: merge-base with origin/main, else with main."""
    for ref in ("origin/main", "main"):
        code, out, _ = vaultgit.run_git(root, "merge-base", "HEAD", ref)
        if code == 0 and out:
            return out
    raise vaultgit.GitUnavailable("this branch shares no commit with main or origin/main")


def vault_before(root, vault, base):
    """The vault as of the branch point: today's pages with each changed one swapped for its old text (the reader
    `check-slice --changed` uses), so both sides are parsed the same way."""
    before = flowstore.changed_files(root, since=base)
    pages = [p for p in vault.pages if p.path not in before]
    pages += [parse.parse_page(path, text) for path, text in sorted(before.items())
              if text is not None and path.endswith(".md")]
    return model.build(pages, vault.config, sorted(vault.other_names), vault.catalog, vault.template_lines)


def run(args, out):
    """Judge the open session; git that can't answer is a tool failure (exit 2) with git's words, never a pass."""
    try:
        return judge_session(args, out)
    except (vaultgit.GitUnavailable, mergegit.MergeGitFailed, closestate.StateUnreadable) as exc:
        print(f"vela close gate: could not judge the session: {exc}", file=out)
        return say.FAILED


def judge_session(args, out):
    from vela import cli  # the shell loads the vault; this module wires it
    from vela import commands
    root = pathlib.Path(args.vault).resolve()
    record, text, early = open_record(root)
    if early is not None:
        return commands.emit(early, args, out)
    vault = cli.load_vault(root)
    after = closegate.states(vault)
    reader = mergegit.is_reader_copy(root)
    if reader:
        changes = closegate.reader_changes(closegate.change_rows(text), after)
    else:
        changes = closegate.consent_changes(closegate.states(vault_before(root, vault, branch_point(root))), after, vault)
    problems, consent = closegate.judge(changes, text, record.id, vault)
    if args.consent_block:
        print("\n".join(closegate.consent_block(consent)), file=out)
        return 0
    sync = mergegit.sync_verdict(root)
    lines = []
    if sync.blocks:
        problems.insert(0, closegate.Problem(sync.plain, f"sync-main: {sync.status or 'not run'}"))
    elif sync.listed:
        lines.append(say.Line(f"Noted: {sync.plain}", plain=sync.plain))
    for problem in problems:
        lines.append(say.Line(f"not ready: {problem.plain} ({problem.detail})", plain=problem.plain))
    head = (say.Line(f"close gate: ready to finish {record.id}.", plain="The session is ready to finish.") if not problems
            else say.Line(f"close gate: {len(problems)} thing{'' if len(problems) == 1 else 's'} before {record.id} can finish:",
                          plain="Before I can finish, " + ("one thing needs sorting:" if len(problems) == 1
                                                           else f"{len(problems)} things need sorting:")))
    result = say.Result("close gate", exit=say.REFUSED if problems else say.DONE, lines=[head] + lines,
                        data={"ready": not problems, "consent": [c.__dict__ for c in consent]})
    return commands.emit(result, args, out, say.Resolver(vault))

