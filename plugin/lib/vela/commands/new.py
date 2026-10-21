"""`vela new --title "<name>" [--handle H] [--initiative INI-nnn]`: start a plan in this folder from the plugin's own
template, with nothing installed but the plugin.

Why it is a command: the plugin from the marketplace ships no template path a person can copy, and the 12-step checklist
it replaced had a model setting a plan up by hand, then hitting the hook that denies `git add` in a plan (only vela
stages). A Paper Tiger would be a command that copies files and leaves the first commit to the model; this one ends
with the first commit, made by `stagegit` (the code path `vela close stage` commits through), staging exactly the
template's files and nothing else.

What it refuses (exit 1, nothing changed): a folder that already holds `.vela.yaml` or `.vela/`; a folder inside another
repository's work tree; a folder with an entry named like one of the template's top-level entries (listed). It never
overwrites. Material the folder already held goes into `.inbox/`, which the template's `.gitignore` keeps out of every
commit and `vela conventions` names as where documents dropped for Discover live; what the folder's own repository
already tracks stays where it is.

Exit codes: 0 started; 1 refused; 2 git, the disk or the new plan's own check failed; 3 needs the lead (the initiative's
name, or the GitHub handle when `gh` doesn't know it): nothing changed, and `--json` carries `needs_lead`.
"""
import argparse
import datetime
import io
import os
import pathlib
import shutil

from vela import commands, newplan, rules, say
from vela.edge import hostprobe, sessiongit, stagegit, vaultgit
from vela.edge.vaultgit import GitUnavailable
from vela.onboardpath import HANDLE

NAME = "new"
TEMPLATE = pathlib.Path(__file__).resolve().parents[3] / "template"
FIRST_COMMIT = "Start the plan"
GIT_DETAIL = "The details are in my notes."


def register(sub):
    new = sub.add_parser("new", help="start a plan in this folder from the plugin's template: files, a clean check "
                                     "and the first commit")
    new.add_argument("--vault", default=".", help="the folder to start the plan in (default: current directory)")
    new.add_argument("--title", default="", help="the initiative's name, in the lead's words")
    new.add_argument("--handle", default="", metavar="HANDLE",
                     help="the lead's GitHub handle (default: the one gh knows, else exit 3 asks for it)")
    new.add_argument("--initiative", default="INI-001", metavar="INI-nnn", help="the initiative's ID (default: INI-001)")
    say.add_output_flags(new)
    new.set_defaults(func=cmd_new)


def cmd_new(args, out):
    from vela import cli
    folder = pathlib.Path(args.vault).resolve()
    if not folder.is_dir():
        raise cli.ToolError(f"{folder} is not a folder, so there is nowhere to start a plan.")
    try:
        result = start_plan(folder, args)
    except GitUnavailable as exc:
        result = say.Result(NAME, exit=say.FAILED, lines=[
            say.Line(f"vela: {exc}", plain=f"Git failed while starting the plan. {GIT_DETAIL}")])
    except OSError as exc:  # atomic.WriteFailed among them
        result = say.Result(NAME, exit=say.FAILED, lines=[
            say.Line(f"vela: couldn't write: {exc}", plain="I couldn't write the plan's files to disk, so I stopped.")])
    return commands.emit(result, args, out)


def refused(rule, plain, fix, recommend):
    return say.Result(NAME, exit=say.REFUSED, refusals=[say.Refusal(rule, plain, fix, "nothing to override: it would "
                      "overwrite or tangle someone's files", recommend=recommend, waiver="")])


def template_files():
    """(relative posix path, source) for every file the template ships, in name order."""
    if not (TEMPLATE / ".vela.yaml").is_file():
        raise GitUnavailable(f"the plugin's template is missing at {TEMPLATE}; reinstall the plugin")
    found = []
    for path in sorted(TEMPLATE.rglob("*")):
        rel = path.relative_to(TEMPLATE)
        if path.is_file() and path.name not in newplan.SKIPPED_FILES and not set(rel.parts) & set(newplan.SKIPPED_FOLDERS):
            found.append((rel.as_posix(), path))
    return found


def enclosing_repo(folder):
    """The work tree this folder sits in, or None. Anything git says besides "not a repository" is a failure."""
    code, out, err = vaultgit.run_git(folder, "rev-parse", "--show-toplevel")
    if code == 0:
        return pathlib.Path(out).resolve()
    if "not a git repository" in err.lower():
        return None
    raise GitUnavailable(f"git rev-parse failed: {err}")


