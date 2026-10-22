"""Several vela plans in one docs repo, each in its own folder (`projects/heron/`, `projects/payments/`).

The Violation these tests hold off is a Distributed Monolith: two plans sharing one repo must not share its index, its
status, its branch names or its hooks' idea of "the vault". Every test that matters has the same shape: plan B has
unsaved work, or an open session, and plan A's command neither sees it, stages it, commits it, publishes it nor counts
it as dirty. A plan that is its own repo is held unchanged by the last tests.
"""
import json
import subprocess
import sys

import pytest
from conftest import REPO, run
from sharing import git

from vela import doctor, planscope
from vela.edge import idgit, plans

LAUNCHER = REPO / "plugin" / "scripts" / "vela"
TODAY = "2026-10-21"

CONSTRAINTS = """---
id: CON-limits
type: constraints
title: Limits
state: draft
---

# Limits

## Summary

<!-- generated:summary sha=0123abcd: do not edit, run vela render -->
| Item | State |
|---|---|
| One team figure | assumption |
<!-- /generated:summary -->
"""


@pytest.fixture(autouse=True)
def a_git_identity(tmp_path, monkeypatch):
    config = tmp_path.parent / f"{tmp_path.name}-gitconfig"
    config.write_text("[user]\n\tname = Test Lead\n\temail = lead@example.com\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def new_plan(folder, title):
    return run("new", "--vault", str(folder), "--title", title, "--handle", "jo")


@pytest.fixture
def docs(tmp_path):
    """(repo, heron folder, payments folder): one docs repo with a README and two plans made by `vela new`."""
    repo = tmp_path / "docs"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "README.md").write_text("# docs\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-q", "-m", "Docs repo")
    heron, payments = repo / "projects" / "heron", repo / "projects" / "payments"
    for folder, title in ((heron, "Heron rollout"), (payments, "Payments move")):
        folder.mkdir(parents=True)
        code, out = new_plan(folder, title)
        assert code == 0, out
    return repo, heron, payments


def session_start(plan, topic, *flags):
    return run("session", "start", "--vault", str(plan), "--mode", "grill", "--topic", topic, "--today", TODAY, *flags)


def checkpoint(plan):
    return run("close", "stage", "--vault", str(plan), "--checkpoint")


def dirty(repo):
    """git's short status lines, without the column that holds a leading space (the test helper strips output)."""
    return sorted(line.strip() for line in git(repo, "status", "--short").split("\n") if line.strip())


def files_in(repo, ref="HEAD"):
    return sorted(git(repo, "show", "--name-only", "--format=", ref).split("\n"))


# ----------------------------------------------------------------------------------------------------- vela new

def test_new_in_a_subfolder_makes_no_repo_and_its_first_commit_holds_only_its_files(docs):
    repo, heron, payments = docs
    assert not (heron / ".git").exists() and git(heron, "rev-parse", "--show-toplevel") == str(repo.resolve())
    log = git(repo, "log", "--format=%s").split("\n")
    assert log == ["Start the plan: payments", "Start the plan: heron", "Docs repo"]
    heron_commit = files_in(repo, "HEAD~1")
    assert heron_commit and all(path.startswith("projects/heron/") for path in heron_commit)
    assert all(path.startswith("projects/payments/") for path in files_in(repo))
    assert git(repo, "status", "--short") == ""


def test_new_refuses_a_folder_inside_another_plan_and_one_with_plans_below_it(docs):
    repo, heron, _ = docs
    inside = heron / "sessions" / "nested"
    inside.mkdir()
    code, out = new_plan(inside, "Nested")
    assert code == 1 and "inside the plan" in out and not (inside / ".vela.yaml").exists()
    code, out = new_plan(repo, "The whole repo")
    assert code == 1 and "below this folder" in out and not (repo / ".vela.yaml").exists()
    code, out = new_plan(heron, "Again")
    assert code == 1 and "already a plan" in out


