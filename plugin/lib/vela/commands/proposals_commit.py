"""`vela proposals commit --step conflicts|edit|render`: the owner's own commits while reviewing a reader's proposal.

Why a command: the proposals skill used to tell the model to `git -C <worktree> add -- <file>` and `commit -am`, so a
review was the one place a model still staged by hand. Once the Claude Code hook denies every model-run `git add`
(plan Task 24), that skill would break, and anywhere the hook doesn't fire it would stage whatever sat in the worktree.
So the three commits a review makes go through here, by exact path (Shield: the review keeps its own steps; the
staging rule stays in `guard.py`):

- `conflicts`: after the owner settled each conflicted file. A three-way apply that conflicted left the reader's other
  changes staged, so this commit carries them too. A file that still holds a conflict marker line (`<<<<<<<`,
  `=======`, `>>>>>>>`) is refused by name and nothing is committed, because committing markers is a Silent Fallback:
  the conflict reads as resolved and the page breaks for every later reader.
- `edit --group KEY`: the owner's edit of one group, as `Edit <KEY> from the proposal`; the hash it prints is what
  `proposals answer` records for an `edited` group.
- `render`: what `vela render` rewrote after the review.

Every changed file in the worktree is staged by exact path except the ones `guard.py` says a commit may never carry
(the inbox, private voice folders, vela's working files), which are named and left out; the whole index is checked
against the same rules before the commit. Only a `proposal/` branch's worktree is accepted, as for `accept` and
`reject`.

Exit codes: 0 committed; 1 refused (markers left, a conflict still open, nothing changed, or a forbidden file already
staged), nothing committed; 2 not a proposal worktree, a missing `--group`, or git failed.
"""
import re

from vela import guard, say
from vela.edge import reviewgit, stagegit, vaultgit

MESSAGES = {"conflicts": "Resolve proposal conflicts", "edit": "Edit {group} from the proposal",
            "render": "Render after reviewing the proposal"}
CONFLICT_LINE = re.compile(rb"^(<{7}|>{7})( |$)|^={7}$", re.M)


def register_proposals(steps):
    one = steps.add_parser("commit", help="commit the owner's own step in a proposal's worktree (conflicts settled, "
                                          "an edit to one group, or what render rewrote), by exact path")
    one.add_argument("--vault", default=".", help="the proposal's worktree (default: current directory)")
    one.add_argument("--step", required=True, choices=sorted(MESSAGES),
                     help="conflicts: every conflicted file is settled; edit: the owner edited one group (needs "
                          "--group); render: vela render rewrote pages")
    one.add_argument("--group", help="with --step edit: the group key, as `vela proposals review` listed it")
    say.add_output_flags(one)
    one.set_defaults(func=cmd_proposals_commit)


def vault_relative(path, prefix):
    return path[len(prefix):] if prefix and path.startswith(prefix) else path


def markers_left(top, paths):
    """The paths whose bytes still hold a conflict marker line. Read as bytes, so a file that isn't UTF-8 is judged
    too; a deleted file has none. An unreadable file raises OSError, which the caller turns into exit 2."""
    return [path for path in paths if (top / path).is_file() and CONFLICT_LINE.search((top / path).read_bytes())]


def refuse(result, key, plain, fix):
    result.exit = say.REFUSED
    result.refusals.append(say.Refusal(key, plain, fix))


def why_not(top, stage, already):
    """The refusal that stops this commit, as (key, plain, fix), or None when it may go ahead."""
    marked = markers_left(top, stage)
    if marked:
        return ("conflict-markers", "A page still has both versions of a change marked in it, so I haven't saved "
                "anything.", "Settle each conflict with the owner and remove the marker lines in: " + ", ".join(marked)
                + ". Then run this again.")
    open_conflicts = [p for p in reviewgit.unmerged(top) if p not in stage]
    if open_conflicts:
        return ("conflicts-open", "Some changes still clash, so I haven't saved anything.",
                "Settle these first, then run `vela proposals commit --step conflicts`: " + ", ".join(open_conflicts))
    if not stage and not already:
        return ("nothing-changed", "Nothing has changed since the last save, so there's nothing to save.",
                "Make the change first, or skip this step.")
    return None


def commit_step(top, prefix, stage, message):
    """Stage `stage` by exact path, check the whole index against guard.py, and commit it. Returns (hash, forbidden):
    a forbidden path already in the index (put there by hand) stops the commit, named, before git runs it."""
    deleted = set(stagegit.staged_deletions(top))  # already gone from the index: naming it again fails the add
    stagegit.stage(top, [p for p in stage if p not in deleted])
    forbidden = guard.forbidden([vault_relative(p, prefix) for p in stagegit.staged_paths(top)])
    if forbidden:
        return None, forbidden
    return stagegit.commit_index(top, message), []


def cmd_proposals_commit(args, out):
    from vela import cli, commands
    if args.step == "edit" and not (args.group or "").strip():
        raise cli.ToolError("--step edit needs --group <key>, the group the owner edited, as `vela proposals review` "
                            "listed it.")
    top, vault_dir, branch = cli.worktree_vault(args)
    result = say.Result("proposals commit")
    try:
        prefix = reviewgit.prefix(vault_dir)
        changed = stagegit.changed_paths(top)
        never = [(p, rule) for p, rule in ((p, guard.never_rule(vault_relative(p, prefix))) for p in changed) if rule]
        stage = [p for p in changed if p not in {p for p, _ in never}]
        stop = why_not(top, stage, stagegit.staged_paths(top) + stagegit.staged_deletions(top))
        if stop:
            refuse(result, *stop)
            return commands.emit(result, args, out)
        message = MESSAGES[args.step].format(group=(args.group or "").strip())
        commit, forbidden = commit_step(top, prefix, stage, message)
    except vaultgit.GitUnavailable as exc:
        raise cli.ToolError(f"git stopped the commit: {exc}") from exc
    except OSError as exc:
        raise cli.ToolError(f"couldn't read a changed file to look for conflict markers: {exc}") from exc
    if forbidden:
        for rule in guard.rules_hit(forbidden):
            refuse(result, rule.key, rule.plain, "Take it out of the index, keeping the file: git rm --cached -- "
                   + " ".join(p for p, r in forbidden if r.key == rule.key))
        return commands.emit(result, args, out)
    result.data = {"commit": commit, "message": message, "staged": stage, "branch": branch,
                   "left_out": [{"path": p, "rule": r.key} for p, r in never]}
    result.wrote = stage
    result.lines.append(say.Line(f"vela proposals commit: committed {commit} on {branch}: {message}",
                                 "Saved the owner's change on the proposal's own copy."))
    for rule in guard.rules_hit([(vault_relative(p, prefix), r) for p, r in never]):
        left = ", ".join(p for p, r in never if r.key == rule.key)
        result.lines.append(say.Line(f"  left out ({rule.key}): {left}", rule.plain))
    return commands.emit(result, args, out)