def tracked_names(folder):
    code, out, err = vaultgit.run_git(folder, "ls-files", "-z", binary=True)
    if code != 0:
        raise GitUnavailable(f"git ls-files failed: {err}")
    return {field.decode("utf-8").split("/", 1)[0] for field in out.split(b"\0") if field}


def known_handle(folder, given):
    """(handle, None) or (None, why-not). A handle given wins; else the one gh knows; vela whoami's order without its cache."""
    if given.strip():
        handle = given.strip().lstrip("@")
        return (handle, None) if HANDLE.match(handle) else (None, f"'{given}' isn't a GitHub handle")
    ran = sessiongit.gh(folder, "api", "user", "-q", ".login")
    login = ran.out.strip() if ran.how == "ok" else ""
    return (login, None) if HANDLE.match(login) else (None, "gh didn't say")


def commit_identity_missing(folder):
    for key in ("user.name", "user.email"):
        code, value, _ = vaultgit.run_git(folder, "config", key)
        if code != 0 or not value:
            return key
    return ""


def folder_refusal(folder, files, entries):
    """The refusal that stops this folder from becoming a plan, or None."""
    if (folder / ".vela.yaml").exists() or (folder / ".vela").exists():
        return refused("plan-exists", "There's already a plan in this folder, so I haven't started another.",
                       "open that plan, or start the new one in an empty folder",
                       "I'd start the new plan in a new folder.")
    repo = enclosing_repo(folder)
    if repo is not None and repo != folder:
        return refused("inside-repo", f"This folder is inside another project's git repository ({repo.name}), and a plan "
                       "needs a repository of its own.", f"start the plan in a folder outside {repo}",
                       "I'd start the plan in a new folder outside that project.")
    clash = newplan.clashes([rel for rel, _ in files], entries)
    if clash:
        shown = [n for n in clash if say.leak_in(n) is None]
        said = say.names_said(shown + ([f"{say.count_words(len(clash) - len(shown))} more"] if len(shown) < len(clash) else []))
        result = refused("name-clash", f"These are already in this folder under names the plan uses: {said}. I haven't "
                         "changed anything, because I won't overwrite your files.",
                         f"rename or move these first: {', '.join(clash)}", "I'd move them to another folder, then start the plan.")
        return result
    return None


def what_is_missing(args, folder):
    """(title, handle, needs_lead, refusal): everything the lead must still say, all at once."""
    needs, title, handle = [], None, None
    try:
        title = newplan.clean_title(args.title) if args.title.strip() else None
    except newplan.NotAPlanTitle:
        title = None
    if title is None:
        needs.append({"ask": "title", "question": newplan.TITLE_QUESTION, "answer_with": '--title "<name>"'})
    handle, why = known_handle(folder, args.handle)
    if handle is None and args.handle.strip():
        return None, None, [], refused("handle", f"'{args.handle}' isn't a GitHub handle: letters, digits and hyphens, "
                                       "up to 39.", "ask the lead for the name after the @ on their GitHub profile",
                                       "I'd ask for their handle again.")
    if handle is None:
        needs.append({"ask": "handle", "question": newplan.HANDLE_QUESTION, "answer_with": "--handle <handle>"})
    return title, handle, needs, None


def start_plan(folder, args):
    from vela import cli
    files = template_files()
    entries = sorted(p.name for p in folder.iterdir())
    stop = folder_refusal(folder, files, entries)
    if stop is not None:
        return stop
    if not newplan.is_initiative(args.initiative):
        return refused("initiative", f"'{args.initiative}' isn't an initiative number: INI- and three digits.",
                       "use --initiative INI-001 style", "I'd use the next free number, such as INI-001.")
    title, handle, needs, bad = what_is_missing(args, folder)
    if bad is not None:
        return bad
    if needs:
        return say.Result(NAME, exit=say.NEEDS_LEAD, needs_lead=needs, lines=[
            say.Line(f"vela new: I need {say.names_said([n['ask'] for n in needs])} first: " + " ".join(
                n["question"] + f" Run again with {n['answer_with']}." for n in needs), plain=n["question"])
            for n in needs])
    missing = commit_identity_missing(folder)
    if missing:
        return say.Result(NAME, exit=say.FAILED, lines=[say.Line(
            f"vela: git has no {missing}, so the first commit can't be made. Set it with git config --global {missing} "
            "<value> and run vela new again.", plain="Git doesn't have your name and email yet, so it can't save the "
            "plan's first version. Set them once in git's settings, then I'll start again.")])
    return make_plan(folder, args, files, entries, title, handle, cli)


