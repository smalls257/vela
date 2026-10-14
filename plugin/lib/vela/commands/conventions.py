"""`planner conventions "<section>"`: print one section of CONVENTIONS.md (CLI/skill overhaul, Task 30).

Why: skills told the model to read CONVENTIONS.md, a 21,000-word file, for one rule at a time. Reading one section is
what the skills meant. The load a session carries before its first question drops, and code stays the enforcer:
`planner check` holds the rules, CONVENTIONS is the format guide a person reads.

- An exact heading (case ignored, a leading `## ` ignored) prints that section and its subsections, exit 0.
- No exact heading: exit 1, "No section called X", and up to five near headings. Never the whole file: a reader who
  asked for one rule and silently got all of them is the load this command exists to remove.
- `--list` prints every heading with its word count, so a skill author can see what a citation costs.

It reads the vault's own CONVENTIONS.md (the rules the vault was made under) and, when the vault has none, the
installed plugin's copy, and says which on its first line, so a reader never mistakes one for the other.
"""
import pathlib

from vela import conventions, say
from vela.commands import emit


def register(sub):
    parser = sub.add_parser("conventions", help="print one section of CONVENTIONS.md, or --list the sections")
    parser.add_argument("section", nargs="?", default="", help='the section heading, like "Overrides" or "Fact bullets"')
    parser.add_argument("--vault", default=".", help="vault root (default: current directory)")
    parser.add_argument("--list", action="store_true", help="every section heading with its word count")
    parser.add_argument("--json", action="store_true", help="the structured result, for the skill to reason over")
    parser.set_defaults(func=cmd_conventions)


def source(vault):
    """(path, which, the line that says which). The vault's copy first; the plugin's when the vault has none."""
    from vela import cli  # cli knows where the installed plugin's copy is; loaded by the time a command runs
    mine = pathlib.Path(vault) / "CONVENTIONS.md"
    if mine.is_file():
        return mine, "vault", f"From the vault's CONVENTIONS.md ({mine})."
    plugin = cli.PLUGIN_CONVENTIONS
    if not plugin.is_file():
        raise cli.ToolError(f"the vault has no CONVENTIONS.md and the plugin's copy is missing at {plugin}; "
                            "reinstall the plugin.")
    return plugin, "plugin", f"The vault has no CONVENTIONS.md, so this is the installed plugin's copy ({plugin})."


def cmd_conventions(args, out):
    from vela import cli
    path, which, said = source(args.vault)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise cli.ToolError(f"cannot read {path}: {exc}") from exc
    found = conventions.sections(text)
    result = say.Result("conventions", data={"source": which, "path": str(path)})
    if args.list:
        result.data["sections"] = [{"title": s.title, "level": s.level, "words": s.words} for s in found]
        result.lines = [say.Line(said)] + [say.Line(f"{'  ' * (s.level - 1)}{s.title} ({s.words} words)") for s in found]
    elif not args.section.strip():
        result.exit = say.REFUSED
        result.lines = [say.Line('Name a section, like planner conventions "Overrides", or run planner conventions --list.')]
    else:
        result = answer(result, found, args.section, said)
    return emit(result, args, out)


def answer(result, found, name, said):
    hit = conventions.section(found, name)
    if hit is not None:
        result.data.update(section=hit.title, words=hit.words)
        result.lines = [say.Line(said), say.Line(hit.text)]
        return result
    close = conventions.near(found, name)
    result.exit = say.REFUSED
    result.data.update(section=None, near=close)
    lines = [f'No section called "{name.strip()}". {said}']
    if close:
        lines += ["Near matches:"] + [f"- {title}" for title in close]
    else:
        lines.append("No heading is close.")
    lines.append("planner conventions --list shows every section.")
    result.lines = [say.Line(line) for line in lines]
    return result
