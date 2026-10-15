"""What the ask skill says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
import re
import shutil
import subprocess

import pytest
import yaml
from conftest import REPO

PLUGIN = REPO / "plugin"


ASK = PLUGIN / "skills" / "ask" / "SKILL.md"


VELA_TOOL = "Bash(python3 *scripts/vela *)"  # the one loose pattern, ruled in design session 15


def ask_meta():
    return yaml.safe_load(ASK.read_text(encoding="utf-8").split("---\n", 2)[1])


def read(*parts):
    return (PLUGIN.joinpath(*parts)).read_text(encoding="utf-8")


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


ASK_INJECT = re.compile(r"^!`(.+)`$", re.M)


def run_injected(cwd, env):
    out = []
    for command in ASK_INJECT.findall(text("skills/ask/SKILL.md")):
        result = subprocess.run(["bash", "-c", command], cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, (command, result.stderr)
        out.append(result.stdout)
    return out


# --- From tests/test_ask_query.py: /ask resolves every ID through vela query before citing it, and never cites a
# not_found.


def test_ask_runs_vela_by_the_one_loose_pattern_and_stays_read_only_by_disallowed_tools():
    allowed = ask_meta()["allowed-tools"]
    assert VELA_TOOL in allowed and allowed.count("scripts/vela") == 1
    assert "Write" not in allowed.split() and "Edit" not in allowed.split()
    assert ask_meta()["disallowed-tools"] == "Write Edit NotebookEdit"


def test_ask_resolves_every_id_before_citing_it():
    ask = ASK.read_text(encoding="utf-8")
    assert "Before you cite any ID, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vela query get <ID> --json`." in ask
    assert "Put the ID, by the `link` it returns, in the `Sources:` list" in ask
    assert "If the answer is `not_found`, never cite that ID" in ask
    assert "`Not recorded: <ID> is not in this vault.`" in ask
    assert "vela query find <words> --json" in ask and "vela query refs <ID> --json" in ask
    assert "`vela query` only reads." in ask
    assert "If `vela query` exits 2" in ask and "never treat that as `not_found`" in ask


# --- From tests/test_override.py: The user can override any rule, and an override is never invisible.

# ------------------------------------------------------------- skill text


def test_ask_reports_an_override_and_an_unconfirmed_decision():
    ask = read("skills", "ask", "SKILL.md")
    assert '"decided by override: <rule>, by @x"' in ask and '"on behalf of @owner, not yet confirmed"' in ask


# --- From tests/test_session_experience.py: What the skills make a lead go through (docs/research/2026-10-12-session-
# experience-review.md and the friction pass).

# --- S36 to S47


def test_ask_cannot_cat_any_file():
    meta = text("skills/ask/SKILL.md").split("---\n", 2)[1]
    assert "Bash(cat" not in meta


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# /ask (V1-15)


def test_ask_answers_from_opened_sections_and_marks_what_is_missing():
    ask = text("skills/ask/SKILL.md")
    assert "Never search or Read a file under `voice/` or `.inbox/`." in ask  # said once
    assert "Cite nothing you did not open in this answer." in ask
    assert "`Not recorded:`" in ask and "`Not decided:`" in ask
    assert "Never create, edit or delete a file." in ask
    assert "Sources:" in ask


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_ask_header_works_with_no_origin_and_no_claude_md(tmp_path):
    import os
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    git = ["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]
    subprocess.run(git + ["init", "-q", "-b", "main"], cwd=tmp_path, check=True, timeout=60)
    (tmp_path / "x.md").write_text("x\n", encoding="utf-8")
    subprocess.run(git + ["add", "x.md"], cwd=tmp_path, check=True, timeout=60)
    subprocess.run(git + ["commit", "-q", "-m", "x"], cwd=tmp_path, check=True, timeout=60)
    (fresh,) = run_injected(tmp_path, env)
    assert re.match(r"HEAD is [0-9a-f]+, committed \d{4}-\d{2}-\d{2}\.\n", fresh)
    assert "Behind origin/main by an unknown number of commits, as of the last fetch on no recorded date." in fresh
    assert len(run_injected(tmp_path, env)) == 1


def test_ask_fix_round_bash_read_only_and_every_claim_sourced():
    ask = text("skills/ask/SKILL.md")
    assert "Never redirect output (`>`, `>>`)." in ask
    for banned in ("`tee`", "`sed -i`", "`git commit`", "`git checkout`", "`git log --output`", "`vela render`"):
        assert banned in ask
    assert "writes a file or changes git state" in ask
    assert "Every claim rests on a page in the `Sources:` list or is labeled `Not from the vault:`. There is no third choice." in ask
    assert "Name each thing in the sentence by its plain name, not its ID." in ask  # the lead reads names; IDs sit in Sources
    assert "Assert nothing you did not open and read. A Grep snippet alone does not count." in ask
    assert "Search and Read `sessions/` only if the question asks about a session or what was said." in ask
    assert "only when the clone is behind origin/main" in ask  # a lead who asks a question does not read a commit hash first
