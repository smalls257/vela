import json
import os
import re
import shutil
import subprocess
import sys

import yaml

from conftest import REPO, check, findings, run

TEMPLATE = REPO / "template"


def test_template_is_clean(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(TEMPLATE, vault)
    code, out = check(vault, today="2026-10-03")
    assert code == 0, out
    assert findings(out) == []


def test_render_is_a_no_op_on_the_template(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(TEMPLATE, vault)
    before = {p: p.read_bytes() for p in vault.rglob("*.md")}
    code, out = run("render", "--vault", str(vault))
    assert code == 0 and "0 blocks changed" in out, out
    assert {p: p.read_bytes() for p in vault.rglob("*.md")} == before


def test_config_files():
    config = yaml.safe_load((TEMPLATE / ".vela.yaml").read_text(encoding="utf-8"))
    assert set(config) == {"initiative", "title", "stale_after_days"}
    assert config["stale_after_days"] == 60
    ignored = (TEMPLATE / ".gitignore").read_text(encoding="utf-8").split()
    assert ignored == [".inbox/", "voice/corpus/", "voice/local/", ".obsidian/workspace*.json", ".obsidian/cache", "__pycache__/", "*.pyc", ".vela/*", "!.vela/explorer-pins.json"]
    assert json.loads((TEMPLATE / ".obsidian" / "app.json").read_text(encoding="utf-8")) == {"alwaysUpdateLinks": False}
    assert json.loads((TEMPLATE / ".claude" / "settings.json").read_text(encoding="utf-8")) == {"autoMemoryEnabled": False}


def test_claude_md_carries_the_rewrite_sentinel():
    first = (TEMPLATE / "CLAUDE.md").read_text(encoding="utf-8").splitlines()[0]
    assert first == "TEMPLATE: a person must rewrite this file."


def test_pr_template_asks_for_the_kill_rule_numbers():
    text = (TEMPLATE / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    for heading in ("## Minutes", "## Structural fixes", "## Prose edits"):
        assert heading in text


def test_eight_concern_pages():
    names = sorted(p.stem for p in (TEMPLATE / "08-concerns").glob("concern-*.md"))
    assert names == ["concern-cost", "concern-data", "concern-observability", "concern-operations",
                     "concern-ownership", "concern-rollout", "concern-security", "concern-testing"]


def test_pr_check_workflow_runs_vela_check():
    workflow = yaml.safe_load((TEMPLATE / ".github" / "workflows" / "vela-check.yml").read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True))  # YAML 1.1 reads a bare "on" key as True
    assert "pull_request" in triggers
    steps = workflow["jobs"]["vela-check"]["steps"]
    commands = [s.get("run", "") for s in steps]
    assert "python .claude/skills/vela/scripts/vela check" in commands
    assert not any("pyyaml" in c for c in commands)  # the plugin brings its own


def test_toolkit_ci_runs_the_suite():
    workflow = yaml.safe_load((REPO / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True))
    assert "push" in triggers
    commands = " ".join(s.get("run", "") for s in workflow["jobs"]["pytest"]["steps"])
    assert "pytest" in commands


def test_installed_plugin_checks_the_vault(tmp_path):
    """The documented install: copy the plugin into the vault, run it from the vault root."""
    vault = tmp_path / "vault"
    shutil.copytree(TEMPLATE, vault)
    shutil.copytree(REPO / "plugin", vault / ".claude" / "skills" / "vela")
    result = subprocess.run([sys.executable, ".claude/skills/vela/scripts/vela", "check"],
                            cwd=vault, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("vela check: 0 errors, 0 warnings in 23 pages, judged as of ")


def test_readme_install_step_works_on_a_fresh_copy(tmp_path):
    """Run the README's own step 2 in a real shell: cp does not create missing parent folders."""
    vault = tmp_path / "vault"
    shutil.copytree(TEMPLATE, vault)
    readme = (TEMPLATE / "README.md").read_text(encoding="utf-8")
    command = re.search(r"^2\. .*?`(.+?)`", readme, re.MULTILINE).group(1)
    assert "mkdir -p .claude/skills" in command
    install = subprocess.run(command.replace("<toolkit>", str(REPO)), shell=True, cwd=vault,
                             capture_output=True, text=True)
    assert install.returncode == 0, install.stderr
    result = subprocess.run([sys.executable, ".claude/skills/vela/scripts/vela", "check"],
                            cwd=vault, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_wrapper_loads_the_copied_plugin():
    """Claude Code does not discover skills under .claude/skills/vela; only --plugin-dir loads them."""
    wrapper = TEMPLATE / "bin" / "claude-vela"
    assert wrapper.exists() and os.access(wrapper, os.X_OK)
    assert "--plugin-dir" in wrapper.read_text(encoding="utf-8")
    assert "bin/claude-vela" in (TEMPLATE / "README.md").read_text(encoding="utf-8")


def test_a_fresh_vault_tracks_the_map_pins_and_ignores_the_rest_of_the_tool_folder(tmp_path):
    """The pins are the one .vela/ file a team shares; a reader's workspace and the built page stay out of commits."""
    vault = tmp_path / "vault"
    shutil.copytree(TEMPLATE, vault)
    subprocess.run(["git", "init", "-q", str(vault)], check=True, timeout=60)

    def ignored(path):
        done = subprocess.run(["git", "-C", str(vault), "check-ignore", "-q", path], timeout=60)
        return done.returncode == 0

    assert not ignored(".vela/explorer-pins.json")
    assert not ignored("dashboard.html"), "colleagues must get the built page from git"
    for path in (".vela/workspace.json", ".vela/baseline/01-goals.md",
                 ".vela/replay-backup/x.md", ".vela/findings/a.md"):
        assert ignored(path), path
