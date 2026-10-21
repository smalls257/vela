"""`vela new`: a plan started in a folder with the installed plugin alone (the Violation: a Paper Tiger of a start that
copies files and leaves the first commit, which only vela may stage, to a model doing it by hand)."""
import io
import json
import pathlib
import subprocess

import pytest

from vela import cli

REPO = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "plugin" / "template"
SKILLS = REPO / "plugin" / "skills"


@pytest.fixture(autouse=True)
def a_git_identity(tmp_path, monkeypatch):
    config = tmp_path.parent / f"{tmp_path.name}-gitconfig"
    config.write_text("[user]\n\tname = Test Lead\n\temail = lead@example.com\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def vela(*argv):
    out = io.StringIO()
    return cli.main(list(argv), out), out.getvalue()


def git(folder, *args):
    return subprocess.run(["git", "-C", str(folder), *args], capture_output=True, text=True, timeout=60, check=True).stdout


def template_paths():
    return sorted(p.relative_to(TEMPLATE).as_posix() for p in TEMPLATE.rglob("*")
                  if p.is_file() and p.name != ".DS_Store")


def new(folder, *extra):
    return vela("new", "--vault", str(folder), "--title", "Try plan", "--handle", "smalls257", *extra)


def test_an_empty_folder_becomes_a_clean_plan_with_one_commit_of_exactly_the_templates_files(tmp_path):
    code, out = new(tmp_path)
    assert code == 0, out
    assert vela("check", "--vault", str(tmp_path))[0] == 0
    assert git(tmp_path, "log", "--format=%s").split("\n")[:-1] == ["Start the plan"]
    assert sorted(git(tmp_path, "ls-files").split()) == template_paths()
    assert git(tmp_path, "status", "--short") == ""
    assert git(tmp_path, "branch", "--show-current").strip() == "main"


def test_the_name_the_initiative_and_the_handle_are_filled_in(tmp_path):
    code, out = new(tmp_path, "--initiative", "INI-007")
    assert code == 0, out
    config = (tmp_path / ".vela.yaml").read_text(encoding="utf-8")
    assert "initiative: INI-007" in config and 'title: "Try plan"' in config and "first session asks" not in config
    assert all("@solution-lead" not in p.read_text(encoding="utf-8") for p in tmp_path.rglob("*.md") if ".git" not in p.parts)
    assert "@smalls257" in (tmp_path / "01-goals.md").read_text(encoding="utf-8")
    assert (tmp_path / ".vela" / "handle").read_text(encoding="utf-8").strip() == "smalls257"


def test_the_plan_needs_no_copied_plugin_and_no_launcher(tmp_path):
    new(tmp_path)
    assert not (tmp_path / ".claude" / "skills").exists() and not (tmp_path / "bin").exists()


def test_json_and_for_lead_say_what_happened_without_codes(tmp_path):
    code, out = new(tmp_path, "--json")
    data = json.loads(out)
    assert code == 0 and data["files"] == len(template_paths()) and data["check"]["errors"] == 0 and data["commit"]
    other = tmp_path.parent / f"{tmp_path.name}-lead"
    other.mkdir()
    code, out = new(other, "--for-lead")
    assert code == 0 and "started the plan" in out and "@" not in out and "--" not in out


def test_a_users_documents_move_to_the_inbox_and_are_never_committed(tmp_path):
    (tmp_path / "brief.docx").write_bytes(b"PK user document")
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "call.txt").write_text("their words\n", encoding="utf-8")
    code, out = new(tmp_path)
    assert code == 0, out
    assert (tmp_path / ".inbox" / "brief.docx").read_bytes() == b"PK user document"
    assert (tmp_path / ".inbox" / "notes" / "call.txt").read_text(encoding="utf-8") == "their words\n"
    assert not any(p.startswith((".inbox", "brief", "notes")) for p in git(tmp_path, "ls-files").split())
    assert git(tmp_path, "status", "--short") == ""


def test_a_plan_already_there_is_refused_and_untouched(tmp_path):
    assert new(tmp_path)[0] == 0
    before = git(tmp_path, "rev-parse", "HEAD")
    code, out = new(tmp_path)
    assert code == 1 and "already a plan" in out
    assert git(tmp_path, "rev-parse", "HEAD") == before


def test_a_folder_holding_only_the_tool_folder_is_refused(tmp_path):
    (tmp_path / ".vela").mkdir()
    code, out = new(tmp_path)
    assert code == 1 and "already a plan" in out and not (tmp_path / ".git").exists()


def test_a_name_clash_is_listed_and_nothing_is_overwritten(tmp_path):
    (tmp_path / "README.md").write_text("mine\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("mine too\n", encoding="utf-8")
    (tmp_path / "other.txt").write_text("fine\n", encoding="utf-8")
    code, out = new(tmp_path)
    assert code == 1 and "CLAUDE.md" in out and "README.md" in out and "other.txt" not in out
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "mine\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["CLAUDE.md", "README.md", "other.txt"]


def test_a_folder_inside_another_repository_becomes_a_plan_without_a_new_repo(tmp_path):
    outer = tmp_path / "bigproject"
    inner = outer / "plans"
    inner.mkdir(parents=True)
    git(outer, "init", "-q")
    code, out = new(inner)
    assert code == 0, out
    assert not (inner / ".git").exists()
    assert git(outer, "rev-parse", "--show-toplevel").strip() == str(outer.resolve())
    assert git(outer, "log", "--format=%s").split("\n")[:-1] == ["Start the plan: plans"]
    assert {p.split("/")[0] for p in git(outer, "ls-files").split()} == {"plans"}


def test_a_folder_that_is_its_own_repository_is_used_as_it_is(tmp_path):
    git(tmp_path, "init", "-q", "-b", "trunk")
    code, out = new(tmp_path)
    assert code == 0, out
    assert git(tmp_path, "branch", "--show-current").strip() == "trunk"
    assert git(tmp_path, "log", "--format=%s").split("\n")[:-1] == ["Start the plan"]


def test_no_title_and_no_handle_ask_the_lead_and_change_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")  # no gh to answer for them
    code, out = vela("new", "--vault", str(tmp_path), "--json")
    data = json.loads(out)
    assert code == 3 and [n["ask"] for n in data["needs_lead"]] == ["title", "handle"]
    assert list(tmp_path.iterdir()) == []


def test_a_bad_handle_or_initiative_is_refused(tmp_path):
    assert vela("new", "--vault", str(tmp_path), "--title", "T", "--handle", "not a handle")[0] == 1
    assert new(tmp_path, "--initiative", "7")[0] == 1
    assert list(tmp_path.iterdir()) == []


def test_session_start_with_no_plan_says_to_run_vela_new(tmp_path):
    code, out = vela("session", "start", "--vault", str(tmp_path), "--mode", "dump", "--topic", "first look")
    assert code == 3 and "no plan here yet; `vela new` starts one" in out and "Git failed" not in out
    code, out = vela("session", "start", "--vault", str(tmp_path), "--mode", "dump", "--topic", "x", "--for-lead")
    assert code == 3 and "no plan in this folder yet" in out
    assert not (tmp_path / ".git").exists()


def test_the_start_skills_point_at_vela_new_and_never_a_hand_setup():
    start = (REPO / "plugin" / "references" / "START.md").read_text(encoding="utf-8")
    assert "vela new --title" in start and "Never set a plan up by hand" in start
    for skill in ("dump", "discover", "import"):
        assert "vela new" in (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8"), skill
