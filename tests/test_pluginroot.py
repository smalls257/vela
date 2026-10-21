"""Where a skill finds the vela program: the order, and the fake environments design session 15 test 10 names
(variable set, literal ${CLAUDE_PLUGIN_ROOT}, vendored only, nothing), plus the skill directory and the recorded path."""
import json

import pytest

from conftest import run

from vela import pluginroot

LITERAL = "${CLAUDE_PLUGIN_ROOT}"


@pytest.fixture(autouse=True)
def no_installed_plugins(tmp_path, monkeypatch):
    """The real ~/.claude/plugins may hold an installed vela plugin; no test here may find it (each sets its own)."""
    empty = tmp_path / "no-plugins"
    empty.mkdir()
    monkeypatch.setenv("CLAUDE_CODE_PLUGIN_CACHE_DIR", str(empty))


def pick(files, plugin_root="", skill_dir="", workspace_path="", vault="/vault"):
    chosen, tried = pluginroot.resolve(plugin_root, skill_dir, vault, workspace_path, lambda path: path in files)
    return (chosen.path if chosen else None), tried


def test_an_expanded_plugin_root_wins_over_everything():
    root = "/plugins/vela/scripts/vela"
    path, _ = pick({root, "/vault/.claude/skills/vela/scripts/vela"}, plugin_root="/plugins/vela")
    assert path == root


def test_a_literal_variable_is_skipped_and_says_why():
    vendored = "/vault/.claude/skills/vela/scripts/vela"
    path, tried = pick({vendored}, plugin_root=LITERAL)
    assert path == vendored
    assert "did not expand it" in tried[1].skipped and tried[1].path == ""


def test_the_skill_directory_comes_before_the_vendored_copy():
    sibling = "/cache/vela/skills/close/../../scripts/vela"
    path, _ = pick({sibling, "/vault/.claude/skills/vela/scripts/vela"}, plugin_root=LITERAL, skill_dir="/cache/vela/skills/close")
    assert path == sibling


def test_vendored_only_still_works():
    vendored = "/vault/.claude/skills/vela/scripts/vela"
    assert pick({vendored}, plugin_root=LITERAL, skill_dir="${CLAUDE_SKILL_DIR}")[0] == vendored


def test_the_recorded_workspace_path_is_the_last_resort():
    recorded = "/opt/vela/scripts/vela"
    path, tried = pick({recorded}, workspace_path=recorded)
    assert path == recorded and [t.usable for t in tried] == [False, False, False, False, True]


def test_an_expanded_variable_pointing_nowhere_falls_through_and_says_so():
    vendored = "/vault/.claude/skills/vela/scripts/vela"
    path, tried = pick({vendored}, plugin_root="/gone")
    assert path == vendored and tried[1].skipped == "does not exist"


def test_nothing_found_returns_none_with_every_reason():
    path, tried = pick(set(), plugin_root=LITERAL)
    assert path is None and len(tried) == 5 and all(t.skipped for t in tried)
    assert "/vela:where" in pluginroot.NOT_FOUND


def test_expanded_rejects_empty_and_unexpanded_text():
    assert not pluginroot.expanded("") and not pluginroot.expanded("  ") and not pluginroot.expanded("${X}/a")
    assert pluginroot.expanded("/a/b")


def test_where_prints_each_rule_and_the_program_to_run(tmp_path):
    program = tmp_path / "plugin" / "scripts" / "vela"
    program.parent.mkdir(parents=True)
    (program.parent.parent / "skills" / "x").mkdir(parents=True)
    program.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    code, text = run("where", "--vault", str(tmp_path), "--plugin-root", LITERAL, "--skill-dir", str(program.parent.parent / "skills" / "x"))
    assert code == 0, text
    assert "did not expand it" in text and f"run sh {program.parent.parent / 'skills' / 'x'}/../../scripts/run-vela" in text


def test_where_reads_the_path_a_workspace_recorded(tmp_path):
    program = tmp_path / "elsewhere" / "vela"
    program.parent.mkdir()
    program.write_text("x", encoding="utf-8")
    (tmp_path / "ws" / ".vela").mkdir(parents=True)
    (tmp_path / "ws" / ".vela" / "workspace.json").write_text(json.dumps({"vela_path": str(program)}), encoding="utf-8")
    code, text = run("where", "--vault", str(tmp_path / "ws"), "--plugin-root", LITERAL)
    assert code == 0 and f"run sh {program.parent / 'run-vela'}" in text


def test_where_with_nothing_exits_1_and_names_the_help(tmp_path):
    code, text = run("where", "--vault", str(tmp_path), "--plugin-root", LITERAL)
    assert code == 1 and "/vela:where" in text


def test_an_installed_copy_is_found_when_the_variables_are_empty():
    """Cowork, 2026-10-14: both variables empty, the plugin synced under ~/.claude/plugins/synced/<id>/vela/."""
    synced = "/root/.claude/plugins/synced/abc/vela/scripts/vela"
    chosen, tried = pluginroot.resolve("", "", ".", "", lambda path: path == synced, installed=[synced])
    assert chosen.path == synced and chosen.source.startswith("an installed copy")
    assert [t.skipped for t in tried[:2]] == ["is empty", "is empty"]


def test_the_newest_installed_copy_wins_and_says_how_many():
    chosen, _ = pluginroot.resolve("", "", ".", "", lambda path: True, installed=["/new", "/old"])
    assert chosen.path == "/new" and "newest of 2" in chosen.source


def test_an_expanded_variable_still_beats_an_installed_copy():
    chosen, _ = pluginroot.resolve("/root", "", ".", "", lambda path: True, installed=["/other"])
    assert chosen.path == "/root/scripts/vela"


def test_where_finds_a_synced_copy_under_the_plugins_root(tmp_path, monkeypatch):
    launcher = tmp_path / "plugins" / "synced" / "x_y" / "vela" / "scripts" / "vela"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/usr/bin/env python3\n")
    monkeypatch.setenv("CLAUDE_CODE_PLUGIN_CACHE_DIR", str(tmp_path / "plugins"))
    from vela import cli
    import io
    out = io.StringIO()
    code = cli.cmd_where(type("A", (), {"vault": str(tmp_path), "plugin_root": "", "skill_dir": ""})(), out)
    assert code == 0 and f"run sh {launcher.parent / 'run-vela'}" in out.getvalue()
