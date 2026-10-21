"""Every `vela` call a skill or reference writes parses with the real parser (overhaul plan Task 3, 8.1).

A skill that tells the model to run a command or flag that no longer exists passes every text pin and fails the first
live session that follows it: a Paper Tiger the free checks could not see. This test reads each call from the code spans
and fenced blocks of `plugin/skills/**/*.md` and `plugin/references/*.md`, in every form the skills use (`vela <cmd>`,
`python3 ${CLAUDE_SKILL_DIR}/../../scripts/vela <cmd>`, `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela <cmd>`), puts a
dummy value in each placeholder, and parses it with `vela.cli.build_parser()`. A failure names the file, the line and
the command, so the fix is in the skill or the parser, never a guess.

It generalizes tests/test_command_registry.py::test_moved_parsers_parse_every_existing_call, which covers only the
commands that moved into the registry.
"""
import contextlib
import io
import re
import shlex

import pytest

from conftest import REPO
from vela import cli

DOCS = sorted((REPO / "plugin" / "skills").rglob("*.md")) + sorted((REPO / "plugin" / "references").glob("*.md"))
FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.S | re.M)
SPAN = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
# The program in any form a skill writes it, then the rest of the call. A path to the program is a call wherever it
# stands; a bare `vela` only where a command starts (the line's start, after env settings, or after `&&`, `|`, `;`, `$(`),
# so quoted output such as "(vela check reports it as E105)" is not read as one.
PROGRAM = re.compile(r"(?:(?:^|(?<=[\s(\"'=]))(?:(?:python3|sh)\s+)?[^\s`\"'()]*/(?:scripts/(?:run-)?vela|bin/vela)"
                     r"|(?:^\s*(?:\$\s+)?(?:[A-Z_]+=\S*\s+)*|(?<=&&\s)|(?<=\|\s)|(?<=;\s)|(?<=\$\()|(?<=!\s)|(?<=python3\s))vela)"
                     r"\s+(?P<rest>.*)$")
# Where the shell's part of a line starts: a pipe, a redirect, a chain, a comment.
SHELL = re.compile(r"\s(?:\||\|\||&&|;|>|>>|2>\S*|<<-?\s*'?\w+'?|#|-->|\))(?:\s|$)")
# Words that are prose after "vela", not a command: "vela itself", "vela bug: ...".
NOT_A_CALL = {"bug:"}
COMMAND_WORD = re.compile(r"^[a-z][a-z-]*:?$")  # "${CACHE}/cache/*/vela" after a path is a glob, not a command

# Calls a skill writes today that do not parse, each with where it is and why. A finding for the skill's rewrite to fix;
# this test never edits a skill.
KNOWN = {}


def calls(path):
    """(line number, the call as written, argv) for each vela call in one file's code spans and fenced blocks."""
    text = path.read_text(encoding="utf-8")
    fenced = []
    for block in FENCE.finditer(text):
        first = text.count("\n", 0, block.start(1)) + 1
        lines = block.group(1).split("\n")
        joined, start = "", None
        for offset, line in enumerate(lines):
            if start is None:
                start = first + offset
            joined += line.rstrip("\\").rstrip() + " " if line.rstrip().endswith("\\") else line
            if line.rstrip().endswith("\\"):
                continue
            fenced.append((start, joined))
            joined, start = "", None
        fenced_span = (block.start(), block.end())
        text = text[:fenced_span[0]] + re.sub(r"[^\n]", " ", text[fenced_span[0]:fenced_span[1]]) + text[fenced_span[1]:]
    spans = [(text.count("\n", 0, m.start()) + 1, m.group(1)) for m in SPAN.finditer(text)]
    for line, code in fenced + spans:
        for found in _calls_in(code):
            yield (line, *found)


def _calls_in(code):
    match = PROGRAM.search(code)
    while match:
        rest = match.group("rest")
        call = SHELL.split(" " + rest, 1)[0].strip()
        argv = _argv(call)
        if argv and COMMAND_WORD.match(argv[0]) and argv[0] not in NOT_A_CALL:
            yield code[match.start():].strip(), argv
        match = PROGRAM.search(rest)


def _argv(call):
    text = re.sub(r"<[^<>]*>", "X", call)  # <APP-id>, "<section>", <path to its tech design>
    text = re.sub(r"\^c(?:NN?|\d+)\b", "^c01", text)  # a mark's capture label
    text = re.sub(r"\[(--[^\]]*)\]", r"\1", text)  # [--today YYYY-MM-DD]: an optional flag is still a flag
    text = text.replace("...", " ").replace("…", " ")
    try:
        return shlex.split(text)
    except ValueError:  # an unclosed quote in prose
        return shlex.split(text.replace('"', "").replace("'", ""))


def _commands(parser):
    """{command: its parser} for the top level, and the same for each command's own subcommands."""
    actions = [a for a in parser._actions if a.__class__.__name__ == "_SubParsersAction"]
    return actions[0].choices if actions else {}


def is_a_mention(parser, argv):
    """`vela close gate` named in prose: every word a command or subcommand, nothing else. A mention is fine even when the
    command needs arguments; a misspelled command is not a mention."""
    current = parser
    for word in argv:
        choices = _commands(current)
        if word not in choices:
            return False
        current = choices[word]
    return True


def parse_error(parser, argv):
    """None when argv parses, else argparse's own message."""
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            _, extras = parser.parse_known_args(argv)
    except SystemExit as stop:
        if stop.code in (0, None):  # --help or --version
            return None
        return err.getvalue().strip().splitlines()[-1] if err.getvalue().strip() else f"exit {stop.code}"
    return f"unrecognized arguments: {' '.join(extras)}" if extras else None


ALL = [(path.relative_to(REPO).as_posix(), line, written, argv) for path in DOCS for line, written, argv in calls(path)]


def _case(item):
    where = f"{item[0]}:{item[1]}"
    if where in KNOWN:
        return pytest.param(*item, id=where, marks=pytest.mark.xfail(reason=KNOWN[where], strict=True))
    return pytest.param(*item, id=where)


def test_the_skills_name_enough_calls_to_mean_something():
    assert len(ALL) >= 100, len(ALL)  # a broken extractor would find none and pass everything below


@pytest.mark.parametrize("where, line, written, argv", [_case(item) for item in ALL])
def test_every_vela_call_a_skill_writes_parses(where, line, written, argv):
    parser = cli.build_parser()
    if is_a_mention(parser, argv):
        return
    error = parse_error(parser, argv)
    assert error is None, f"{where}:{line}: `{written}` does not parse ({error}); parsed as {argv}"


def test_a_misspelled_command_or_flag_fails_and_a_placeholder_does_not():
    parser = cli.build_parser()
    assert parse_error(parser, _argv('conventions "<section>"')) is None
    assert parse_error(parser, _argv("check --gate epics --app <APP-id>")) is None
    assert parse_error(parser, _argv("check --no-such-flag")) is not None
    assert not is_a_mention(parser, ["chekc"]) and parse_error(parser, ["chekc"]) is not None
    assert is_a_mention(parser, ["close", "gate"])
    assert [argv for _, argv in _calls_in("python3 ${CLAUDE_SKILL_DIR}/../../scripts/vela check --vault . | tail -3")] == [["check", "--vault", "."]]
    assert [argv for _, argv in _calls_in("sh ${CLAUDE_PLUGIN_ROOT}/scripts/run-vela next-id UNK && git add x")] == [["next-id", "UNK"]]
