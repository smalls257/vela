"""Role by access: an owner works in the vault's git work tree and can commit; a reader has a published copy with no
.git; .planner.yaml can only give authority up. Authority never comes from a file that ships in the copy."""
import json

from conftest import edit, run
from sharing import git, make_vault, make_workspace, with_remote

from vela import roles
from vela.edge import vaultgit

OWNER_FACTS = dict(in_work_tree=True, git_here=True, has_origin=True, can_commit=True)


def test_a_work_tree_with_origin_and_a_git_identity_is_an_owner():
    found = roles.decide(roles.Facts(**OWNER_FACTS))
    assert found.role == roles.OWNER and found.notes == () and found.warnings == ()


def test_a_work_tree_with_no_origin_is_an_owner_who_is_told_nothing_can_be_pushed():
    found = roles.decide(roles.Facts(**{**OWNER_FACTS, "has_origin": False}))
    assert found.role == roles.OWNER
    assert "nothing can be pushed" in found.notes[0]


def test_a_work_tree_where_commits_are_impossible_is_neither_and_says_why():
    found = roles.decide(roles.Facts(**{**OWNER_FACTS, "can_commit": False, "commit_problem": "git user.email is not set"}))
    assert found.role == roles.NONE and "git user.email is not set" in found.reason


def test_a_published_copy_with_a_workspace_and_no_git_is_a_reader():
    found = roles.decide(roles.Facts(has_workspace=True))
    assert found.role == roles.READER


def test_a_workspace_inside_somebody_elses_repo_is_still_a_reader():
    # Unzipped into a folder that happens to be a git work tree: no .git of its own, so access is read-only.
    found = roles.decide(roles.Facts(has_workspace=True, in_work_tree=True, can_commit=True))
    assert found.role == roles.READER


def test_a_workspace_that_got_its_own_git_init_is_an_owner_of_that_repo():
    found = roles.decide(roles.Facts(**OWNER_FACTS, has_workspace=True))
    assert found.role == roles.OWNER


def test_config_role_reader_downgrades_an_owner():
    found = roles.decide(roles.Facts(**OWNER_FACTS, config_role="reader"))
    assert found.role == roles.READER and "gives authority up" in found.reason


def test_config_role_owner_cannot_promote_a_reader_and_warns():
    found = roles.decide(roles.Facts(has_workspace=True, config_role="owner"))
    assert found.role == roles.READER
    assert "ignored" in found.warnings[0]


def test_config_role_owner_on_an_owner_is_still_ignored_with_a_warning():
    found = roles.decide(roles.Facts(**OWNER_FACTS, config_role="owner"))
    assert found.role == roles.OWNER and len(found.warnings) == 1


def test_an_unknown_config_role_warns_and_changes_nothing():
    found = roles.decide(roles.Facts(**OWNER_FACTS, config_role="admin"))
    assert found.role == roles.OWNER and "isn't recognized" in found.warnings[0]


def test_an_unreadable_config_is_a_warning_not_a_silent_skip():
    found = roles.decide(roles.Facts(**OWNER_FACTS, config_error="mapping values are not allowed here"))
    assert found.role == roles.OWNER and "could not be read" in found.warnings[0]


def test_neither_stops_with_the_sentence_the_spec_gives():
    found = roles.decide(roles.Facts())
    assert found.role == roles.NONE
    assert found.reason == "this folder is neither a vault repo nor a published copy"


def test_git_missing_is_named_when_nothing_else_decides():
    found = roles.decide(roles.Facts(git_error="git is not installed or not on PATH"))
    assert found.role == roles.NONE and "not installed" in found.reason


# ---- against real repos and folders


def test_a_cloned_vault_with_origin_reads_as_owner(tmp_path):
    root = make_vault(tmp_path)
    with_remote(tmp_path, root)
    found = roles.decide(vaultgit.role_facts(root))
    assert found.role == roles.OWNER and found.notes == ()


def test_a_repo_with_no_identity_cannot_commit(tmp_path, monkeypatch):
    root = make_vault(tmp_path)
    git(root, "config", "--unset", "user.name")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "no-global"))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(tmp_path / "no-system"))
    found = roles.decide(vaultgit.role_facts(root))
    assert found.role == roles.NONE and "user.name is not set" in found.reason


def test_a_workspace_folder_with_no_git_reads_as_reader(tmp_path):
    root = make_vault(tmp_path)
    published = tmp_path / "published"
    assert run("publish", "--vault", str(root), "--out", str(published), "--today", "2026-10-11")[0] == 0
    workspace = make_workspace(tmp_path, published)
    assert roles.decide(vaultgit.role_facts(workspace)).role == roles.READER


def test_a_published_copy_that_was_not_opened_is_neither(tmp_path):
    root = make_vault(tmp_path)
    published = tmp_path / "published"
    run("publish", "--vault", str(root), "--out", str(published))
    assert roles.decide(vaultgit.role_facts(published)).role == roles.NONE


def test_planner_yaml_cannot_promote_a_reader_workspace(tmp_path):
    root = make_vault(tmp_path)
    published = tmp_path / "published"
    run("publish", "--vault", str(root), "--out", str(published))
    workspace = make_workspace(tmp_path, published)
    edit(workspace / ".planner.yaml", "title:", "role: owner\ntitle:")
    found = roles.decide(vaultgit.role_facts(workspace))
    assert found.role == roles.READER and "ignored" in found.warnings[0]


def test_planner_yaml_role_reader_downgrades_a_real_owner(tmp_path):
    root = make_vault(tmp_path)
    edit(root / ".planner.yaml", "title:", "role: reader\ntitle:")
    assert roles.decide(vaultgit.role_facts(root)).role == roles.READER


def test_a_plain_folder_is_neither(tmp_path):
    (tmp_path / "plain").mkdir()
    assert roles.decide(vaultgit.role_facts(tmp_path / "plain")).role == roles.NONE


def test_role_command_prints_the_role_and_exits_1_for_neither(tmp_path):
    root = make_vault(tmp_path)
    code, out = run("role", "--vault", str(root))
    assert code == 0 and out.startswith("planner role: owner.")
    (tmp_path / "plain").mkdir()
    code, out = run("role", "--vault", str(tmp_path / "plain"))
    assert code == 1 and "neither a vault repo nor a published copy" in out


def test_role_command_json(tmp_path):
    root = make_vault(tmp_path)
    code, out = run("role", "--vault", str(root), "--json")
    assert code == 0 and json.loads(out)["role"] == "owner"
