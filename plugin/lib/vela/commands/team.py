"""`vela team commit --about "<section or story>"`: a team session's commit on its `design/<slug>` branch.

Why a command: design and breakdown commit after each settled section or story, and they open no session record, so
`close stage` (which files one session) can't serve them. Their skills used to say "commit it on the branch", which a
model typed as `git add` by hand; once the Claude Code hook denies every model-run `git add` (plan Task 24), those
skills would stop, and wherever the hook doesn't fire they'd sweep in whatever else changed. So the team's commit goes
through here, by exact path from `guard.team_plan`: everything under `docs/` and `CONTEXT.md`; the never-staged rules
still win (Silent Fallback ruled out: the inbox can't ride a design commit), and a changed vault page is named and
left out, because a team never edits the plan itself.

It commits only on a branch that isn't `main` or `master` (the skills use `design/<slug>`): the design goes through
the team's review like any other change, so a commit straight to main is refused, not made. In a reader copy (no
git) nothing runs, and it says so.

A section that adds a design choice (`designchoice`: an ADR, a Decisions bullet, "we'll use X") is not committed until
a person's capture names it. The senior's yes goes in with `vela record add`, which on a design branch writes to the
branch's own record under `.vela/design/`; Claude's own captures never count (Silent Fallback ruled out: a doc that
reads as decided and was decided by nobody).

Exit codes: 0 committed; 1 refused (on main, detached, or nothing of the team's changed) or files left out (named; the
team's files are still committed); 2 git failed; 3 a choice nobody has said yes to (ask the person; nothing changed).
"""
import pathlib

from vela import closegate, designchoice, guard, say
from vela.commands import record
from vela.edge import stagegit, vaultgit

PROTECTED = ("main", "master")


def register(sub):
    top = sub.add_parser("team", help="a team session's own steps (design, breakdown) on its design branch")
    each = top.add_subparsers(dest="what", required=True)
    one = each.add_parser("commit", help="commit the team's changed files (docs/ and CONTEXT.md) by exact path, on "
                                         "the design branch")
    one.add_argument("--about", required=True, help="what settled, in a few words (the section or the story); the "
                                                    "message is `design: <about>`")
    one.add_argument("--vault", default=".", help="the repository the team works in (default: current directory)")
    say.add_output_flags(one)
    one.set_defaults(func=cmd_team_commit)


def refuse(result, key, plain, fix):
    result.exit = say.REFUSED
    result.refusals.append(say.Refusal(key, plain, fix))
    return result


def branch_refusal(result, branch):
    if not branch:
        return refuse(result, "team-detached", "This copy isn't on a branch, so I haven't saved anything.",
                      "Switch to the team's design/<slug> branch (create it if it doesn't exist), then run this again.")
    return refuse(result, "team-on-main", "The design goes through the team's review, so I don't save it straight "
                  "to main.", f"You're on {branch}: switch to the design/<slug> branch, then run this again.")


def report(result, plan, commit, message, branch):
    result.data = {"commit": commit, "message": message, "branch": branch, "staged": list(plan.stage),
                   "left": [{"path": p, "reason": why} for p, why in plan.left],
                   "never": [{"path": p, "rule": r.key} for p, r in plan.never]}
    result.wrote = list(plan.stage)
    result.lines.append(say.Line(f"vela team commit: committed {commit} on {branch}: {message} "
                                 f"({len(plan.stage)} file{'s' if len(plan.stage) != 1 else ''})",
                                 "Saved on the team's design branch."))
    result.lines += [say.Line(f"  left out: {p} ({why})") for p, why in plan.left]
    for rule in guard.rules_hit(plan.never):
        result.refusals.append(say.Refusal(rule.key, rule.plain, rule.fix))
    if plan.left or plan.never:
        result.exit = say.REFUSED


def head_text(root, rel):
    """The committed text of `rel`, "" when HEAD doesn't have it (a new file)."""
    code, out, _ = vaultgit.run_git(root, "show", f"HEAD:{rel}")
    return out if code == 0 else ""


def person_yes_words(root, branch):
    """The words of every capture a person made in this design's record (origin not claude's)."""
    rel = record.design_record_path(branch)
    path = root / rel if rel else None
    if not path or not path.is_file():
        return []
    matches = (closegate.CAPTURE_RE.match(row) for row in path.read_text(encoding="utf-8").splitlines())
    return [m.group("words") for m in matches if m and not m.group("origin").strip().lower().startswith("claude")]


def unbacked_choices(root, branch, staged):
    """The design choices these docs add that no person's capture names."""
    added = []
    for rel in staged:
        if rel.endswith(".md") and (root / rel).is_file():
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
            added += designchoice.added_choices(rel, head_text(root, rel), text)
    return designchoice.unbacked(added, person_yes_words(root, branch)) if added else []


def ask_for_yes(result, unsaid):
    result.exit = say.NEEDS_LEAD
    result.needs_lead = [{"ask": "design-yes", "choice": designchoice.plain_choice(c)} for c in unsaid]
    for c in unsaid:
        words = designchoice.plain_choice(c)
        result.lines.append(say.Line(
            f"vela team commit: not committed, no yes recorded for: {words}",
            f"This adds a choice nobody has said yes to: {words}. Ask, record the yes, then commit."))
    return result


def cmd_team_commit(args, out):
    from vela import cli, commands
    root = pathlib.Path(args.vault).resolve()
    result = say.Result("team commit")
    if not (root / ".git").exists() and (root / ".vela" / "workspace.json").is_file():
        result.lines.append(say.Line("vela team commit: this is a reader copy, so nothing is committed.",
                                     "This is your copy, so the files are written here and nothing is committed."))
        return commands.emit(result, args, out)
    about = " ".join(args.about.split())
    if not about:
        raise cli.ToolError("--about needs a few words: the section or the story that settled.")
    try:
        branch = vaultgit.current_branch(root)
        if not branch or branch in PROTECTED:
            return commands.emit(branch_refusal(result, branch), args, out)
        plan = guard.team_plan(stagegit.changed_paths(root))
        if not plan.stage:
            refuse(result, "team-nothing", "None of the team's files changed, so there's nothing to save.",
                   "Write the section or the story into docs/ first.")
            return commands.emit(result, args, out)
        unsaid = unbacked_choices(root, branch, plan.stage)
        if unsaid:
            return commands.emit(ask_for_yes(result, unsaid), args, out)
        message = f"design: {about}"
        stagegit.stage(root, list(plan.stage))
        commit = stagegit.commit(root, message, list(plan.stage))
    except vaultgit.GitUnavailable as exc:
        raise cli.ToolError(f"team commit: {exc}") from exc
    report(result, plan, commit, message, branch)
    return commands.emit(result, args, out)
