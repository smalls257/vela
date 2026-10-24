"""Where `vela` subcommands are wired to argparse, one module per command group (CLI/skill overhaul, Task 2).

The Violation this layout prevents is a Distributed Monolith in the repo itself: with every parser in `cli.py`, every
task that adds or extends a command edits the same file, and parallel work collides there. So:

- `MOVED` are the existing parsers later tasks extend (`check`, `explore`, `handoff`, `questions`, `where`). Their
  command functions stay in `cli.py`; only the argparse wiring lives in `commands/<name>.py`. `cli.build_parser`
  registers each where it used to sit, so `vela --help` keeps its order.
- `GROUPS` are the new command groups. Each module has a `register(sub)`; one that has nothing to offer yet adds no
  parser, so `vela --help` never lists a command that does nothing. A task adds its group's subcommands inside its
  own module and never touches `cli.py`.

Each command module prints through `emit`, the one place output reaches stdout for `say.Result`s, because the core
modules (`say.py` among them) only return text.
"""
import importlib
import traceback

from vela import errors, say

MOVED = ("check", "explore", "where", "questions", "handoff")
GROUPS = ("session", "record", "close", "guard", "conventions", "apply", "decide", "marks", "voice", "reviewers",
          "hook", "epics", "releases", "boundary", "prose", "whoami", "new", "add", "team", "map", "importer", "onboard", "library", "grill", "plans", "private_records")
# A group whose command is a Python keyword lives in a module named apart: `vela import` is commands/importer.py.
COMMAND_OF = {"importer": "import", "private_records": "records"}


def module(name):
    return importlib.import_module(f"vela.commands.{name}")


def register(sub, name):
    """Add one command module's parsers to the top-level subparsers."""
    module(name).register(sub)


def register_groups(sub):
    for name in GROUPS:
        register(sub, name)


def run(args, out):
    """Run a parsed command and return its exit code, the way every command means its codes (see `cli.main`): a
    ToolError is `vela: <message>` and 2, a leaked ID fails loudly at its source, and any other exception is a bug in
    vela, never a finding about the vault."""
    try:
        return args.func(args, out)
    except errors.ToolError as exc:
        print(f"vela: {exc}", file=out)
        return 2
    except say.LeadLeak as exc:  # a leak fails loudly at its source, never reaches the lead as a quiet code
        print(str(exc), file=out)
        return 2
    except Exception as exc:  # the tool failed; never report this as a vault finding
        print(f"vela: internal error: {exc!r}. This is a bug in vela, not in the vault.", file=out)
        traceback.print_exc(file=out)
        return 2


def emit(result, args, out, resolver=None):
    """Print a `say.Result` in the mode the flags chose, and return its exit code."""
    text = say.render(result, say.mode_of(args), resolver, more=getattr(args, "more", False))
    if text:
        print(text, file=out)
    return result.exit
