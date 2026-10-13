"""planner propose and planner proposals: a reader's changes become a patch an owner can apply, and the owner's answer
comes back. Run end to end against a real git repo: publish, open, edit as a reader, propose, review as the owner."""
import io
import json
import pathlib
import re
import shutil
import subprocess
import zipfile

import pytest
from conftest import run
from sharing import commit_snapshot, git

from planner import drafts, proposal, review

PAGE = "05-building-blocks/coach-building-blocks.md"
OLD_LINE = "so no real order ever crosses."
NEW_LINE = "so no real order ever crosses, and a reader's cap is a must."
MARKER = "#### CON-001 Lessons and track\n\n"
TODAY = "2026-10-18"
GONE = "sessions/2026-10-09-broker-data-coach-limits.md"
GROUPS = ["CON-001", "CON-002", "reader-notes", "2026-10-09-broker-data-coach-limits"]


def session_edit(workspace):
    """What a reader does: change a criterion, add a page, delete a page, and record one decision (pending approval)."""
    page = workspace / PAGE
    text = page.read_text(encoding="utf-8")
    assert OLD_LINE in text and MARKER in text
    text = text.replace(OLD_LINE, NEW_LINE, 1).replace(MARKER, MARKER + "- **Pending approval:** @sam, 2026-10-18\n", 1)
    page.write_text(text, encoding="utf-8")
    (workspace / "reader-notes.md").write_text("---\nid: reader-notes\ntype: initiative-section\ntitle: Notes\n---\n\n# Notes\n\nWhat Finance said.\n", encoding="utf-8")
    (workspace / GONE).unlink()


@pytest.fixture
def world(tmp_path):
    """(owner repo at the published commit, reader workspace after a session's edits)."""
    src = commit_snapshot(tmp_path)
    published, workspace = tmp_path / "published", tmp_path / "workspace"
    assert run("publish", "--vault", str(src), "--out", str(published), "--today", "2026-10-11")[0] == 0
    assert run("open", str(published), "--into", str(workspace), "--author", "Sam Okoye", "--today", "2026-10-12")[0] == 0
    session_edit(workspace)
    return src, workspace


def propose(workspace, *extra, title="Clearer cap rule"):
    return run("propose", "--vault", str(workspace), "--title", title, "--today", TODAY, *extra)


def whys(tmp_path, **by_group):
    path = tmp_path / "whys.json"
    path.write_text(json.dumps(by_group), encoding="utf-8")
    return str(path)


@pytest.fixture
def proposed(world, tmp_path):
    src, workspace = world
    code, text = propose(workspace, "--whys", whys(tmp_path, **{"CON-001": "Finance said anything else fails audit.", "CON-002": "Clearer for builders."}))
    assert code == 0, text
    return src, workspace, tmp_path / "proposals" / "2026-10-18-clearer-cap-rule"


def read(path):
    return pathlib.Path(path).read_text(encoding="utf-8")


def review_it(src, source, *extra):
    return run("proposals", "review", str(source), "--vault", str(src), "--today", TODAY, *extra)


def wt_of(src, slug="clearer-cap-rule"):
    return src.parent / f"{src.name}-proposal-{slug}"


# ------------------------------------------------------------------ propose

def test_the_proposal_folder_holds_the_note_and_a_patch_git_accepts(proposed):
    src, workspace, folder = proposed
    assert sorted(p.name for p in folder.iterdir()) == ["changes.patch", "proposal.md"]
    patch = read(folder / "changes.patch")
    base = git(src, "rev-parse", "HEAD")
    assert patch.startswith(f"# planner proposal\n# base: {base}\n# initiative: INI-001\ndiff --git ")
    assert "new file mode 100644\nindex " in patch and "--- /dev/null\n+++ b/reader-notes.md" in patch
    assert f"deleted file mode 100644\nindex " in patch and f"+++ /dev/null" in patch
    assert "+- **Pending approval:** @sam, 2026-10-18\n" in patch
    for flags in (["--check"], ["--3way", "--check"]):
        done = subprocess.run(["git", "-C", str(src), "apply", *flags, str(folder / "changes.patch")], capture_output=True, text=True, timeout=60)
        assert done.returncode == 0, done.stderr


