"""`vela close stage`: stage a close's files from the allow-list, by exact path, and optionally commit them.

Why it is a command and not a skill sentence: "never `git add -A`" sat in the close skill four times and still could
not stop a model that typed `git add .`. A deny-list of spellings misses the next spelling (Paper Tiger), so the
allow-list in `guard.py` decides what a close stages and this command is the only thing that stages it. A file outside
the list is named and left out, never swept in quietly: a stray change in a close commit is how the owner's scratch
notes, or the inbox, reach a pull request.

Exit codes: 0 staged (and committed, with a commit flag); 1 something changed that the allow-list leaves out or
forbids, named in the output. The allowed files are still staged and committed, because a stray file is the lead's
to deal with, not a reason to lose the session's work; the commit holds the allowed paths only (`--only`), so a left-out
file cannot ride along even if something else staged it. 2 git failed; 3 the session is not clear (none open, or
several): nothing was staged.

The commit flags carry the close skill's own messages:
- `--draft`: `draft: prose for <id>`, the drafted pages whole, so the reviewer's later edits show as a diff against it.
- `--checkpoint`: `Checkpoint <id>`, because a merge refuses to run over uncommitted edits (`close sync-main` says when).
- `--close`: `Close session <id>`, after the record says `status: closed`.

A reader copy (`.vela/workspace.json`, no `.git`) has no git, so nothing is run at all: the record is the reader's
work, and it reaches the owner through a proposal.
"""
import pathlib

from vela import guard, parse, roles, say
from vela.edge import stagegit, vaultgit

MESSAGES = {"draft": "draft: prose for {id}", "checkpoint": "Checkpoint {id}", "close": "Close session {id}"}


def register_close(steps):
    stage = steps.add_parser("stage", help="stage this session's files by exact path from the allow-list; anything "
                                           "else that changed is named and left out")
    stage.add_argument("--vault", default=".", help="vault root (default: current directory)")
    stage.add_argument("--session", help="the session id; default: the one record in sessions/ that says status: open")
    which = stage.add_mutually_exclusive_group()
    which.add_argument("--draft", dest="commit", action="store_const", const="draft",
                       help="then commit as `draft: prose for <id>`")
    which.add_argument("--checkpoint", dest="commit", action="store_const", const="checkpoint",
                       help="then commit as `Checkpoint <id>`, before a merge")
    which.add_argument("--close", dest="commit", action="store_const", const="close",
                       help="then commit as `Close session <id>`")
    stage.add_argument("--paths-from-render", action="store_true",
                       help="first check that render has nothing left to rewrite, so the staged pages are its output")
    say.add_output_flags(stage)
    stage.set_defaults(func=cmd_close_stage)


def is_reader_copy(root):
    """Decided from the disk alone, by the same rule `roles` applies, so a reader copy runs no git at all."""
    facts = roles.Facts(git_here=(root / ".git").exists(), has_workspace=(root / ".vela" / "workspace.json").is_file())
    return facts.has_workspace and not facts.git_here and roles.decide(facts).role == roles.READER


def open_records(root):
    """Ids of the records in sessions/ whose frontmatter says `status: open`, in name order.

    Minimal on purpose: the working tree only. Task 6a's `session open` picker also reads `session/*` branches and
    shared answer branches; once it lands, this should call it instead of reading the folder."""
    found = []
    for path in sorted((root / "sessions").glob("*.md")):
        meta, _, error = parse.split_frontmatter(path.read_text(encoding="utf-8"))
        if error is None and str(meta.get("status", "")).strip() == "open":
            found.append(path.stem)
    return found


def session_id(args, root, result):
    """The session to file, or None after filling `result` with the exit-3 choice."""
    if args.session:
        if "/" in args.session or "\\" in args.session or args.session.endswith(".md"):
            raise ValueError(f"--session takes the id alone (the record's file name without .md), not {args.session!r}")
        return args.session
    records = open_records(root)
    if len(records) == 1:
        return records[0]
    result.exit = say.NEEDS_LEAD
    if records:
        result.needs_lead = records
        result.lines.append(say.Line(f"vela close stage: {len(records)} records are open: {', '.join(records)}. "
                                     "Run again with --session <id>. Nothing was staged.",
                                     "More than one session is open here, so I need to know which one to file."))
    else:
        result.needs_lead = ["--session <id>"]
        result.lines.append(say.Line("vela close stage: no record in sessions/ says status: open. Run again with "
                                     "--session <id>. Nothing was staged.",
                                     "I couldn't find an open session here, so I haven't staged anything."))
    return None


def stale_render(root):
    """Pages render would still rewrite, or the count of problems that stop render. Loaded through cli, the shell."""
    from vela import cli, render
    texts, _, _, refusals = render.render_vault(cli.load_vault(root))
    if refusals:
        return [], len(refusals)
    stale = [path for path, text in sorted(texts.items())
             if (root / path).read_text(encoding="utf-8").replace("\r\n", "\n").lstrip("﻿") != text]
    return stale, 0