def test_new_still_starts_a_plan_in_a_folder_with_no_repo_around_it(tmp_path):
    folder = tmp_path / "alone"
    folder.mkdir()
    code, out = new_plan(folder, "Alone")
    assert code == 0, out
    assert git(folder, "log", "--format=%s") == "Start the plan"
    assert git(folder, "rev-parse", "--show-prefix") == ""


# ---------------------------------------------------------------------------------------------------- vela plans

def test_plans_lists_both_with_folders_and_titles(docs):
    repo, _, _ = docs
    code, out = run("plans", "--vault", str(repo), "--json")
    data = json.loads(out)
    assert code == 0
    assert [(p["folder"], p["title"], p["scope"]) for p in data["plans"]] == [
        ("projects/heron", "Heron rollout", "heron"), ("projects/payments", "Payments move", "payments")]
    code, out = run("plans", "--vault", str(repo), "--for-lead")
    assert code == 0 and out.strip() == "There are two plans here: Heron rollout and Payments move."


def test_plans_here_finds_the_plan_above_a_folder_and_asks_at_a_root_with_several(docs):
    repo, heron, _ = docs
    code, out = run("plans", "--vault", str(heron / "sessions"), "--here", "--paths")
    assert code == 0 and out.strip() == "projects/heron"
    code, out = run("plans", "--vault", str(repo), "--here", "--json")
    data = json.loads(out)
    assert code == 3 and [c["said"] for c in data["needs_lead"][0]["choices"]] == ["Heron rollout", "Payments move"]
    code, out = run("plans", "--vault", str(repo), "--here", "--for-lead")
    assert code == 3 and "Which one are we working on?" in out and "projects" not in out


def test_plans_in_a_repo_with_none_says_so_and_a_root_plan_is_dot(tmp_path):
    folder = tmp_path / "alone"
    folder.mkdir()
    assert run("plans", "--vault", str(folder), "--json")[0] == 1
    assert new_plan(folder, "Alone")[0] == 0
    assert run("plans", "--vault", str(folder), "--paths")[1].split() == ["."]


# ----------------------------------------------------------------- session start and checkpoint, plan by plan

def test_each_plan_starts_a_session_on_a_branch_that_carries_its_name(docs):
    repo, heron, payments = docs
    code, out = session_start(heron, "pilot scope", "--new-branch")
    assert code == 0, out
    assert git(repo, "branch", "--show-current") == f"session/heron/{TODAY}-pilot-scope"
    git(repo, "switch", "-q", "main")
    code, out = session_start(payments, "pilot scope", "--new-branch")  # the same topic on the same day does not collide
    assert code == 0, out
    assert git(repo, "branch", "--show-current") == f"session/payments/{TODAY}-pilot-scope"
    branches = git(repo, "branch", "--format=%(refname:short)").split("\n")
    assert f"session/heron/{TODAY}-pilot-scope" in branches and f"session/payments/{TODAY}-pilot-scope" in branches


def test_one_plans_open_session_is_not_the_others(docs):
    repo, heron, payments = docs
    assert session_start(heron, "pilot scope")[0] == 0
    git(repo, "switch", "-q", "main")
    assert session_start(payments, "ledger")[0] == 0
    code, out = run("session", "open", "--vault", str(heron), "--json")
    assert code == 0, out
    assert [r["id"] for r in json.loads(out)["open"]] == [f"{TODAY}-pilot-scope"]
    code, out = run("session", "open", "--vault", str(payments), "--json")
    assert [r["id"] for r in json.loads(out)["open"]] == [f"{TODAY}-ledger"]


def test_a_checkpoint_in_one_plan_stages_commits_and_leaves_alone_only_that_plans_files(docs):
    repo, heron, payments = docs
    assert session_start(heron, "pilot scope")[0] == 0
    (heron / "01-goals.md").write_text((heron / "01-goals.md").read_text(encoding="utf-8") + "\nHeron goal.\n", encoding="utf-8")
    (payments / "01-goals.md").write_text((payments / "01-goals.md").read_text(encoding="utf-8") + "\nUnsaved.\n", encoding="utf-8")
    (payments / "scratch.md").write_text("untracked in the other plan\n", encoding="utf-8")
    code, out = checkpoint(heron)
    assert code == 0, out
    committed = files_in(repo)
    assert committed and all(path.startswith("projects/heron/") for path in committed)
    assert "projects/heron/01-goals.md" in committed
    assert git(repo, "diff", "--cached", "--name-only") == ""  # nothing of payments sits in the index
    assert dirty(repo) == ["?? projects/payments/scratch.md", "M projects/payments/01-goals.md"]