def test_the_note_lists_pending_decisions_first_with_the_readers_own_reasons(proposed):
    _, _, folder = proposed
    note = read(folder / "proposal.md")
    assert note.startswith("# Proposal: Clearer cap rule\n")
    assert "- **Author:** Sam Okoye\n" in note and re.search(r"- \*\*Base:\*\* INI-001 at [0-9a-f]{7}, published 2026-10-11 by Priya Nair", note)
    assert "- **Written:** 2026-10-18" in note and "- **Check on this copy:** " in note
    assert note.index("## Pending decisions (need your approval)") < note.index("## Other changes and why") < note.index("## Files")
    pending = note.split("## Pending decisions")[1].split("## Other changes")[0]
    assert "### CON-001 Lessons and track: decided" in pending and "Finance said anything else fails audit." in pending
    assert "Pending approval: @sam, 2026-10-12." not in pending and "Pending approval: @sam, 2026-10-18." in pending
    other = note.split("## Other changes and why")[1]
    assert "### CON-002" in other and "Clearer for builders." in other
    assert "(1 changed, 1 added, 1 removed)" in note


def test_a_change_with_no_reason_reads_no_reason_given_never_an_invented_one(world, tmp_path):
    _, workspace = world
    assert propose(workspace)[0] == 0
    note = read(tmp_path / "proposals" / "2026-10-18-clearer-cap-rule" / "proposal.md")
    assert note.count("no reason given") == 4


def test_the_groups_listing_names_what_needs_a_reason_and_writes_nothing(world, tmp_path):
    _, workspace = world
    code, text = run("propose", "--vault", str(workspace), "--groups", "--json")
    groups = json.loads(text)
    assert code == 0 and [g["group"] for g in groups][0] == "CON-001" and groups[0]["pending"] is True
    assert [g["group"] for g in groups] == GROUPS and not (tmp_path / "proposals").exists()


def test_nothing_private_leaks_into_either_file(proposed, tmp_path):
    src, workspace, folder = proposed
    record = json.loads(read(workspace / ".planner" / "workspace.json"))
    secrets = {str(tmp_path), str(tmp_path.resolve()), str(pathlib.Path.home()), record["source_path"], record["planner_path"], str(workspace)}
    for name in ("proposal.md", "changes.patch"):
        text = read(folder / name)
        assert not [s for s in secrets if s and s in text], name
        assert not proposal.HOME_PATH.search(text) and "workspace.json" not in text


def test_a_home_path_in_a_page_stops_the_proposal_until_the_reader_agrees_to_hide_it(world, tmp_path, monkeypatch):
    _, workspace = world
    home = tmp_path / "Users" / "sam"
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: home))
    notes = workspace / "reader-notes.md"
    notes.write_text(notes.read_text(encoding="utf-8") + f"\nI looked at {home}/Documents/contract.txt\n", encoding="utf-8")
    code, text = propose(workspace)
    assert code == 2 and "private path" in text and "line" in text and "Nothing was written" in text
    assert not (tmp_path / "proposals").exists() or not list((tmp_path / "proposals").iterdir())
    code, text = propose(workspace, "--rewrite-home")
    assert code == 0, text
    patch = read(tmp_path / "proposals" / "2026-10-18-clearer-cap-rule" / "changes.patch")
    assert "<home>/Documents/contract.txt" in patch and str(home) not in patch
    assert str(home) in notes.read_text(encoding="utf-8")  # the reader's own file is not touched


def test_zip_is_one_file_with_one_top_folder(world, tmp_path):
    _, workspace = world
    assert propose(workspace, "--zip")[0] == 0
    archive = tmp_path / "proposals" / "2026-10-18-clearer-cap-rule.zip"
    assert archive.is_file() and not (tmp_path / "proposals" / "2026-10-18-clearer-cap-rule").exists()
    with zipfile.ZipFile(archive) as z:
        assert sorted(z.namelist()) == ["2026-10-18-clearer-cap-rule/changes.patch", "2026-10-18-clearer-cap-rule/proposal.md"]


def test_a_second_proposal_with_the_same_title_does_not_overwrite_the_first(world, tmp_path):
    _, workspace = world
    assert propose(workspace)[0] == 0 and propose(workspace)[0] == 0
    assert sorted(p.name for p in (tmp_path / "proposals").iterdir()) == ["2026-10-18-clearer-cap-rule", "2026-10-18-clearer-cap-rule-2"]


