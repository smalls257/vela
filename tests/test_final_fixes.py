"""Fixes from the final whole-branch review: each test names the failure it keeps out."""
import os
import subprocess
import sys

from conftest import REPO, check, edit, findings

BIN = REPO / "plugin" / "bin" / "planner"
CAP = "capabilities/CAP-001-sell.md"
GOALS = "01-goals.md"
SESSION = "sessions/2026-01-10-shop-api.md"
CAP_PAGE = """---
id: CAP-001
type: capability
title: Sell
origin: proposed
change: unchanged
state: assumption
owner: "@mini-lead"
authored: authored
---

# CAP-001 Sell

### CAP-001.FR1 A till sells a basket

- **State:** assumption
"""


def codes(out):
    # W505: these vaults hold an FR and an app but no allocation, which T7 rightly reports; the tests are about FR states.
    # W357: the FR here lists no acceptance criteria, which is a different test's subject.
    return sorted(f for f in findings(out) if f[0] not in ("W402", "W505", "W357"))


def add_cap(vault, text=CAP_PAGE):
    (vault / "capabilities").mkdir(exist_ok=True)
    (vault / CAP).write_text(text, encoding="utf-8")


def run_bin(vault, *args, env=None):
    return subprocess.run([sys.executable, str(BIN), *args], cwd=vault, capture_output=True, text=True,
                          env={**os.environ, **(env or {})})


# 2. a missing PyYAML is a tool failure with the fix in the message, not "vault has errors"

def test_missing_pyyaml_exits_2_with_the_install_command(mini, tmp_path):
    (tmp_path / "shadow").mkdir()
    (tmp_path / "shadow" / "yaml.py").write_text("raise ImportError('no yaml here')\n", encoding="utf-8")
    result = run_bin(mini, "check", env={"PYTHONPATH": str(tmp_path / "shadow")})
    assert result.returncode == 2
    assert "planner needs PyYAML: python3 -m pip install pyyaml" in result.stderr
    assert "Traceback" not in result.stderr


# 3. running the bin never writes bytecode into a vault

