"""/ask resolves every ID through planner query before citing it, and never cites a not_found."""
import json
import shutil
import subprocess
import sys

import yaml

from conftest import REPO

PLUGIN = REPO / "plugin"
ASK = PLUGIN / "skills" / "ask" / "SKILL.md"
QUERY_TOOL = "Bash(python3 .claude/skills/planner/scripts/planner query *)"


def ask_meta():
    return yaml.safe_load(ASK.read_text(encoding="utf-8").split("---\n", 2)[1])


def test_ask_may_run_planner_query_and_nothing_else_of_planner():
    allowed = ask_meta()["allowed-tools"]
    assert QUERY_TOOL in allowed
    assert allowed.count("planner/scripts/planner") == 1  # query only: never render, check or handoff
    assert ask_meta()["disallowed-tools"] == "Write Edit NotebookEdit"


def test_ask_resolves_every_id_before_citing_it():
    ask = ASK.read_text(encoding="utf-8")
    assert "Before you cite any ID, run `python3 .claude/skills/planner/scripts/planner query get <ID> --json`." in ask
    assert "Cite the ID by the `link` it returns" in ask
    assert "If the answer is `not_found`, never cite that ID" in ask
    assert "`Not recorded: <ID> is not in this vault.`" in ask
    assert "planner query find <words> --json" in ask and "planner query refs <ID> --json" in ask
    assert "`planner query` only reads." in ask
    assert "If `planner query` exits 2" in ask and "never treat that as `not_found`" in ask


def test_the_ask_eval_requires_planner_query():
    case = yaml.safe_load((REPO / "tests" / "evals" / "plugin" / "e5-ask" / "case.yaml").read_text(encoding="utf-8"))
    graders = {g["name"]: g for g in case["graders"]}
    assert graders["query-before-citing"] == {"name": "query-before-citing", "type": "tool_used", "tool": "Bash",
                                              "input_match": "planner query", "arm": "with-only"}


def test_the_command_ask_allows_runs_from_an_installed_vault(tmp_path):
    """The allowed-tools pattern is the installed path, run from the vault root."""
    vault = tmp_path / "vault"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    shutil.copytree(PLUGIN, vault / ".claude" / "skills" / "planner")
    found = subprocess.run([sys.executable, ".claude/skills/planner/scripts/planner", "query", "get", "CON-001", "--json"],
                           cwd=vault, capture_output=True, text=True)
    assert found.returncode == 0, found.stdout + found.stderr
    assert json.loads(found.stdout)["link"] == "[[booking-building-blocks#CON-001 Booking API|CON-001]]"
    missing = subprocess.run([sys.executable, ".claude/skills/planner/scripts/planner", "query", "get", "CON-404", "--json"],
                             cwd=vault, capture_output=True, text=True)
    assert missing.returncode == 1 and json.loads(missing.stdout) == {"id": "CON-404", "not_found": True}