def test_an_owner_cannot_propose_and_is_told_what_to_do_instead(tmp_path):
    src = commit_snapshot(tmp_path)
    code, text = propose(src)
    assert code == 2 and "owner" in text and "PR" in text and "Nothing was written" in text
    assert not (tmp_path / "proposals").exists()


def test_a_reader_with_no_changes_has_nothing_to_propose(tmp_path):
    src = commit_snapshot(tmp_path)
    run("publish", "--vault", str(src), "--out", str(tmp_path / "pub"), "--today", "2026-10-11")
    run("open", str(tmp_path / "pub"), "--into", str(tmp_path / "ws"), "--author", "Sam Okoye")
    code, text = propose(tmp_path / "ws")
    assert code == 2 and "nothing to propose" in text


def test_a_reason_for_a_group_that_does_not_exist_is_an_error_not_a_lost_reason(world, tmp_path):
    _, workspace = world
    code, text = propose(workspace, "--whys", whys(tmp_path, **{"CON-009": "typo"}))
    assert code == 2 and "CON-009" in text and "CON-001" in text


def test_the_proposal_and_the_drafts_chip_count_the_same_files(world):
    _, workspace = world
    from planner.edge import copies
    shown = drafts.compare(copies.read_tree(workspace / ".planner" / "baseline", skip_published=True), copies.read_tree(workspace, skip_published=True))
    code, text = run("propose", "--vault", str(workspace), "--groups", "--json")
    assert len(shown) == 3 and {p for g in json.loads(text) for p in (c["path"] for c in g["changes"])} == {c["path"] for c in shown}


def test_a_file_that_is_not_a_page_is_grouped_as_not_tied_to_an_id(world):
    _, workspace = world
    (workspace / "notes.txt").write_text("plain\n", encoding="utf-8")
    groups = json.loads(run("propose", "--vault", str(workspace), "--groups", "--json")[1])
    loose = next(g for g in groups if g["group"] == proposal.NO_ID)
    assert [c["path"] for c in loose["changes"]] == ["notes.txt"]


def test_a_file_name_with_a_backtick_is_refused_by_name(world):
    _, workspace = world
    (workspace / "odd`name.md").write_text("x\n", encoding="utf-8")
    code, text = propose(workspace)
    assert code == 2 and "odd`name.md" in text


# ------------------------------------------------------------------ the patch writer on its own

def build(old, new, path="a.md"):
    built = proposal.build({path: old} if old is not None else {}, {path: new} if new is not None else {}, "f" * 40, "INI-001")
    return built


def apply_in_repo(tmp_path, files, patch):
    repo = tmp_path / "scratch"
    repo.mkdir()
    git(tmp_path, "init", "-q", "-b", "main", str(repo))
    git(repo, "config", "user.name", "T")
    git(repo, "config", "user.email", "t@example.com")
    for name, data in files.items():
        (repo / name).write_bytes(data)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", "base")
    (tmp_path / "p.patch").write_bytes(patch.encode("utf-8"))
    done = subprocess.run(["git", "-C", str(repo), "apply", "--3way", str(tmp_path / "p.patch")], capture_output=True, text=True, timeout=60)
    return repo, done


@pytest.mark.parametrize("old,new", [
    (b"one\r\ntwo\r\nthree\r\n", b"one\r\nTWO\r\nthree\r\nfour\r\n"),
    (b"one\ntwo", b"one\ntwo\nthree"),
    (b"one\ntwo\n", b"one\ntwo"),
    (b"a\x0cb\nc\n", b"a\x0cb\nC\n"),
    (b"caf\xc3\xa9\n", b"caf\xc3\xa9 au lait\n"),
])
def test_line_endings_and_the_missing_final_newline_survive_a_round_trip(tmp_path, old, new):
    built = build(old, new)
    repo, done = apply_in_repo(tmp_path, {"a.md": old}, built.patch)
    assert done.returncode == 0, done.stderr
    assert (repo / "a.md").read_bytes() == new