def test_a_start_refuses_when_files_outside_the_plan_have_unsaved_changes_and_changes_nothing(docs):
    repo, heron, payments = docs
    (payments / "01-goals.md").write_text((payments / "01-goals.md").read_text(encoding="utf-8") + "\nUnsaved.\n", encoding="utf-8")
    code, out = run("session", "start", "--vault", str(heron), "--mode", "grill", "--topic", "pilot scope", "--for-lead")
    assert code == 3 and "outside this plan" in out and "projects" not in out and "session/" not in out
    assert git(repo, "branch", "--show-current") == "main" and dirty(repo) == ["M projects/payments/01-goals.md"]
    assert not list((heron / "sessions").glob(f"{TODAY}-*"))


def test_a_start_on_the_owners_branch_with_nothing_unsaved_outside_the_plan_starts(docs):
    repo, heron, payments = docs
    assert session_start(heron, "pilot scope", "--new-branch")[0] == 0
    code, out = run("session", "start", "--vault", str(payments), "--mode", "grill", "--topic", "ledger")
    assert code == 0, out  # HEAD is on heron's session branch: any branch will do while nothing outside is unsaved
    assert git(repo, "branch", "--show-current") == f"session/heron/{TODAY}-pilot-scope"  # nothing moved
    git(repo, "switch", "-q", "-c", "owner-feature")
    code, out = session_start(payments, "second", "--new")
    assert code == 0, out
    assert git(repo, "branch", "--show-current") == "owner-feature"
    record = (payments / "sessions" / f"{TODAY}-second.md").read_text(encoding="utf-8")
    assert "branch: owner-feature\n" in record


def test_a_start_from_the_plans_own_open_session_branch_is_not_refused(docs):
    repo, heron, _ = docs
    assert session_start(heron, "pilot scope")[0] == 0
    code, out = run("session", "start", "--vault", str(heron), "--mode", "grill", "--resume", f"{TODAY}-pilot-scope")
    assert code == 0, out


def test_a_plan_that_is_its_own_repo_still_starts_from_any_branch(tmp_path):
    folder = tmp_path / "solo"
    folder.mkdir()
    assert new_plan(folder, "Solo")[0] == 0
    git(folder, "switch", "-q", "-c", "feature")
    assert session_start(folder, "kickoff")[0] == 0


def test_close_stage_and_close_push_refuse_when_head_left_the_sessions_branch(docs):
    repo, heron, _ = docs
    assert session_start(heron, "pilot scope")[0] == 0
    git(repo, "switch", "-q", "-c", "elsewhere")  # the record is still in the tree: only the branch is wrong
    (heron / "01-goals.md").write_text((heron / "01-goals.md").read_text(encoding="utf-8") + "\nGoal.\n", encoding="utf-8")
    code, out = checkpoint(heron)
    assert code == 1 and "wrong branch" in out.lower()
    assert git(repo, "log", "--format=%s", "-1") != f"Checkpoint {TODAY}-pilot-scope"
    code, out = run("close", "push", "--vault", str(heron), "--today", TODAY)
    assert code != 0 and "HEAD is on elsewhere" in out


