"""/ask resolves every ID through planner query before citing it, and never cites a not_found."""
import json
import shutil
import subprocess
import sys

import yaml

from conftest import REPO

PLUGIN = REPO / "plugin"
ASK = PLUGIN / "skills" / "ask" / "SKILL.md"
PLANNER_TOOL = "Bash(python3 *scripts/planner *)"  # the one loose pattern, ruled in design session 15


def ask_meta():
    return yaml.safe_load(ASK.read_text(encoding="utf-8").split("---\n", 2)[1])


def test_ask_runs_the_planner_by_the_one_loose_pattern_and_stays_read_only_by_disallowed_tools():
    allowed = ask_meta()["allowed-tools"]
    assert PLANNER_TOOL in allowed and allowed.count("scripts/planner") == 1
    assert "Write" not in allowed.split() and "Edit" not in allowed.split()
    assert ask_meta()["disallowed-tools"] == "Write Edit NotebookEdit"


def test_ask_resolves_every_id_before_citing_it():
    ask = ASK.read_text(encoding="utf-8")
    assert "Before you cite any ID, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner query get <ID> --json`." in ask
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


def test_planner_style_does_not_tell_a_session_to_delete_an_ask_line():
    """Heron run 2026-10-11: planner style called '**Ask:**' prose dressed as data, close deleted it, and 27 unknowns ended
    with no one to ask. Ask, a release's Target and an epic's Owning team are labels the planner reads."""
    sys.path.insert(0, str(PLUGIN / "lib"))
    from planner import parse, reading
    text = ("# Unknowns\n\nOpen questions.\n\n### UNK-001 Call tools\n\nNobody knows which tools the team uses.\n\n"
            "- **Question:** Which call tools?\n- **Owner:** @lead\n- **Ask:** @pilot-lead\n- **State:** open\n"
            "- **Blocks:** nothing\n- **Ask by:** 2026-11-01\n\n## Release one\n\n- **Target:** 2027-02-02\n- **Owning team:** @agent-lead\n")
    problems = reading.style_problems(text, "unknowns", parse.KNOWN_LABELS.values())
    assert not [why for _, why in problems if "not a fact bullet" in why], problems
