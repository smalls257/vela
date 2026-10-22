"""`vela session open` (overhaul Task 6a): the open record and its branch, found by the tool instead of a git recipe
the close skill ran by hand. Real repos in tmp_path, with a bare origin where a test needs one."""
import datetime
import json
import os
import shutil

from conftest import MINI, run
from sharing import git, make_vault, with_remote
import session_files

YEAR = datetime.date.today().year  # `--for-lead` says the year only when it is not this one


def record(record_id, modes, status="open", title=None, date=None):
    lines = ["---", f"id: {record_id}", "type: session"]
    if title:
        lines.append(f'title: "{title}"')
    lines += [f"date: {date or record_id[:10]}", f"modes: [{', '.join(modes)}]", f"status: {status}",
              "summary: In progress.", "---", "", f"# {record_id[:10]} {title or record_id}", "", "## Captures", ""]
    return "\n".join(lines) + "\n"


def commit_record(root, branch, record_id, modes, status="open", title=None, new_branch=True, date=None):
    """Write a session record on `branch` (created from main when new), commit it, and come back to main."""
    git(root, "switch", "-q", *(["-c"] if new_branch else []), branch)
    session_files.write_record(root, record_id, record(record_id, modes, status, title, date))
    git(root, "add", "sessions")
    git(root, "commit", "-q", "-m", f"Open session {record_id}")
    git(root, "switch", "-q", "main")


def current(root):
    return git(root, "rev-parse", "--abbrev-ref", "HEAD")


def test_two_records_on_one_branch_finds_the_open_one(tmp_path):
    vault = make_vault(tmp_path)
    challenge = "2026-10-10-challenge-con-001"
    commit_record(vault, f"session/{challenge}", challenge, ["challenge"], status="closed")
    commit_record(vault, f"session/{challenge}", "2026-10-12-answer-con-001", ["answer"], new_branch=False)
    code, output = run("session", "open", "--vault", str(vault), "--json")
    assert code == 0, output
    found = json.loads(output)["open"]
    assert [(r["id"], r["branch"], r["modes"]) for r in found] == [
        ("2026-10-12-answer-con-001", f"session/{challenge}", ["answer"])]
    code, output = run("session", "open", "--vault", str(vault))
    assert output.strip() == (f"open: 2026-10-12-answer-con-001 on session/{challenge}, modes: answer, "
                              "date: 2026-10-12")


def test_several_open_exits_3_and_lists(tmp_path):
    vault = make_vault(tmp_path)
    commit_record(vault, "session/2026-10-13-shop-boundary", "2026-10-13-shop-boundary", ["boundary"])
    commit_record(vault, "session/2026-10-14-consent-grill", "2026-10-14-consent-grill", ["grill"])
    code, output = run("session", "open", "--vault", str(vault), "--switch")
    assert code == 3, output
    assert current(vault) == "main"  # --switch never guesses
    assert output.splitlines() == [
        "2 sessions are open; nothing changed. Run again with --id <id> to pick one:",
        "- 2026-10-13-shop-boundary on session/2026-10-13-shop-boundary, modes: boundary, date: 2026-10-13",
        "- 2026-10-14-consent-grill on session/2026-10-14-consent-grill, modes: grill, date: 2026-10-14"]
    code, output = run("session", "open", "--vault", str(vault), "--json")
    assert code == 3
    assert [c["branch"] for c in json.loads(output)["needs_lead"]] == [
        "session/2026-10-13-shop-boundary", "session/2026-10-14-consent-grill"]


def test_id_picks_one_of_several_and_switches(tmp_path):
    vault = make_vault(tmp_path)
    commit_record(vault, "session/2026-10-13-shop-boundary", "2026-10-13-shop-boundary", ["boundary"])
    commit_record(vault, "session/2026-10-14-consent-grill", "2026-10-14-consent-grill", ["grill"])
    code, output = run("session", "open", "--vault", str(vault), "--switch", "--id", "2026-10-14-consent-grill")
    assert code == 0, output
    assert output.splitlines()[-1] == "switched to session/2026-10-14-consent-grill."
    assert current(vault) == "session/2026-10-14-consent-grill"
    code, output = run("session", "open", "--vault", str(vault), "--id", "2026-10-01-nothing-here")
    assert (code, output.strip()) == (1, "No open session has the id 2026-10-01-nothing-here.")


def test_none_open_exits_1_plainly(tmp_path):
    vault = make_vault(tmp_path)
    commit_record(vault, "session/2026-10-13-done", "2026-10-13-done", ["grill"], status="closed")
    for flag in ([], ["--for-lead"]):
        code, output = run("session", "open", "--vault", str(vault), *flag)
        assert (code, output) == (1, "No session is open.\n")


def test_local_copy_wins_over_a_stale_origin(tmp_path):
    """Closed here and not yet pushed: origin still says open, but this machine's copy is the one the work is on."""
    vault = make_vault(tmp_path)
    with_remote(tmp_path, vault)
    commit_record(vault, "session/2026-10-13-done", "2026-10-13-done", ["grill"])
    git(vault, "push", "-q", "origin", "session/2026-10-13-done")
    commit_record(vault, "session/2026-10-13-done", "2026-10-13-done", ["grill"], status="closed", new_branch=False)
    assert run("session", "open", "--vault", str(vault))[0] == 1