def test_running_the_bin_writes_no_pycache(tmp_path):
    import shutil
    plugin = tmp_path / "plugin"
    shutil.copytree(REPO / "plugin", plugin, ignore=shutil.ignore_patterns("__pycache__"))
    vault = tmp_path / "vault"
    shutil.copytree(REPO / "tests" / "fixtures" / "mini", vault)
    result = subprocess.run([sys.executable, str(plugin / "bin" / "planner"), "check"], cwd=vault,
                            capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"})
    assert result.returncode in (0, 1), result.stderr
    assert not list(plugin.rglob("*.pyc"))


def test_template_ignores_pycache():
    lines = (REPO / "template" / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "__pycache__/" in lines


# 4. an impossible date is a finding, not exit 2

def test_impossible_date_is_e102_not_a_crash(mini):
    edit(mini / SESSION, "date: 2026-01-10\n", "date: 2026-13-01\n")
    code, out = check(mini)
    assert code == 1
    assert ("E102", SESSION) in findings(out)
    assert "Fix the date" in out


# 5. Changes rows mention IDs; they do not register them

def test_source_id_found_only_in_a_changes_table_is_e207(mini):
    edit(mini / SESSION, "| CON-001 | assumption | decided | [[2026-01-10-shop-api#^c01]] |",
         "| CON-001 | assumption | decided | [[2026-01-10-shop-api#^c01]] |\n| SRC-99 | - | fact | [[2026-01-10-shop-api#^c01]] |")
    edit(mini / GOALS, 'sources: ["2026-01-10-shop-api"]', "sources: [SRC-99]")
    _, out = check(mini)
    assert ("E207", GOALS) in codes(out)
    assert "Source SRC-99 is not a row in sources.md" in out


def test_epic_delivering_a_goal_found_only_in_changes_is_e207(mini):
    edit(mini / SESSION, "| CON-001 | assumption | decided | [[2026-01-10-shop-api#^c01]] |",
         "| CON-001 | assumption | decided | [[2026-01-10-shop-api#^c01]] |\n| G9 | - | assumption | [[2026-01-10-shop-api#^c01]] |")
    (mini / "13-epics").mkdir(exist_ok=True)
    (mini / "13-epics" / "EPC-001-sell.md").write_text("""---
id: EPC-001
type: epic
title: Sell
initiative: INI-900
state: draft
owner: "@mini/shop-team"
authored: authored
apps: [APP-shop]
delivers: [G9]
---

# EPC-001 Sell
""", encoding="utf-8")
    _, out = check(mini)
    assert "delivers lists 'G9', which is not an ID in this vault" in out


def test_real_goal_and_source_rows_still_resolve(mini):
    _, out = check(mini)
    assert "E207" not in out


# 6. functional requirements are items check validates like contracts

def test_fr_page_is_clean_at_assumption(mini):
    add_cap(mini)
    code, out = check(mini)
    assert code == 0 and codes(out) == []


def test_decided_fr_with_no_grill_is_e303(mini):
    add_cap(mini, CAP_PAGE.replace("State:** assumption", "State:** decided"))
    _, out = check(mini)
    assert codes(out) == [("E303", CAP)]
    assert "CAP-001.FR1" in out


def test_decided_fr_linking_a_grill_passes(mini):
    add_cap(mini, CAP_PAGE.replace("- **State:** assumption", "- **State:** decided\n- **Decision:** [[2026-01-10-shop-api]]"))
    _, out = check(mini)
    assert codes(out) == []


def test_decided_fr_linking_a_requirements_session_is_e317(mini):
    edit(mini / SESSION, "modes: [grill]", "modes: [requirements]")
    add_cap(mini, CAP_PAGE.replace("- **State:** assumption", "- **State:** decided\n- **Decision:** [[2026-01-10-shop-api]]"))
    _, out = check(mini)
    assert ("E317", CAP) in codes(out)


def test_fact_fr_needs_a_source(mini):
    add_cap(mini, CAP_PAGE.replace("State:** assumption", "State:** fact"))
    _, out = check(mini)
    assert codes(out) == [("E304", CAP)]
    add_cap(mini, CAP_PAGE.replace("- **State:** assumption", "- **State:** fact\n- **Source:** SRC-01"))
    assert [c for c in codes(check(mini)[1]) if c[0] != "W326"] == []  # W326: the page could say fact now


def test_fr_state_must_be_in_the_enum_and_present(mini):
    add_cap(mini, CAP_PAGE.replace("State:** assumption", "State:** maybe"))
    assert codes(check(mini)[1]) == [("E105", CAP)]
    add_cap(mini, CAP_PAGE.replace("- **State:** assumption\n", ""))
    assert codes(check(mini)[1]) == [("E320", CAP)]


def test_open_unknown_blocks_a_decided_fr(mini):
    add_cap(mini, CAP_PAGE.replace("- **State:** assumption", "- **State:** decided\n- **Decision:** [[2026-01-10-shop-api]]"))
    edit(mini / "11-unknowns-and-risks.md", "- **Blocks:** nothing\n", "- **Blocks:** [[CAP-001-sell#CAP-001.FR1 A till sells a basket|CAP-001.FR1]]\n")
    _, out = check(mini)
    assert ("E316", CAP) in codes(out)


def test_open_unknown_blocking_an_fr_still_blocks_its_decided_capability(mini):
    decided = CAP_PAGE.replace("state: assumption", "state: decided").replace(
        "# CAP-001 Sell\n", "# CAP-001 Sell\n\n- **Decision:** [[2026-01-10-shop-api]]\n")
    add_cap(mini, decided)
    edit(mini / "11-unknowns-and-risks.md", "- **Blocks:** nothing\n", "- **Blocks:** [[CAP-001-sell#CAP-001.FR1 A till sells a basket|CAP-001.FR1]]\n")
    code, out = check(mini)
    assert code == 1
    assert "E316 CAP-001 is decided, but open unknown UNK-001 blocks it." in out
    assert codes(out) == [("E316", CAP)]


def test_a_decided_fr_without_a_grill_gets_its_own_findings(mini):
    add_cap(mini, CAP_PAGE.replace("- **State:** assumption", "- **State:** decided"))
    assert codes(check(mini)[1]) == [("E303", CAP)]


def test_conventions_and_grill_document_the_fr_format():
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert "### CAP-nnn.FRn" in conventions and "CAP-001.FR1" in conventions
    grill = (REPO / "plugin" / "skills" / "grill" / "SKILL.md").read_text(encoding="utf-8")
    assert "### CAP-nnn.FRn" in grill and "`**State:**` bullet moves to `decided`" in grill


# M8. a goal at fact needs a source

def test_goal_row_at_fact_needs_the_page_to_list_sources(mini):
    edit(mini / GOALS, "| G1 | Sell from one till | One till sells every product | decided |",
         "| G1 | Sell from one till | One till sells every product | fact |")
    edit(mini / GOALS, "state: decided\n", "state: assumption\n")
    edit(mini / GOALS, "- **Decision:** [[2026-01-10-shop-api]]\n", "")
    edit(mini / GOALS, 'sources: ["2026-01-10-shop-api"]\n', "")
    _, out = check(mini)
    assert [c for c in codes(out) if c[0] != "W326"] == [("E304", GOALS)] and "Goal G1 is a fact" in out
    edit(mini / GOALS, "authored: mixed\n", "authored: mixed\nsources: [SRC-01]\n")
    assert [c for c in codes(check(mini)[1]) if c[0] != "W326"] == []  # W326: the page could say fact now


# 1, M6, M9, M5, M4, 7, M2, M3, README: the words the skills and template must carry

def read(*parts):
    return (REPO.joinpath(*parts)).read_text(encoding="utf-8")


def test_close_and_epics_stage_what_render_rewrote():
    close, epics, modes = read("plugin/skills/close/SKILL.md"), read("plugin/skills/epics/SKILL.md"), read("plugin/references/MODES.md")
    assert "Stage every file `planner render` reported" in close
    assert "`git status --short` must show nothing modified" in close
    assert "Stage every file `planner render` reported" in epics
    assert "Close runs `planner render` for those." not in modes and "so does `epics`" in modes


def test_pr_workflow_fails_a_stale_generated_block():
    import yaml
    workflow = yaml.safe_load(read("template/.github/workflows/planner-check.yml"))
    commands = [s.get("run", "") for s in workflow["jobs"]["planner-check"]["steps"]]
    assert "python .claude/skills/planner/bin/planner render && git diff --exit-code" in commands
    assert commands.index("python .claude/skills/planner/bin/planner check") < commands.index(commands[-1])


def test_epics_writes_owning_team_and_close_leaves_it():
    close, epics = read("plugin/skills/close/SKILL.md"), read("plugin/skills/epics/SKILL.md")
    assert "written now, in this session" in epics
    assert "and its `**Owning team:**` line" not in close and "close leaves it as written" in close


def test_close_checks_remote_session_records_before_taking_an_id():
    close = read("plugin/skills/close/SKILL.md")
    step3 = close.split("## 3.")[1].split("## 4.")[0]
    assert "git branch -r --list 'origin/session/*'" in step3


def test_grill_agenda_status_names_the_failed_gate():
    assert "off-agenda: GATE-n" in read("plugin/skills/grill/SKILL.md")


def test_checkpoint_commits_stage_by_exact_path():
    assert "by exact path, never `git add -A`" in read("plugin/references/START.md")


def test_requirements_called_from_another_mode_joins_the_open_session():
    text = read("plugin/references/REQUIREMENTS-IN-VAULT.md")
    assert "If a session record is already open in this conversation, add `requirements` to its `modes`" in text
    assert "otherwise run START" in text


def test_template_wrapper_readme_and_claude_md():
    assert 'cd "$root" && exec claude' in read("template/bin/claude-planner")
    assert "`/ask`" not in read("template/CLAUDE.md") and "`/planner:ask`" in read("template/CLAUDE.md")
    readme = read("template/README.md")
    assert "Python 3.11" in readme and "PyYAML" in readme
    assert "python3 .claude/skills/planner/bin/planner view --out ~/Desktop/<name>.html" in readme