def test_a_new_file_a_deleted_file_an_empty_file_and_a_name_with_a_space_apply(tmp_path):
    base = {"gone.md": b"bye\n", "sp ace.md": b"x\ny\n", "empty-gone.md": b""}
    work = {"sp ace.md": b"x\ny\nz\n", "fresh.md": b"hello\n", "empty-new.md": b""}
    built = proposal.build(base, work, "f" * 40, "INI-001")
    repo, done = apply_in_repo(tmp_path, base, built.patch)
    assert done.returncode == 0, done.stderr
    assert sorted(p.name for p in repo.iterdir() if p.name != ".git") == ["empty-new.md", "fresh.md", "sp ace.md"]
    assert (repo / "sp ace.md").read_bytes() == b"x\ny\nz\n"


def test_a_binary_file_is_listed_and_never_patched(tmp_path):
    built = proposal.build({"doc.pdf": b"%PDF\x00\x01"}, {"doc.pdf": b"%PDF\x00\x02", "bad.md": b"\xff\xfe broken"}, "f" * 40, "INI-001")
    assert built.files == () and sorted(p for _, p in built.binaries) == ["bad.md", "doc.pdf"]
    assert "doc.pdf" not in built.patch and "diff --git" not in built.patch


def test_binary_files_appear_in_the_note_as_not_included(world, tmp_path):
    _, workspace = world
    (workspace / "sources").mkdir(exist_ok=True)
    (workspace / "sources" / "contract.pdf").write_bytes(b"%PDF-1.4\x00\x00binary")
    assert propose(workspace)[0] == 0
    note = read(tmp_path / "proposals" / "2026-10-18-clearer-cap-rule" / "proposal.md")
    assert "binary file added: sources/contract.pdf, not included" in note and "binary files not included" in note


@pytest.mark.parametrize("path", ["../x.md", "/etc/x.md", ".git/config", ".planner/baseline/x.md", "voice/local/me.md", "C:/x.md", "a\\b.md"])
def test_paths_that_escape_or_belong_to_git_are_refused_when_writing(path):
    with pytest.raises(proposal.ProposalError):
        proposal.check_path(path)


def test_group_keys_follow_the_item_heading_a_change_sits_under():
    text = "---\nid: APP-x\n---\n\n## Contracts\n\n### CON-001 One\n\nfoo\n\n### CON-002 Two\n\nbar\n\n## Other\n\nbaz\n"
    ids = proposal.ids_by_line("p.md", text)
    assert [ids[i] for i in (8, 12, 16)] == ["CON-001", "CON-002", "APP-x"]


# ------------------------------------------------------------------ review

def test_review_applies_the_proposal_on_its_own_branch_in_a_worktree_and_leaves_main_alone(proposed):
    src, _, folder = proposed
    head = git(src, "rev-parse", "HEAD")
    code, text = review_it(src, folder)
    assert code == 0, text
    wt = wt_of(src)
    assert "Applied cleanly and committed" in text and "Branch proposal/clearer-cap-rule" in text
    assert git(src, "rev-parse", "HEAD") == head and git(src, "status", "--porcelain") == "" and git(src, "branch", "--show-current") == "main"
    assert git(wt, "branch", "--show-current") == "proposal/clearer-cap-rule"
    assert git(wt, "log", "-1", "--format=%s", "proposal/clearer-cap-rule") != "" and "Proposal: Clearer cap rule (from Sam Okoye)" in git(wt, "log", "--format=%s", "-3")
    assert NEW_LINE in read(wt / PAGE) and (wt / "reader-notes.md").is_file() and not (wt / GONE).exists()
    assert text.index("CON-001 (pending decision)") < text.index("CON-002:")


def test_review_takes_a_zip_and_a_bare_patch_too(proposed, tmp_path):
    src, workspace, folder = proposed
    assert propose(workspace, "--zip", title="Zipped")[0] == 0
    code, text = review_it(src, tmp_path / "proposals" / "2026-10-18-zipped.zip", "--slug", "zipped")
    assert code == 0, text
    code, text = review_it(src, folder / "changes.patch", "--slug", "bare")
    assert code == 0 and "changes.patch" in text and "Applied cleanly" in text


