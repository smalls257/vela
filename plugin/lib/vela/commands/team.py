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

Exit codes: 0 committed; 1 refused (on main, detached, or nothing of the team's changed) or files left out (named; the
team's files are still committed); 2 git failed.
"""
import pathlib

from vela import guard, say
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
        message = f"design: {about}"
        stagegit.stage(root, list(plan.stage))
        commit = stagegit.commit(root, message, list(plan.stage))
    except vaultgit.GitUnavailable as exc:
        raise cli.ToolError(f"team commit: {exc}") from exc
    report(result, plan, commit, message, branch)
    return commands.emit(result, args, out)
