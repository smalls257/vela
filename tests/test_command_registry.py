"""The command registry (overhaul Task 2): new commands register from `planner/commands/`, and the moved parsers still
take every call the skills and references write."""
import re
import shlex
import sys
import types

from conftest import REPO
from planner import cli, commands

MOVED_CALL = re.compile(r"`(?:python3 [^`]*?scripts/planner|planner) (check|explore|handoff|questions|where)(?![\w-])([^`]*)`")


def test_every_group_module_registers_without_touching_cli(monkeypatch):
    fake = types.ModuleType("planner.commands.demo")
    fake.register = lambda sub: sub.add_parser("demo-command").set_defaults(func=lambda args, out: 0)
    monkeypatch.setitem(sys.modules, "planner.commands.demo", fake)
    monkeypatch.setattr(commands, "GROUPS", commands.GROUPS + ("demo",))
    args = cli.build_parser().parse_args(["demo-command"])
    assert args.func(args, None) == 0
    for name in commands.GROUPS[:-1] + commands.MOVED:
        assert callable(commands.module(name).register), name


def test_a_group_with_nothing_built_adds_no_command():
    """`planner --help` never lists a command that does nothing: an unbuilt group registers no parser."""
    names = set(cli.build_parser()._subparsers._group_actions[0].choices)
    for name in ("apply", "decide", "marks", "epics", "boundary"):
        assert name not in names, name
    assert {"check", "explore", "where", "questions", "handoff", "capture"} <= names


def calls_in_docs():
    paths = list((REPO / "plugin" / "skills").rglob("*.md")) + list((REPO / "plugin" / "references").glob("*.md"))
    for path in paths:
        for match in MOVED_CALL.finditer(path.read_text(encoding="utf-8")):
            yield path.relative_to(REPO), match.group(1), match.group(2)


def words(rest):
    text = re.sub(r"<[^>]*>", "X", rest).replace("...", "").replace("…", "")
    text = re.split(r"\s(?:>|\||&&|2>)\s", text)[0]  # the shell's part of the line, not the command's
    return shlex.split(text)


def test_moved_parsers_parse_every_existing_call():
    parser = cli.build_parser()
    seen = 0
    for path, command, rest in calls_in_docs():
        if not rest.strip():  # the command named in prose ("`planner handoff` writes ..."), not a call
            continue
        argv = [command] + words(rest)
        try:
            args, extras = parser.parse_known_args(argv)
        except SystemExit:
            raise AssertionError(f"{path}: `planner {command}{rest}` no longer parses")
        assert not extras, (path, argv, extras)
        seen += 1
    assert seen >= 15, seen