def make_plan(folder, args, files, entries, title, handle, cli):
    repo = enclosing_repo(folder)
    tracked = tracked_names(folder) if repo is not None else set()
    moving = newplan.to_inbox(entries, tracked)
    inbox = folder / newplan.INBOX
    taken = newplan.inbox_clashes(moving, [p.name for p in inbox.iterdir()] if inbox.is_dir() else [])
    if taken:
        return refused("inbox-clash", "The folder's inbox already holds files with the same names as things I'd move into "
                       "it, so I haven't changed anything.", f"rename these first: {', '.join(taken)}",
                       "I'd rename them, then start the plan.")
    if repo is None:
        code, _, err = vaultgit.run_git(folder, "init", "-q", "-b", "main")
        if code != 0:
            raise GitUnavailable(f"git init failed: {err}")
    for name in moving:
        inbox.mkdir(exist_ok=True)
        shutil.move(str(folder / name), str(inbox / name))
    copy_template(folder, files, args.initiative, title, handle)
    rendered = io.StringIO()
    if cli.cmd_render(argparse.Namespace(vault=str(folder), discard_edits=False), rendered) != 0:
        return failed_check("render stopped", rendered.getvalue())
    errors, warnings, first = new_plan_check(folder, cli)
    if errors:
        return failed_check(f"the new plan's own check found {errors} errors", "\n".join(first))
    paths = [rel for rel, _ in files]
    stagegit.stage(folder, paths)
    commit = stagegit.commit(folder, FIRST_COMMIT, paths)
    sessiongit.write_text(folder, sessiongit.HANDLE_FILE, handle + "\n")
    return started(folder, args, title, handle, len(paths), commit, moving, warnings)


def copy_template(folder, files, initiative, title, handle):
    for rel, source in files:
        target = folder / rel
        if target.exists():
            raise GitUnavailable(f"vela bug: {rel} is already here and would be overwritten")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        raw = source.read_bytes()
        if b"\0" in raw:
            continue  # a binary file has no handle to fill
        text = raw.decode("utf-8")
        filled = newplan.vela_yaml(text, initiative, title) if rel == ".vela.yaml" else newplan.with_handle(text, handle)
        if filled != text:
            target.write_bytes(filled.encode("utf-8"))


def new_plan_check(folder, cli):
    vault = cli.load_vault(folder)
    findings = rules.check(vault, datetime.date.today()) + cli.vault_file_findings(folder)
    errors = [f for f in findings if f.is_error]
    return len(errors), len(findings) - len(errors), [f.format() for f in errors[:5]]


def failed_check(what, detail):
    return say.Result(NAME, exit=say.FAILED, lines=[
        say.Line(f"vela bug: {what}, so nothing was committed. The files are in the folder.\n{detail}",
                 plain="Something went wrong on my side while setting up the plan, so I stopped before saving it.")])


def started(folder, args, title, handle, count, commit, moved, warnings):
    lines = [say.Line(f"vela new: started {args.initiative} {title!r} for @{handle} in {folder}: {count} files, committed "
                      f"{commit}: {FIRST_COMMIT}.", plain="I've started the plan in this folder and saved its first version."),
             say.Line(f"vela check: 0 errors, {warnings} warnings.", plain="", audience=say.MODEL)]
    if moved:
        lines.append(say.Line(f"vela new: moved {len(moved)} existing entries into .inbox/ (never committed): "
                              f"{', '.join(moved)}.", plain="What was already in this folder is in the plan's inbox "
                              "now. The plan never saves the inbox, and Discover reads from it."))
    lines.append(say.Line("Left for a person: a GitHub repository, the required check, Obsidian (see README.md).",
                          plain="What's left for you is in the plan's README: GitHub, the required check and Obsidian."))
    return say.Result(NAME, lines=lines, wrote=[], data={
        "folder": str(folder), "initiative": args.initiative, "title": title, "handle": handle, "commit": commit,
        "files": count, "moved_to_inbox": moved, "check": {"errors": 0, "warnings": warnings}})
