"""What the requirements-in-vault reference says, pinned in one place (overhaul plan Task 3).

Every test that pins this text lives here, so the rewrite that changes it edits this file and no other skill's.
Each section is headed by the file it came from and that file's reason.
"""
from conftest import REPO


def read(*parts):
    return (REPO.joinpath(*parts)).read_text(encoding="utf-8")


PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


# --- From tests/test_final_fixes.py: Fixes from the final whole-branch review: each test names the failure it keeps
# out.

# 1, M6, M9, M5, M4, 7, M2, M3, README: the words the skills and template must carry


def test_requirements_called_from_another_mode_joins_the_open_session():
    text = read("plugin/references/REQUIREMENTS-IN-VAULT.md")
    assert "If a session is already open in this conversation, add `requirements` to its `modes`" in text
    assert "otherwise run START" in text


# --- From tests/test_skills.py: The plugin's skills: frontmatter, size, the files they point at, the plugin
# validator, and the rules each skill exists to hold.

# requirements-grill vault mode (V1-12): the vault rules live in vela, not in the user's skill.


def test_requirements_in_vault_caps_certainty_and_moves_the_output():
    ref = text("references/REQUIREMENTS-IN-VAULT.md")
    assert "It writes at most `assumption`." in ref
    assert "It never writes `fact`." in ref
    assert "there is no `docs/requirements/<slug>.md`" in ref
    assert "### CAP-NNN.FRn <short name>" in ref
    assert "Offer `/vela:grill CAP-NNN.FRn`." in ref
    assert "E316" in ref
    assert "/vela:close" in ref
