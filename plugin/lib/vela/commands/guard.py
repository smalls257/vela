"""`vela guard staged` and `vela guard path P`: the never-staged rules of `guard.py`, for hooks.

`guard staged` is what the vault's pre-commit hook (`plugin/template/.githooks/pre-commit`) runs, so a commit typed by hand or
by a model cannot carry `.inbox/`, `voice/local/`, `voice/corpus/` or `.vela/` (except the pins file). `guard path`
judges one path for the Claude Code hooks a later task adds. Neither is the real gate: `vela close stage` already
refuses those paths, so a hook that never fires costs earlier feedback, never correctness (plan section 1, Silent
Fallback). Only the never-staged rules apply here; the allow-list is the close's business, so an owner's own commit of
the README still goes through.

Exit codes: 0 nothing forbidden; 1 refused, each path named with its plain reason; 2 git failed.
"""
import pathlib
import shlex

from vela import guard, planscope, say
from vela.edge import plans, stagegit, vaultgit


def register(sub):
    top = sub.add_parser("guard", help="the paths a commit may never carry (the inbox, private voice folders, the "
                                       "tool's own state), for hooks")
    each = top.add_subparsers(dest="what", required=True)
    staged = each.add_parser("staged", help="refuse when the index holds a forbidden path (the pre-commit hook)")
    staged.add_argument("--vault", default=".", help="vault root (default: current directory)")
    say.add_output_flags(staged)
    staged.set_defaults(func=cmd_guard_staged)
    one = each.add_parser("path", help="0 when this path may be staged, 1 when it may never be")
    one.add_argument("path", help="a path, relative to the vault root or absolute inside it")
    one.add_argument("--vault", default=".", help="vault root (default: current directory)")
    say.add_output_flags(one)
    one.set_defaults(func=cmd_guard_path)


def refuse(result, found):
    """Exit 1 with one refusal per rule (the lead hears each reason once) naming every path it caught."""
    result.exit = say.REFUSED
    for rule in guard.rules_hit(found):
        paths = [p for p, r in found if r.key == rule.key]
        # `rm --cached` works with no commit yet too, and leaves the files on disk.
        result.refusals.append(say.Refusal(rule.key, rule.plain, "Take it out of the commit, keeping the files: "
                                           f"git rm -r --cached --quiet -- {' '.join(shlex.quote(p) for p in paths)}"))
    result.data = {"forbidden": [{"path": p, "rule": r.key, "reason": r.plain} for p, r in found]}


def plan_paths(root, staged):
    """[(path as git names it, path inside its plan)] for every staged path. A commit carries the whole index, so the
    pre-commit hook, run from the repo's top, judges every plan's files, each by its own plan's rules. Pointed at one
    plan's folder, it judges that plan's. A path in no plan is no plan's business and is left alone; a repo with no
    plan at all is judged as one plan, as before."""
    top = plans.repo_root(root)
    if top is None:
        return [(path, path) for path in staged]
    folders = [plans.prefix_of(root, top)] if plans.is_plan(root) else [plans.prefix_of(f, top) for f in plans.plans_in(root)]
    if not folders:
        return [(path, path) for path in staged]
    owned = [(path, planscope.plan_of(path, folders)) for path in staged]
    return [(path, planscope.inside(path, folder)) for path, folder in owned if folder is not None]


def forbidden_since(root, since):
    """[(path, Rule)] for every path a commit in `since..HEAD` carries that `guard.never_rule` forbids: the same check
    `guard staged` makes on the index, made on what a push would send. This is the backstop the pre-commit hook and the
    Bash hook can't be, because both can be skipped (`--no-verify`, `commit -a` after the hook read the index)."""
    found = []
    for path, inner in plan_paths(root, stagegit.committed_paths_since(root, since)):
        rule = guard.never_rule(inner)
        if rule is not None:
            found.append((guard.normal(path), rule))
    return found


def cmd_guard_staged(args, out):
    from vela import cli, commands
    root = pathlib.Path(args.vault).resolve()
    try:
        staged = stagegit.staged_paths_in_repo(root)
    except vaultgit.GitUnavailable as exc:
        raise cli.ToolError(f"guard staged: {exc}. The staged files were not checked.") from exc
    result = say.Result("guard staged")
    found = []
    for path, inner in plan_paths(root, staged):
        rule = guard.never_rule(inner)
        if rule is not None:
            found.append((guard.normal(path), rule))
    if found:
        refuse(result, found)
    else:
        result.data = {"forbidden": []}
        result.lines.append(say.Line(f"vela guard staged: {len(staged)} staged paths, none forbidden.",
                                     "Nothing in this save has to stay on your machine."))  # row 226: not "staged"
    return commands.emit(result, args, out)


def relative(path, root):
    """`path` relative to the vault root, as guard.normal reads it. An absolute path outside the vault keeps its own
    form, so it matches no rule and is reported as allowed (the vault's rules say nothing about it)."""
    given = pathlib.PurePath(path)
    if given.is_absolute():
        try:
            return pathlib.Path(given).resolve().relative_to(root).as_posix()
        except ValueError:
            return str(path)
    return str(path)


def cmd_guard_path(args, out):
    from vela import commands
    root = pathlib.Path(args.vault).resolve()
    path = guard.normal(relative(args.path, root))
    rule = guard.never_rule(path)
    result = say.Result("guard path", data={"path": path, "allowed": rule is None, "rule": rule.key if rule else None})
    if rule is None:
        result.lines.append(say.Line(f"vela guard path: {path} may be staged.", "That file may be shared."))
    else:
        result.exit = say.REFUSED
        result.refusals.append(say.Refusal(rule.key, rule.plain, rule.fix))
    return commands.emit(result, args, out)