def render_refusal(stale, problems):
    if problems:
        detail = f"render cannot run: {problems} problems (run vela render to see them)"
    else:
        detail = "render would still rewrite " + ", ".join(stale)
    return say.Refusal("render-current", "Some generated tables are out of date, so I haven't staged anything yet.",
                       f"Run vela render, then close stage again. ({detail})")


def vault_pages(paths):
    from vela import cli
    return {p for p in paths if p.endswith(".md") and cli.page_kind(p) == "page"}


def lead_name(path):
    """A path the lead may hear: as it is, unless it holds something the lead check forbids (`ADR-0004-x.md`)."""
    if say.leak_in(path) is None:
        return path
    folder = path.rsplit("/", 1)[0] if "/" in path else ""
    return f"a file in {folder}" if folder and say.leak_in(folder) is None else "one more file"


def lead_summary(plan, committed):
    rest = [p for p in plan.stage if not p.startswith((guard.SESSIONS, guard.EXAMPLES))]
    pages = sum(1 for p in rest if p.endswith(".md"))
    parts = [f"{pages} changed page{'s' if pages != 1 else ''}"] if pages else []
    if len(rest) > pages:
        others = len(rest) - pages
        parts.append(f"{others} settings file{'s' if others != 1 else ''}")
    if any(p.startswith(guard.SESSIONS) for p in plan.stage):
        parts.append("the session record")
    examples = sum(1 for p in plan.stage if p.startswith(guard.EXAMPLES))
    if examples:
        parts.append(f"{examples} voice example{'s' if examples != 1 else ''}")
    if not parts:
        return "Nothing this session changed needed staging."
    said = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"I've {'committed' if committed else 'staged'} {said}."


def report(result, plan, commit_line, committed, mode):
    for rule in guard.rules_hit(plan.never):
        paths = [p for p, r in plan.never if r.key == rule.key]
        result.refusals.append(say.Refusal(rule.key, rule.plain, f"{rule.fix} Left out: {', '.join(paths)}."))
    if mode == "for-lead":
        result.lines.append(say.Line("", lead_summary(plan, committed)))
        if plan.left:
            names = [lead_name(p) for p, _ in plan.left]
            result.lines.append(say.Line("", f"{len(names)} other changed file{'s' if len(names) != 1 else ''} "
                                             f"{'aren' if len(names) != 1 else 'isn'}'t part of this session, so I've "
                                             f"left {'them' if len(names) != 1 else 'it'} out: {', '.join(names)}."))
        return
    result.lines.append(say.Line(f"vela close stage: staged {len(plan.stage)}, left out {len(plan.left)}, "
                                 f"never staged {len(plan.never)}."))
    result.lines += [say.Line(f"  staged: {p}") for p in plan.stage]
    result.lines += [say.Line(f"  left out: {p} ({why})") for p, why in plan.left]
    if commit_line:
        result.lines.append(say.Line(commit_line))


def cmd_close_stage(args, out):
    from vela import cli
    root = pathlib.Path(args.vault).resolve()
    mode = say.mode_of(args)
    result = say.Result("close stage")
    if is_reader_copy(root):
        result.lines.append(say.Line("vela close stage: this is a read copy, so nothing is staged or committed.",
                                     "This is a read copy, so nothing is staged or committed here."))
        return cli_emit(result, args, out)
    try:
        ident = session_id(args, root, result)
    except ValueError as exc:
        raise cli.ToolError(str(exc)) from exc
    if ident is None:
        return cli_emit(result, args, out)
    if args.paths_from_render:
        stale, problems = stale_render(root)
        if stale or problems:
            result.exit = say.REFUSED
            result.refusals.append(render_refusal(stale, problems))
            return cli_emit(result, args, out)
    try:
        changed = stagegit.changed_paths(root)
        plan = guard.plan(changed, vault_pages(changed), ident)
        stagegit.stage(root, list(plan.stage))
        commit_line, committed = "", False
        if args.commit and plan.stage:
            message = MESSAGES[args.commit].format(id=ident)
            commit_line = f"committed {stagegit.commit(root, message, list(plan.stage))}: {message}"
            committed = True
        elif args.commit:
            commit_line = "nothing to commit: no allow-listed file changed"
    except vaultgit.GitUnavailable as exc:
        raise cli.ToolError(f"close stage: {exc}") from exc
    result.data = {"session": ident, "staged": list(plan.stage),
                   "left": [{"path": p, "reason": why} for p, why in plan.left],
                   "never": [{"path": p, "rule": r.key, "reason": r.plain} for p, r in plan.never],
                   "commit": commit_line or None}
    result.wrote = list(plan.stage)
    result.exit = say.REFUSED if (plan.left or plan.never) else say.DONE
    report(result, plan, commit_line, committed, mode)
    return cli_emit(result, args, out)


def cli_emit(result, args, out):
    from vela import commands
    return commands.emit(result, args, out)