def test_accepting_a_pending_decision_clears_the_marker_credits_the_reader_and_keeps_check_green(proposed):
    src, _, folder = proposed
    review_it(src, folder, "--json")
    wt = wt_of(src)
    assert "Pending approval" in read(wt / PAGE)
    code, text = run("proposals", "accept", "--vault", str(wt), "--item", "CON-001", "--by", "@priya")
    assert code == 0, text
    page = read(wt / PAGE)
    assert "Pending approval" not in page
    section = page.split("#### CON-001 Lessons and track\n")[1].split("####")[0]
    assert "- **Decided by:** @priya\n" in section and "**Credit:** @sam proposed this on 2026-10-18" in section
    code, text = run("check", "--vault", str(wt), "--today", TODAY)
    assert "E322" not in text and "W327" not in text
    assert not [line for line in text.splitlines() if "coach-building-blocks" in line and ("W324" in line or "E3" in line)]
    assert "Accept CON-001" in git(wt, "log", "-1", "--format=%s")


def test_accepting_with_no_marker_says_so(proposed):
    src, _, folder = proposed
    review_it(src, folder)
    code, text = run("proposals", "accept", "--vault", str(wt_of(src)), "--item", "CON-002", "--by", "@priya")
    assert code == 2 and "no well-formed **Pending approval:** marker" in text


def test_rejecting_a_group_takes_its_changes_back_out_and_keeps_the_rest(proposed):
    src, _, folder = proposed
    review_it(src, folder)
    wt = wt_of(src)
    code, text = run("proposals", "reject", str(folder), "--vault", str(wt), "--group", "CON-002", "--reason", "The cap stays a may until Finance writes it down.")
    assert code == 0, text
    page = read(wt / PAGE)
    assert NEW_LINE not in page and OLD_LINE in page and "Pending approval: @sam" in page.replace("**", "")
    assert (wt / "reader-notes.md").is_file()
    assert "Reject CON-002" in git(wt, "log", "-1", "--format=%s")


def test_rejecting_needs_the_owners_reason(proposed):
    src, _, folder = proposed
    review_it(src, folder)
    code, text = run("proposals", "reject", str(folder), "--vault", str(wt_of(src)), "--group", "CON-002", "--reason", "  ")
    assert code == 2 and "reason" in text


def test_rejecting_a_pending_decision_removes_its_marker(proposed):
    src, _, folder = proposed
    review_it(src, folder)
    wt = wt_of(src)
    assert run("proposals", "reject", str(folder), "--vault", str(wt), "--group", "CON-001", "--reason", "Not decided yet.")[0] == 0
    assert "Pending approval" not in read(wt / PAGE)


def test_accept_and_reject_only_run_in_a_proposal_worktree(proposed):
    src, _, folder = proposed
    code, text = run("proposals", "accept", "--vault", str(src), "--item", "CON-001", "--by", "@priya")
    assert code == 2 and "not a proposal/ branch" in text
    code, text = run("proposals", "reject", str(folder), "--vault", str(src), "--group", "CON-002", "--reason", "x")
    assert code == 2 and "not a proposal/ branch" in text


def answer(src, folder, decisions, tmp_path):
    path = tmp_path / "decisions.json"
    path.write_text(json.dumps(decisions), encoding="utf-8")
    return run("proposals", "answer", str(folder), "--vault", str(wt_of(src)), "--decisions", str(path), "--today", "2026-10-20")


def test_answer_md_has_one_entry_per_group_with_the_owners_reason(proposed, tmp_path):
    src, _, folder = proposed
    review_it(src, folder)
    wt = wt_of(src)
    run("proposals", "accept", "--vault", str(wt), "--item", "CON-001", "--by", "@priya")
    run("proposals", "reject", str(folder), "--vault", str(wt), "--group", "CON-002", "--reason", "The cap stays a may.")
    code, text = answer(src, folder, [{"group": "CON-001", "outcome": "accepted"},
                                      {"group": "CON-002", "outcome": "rejected", "reason": "The cap stays a may."},
                                      {"group": "reader-notes", "outcome": "edited", "reason": "I kept your notes and fixed the heading."},
                                      {"group": GROUPS[3], "outcome": "accepted"}], tmp_path)
    assert code == 0, text
    md = read(folder / "answer.md")
    assert md.startswith("# Answer: Clearer cap rule\n") and "- **Reviewed by:** Priya Nair" in md and "branch proposal/clearer-cap-rule" in md
    assert [h for h in re.findall(r"^## (.+)$", md, re.M)] == [*GROUPS[:3], GROUPS[3], "Next"]
    assert "Rejected.\n\nThe cap stays a may." in md and "Accepted with the owner's edit." in md
    assert "Publish a new copy and re-open to continue." in md
    for secret in (str(tmp_path), str(tmp_path.resolve()), str(pathlib.Path.home())):
        assert secret not in md