def test_sync_main_ignores_the_other_plans_uncommitted_files(docs, tmp_path):
    repo, heron, payments = docs
    bare = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-q", "-u", "origin", "main")
    assert session_start(heron, "pilot scope")[0] == 0
    teammate = tmp_path / "teammate"
    git(tmp_path, "clone", "-q", str(bare), str(teammate))
    (teammate / "projects" / "heron" / "02-constraints.md").write_text(
        (teammate / "projects" / "heron" / "02-constraints.md").read_text(encoding="utf-8") + "\nNew rule.\n", encoding="utf-8")
    git(teammate, "add", "-A")
    git(teammate, "commit", "-q", "-m", "teammate")
    git(teammate, "push", "-q", "origin", "main")
    (payments / "01-goals.md").write_text((payments / "01-goals.md").read_text(encoding="utf-8") + "\nUnsaved.\n", encoding="utf-8")
    code, out = run("close", "sync-main", "--vault", str(heron), "--today", TODAY, "--json")
    data = json.loads(out)
    assert code == 0 and data["status"] == "merged", out
    assert data["wrote"] == ["02-constraints.md"]  # plan-relative, and no file of another plan
    assert dirty(repo) == ["M projects/payments/01-goals.md"]


def test_sync_main_stops_and_says_so_when_main_and_the_branch_clash_outside_the_plan(docs, tmp_path):
    repo, heron, _ = docs
    bare = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-q", "-u", "origin", "main")
    assert session_start(heron, "pilot scope")[0] == 0
    (repo / "README.md").write_text("# docs, mine\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-q", "-m", "my readme")
    teammate = tmp_path / "teammate"
    git(tmp_path, "clone", "-q", str(bare), str(teammate))
    (teammate / "README.md").write_text("# docs, theirs\n", encoding="utf-8")
    git(teammate, "add", "-A")
    git(teammate, "commit", "-q", "-m", "their readme")
    git(teammate, "push", "-q", "origin", "main")
    code, out = run("close", "sync-main", "--vault", str(heron), "--today", TODAY, "--json")
    assert code == 1, out
    assert json.loads(out)["status"] == "conflict" and "outside" in out
    assert (repo / "README.md").read_text(encoding="utf-8") == "# docs, mine\n"  # main's change was not settled away
    assert git(repo, "status", "--short") == ""  # the merge was aborted


def test_the_path_filter_is_added_only_for_a_plan_in_a_subfolder(docs, tmp_path):
    from vela.edge import vaultgit
    _, heron, _ = docs
    solo = tmp_path / "solo"
    solo.mkdir()
    assert new_plan(solo, "Solo")[0] == 0
    assert vaultgit.plan_pathspec(solo) == () and vaultgit.plan_pathspec(heron) == ("--", ".")


