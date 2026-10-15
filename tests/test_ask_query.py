"""/ask resolves every ID through vela query before citing it, and never cites a not_found."""
import json
import shutil
import subprocess
import sys

import yaml

from conftest import REPO

PLUGIN = REPO / "plugin"


def test_the_ask_eval_requires_vela_query():
    case = yaml.safe_load((REPO / "tests" / "evals" / "plugin" / "e5-ask" / "case.yaml").read_text(encoding="utf-8"))
    graders = {g["name"]: g for g in case["graders"]}
    assert graders["query-before-citing"] == {"name": "query-before-citing", "type": "tool_used", "tool": "Bash",
                                              "input_match": "vela query", "arm": "with-only"}


def test_the_command_ask_allows_runs_from_an_installed_vault(tmp_path):
    """The allowed-tools pattern is the installed path, run from the vault root."""
    vault = tmp_path / "vault"
    shutil.copytree(REPO / "examples" / "unified-booking", vault)
    shutil.copytree(PLUGIN, vault / ".claude" / "skills" / "vela")
    found = subprocess.run([sys.executable, ".claude/skills/vela/scripts/vela", "query", "get", "CON-001", "--json"],
                           cwd=vault, capture_output=True, text=True)
    assert found.returncode == 0, found.stdout + found.stderr
    assert json.loads(found.stdout)["link"] == "[[booking-building-blocks#CON-001 Booking API|CON-001]]"
    missing = subprocess.run([sys.executable, ".claude/skills/vela/scripts/vela", "query", "get", "CON-404", "--json"],
                             cwd=vault, capture_output=True, text=True)
    assert missing.returncode == 1 and json.loads(missing.stdout) == {"id": "CON-404", "not_found": True}


def test_vela_style_does_not_tell_a_session_to_delete_an_ask_line():
    """Heron run 2026-10-11: vela style called '**Ask:**' prose dressed as data, close deleted it, and 27 unknowns ended
    with no one to ask. Ask, a release's Target and an epic's Owning team are labels vela reads."""
    sys.path.insert(0, str(PLUGIN / "lib"))
    from vela import parse, reading
    text = ("# Unknowns\n\nOpen questions.\n\n### UNK-001 Call tools\n\nNobody knows which tools the team uses.\n\n"
            "- **Question:** Which call tools?\n- **Owner:** @lead\n- **Ask:** @pilot-lead\n- **State:** open\n"
            "- **Blocks:** nothing\n- **Ask by:** 2026-11-01\n\n## Release one\n\n- **Target:** 2027-02-02\n- **Owning team:** @agent-lead\n")
    problems = reading.style_problems(text, "unknowns", parse.KNOWN_LABELS.values())
    assert not [why for _, why in problems if "not a fact bullet" in why], problems
