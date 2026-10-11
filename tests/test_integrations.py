"""Vault modes for the user's own grill skills. The toolkit never edits ~/.claude/skills; it ships a
patched copy, the patch, and install steps. These tests keep the three in step."""
import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

from conftest import REPO

# A folder with vault-mode.patch changes one of the user's existing skills; one without is a new skill the toolkit
# ships whole, such as work-breakdown.
ALL = sorted(p for p in (REPO / "integrations").iterdir() if p.is_dir())
INTEGRATIONS = [p for p in ALL if (p / "vault-mode.patch").is_file()]
NEW_SKILLS = [p for p in ALL if p not in INTEGRATIONS]
UPSTREAM = pathlib.Path.home() / ".claude" / "skills"
PATCHED_FILES = {
    "requirements-grill": {"SKILL.md", "PREREQ-CHECK.md"},
    # Design 11 adds the review checkpoint and the complete-with-gaps status.
    "tech-design-grill": {"SKILL.md", "PREREQ-CHECK.md", "FRONTMATTER-FORMAT.md", "NEG-AUDIT.md", "REVIEW-CHECKPOINT.md"},
}


def ids(paths):
    return [p.name for p in paths]


@pytest.mark.parametrize("folder", INTEGRATIONS, ids=ids(INTEGRATIONS))
def test_layout(folder):
    assert (folder / "skill" / "SKILL.md").is_file()
    assert (folder / "vault-mode.patch").is_file()
    install = (folder / "INSTALL.md").read_text(encoding="utf-8")
    assert "patch -p1 --dry-run" in install and "patch -p1 -R" in install


@pytest.mark.parametrize("folder", INTEGRATIONS, ids=ids(INTEGRATIONS))
def test_patch_touches_only_skill_and_prereq(folder):
    patch = (folder / "vault-mode.patch").read_text(encoding="utf-8")
    touched = set(re.findall(rf"^\+\+\+ b/{folder.name}/(\S+)$", patch, re.M))
    assert touched == PATCHED_FILES[folder.name]


@pytest.mark.parametrize("folder", INTEGRATIONS, ids=ids(INTEGRATIONS))
def test_patched_skill_frontmatter_parses_and_mentions_vaults(folder):
    text = (folder / "skill" / "SKILL.md").read_text(encoding="utf-8")
    meta = yaml.safe_load(text.split("---\n", 2)[1])
    assert meta["name"] == folder.name
    assert "vault" in meta["description"]


# The planner reference each integration follows in vault mode. PREREQ-CHECK.md names both, because the
# two grill skills share that file byte for byte; each skill depends only on its own.
REFERENCE = {"requirements-grill": "REQUIREMENTS-IN-VAULT.md", "tech-design-grill": "TECH-DESIGN-FROM-VAULT.md"}


@pytest.mark.parametrize("folder", INTEGRATIONS, ids=ids(INTEGRATIONS))
def test_vault_mode_names_a_planner_reference_that_exists(folder):
    name = REFERENCE[folder.name]
    assert f".claude/skills/planner/references/{name}" in (folder / "skill" / "PREREQ-CHECK.md").read_text(encoding="utf-8")
    assert (REPO / "plugin" / "references" / name).is_file(), f"the plugin has no references/{name}"


@pytest.mark.skipif(shutil.which("patch") is None, reason="patch is not installed")
@pytest.mark.parametrize("folder", INTEGRATIONS, ids=ids(INTEGRATIONS))
def test_reversing_the_patch_gives_the_upstream_skill(folder, tmp_path):
    work = tmp_path / folder.name
    shutil.copytree(folder / "skill", work)
    # -E removes a file the patch created, so the reverse leaves no empty file behind.
    result = subprocess.run(["patch", "-p1", "-R", "-E", "-s", "-i", str(folder / "vault-mode.patch")], cwd=tmp_path,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    upstream = UPSTREAM / folder.name
    if not upstream.is_dir():
        pytest.skip(f"{upstream} is not on this machine, so only the reverse apply was checked")
    if same_tree(upstream, folder / "skill"):
        # Installed: the user's skill is the patched copy, so the original is the backup taken before installing.
        backups = sorted((REPO / "tests" / "sim" / "results").glob(f"skill-backups-*/{folder.name}"))
        if not backups:
            pytest.skip(f"{upstream} is the patched copy and no backup of the original is on this machine")
        upstream = backups[-1]
    assert same_tree(work, upstream), f"reversing the patch does not give {upstream} file for file"
    for path in sorted(upstream.iterdir()):
        if path.is_file():
            assert (work / path.name).read_bytes() == path.read_bytes(), (
                f"{path.name} differs from {upstream}: your skill changed since the copy. Re-copy it and re-apply the edits.")


def same_tree(a, b):
    names = lambda d: sorted(p.name for p in d.iterdir() if p.is_file())
    return names(a) == names(b) and all((a / n).read_bytes() == (b / n).read_bytes() for n in names(a))


@pytest.mark.parametrize("folder", NEW_SKILLS, ids=ids(NEW_SKILLS))
def test_a_new_skill_ships_whole_with_install_steps(folder):
    text = (folder / "skill" / "SKILL.md").read_text(encoding="utf-8")
    assert yaml.safe_load(text.split("---\n", 2)[1])["name"] == folder.name
    install = (folder / "INSTALL.md").read_text(encoding="utf-8")
    assert f"cp -R <toolkit>/integrations/{folder.name}/skill ~/.claude/skills/{folder.name}" in install


def test_prereq_check_is_byte_identical_across_the_copies():
    copies = [p / "skill" / "PREREQ-CHECK.md" for p in INTEGRATIONS]
    if len(copies) < 2:
        pytest.skip("only one integration exists")
    assert len({p.read_bytes() for p in copies}) == 1, "PREREQ-CHECK.md is shared by both grill skills and must stay identical"


@pytest.mark.parametrize("folder", INTEGRATIONS, ids=ids(INTEGRATIONS))
def test_install_backs_up_the_skill_outside_the_skills_folder(folder):
    install = (folder / "INSTALL.md").read_text(encoding="utf-8")
    backups = re.findall(r"^cp -R ~/\.claude/skills/\S+ (.+)$", install, re.M)
    assert backups, "INSTALL.md has no `cp -R` backup of the skill"
    assert all(not b.startswith("~/.claude/skills") for b in backups), "the backup must sit outside ~/.claude/skills"
    assert install.index(backups[0]) < install.index("patch -p1 < "), "back up before applying the patch"