def test_an_answer_that_skips_a_group_or_gives_no_reason_for_a_rejection_is_refused(proposed, tmp_path):
    src, _, folder = proposed
    review_it(src, folder)
    code, text = answer(src, folder, [{"group": "CON-001", "outcome": "accepted"}], tmp_path)
    assert code == 2 and "no decision yet" in text and "CON-002" in text and not (folder / "answer.md").exists()
    code, text = answer(src, folder, [{"group": g, "outcome": "rejected"} for g in GROUPS], tmp_path)
    assert code == 2 and "needs the owner's reason" in text


def test_an_answer_that_quotes_a_private_path_is_refused(proposed, tmp_path):
    src, _, folder = proposed
    review_it(src, folder)
    decisions = [{"group": g, "outcome": "rejected", "reason": f"see {wt_of(src)}/x"} for g in GROUPS]
    code, text = answer(src, folder, decisions, tmp_path)
    assert code == 2 and "private path" in text and not (folder / "answer.md").exists()


def test_a_zip_proposal_is_answered_beside_the_zip(proposed, tmp_path):
    src, workspace, _ = proposed
    assert propose(workspace, "--zip", title="Zipped")[0] == 0
    archive = tmp_path / "proposals" / "2026-10-18-zipped.zip"
    review_it(src, archive, "--slug", "zipped")
    path = tmp_path / "d.json"
    path.write_text(json.dumps([{"group": g, "outcome": "accepted"} for g in GROUPS]), encoding="utf-8")
    code, text = run("proposals", "answer", str(archive), "--vault", str(wt_of(src, "zipped")), "--decisions", str(path))
    assert code == 0, text
    assert (tmp_path / "proposals" / "2026-10-18-zipped-answer.md").is_file()


# ------------------------------------------------------------------ review: the owner's side has moved, or the proposal is bad

