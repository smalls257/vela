"""The fast entry: the commands a chat waits on start without loading the whole CLI.

Every hook runs before and after every Bash call and every edit, and the companion panels run after every vault
write. Importing `vela.cli` costs 0.13 to 0.32 s of CPU before any work, and none of these commands needs it, so
`scripts/vela` sends them here. This module imports only the command registry and `say` (Computational Friction
ruled out); an import test holds it, so a later change cannot quietly drag the whole CLI back in.
"""
import argparse
import sys

from vela import commands

FAST = ("companion", "hook")  # why: the commands a chat waits on; neither needs the whole CLI


def serves(argv):
    """True when `argv` names a command this entry owns. A command listed in FAST but not yet wired into
    `commands.GROUPS` falls through to the full CLI and its usual "invalid choice" message."""
    return bool(argv) and argv[0] in FAST and argv[0] in commands.GROUPS


def build_parser():
    parser = argparse.ArgumentParser(prog="vela", description="Check and render an initiative vault.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in FAST:
        if name in commands.GROUPS:
            commands.register(sub, name)
    return parser


def main(argv, out=None):
    """Parse with only FAST's modules, then run through `commands.run` (the error mapping `cli.main` has)."""
    out = out or sys.stdout
    try:
        args, extras = build_parser().parse_known_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    if extras:
        print(f"vela: unrecognized arguments: {' '.join(extras)}", file=out)
        return 2
    return commands.run(args, out)