def test_voice_harvest_names_pages_relative_to_the_plan(docs):
    from vela.edge import voicegit
    repo, heron, _ = docs
    (heron / "01-goals.md").write_text((heron / "01-goals.md").read_text(encoding="utf-8") + "\nVoice.\n", encoding="utf-8")
    (repo / "README.md").write_text("# docs, edited\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "both")
    assert voicegit.pages_of(heron, git(repo, "rev-parse", "HEAD")) == ["01-goals.md"]


def test_freshness_counts_only_the_plans_own_uncommitted_files(docs):
    repo, heron, payments = docs
    (payments / "01-goals.md").write_text((payments / "01-goals.md").read_text(encoding="utf-8") + "\nUnsaved.\n", encoding="utf-8")
    assert "0 uncommitted files" in run("freshness", "--vault", str(heron))[1]
    assert "1 uncommitted file" in run("freshness", "--vault", str(payments))[1]


# ------------------------------------------------------------------------------------------------------- publish

def test_publish_copies_one_plans_folder_and_counts_only_its_own_dirty_files(docs, tmp_path):
    repo, heron, payments = docs
    (payments / "01-goals.md").write_text((payments / "01-goals.md").read_text(encoding="utf-8") + "\nUnsaved.\n", encoding="utf-8")
    copy = tmp_path / "heron-copy"
    code, out = run("publish", "--vault", str(heron), "--out", str(copy), "--today", TODAY)
    assert code == 0, out
    names = sorted(p.relative_to(copy).as_posix() for p in copy.rglob("*") if p.is_file())
    assert ".vela.yaml" in names and "01-goals.md" in names
    assert not [n for n in names if n.startswith("projects")]  # nothing of the repo around the plan, or of the other plan
    assert json.loads((copy / ".vela" / "published.json").read_text(encoding="utf-8"))["dirty"] is False
    other = tmp_path / "payments-copy"
    assert run("publish", "--vault", str(payments), "--out", str(other), "--today", TODAY)[0] == 0
    assert json.loads((other / ".vela" / "published.json").read_text(encoding="utf-8"))["dirty"] is True


# --------------------------------------------------------------------------------------------------------- hooks

def hook(which, payload):
    done = subprocess.run([sys.executable, str(LAUNCHER), "hook", which], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout) if done.stdout.strip() else {}


def verdict(out):
    return out.get("hookSpecificOutput", {}).get("permissionDecision")


def test_a_bash_hook_at_the_repo_root_or_in_a_plan_denies_staging_by_hand(docs):
    repo, heron, _ = docs
    for folder in (repo, heron, heron / "sessions"):
        out = hook("bash", {"cwd": str(folder), "tool_input": {"command": "git add -A"}})
        assert verdict(out) == "deny", folder


def test_a_plain_commit_at_a_repo_root_is_denied_only_when_the_index_holds_a_plans_files(docs):
    repo, heron, _ = docs
    (repo / "README.md").write_text("# docs, edited\n", encoding="utf-8")
    git(repo, "add", "README.md")
    assert stage_verdict(repo, "git commit -m wip")[0] is None  # the index holds only an owner's file
    (heron / "01-goals.md").write_text((heron / "01-goals.md").read_text(encoding="utf-8") + "\nX.\n", encoding="utf-8")
    git(repo, "add", "projects/heron/01-goals.md")
    assert stage_verdict(repo, "git commit -m wip")[0] == "deny"
    assert stage_verdict(repo, "git commit -am wip")[0] == "deny"


def test_a_bash_hook_in_a_folder_with_no_plan_above_or_below_is_silent(docs, tmp_path):
    repo, _, _ = docs
    (repo / "notes").mkdir()
    # a folder of the repo with no plan above it: the repo root holds plans, but `notes/` is not under one
    assert verdict(hook("bash", {"cwd": str(repo / "notes"), "tool_input": {"command": "git add x"}})) is None
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    assert verdict(hook("bash", {"cwd": str(elsewhere), "tool_input": {"command": "git add x"}})) is None


def stage_verdict(folder, command):
    out = hook("bash", {"cwd": str(folder), "tool_input": {"command": command}})
    return verdict(out), out.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")


@pytest.mark.parametrize("command", [
    "git add notes/todo.md", "git add README.md notes/a.md", "git add -- notes", "git add notes/*.md",
    "git commit -m wip", "git commit -m wip README.md"])
def test_at_a_repo_root_with_plans_staging_named_files_outside_every_plan_is_allowed(docs, command):
    repo, _, _ = docs
    (repo / "notes").mkdir()
    assert stage_verdict(repo, command)[0] is None


@pytest.mark.parametrize("command", [
    "git add projects/heron/01-goals.md", "git add README.md projects/payments/x.md", "git add projects",
    "git add -A", "git add --all", "git add .", "git add -u", "git add projects/*", "git add */01-goals.md",
    "git commit -a -m wip", "git commit --all -m wip", "git add notes && git add -A"])
def test_at_a_repo_root_with_plans_staging_that_reaches_a_plan_is_denied_with_the_way_out(docs, command):
    repo, _, _ = docs
    (repo / "notes").mkdir()
    decision, reason = stage_verdict(repo, command)
    assert decision == "deny"
    assert "vela close stage" in reason and "name each path" in reason


def test_the_same_rules_hold_from_a_folder_beside_the_plans_and_not_from_inside_one(docs):
    repo, heron, _ = docs
    (repo / "notes").mkdir()
    assert stage_verdict(repo / "notes", "git add todo.md")[0] is None
    assert stage_verdict(repo / "notes", "git add ../projects/heron/x.md")[0] == "deny"
    assert stage_verdict(repo / "notes", "git add -A")[0] == "deny"
    assert stage_verdict(heron, "git add notes.md")[0] == "deny"  # inside a plan, every hand staging is denied


def test_an_edit_in_a_plan_is_guarded_by_that_plans_rules_from_the_repo_root_and_one_outside_is_not(docs):
    repo, heron, _ = docs
    (repo / "notes").mkdir()
    (heron / "02-constraints.md").write_text(CONSTRAINTS, encoding="utf-8")
    (repo / "notes" / "02-constraints.md").write_text(CONSTRAINTS, encoding="utf-8")
    inside = {"file_path": "projects/heron/02-constraints.md", "old_string": "| One team figure | assumption |",
              "new_string": "| One team figure | decided |"}
    outside = dict(inside, file_path="notes/02-constraints.md")
    assert verdict(hook("edit", {"cwd": str(repo), "tool_name": "Edit", "tool_input": inside})) == "deny"
    assert verdict(hook("edit", {"cwd": str(repo), "tool_name": "Edit", "tool_input": outside})) is None


def test_session_start_leaves_its_marker_in_every_plan_when_opened_at_the_repo_root(docs):
    repo, heron, payments = docs
    hook("session-start", {"cwd": str(repo), "session_id": "s1"})
    for plan in (heron, payments):
        assert json.loads((plan / ".vela" / "hooks-active").read_text(encoding="utf-8"))["session_id"] == "s1"


def test_the_canary_command_marks_each_plan_when_the_project_is_the_repo_root(docs, tmp_path):
    repo, heron, payments = docs
    command = json.loads((REPO / "plugin" / "hooks" / "hooks.json").read_text(encoding="utf-8"))[
        "hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    done = subprocess.run(["sh", "-c", command], input='{"tool_input":{"command":"vela where --probe"}}',
                          capture_output=True, text=True, timeout=30, env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(repo)})
    assert done.returncode == 0, done.stderr
    assert (heron / ".vela" / "hook-canary").is_file() and (payments / ".vela" / "hook-canary").is_file()
    assert not (repo / ".vela").exists()