def commit_in(src, path, old, new):
    page = src / path
    page.write_text(page.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8")
    git(src, "commit", "-qam", "owner moved on")


def test_when_the_vault_moved_elsewhere_in_the_page_the_three_way_apply_still_succeeds_and_says_how_far(proposed):
    src, _, folder = proposed
    page = read(src / PAGE)
    other = next(line for line in page.splitlines() if line.startswith("- **Consumers:**") and "CON-002" not in line)
    commit_in(src, PAGE, other, other + " (owner edit)")
    code, text = review_it(src, folder, "--json")
    state = json.loads(text)
    assert code == 0 and state["applied"] is True and state["behind"] == 1
    assert NEW_LINE in read(wt_of(src) / PAGE) and "(owner edit)" in read(wt_of(src) / PAGE)


def test_when_the_owner_changed_the_same_line_the_conflict_is_reported_plainly_with_markers_left(proposed):
    src, _, folder = proposed
    commit_in(src, PAGE, OLD_LINE, "so no real order ever crosses; the owner rewrote this.")
    code, text = review_it(src, folder)
    assert code == 1 and "CONFLICTS in 05-building-blocks/coach-building-blocks.md" in text and "moved 1 commit" in text
    merged = read(wt_of(src) / PAGE)
    assert "<<<<<<<" in merged and ">>>>>>>" in merged and "the owner rewrote this" in merged


def test_a_base_commit_this_clone_does_not_have_says_which_clone_to_fetch(proposed):
    src, _, folder = proposed
    patch = folder / "changes.patch"
    patch.write_text(read(patch).replace(git(src, "rev-parse", "HEAD"), "a" * 40), encoding="utf-8")
    code, text = review_it(src, folder)
    assert code == 2 and "aaaaaaa" in text and "git fetch" in text and not wt_of(src).exists()


def test_a_dirty_checkout_is_refused_with_the_reason_and_no_worktree_is_made(proposed):
    src, _, folder = proposed
    (src / "scratch.md").write_text("mine\n", encoding="utf-8")
    code, text = review_it(src, folder)
    assert code == 2 and "uncommitted" in text and "scratch.md" in text and not wt_of(src).exists()


def test_a_branch_that_already_exists_is_not_reused(proposed):
    src, _, folder = proposed
    assert review_it(src, folder)[0] == 0
    code, text = review_it(src, folder)
    assert code == 2 and "already exists" in text


@pytest.mark.parametrize("damage,message", [
    (lambda t: re.sub(r"@@ -(\d+),7 \+(\d+),7 @@", r"@@ -\1,7 +\2,9 @@", t, count=1), "says 7 old and 9 new"),
    (lambda t: t.split("diff --git", 1)[0], "no 'diff --git' section"),
    (lambda t: t.replace("# base: ", "# basis: "), "no '# base:"),
    (lambda t: t.replace("diff --git a/reader-notes.md b/reader-notes.md", "diff --git a/../evil.md b/../evil.md"), "climbs out"),
    (lambda t: t.replace("diff --git a/reader-notes.md b/reader-notes.md", "diff --git a/.git/hooks/pre-commit b/.git/hooks/pre-commit"), "git's own folder"),
    (lambda t: t.replace("diff --git a/reader-notes.md b/reader-notes.md", "diff --git a/old.md b/new.md"), "plain a/<path> b/<path>"),
])
def test_a_malformed_or_hostile_patch_is_refused_before_git_sees_it(proposed, damage, message):
    src, _, folder = proposed
    patch = folder / "changes.patch"
    patch.write_text(damage(read(patch)), encoding="utf-8")
    code, text = review_it(src, folder)
    assert code == 2 and message in text and not wt_of(src).exists()
    assert git(src, "branch", "--list", "proposal/*") == ""


def test_a_patch_git_cannot_apply_leaves_the_repo_as_it_found_it(proposed):
    src, _, folder = proposed
    git(src, "rm", "-q", PAGE)
    git(src, "commit", "-qm", "owner removed the page the proposal edits")
    code, text = review_it(src, folder)
    assert code == 2 and "nothing was changed" in text and "coach-building-blocks.md" in text
    assert git(src, "branch", "--list", "proposal/*") == "" and not wt_of(src).exists() and git(src, "worktree", "list").count("\n") == 0


def test_a_reader_cannot_review(proposed):
    _, workspace, folder = proposed
    code, text = run("proposals", "review", str(folder), "--vault", str(workspace))
    assert code == 2 and "owner's job" in text


def test_a_missing_proposal_names_the_path(proposed, tmp_path):
    src, _, _ = proposed
    code, text = review_it(src, tmp_path / "nope")
    assert code == 2 and "nope" in text and "does not exist" in text


def test_a_zip_with_a_name_that_climbs_out_is_refused_unread(proposed, tmp_path):
    src, _, folder = proposed
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("../changes.patch", "x")
    code, text = review_it(src, evil)
    assert code == 2 and "outside its folder" in text


# ------------------------------------------------------------------ accept_pending on its own

PAGE_TEXT = "---\nid: APP-x\ntype: app-building-blocks\ntitle: X\n---\n\n## Contracts\n\n### CON-001 One\n\n- **Pending approval:** @sam, 2026-10-18\n- **Consumers:** a\n"


def test_accept_pending_adds_history_when_the_page_has_none():
    new, by, date = review.accept_pending("p.md", PAGE_TEXT, "CON-001", "@priya")
    assert (by, date) == ("@sam", "2026-10-18")
    assert "- **Decided by:** @priya\n- **Consumers:** a\n" in new
    assert new.endswith("\n## History\n\n#### CON-001\n\n**Credit:** @sam proposed this on 2026-10-18\n")


def test_accept_pending_credits_inside_an_existing_history_entry_and_keeps_crlf():
    text = (PAGE_TEXT.replace("- **Pending approval:** @sam, 2026-10-18\n", "") +
            "\n## History\n\n#### CON-001\n\n- **Pending approval:** @sam, 2026-10-18\n- **Decision:** [[x]]\n\n#### CON-002\n\n- **Decision:** [[y]]\n").replace("\n", "\r\n")
    new, _, _ = review.accept_pending("p.md", text, "CON-001", "@priya")
    assert "\n" not in new.replace("\r\n", "")
    entry = new.split("#### CON-001")[1].split("#### CON-002")[0]
    assert "- **Decided by:** @priya\r\n" in entry and "**Credit:** @sam proposed this on 2026-10-18" in entry and "Pending approval" not in new


def test_accept_pending_on_a_page_level_marker_credits_directly_under_history():
    text = "---\nid: APP-x\ntype: app-building-blocks\ntitle: X\n---\n\n## Stuff\n\ntext\n\n## History\n\n- **Pending approval:** @sam, 2026-10-18\n"
    new, _, _ = review.accept_pending("p.md", text, "", "@priya")
    assert "## History\n\n**Credit:** @sam proposed this on 2026-10-18\n\n- **Decided by:** @priya\n" in new


def test_accept_pending_refuses_a_malformed_marker_and_a_bad_handle():
    with pytest.raises(review.ReviewError, match="not a handle"):
        review.accept_pending("p.md", PAGE_TEXT, "CON-001", "priya")
    with pytest.raises(review.ReviewError, match="no @handle"):
        review.accept_pending("p.md", PAGE_TEXT.replace("@sam, 2026-10-18", "sam"), "CON-001", "@priya")


def test_reasons_and_decisions_can_arrive_on_standard_input(world, tmp_path, monkeypatch):
    src, workspace = world
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"CON-002": "Said with \"quotes\" and $dollars and `ticks`."})))
    assert propose(workspace, "--whys", "-")[0] == 0
    folder = tmp_path / "proposals" / "2026-10-18-clearer-cap-rule"
    assert 'Said with "quotes" and $dollars and `ticks`.' in read(folder / "proposal.md")
    review_it(src, folder)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps([{"group": g, "outcome": "accepted"} for g in GROUPS])))
    code, text = run("proposals", "answer", str(folder), "--vault", str(wt_of(src)), "--decisions", "-")
    assert code == 0, text
    assert read(folder / "answer.md").count("Accepted.") == len(GROUPS)


