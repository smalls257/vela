"""`vela plans [--vault DIR] [--here] [--paths]`: the plans a git repo holds, each in its own folder.

One docs repo may hold several plans: any folder with `.vela.yaml` is one, at the repo's root or in a subfolder
(`projects/heron/`). The plan's folder is the vault root for every other command. This command is how a skill, a
person finds those folders, so none of them guesses a path (Forensic Coding) or runs a command in the
repo's root where no plan lives.

- no flag: every plan in the repo `--vault` sits in, with its folder and title.
- `--here`: the one plan that holds `--vault`, found by walking up to the nearest `.vela.yaml` and stopping at the repo's
  root. Opened at a repo's root that holds several plans, it exits 3 with the plans by title for the lead to choose
  from; with exactly one plan below, that one; with none, exit 1 (`vela new` starts one).
- `--paths`: the folders only, one per line, relative to the repo's root (`.` for a plan at the root), for a shell loop.

Exit codes: 0 listed; 1 no plan; 2 git failed; 3 several plans and the lead has not said which.
"""
import pathlib

import yaml

from vela import commands, planscope, say
from vela.edge import plans

NAME = "plans"
UNNAMED = "New initiative"  # the template's title until the first session replaces it


def register(sub):
    one = sub.add_parser("plans", help="the plans this git repo holds, each in its own folder (a plan's folder is its "
                                       "vault root)")
    one.add_argument("--vault", default=".", help="any folder in the repo (default: current directory)")
    one.add_argument("--here", action="store_true",
                     help="only the plan that holds --vault; several below a repo's root exits 3 with the choices")
    one.add_argument("--paths", action="store_true", help="print the folders only, one per line, for a shell loop")
    say.add_output_flags(one)
    one.set_defaults(func=cmd_plans)


def read_config(folder):
    """(title, initiative) of the plan in `folder`. A `.vela.yaml` that cannot be read is named in the title, not hidden."""
    try:
        data = yaml.safe_load((folder / plans.CONFIG).read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return f"(unreadable .vela.yaml: {str(exc).splitlines()[0] if str(exc) else type(exc).__name__})", ""
    if not isinstance(data, dict):
        return "(unreadable .vela.yaml)", ""
    return str(data.get("title") or ""), str(data.get("initiative") or "")


def describe(folder, top):
    """One plan as a row: where it is, what it is called, and the name its branches carry."""
    title, initiative = read_config(folder)
    prefix = plans.prefix_of(folder, top)
    return {"folder": prefix.rstrip("/") or ".", "path": str(folder), "title": title, "initiative": initiative,
            "scope": planscope.slug_of(prefix)}


def said_name(row):
    """How the lead hears a plan: its title, or, while it still has the template's, the folder it lives in."""
    if row["title"] and row["title"] != UNNAMED and not row["title"].startswith("("):
        return row["title"]
    where = row["folder"].rsplit("/", 1)[-1].replace("-", " ").replace("_", " ")
    return f"the new plan in {where}" if row["folder"] != "." else "the new plan"


def find_rows(start):
    """(repo root or the folder itself, [rows]) for the plans in the repo `start` sits in. A folder in no repo holds the
    plans below it."""
    start = pathlib.Path(start).resolve()
    top = plans.repo_root(start) or start
    return top, [describe(folder, top) for folder in plans.plans_in(top)]


def folder_of(row):
    return "" if row["folder"] == "." else row["folder"] + "/"


def names(rows):
    return say.names_said([said_name(row) for row in rows])


def no_plan():
    return say.Result(NAME, exit=say.REFUSED, refusals=[say.Refusal(
        "no-plan", "There's no plan in this folder or the repository around it yet.",
        'start one with vela new --title "<initiative name>" in the folder it should live in', "",
        recommend="I'd start one here, if you give me its name.", waiver="")])


def which_plan(rows):
    choices = [{"folder": row["folder"], "title": row["title"], "said": said_name(row)} for row in rows]
    line = say.Line("vela plans: several plans here and none named: " + "; ".join(
        f"{row['folder']} ({row['title']})" for row in rows) + ". Run again with --vault <folder>.",
                    plain=f"There's more than one plan here: {names(rows)}. Which one are we working on?")
    return say.Result(NAME, exit=say.NEEDS_LEAD, lines=[line], needs_lead=[{
        "ask": "which plan", "question": "Which plan are we working on?", "choices": choices,
        "answer_with": "--vault <folder>"}], data={"plans": rows})


def here(start, top, rows):
    """(rows, None) for the one plan that holds `start`, or (rows, the Result that ends the command)."""
    above = plans.plan_above(start)
    if above is not None:
        return [row for row in rows if row["path"] == str(above)] or [describe(above, top)], None
    if len(rows) == 1:
        return rows, None
    return rows, (no_plan() if not rows else which_plan(rows))


def listing(rows):
    if not rows:
        said = "There's no plan here yet."
    elif len(rows) == 1:
        said = f"There's one plan here: {names(rows)}."
    else:
        said = f"There are {say.count_words(len(rows))} plans here: {names(rows)}."
    lines = [say.Line(f"vela plans: {len(rows)} plan{'s' if len(rows) != 1 else ''}.", plain=said)]
    lines += [say.Line(f"  {row['folder']}: {row['title']}", audience=say.MODEL) for row in rows]
    return lines


def cmd_plans(args, out):
    from vela import cli
    start = pathlib.Path(args.vault).resolve()
    if not start.is_dir():
        raise cli.ToolError(f"{start} is not a folder.")
    top, rows = find_rows(start)
    held = len(rows)
    ended = None
    if args.here:
        rows, ended = here(start, top, rows)
    if ended is not None:
        return commands.emit(ended, args, out)
    if args.paths:
        for row in rows:
            print(row["folder"], file=out)
        return say.DONE if held else say.REFUSED
    shared = planscope.duplicate_slugs([folder_of(row) for row in rows])
    result = say.Result(NAME, lines=listing(rows), data={"repo": str(top), "plans": rows, "duplicate_names": shared})
    for slug, folders in shared.items():
        result.lines.append(say.Line(f"vela plans: {', '.join(folders)} all go by '{slug}', so their session branches and "
                                     "pull request titles share one name; rename a folder.", audience=say.MODEL))
    if not held:
        result.exit = say.REFUSED
    return commands.emit(result, args, out)