def test_the_pre_commit_guard_judges_every_plans_staged_files_by_that_plans_rules(docs):
    repo, heron, payments = docs
    (heron / ".inbox").mkdir()
    (heron / ".inbox" / "call.md").write_text("company material\n", encoding="utf-8")
    (repo / "notes").mkdir()
    (repo / "notes" / ".inbox").mkdir()
    (repo / "notes" / ".inbox" / "x.md").write_text("not in a plan\n", encoding="utf-8")
    git(repo, "add", "-f", "notes/.inbox/x.md")
    assert run("guard", "staged", "--vault", str(repo))[0] == 0  # a path in no plan is no plan's business
    git(repo, "add", "-f", "projects/heron/.inbox/call.md")
    code, out = run("guard", "staged", "--vault", str(repo), "--json")
    assert code == 1 and [f["path"] for f in json.loads(out)["forbidden"]] == ["projects/heron/.inbox/call.md"]
    code, out = run("guard", "staged", "--vault", str(payments))
    assert code == 0  # pointed at the other plan, it judges only that plan's files


# ------------------------------------------------------------------------------------- numbers and git helpers

def test_a_plans_numbers_come_from_its_own_folder_on_every_branch(docs):
    repo, heron, payments = docs
    assert session_start(payments, "ledger")[0] == 0
    (payments / "11-unknowns-and-risks.md").write_text(
        (payments / "11-unknowns-and-risks.md").read_text(encoding="utf-8") + "\nUNK-099 a payments question\n", encoding="utf-8")
    assert checkpoint(payments)[0] == 0
    git(repo, "switch", "-q", "main")
    assert idgit.branch_texts(heron), "a plan in a subfolder reads its branches"
    assert "UNK-099" not in "\n".join(idgit.branch_texts(heron))
    assert "UNK-099" in "\n".join(idgit.branch_texts(payments))


