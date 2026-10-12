"""Where a skill finds the planner program: the order, and the fake environments design session 15 test 10 names
(variable set, literal ${CLAUDE_PLUGIN_ROOT}, vendored only, nothing), plus the skill directory and the recorded path."""
import json

from conftest import run

from planner import pluginroot

LITERAL = "${CLAUDE_PLUGIN_ROOT}"


def pick(files, plugin_root="", skill_dir="", workspace_path="", vault="/vault"):
    chosen, tried = pluginroot.resolve(plugin_root, skill_dir, vault, workspace_path, lambda path: path in files)
    return (chosen.path if chosen else None), tried


def test_an_expanded_plugin_root_wins_over_everything():
    root = "/plugins/planner/scripts/planner"
    path, _ = pick({root, "/vault/.claude/skills/planner/scripts/planner"}, plugin_root="/plugins/planner")
    assert path == root


def test_a_literal_variable_is_skipped_and_says_why():
    vendored = "/vault/.claude/skills/planner/scripts/planner"
    path, tried = pick({vendored}, plugin_root=LITERAL)
    assert path == vendored
    assert "did not expand it" in tried[0].skipped and tried[0].path == ""


def test_the_skill_directory_comes_before_the_vendored_copy():
    sibling = "/cache/planner/skills/close/../../scripts/planner"
    path, _ = pick({sibling, "/vault/.claude/skills/planner/scripts/planner"}, plugin_root=LITERAL, skill_dir="/cache/planner/skills/close")
    assert path == sibling


def test_vendored_only_still_works():
    vendored = "/vault/.claude/skills/planner/scripts/planner"
    assert pick({vendored}, plugin_root=LITERAL, skill_dir="${CLAUDE_SKILL_DIR}")[0] == vendored


def test_the_recorded_workspace_path_is_the_last_resort():
    recorded = "/opt/planner/scripts/planner"
    path, tried = pick({recorded}, workspace_path=recorded)
    assert path == recorded and [t.usable for t in tried] == [False, False, False, True]


def test_an_expanded_variable_pointing_nowhere_falls_through_and_says_so():
    vendored = "/vault/.claude/skills/planner/scripts/planner"
    path, tried = pick({vendored}, plugin_root="/gone")
    assert path == vendored and tried[0].skipped == "does not exist"


def test_nothing_found_returns_none_with_every_reason():
    path, tried = pick(set(), plugin_root=LITERAL)
    assert path is None and len(tried) == 4 and all(t.skipped for t in tried)
    assert "/planner:where" in pluginroot.NOT_FOUND


def test_expanded_rejects_empty_and_unexpanded_text():
    assert not pluginroot.expanded("") and not pluginroot.expanded("  ") and not pluginroot.expanded("${X}/a")
    assert pluginroot.expanded("/a/b")


def test_where_prints_each_rule_and_the_program_to_run(tmp_path):
    program = tmp_path / "plugin" / "scripts" / "planner"
    program.parent.mkdir(parents=True)
    (program.parent.parent / "skills" / "x").mkdir(parents=True)
    program.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    code, text = run("where", "--vault", str(tmp_path), "--plugin-root", LITERAL, "--skill-dir", str(program.parent.parent / "skills" / "x"))
    assert code == 0, text
    assert "did not expand it" in text and f"run python3 {program.parent.parent / 'skills' / 'x'}/../../scripts/planner" in text


def test_where_reads_the_path_a_workspace_recorded(tmp_path):
    program = tmp_path / "elsewhere" / "planner"
    program.parent.mkdir()
    program.write_text("x", encoding="utf-8")
    (tmp_path / "ws" / ".planner").mkdir(parents=True)
    (tmp_path / "ws" / ".planner" / "workspace.json").write_text(json.dumps({"planner_path": str(program)}), encoding="utf-8")
    code, text = run("where", "--vault", str(tmp_path / "ws"), "--plugin-root", LITERAL)
    assert code == 0 and f"run python3 {program}" in text


def test_where_with_nothing_exits_1_and_names_the_help(tmp_path):
    code, text = run("where", "--vault", str(tmp_path), "--plugin-root", LITERAL)
    assert code == 1 and "/planner:where" in text
