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

from vela import say

MOVED = ("check", "explore", "where", "questions", "handoff")
GROUPS = ("session", "record", "close", "guard", "conventions", "apply", "decide", "marks", "voice", "reviewers",
          "hook", "epics", "releases", "boundary", "prose", "whoami")


def module(name):
    return importlib.import_module(f"vela.commands.{name}")


def register(sub, name):
    """Add one command module's parsers to the top-level subparsers."""
    module(name).register(sub)


def register_groups(sub):
    for name in GROUPS:
        register(sub, name)


def emit(result, args, out, resolver=None):
    """Print a `say.Result` in the mode the flags chose, and return its exit code."""
    text = say.render(result, say.mode_of(args), resolver)
    if text:
        print(text, file=out)
    return result.exit