def test_remote_only_branch_is_found_and_switch_tracks_it(tmp_path):
    vault = make_vault(tmp_path)
    bare = with_remote(tmp_path, vault)
    other = tmp_path / "laptop"
    git(tmp_path, "clone", "-q", str(bare), str(other))
    commit_record(other, "session/2026-10-14-consent-grill", "2026-10-14-consent-grill", ["grill"])
    git(other, "push", "-q", "origin", "session/2026-10-14-consent-grill")
    git(vault, "fetch", "-q", "origin")
    code, output = run("session", "open", "--vault", str(vault), "--json")
    assert code == 0, output
    assert json.loads(output)["open"][0]["remote_only"] is True
    code, output = run("session", "open", "--vault", str(vault), "--switch")
    assert code == 0, output
    assert output.splitlines() == [
        "open: 2026-10-14-consent-grill on session/2026-10-14-consent-grill (only on origin), modes: grill, "
        "date: 2026-10-14",
        "switched to session/2026-10-14-consent-grill (a new local branch tracking origin)."]
    assert current(vault) == "session/2026-10-14-consent-grill"
    assert git(vault, "rev-parse", "--abbrev-ref", "@{upstream}") == "origin/session/2026-10-14-consent-grill"


def test_switch_moves_to_the_one_open_branch(tmp_path):
    vault = make_vault(tmp_path)
    commit_record(vault, "session/2026-10-14-consent-grill", "2026-10-14-consent-grill", ["grill"])
    blocker = vault / "sessions" / "2026-10-14-consent-grill.md"
    blocker.write_text("an untracked file the switch would overwrite\n", encoding="utf-8")
    code, output = run("session", "open", "--vault", str(vault), "--switch")
    assert code == 2, output
    assert "git switch session/2026-10-14-consent-grill failed:" in output and "untracked" in output
    assert current(vault) == "main"
    blocker.unlink()
    code, output = run("session", "open", "--vault", str(vault), "--switch")
    assert code == 0, output
    assert current(vault) == "session/2026-10-14-consent-grill"
    code, output = run("session", "open", "--vault", str(vault), "--switch")
    assert output.splitlines()[-1] == "already on session/2026-10-14-consent-grill."


def test_for_lead_says_the_topic_not_the_id(tmp_path):
    vault = make_vault(tmp_path)
    record_id = f"{YEAR}-10-14-consent-grill"
    commit_record(vault, f"session/{record_id}", record_id, ["grill"], title="Consent and identity grill")
    code, output = run("session", "open", "--vault", str(vault), "--for-lead", "--switch")
    assert code == 0, output
    assert output.splitlines() == ["One session is open: Consent and identity grill, started October 14.",
                                   "Switched to its branch."]
    assert record_id not in output and "session/" not in output


def test_for_lead_names_an_item_in_a_title_by_its_name(tmp_path):
    """An answer session's title is `Answer: <ID>`; the lead hears the item's name, and the leak check holds."""
    vault = make_vault(tmp_path)
    commit_record(vault, "session/2026-01-20-answer-con-001", "2026-01-20-answer-con-001", ["answer"],
                  title="Answer: CON-001")
    code, output = run("session", "open", "--vault", str(vault), "--for-lead")
    assert code == 0, output
    assert "CON-001" not in output and output.startswith("One session is open: Answer: ")


def test_reader_copy_uses_no_git(tmp_path, monkeypatch):
    copy = tmp_path / "copy"
    shutil.copytree(MINI, copy)
    (copy / ".vela").mkdir()
    (copy / ".vela" / "workspace.json").write_text('{"role": "reader"}', encoding="utf-8")
    session_files.write_record(copy, "2026-10-14-reading", record("2026-10-14-reading", ["discover"]))
    shims, called = tmp_path / "shims", tmp_path / "git-was-called"
    shims.mkdir()
    (shims / "git").write_text(f"#!/bin/sh\ntouch '{called}'\nexit 1\n", encoding="utf-8")
    (shims / "git").chmod(0o755)
    monkeypatch.setenv("PATH", f"{shims}{os.pathsep}{os.environ['PATH']}")
    code, output = run("session", "open", "--vault", str(copy), "--switch")
    assert code == 0, output
    assert output.splitlines() == ["open: 2026-10-14-reading on this folder, modes: discover, date: 2026-10-14",
                                   "read copy: no branches, nothing switched."]
    code, output = run("session", "open", "--vault", str(copy), "--switch", "--for-lead")
    assert output.splitlines()[-1] == "This is your copy, so it has no branches to switch to."
    assert not called.exists(), "a reader copy ran git"


def test_vault_in_a_subfolder_of_its_repo(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(MINI, repo / "plan")
    git(tmp_path, "init", "-q", "-b", "main", str(repo))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "first")
    git(repo, "switch", "-q", "-c", "session/2026-10-14-consent-grill")
    session_files.write_record(repo / "plan", "2026-10-14-consent-grill", record("2026-10-14-consent-grill", ["grill"]))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "Open session")
    git(repo, "switch", "-q", "main")
    code, output = run("session", "open", "--vault", str(repo / "plan"), "--json")
    assert code == 0, output
    assert json.loads(output)["open"][0]["path"] == "sessions/2026-10-14-consent-grill.md"