def test_doctor_points_the_hooks_path_at_the_plans_own_folder():
    hook_facts = doctor.Hook(hook_file=True, hooks_on=False, env_vela="", config_path="", vendored="/x", launcher="",
                             hooks_dir="projects/heron/.githooks")
    assert doctor.wire_command(hook_facts, "") == "git config core.hooksPath projects/heron/.githooks"


# --------------------------------------------------------------------------------------------- a plan that is its own repo

def test_a_plan_that_is_its_own_repo_keeps_every_name_it_had(tmp_path):
    folder = tmp_path / "solo"
    folder.mkdir()
    assert new_plan(folder, "Solo")[0] == 0
    assert git(folder, "log", "--format=%s") == "Start the plan"
    code, out = session_start(folder, "kickoff", "--new-branch")
    assert code == 0, out
    assert git(folder, "branch", "--show-current") == f"session/{TODAY}-kickoff"
    (folder / "01-goals.md").write_text((folder / "01-goals.md").read_text(encoding="utf-8") + "\nA goal.\n", encoding="utf-8")
    assert checkpoint(folder)[0] == 0
    assert "01-goals.md" in files_in(folder)
    assert run("freshness", "--vault", str(folder))[1].count("uncommitted") == 1


# ---------------------------------------------------------------------------------------------------- planscope

def hook_facts(plan):
    from vela.edge import machine
    return machine.hook_facts(plan, environ={}, home=plan)


def test_either_plans_githooks_folder_counts_as_the_hooks_being_on(docs):
    repo, heron, payments = docs
    git(repo, "config", "core.hooksPath", "projects/payments/.githooks")
    assert hook_facts(heron).hooks_on and hook_facts(payments).hooks_on


def test_doctor_never_suggests_replacing_a_hooks_path_that_is_not_velas(docs):
    repo, heron, _ = docs
    git(repo, "config", "core.hooksPath", ".husky")
    facts = hook_facts(heron)
    assert not facts.hooks_on and facts.hooks_set == ".husky"
    line = doctor.hook_line(facts, lambda _: True)
    assert ".husky" in line.text and "git config core.hooksPath" not in line.text


def test_planscope_names_follow_the_plans_folder():
    assert planscope.slug_of("projects/heron/") == "heron"
    assert planscope.slug_of("Projects/Heron Rollout/") == "heron-rollout"
    assert planscope.slug_of("") == ""
    assert planscope.session_branch("heron", "2026-10-21-x") == "session/heron/2026-10-21-x"
    assert planscope.session_branch("", "2026-10-21-x") == "session/2026-10-21-x"
    assert planscope.titled("heron", "2026-10-21 Grill: x") == "[heron] 2026-10-21 Grill: x"
    assert planscope.titled("", "2026-10-21 Grill: x") == "2026-10-21 Grill: x"
    assert planscope.dashboard_branch("heron", TODAY) == f"dashboard/heron/{TODAY}"
    assert planscope.dashboard_branch("", TODAY) == f"dashboard/{TODAY}"


def test_a_plan_owns_its_own_session_branches_and_the_old_unscoped_ones():
    assert planscope.owns_session_branch("heron", "session/heron/2026-10-21-x")
    assert planscope.owns_session_branch("heron", "session/2026-10-21-old")
    assert not planscope.owns_session_branch("heron", "session/payments/2026-10-21-x")
    assert planscope.owns_session_branch("", "session/payments/2026-10-21-x")  # a repo-root plan owns them all, as before


def test_the_deepest_plan_holds_a_path():
    folders = ["projects/heron/", "projects/payments/"]
    assert planscope.plan_of("projects/heron/a.md", folders) == "projects/heron/"
    assert planscope.plan_of("README.md", folders) is None
    assert planscope.duplicate_slugs(["a/heron/", "b/heron/", "c/other/"]) == {"heron": ["a/heron/", "b/heron/"]}


def test_plan_above_stops_at_the_repo_root(docs, tmp_path):
    repo, heron, _ = docs
    assert plans.plan_above(heron / "sessions") == heron.resolve()
    assert plans.plan_above(repo) is None and plans.plan_above(repo / "projects") is None