# ------------------------------------------------------------------ the two skills

def skill(name):
    return (pathlib.Path(__file__).resolve().parent.parent / "plugin" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def option_strings():
    from planner import cli
    parser = cli.build_parser()
    commands = parser._subparsers._group_actions[0].choices
    found = set()
    for sub in [commands["propose"], *commands["proposals"]._subparsers._group_actions[0].choices.values()]:
        found |= {o for action in sub._actions for o in action.option_strings}
    return found


@pytest.mark.parametrize("name", ["propose", "proposals"])
def test_every_flag_a_skill_tells_claude_to_run_exists(name):
    flags = {flag for line in skill(name).splitlines() if "planner" in line and ("propos" in line) for flag in re.findall(r"--[a-z][a-z-]*", line)}
    assert flags and flags <= option_strings(), flags - option_strings()


def test_propose_never_invents_a_reason_or_sends_anything():
    text = skill("propose")
    for rule in ("no reason given", "Never invent a reason", "Never send, email, upload or share the proposal", "never run `git` or `gh`",
                 "Never add that flag without their yes", "A skipped question, \"not sure\", or silence is fine"):
        assert rule in text, rule
    assert "planner role" in text and "you decide directly" in text and "--whys -" in text


def test_review_leaves_every_decision_to_the_owner_and_never_pushes():
    text = skill("proposals")
    for rule in ("pending decisions first", "The owner always decides", "Never write the owner's reason for them", "**Never push, and never open a PR yourself.**",
                 "Never block it, never hide it", "E316", "git worktree remove", "planner proposals accept", "planner proposals reject", "planner proposals answer"):
        assert rule in text, rule


def test_the_readers_drafts_view_names_the_propose_command_and_the_page_stays_offline(world):
    _, workspace = world
    assert run("explore", str(workspace), "--today", "2026-10-12")[0] == 0
    page = read(workspace / "dashboard.html")
    assert "/planner:propose" in page and "Nothing is sent from this page." in page
    assert str(pathlib.Path.home()) not in page
