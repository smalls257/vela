"""A session's private notes never leave their machine by a route the lead did not pick (private-sessions Task 14).

The Violation these tests guard is an Infected Core of the plan's history at its edges: the ignore line, the guard and
the loader each keep the notes in, and publish and propose are the two places that copy a vault's files outward. Each
holds the rule by itself (a path rule in `publish.is_excluded`), so a vault that lost its ignore line still leaks
nothing. A reader may send their own notes, but only by name (`--with-record`), and the owner is told they are there
and never has them applied."""
import json
import zipfile

import pytest

from conftest import run
from sharing import git
import test_proposals
from test_proposals import propose, read, review_it, whys
from test_session_cli import TODAY, owner, start
from vela import privaterecord, publish
from vela.edge import proposals

SECRET = "SECRET-WORDS"
READER_ID = "2026-10-18-cap-rule"
world = test_proposals.world  # the reader workspace fixture, shared with the proposal tests


def an_owner_vault_that_lost_its_ignore_line(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    assert start(vault, "--mode", "dump", "--topic", "consent")[0] == 0  # start puts the line back, so lose it after
    ignore = vault / ".gitignore"
    ignore.write_text(ignore.read_text(encoding="utf-8").replace("sessions/private/\n", ""), encoding="utf-8")
    git(vault, "commit", "-qam", "lose the ignore line")
    private = vault / "sessions" / "private" / f"{TODAY}-consent.md"
    private.write_text(private.read_text(encoding="utf-8") + f"\n{SECRET}\n", encoding="utf-8")
    return vault, private


def test_a_private_file_never_leaves_without_the_ignore_line(tmp_path, monkeypatch):
    vault, private = an_owner_vault_that_lost_its_ignore_line(tmp_path, monkeypatch)
    code, output = run("close", "stage", "--vault", str(vault), "--checkpoint", "--json")
    data = json.loads(output)
    assert any(n["rule"] == "session-private" for n in data["never"]), data
    assert not any(p.startswith("sessions/private/") for p in data["staged"])
    assert "sessions/private" not in git(vault, "diff", "--cached", "--name-only")
    git(vault, "add", "-f", private.relative_to(vault).as_posix())  # committed by hand, the way W720 finds it
    git(vault, "commit", "-qm", "by hand")
    out = tmp_path / "published"
    assert run("publish", "--vault", str(vault), "--out", str(out), "--today", TODAY)[0] == 0
    sent = [p for p in out.rglob("*") if p.is_file()]
    assert sent and not any("private" in p.relative_to(out).parts for p in sent)
    assert not any(SECRET.encode() in p.read_bytes() for p in sent), "not in a page and not in the dashboard"
    assert (out / "dashboard.html").is_file()


def test_the_dashboard_built_in_the_vault_leaves_the_notes_out(tmp_path, monkeypatch):
    vault, _ = an_owner_vault_that_lost_its_ignore_line(tmp_path, monkeypatch)
    assert run("explore", str(vault), "--today", TODAY)[0] == 0
    assert SECRET.encode() not in (vault / "dashboard.html").read_bytes()


def test_publish_excludes_a_private_path_at_any_depth_and_case():
    for path in ("sessions/private/x.md", "plans/a/sessions/private/x.md", "Sessions/Private/x.md"):
        assert publish.is_excluded(path), path
    assert not publish.is_excluded("sessions/2026-10-14-x.md")
    assert not publish.is_excluded("sessions/privately.md")


def reader_with_a_session(world):
    """The reader workspace after a session of their own: a stub that names CON-001 as waiting, and private notes."""
    _, workspace = world
    stub = privaterecord.new_stub(READER_ID, "Cap rule", "2026-10-18", ["grill"])
    stub = privaterecord.with_lists(stub, {"ready": ["CON-001"]})
    (workspace / "sessions" / f"{READER_ID}.md").write_text(stub, encoding="utf-8")
    private = workspace / "sessions" / "private" / f"{READER_ID}.md"
    private.parent.mkdir(parents=True)
    private.write_text(privaterecord.new_private(READER_ID, "Cap rule", "2026-10-18", 1) + f"\n{SECRET}\n", encoding="utf-8")
    return workspace


def folder_of(tmp_path, name="2026-10-18-clearer-cap-rule"):
    return tmp_path / "proposals" / name


def test_a_proposal_leaves_the_record_out_unless_asked(world, tmp_path):
    workspace = reader_with_a_session(world)
    reasons = whys(tmp_path, **{"CON-001": "Finance said so."})
    code, text = propose(workspace, "--whys", reasons)
    assert code == 0, text
    folder = folder_of(tmp_path)
    patch, note = read(folder / "changes.patch"), read(folder / "proposal.md")
    assert "sessions/private" not in patch and SECRET not in patch + note
    assert f"sessions/{READER_ID}.md" in patch, "the stub travels; it holds only a header"
    assert f"Session: {READER_ID}." in note, "the session is named from the stub, not from the notes"
    assert not (folder / proposals.RECORD).exists()
    assert proposals.read(folder).record is False


def test_with_record_attaches_the_notes_beside_the_patch_and_review_never_applies_them(world, tmp_path):
    src, _ = world
    workspace = reader_with_a_session(world)
    code, text = propose(workspace, "--whys", whys(tmp_path, **{"CON-001": "Finance said so."}), "--with-record", READER_ID)
    assert code == 0, text
    folder = folder_of(tmp_path)
    assert sorted(p.name for p in folder.iterdir()) == ["changes.patch", "proposal.md", "record.md"]
    assert SECRET in read(folder / "record.md")
    assert SECRET not in read(folder / "changes.patch") + read(folder / "proposal.md")
    assert proposals.read(folder).record is True
    code, text = review_it(src, folder, "--json")
    assert code == 0, text
    state = json.loads(text)
    assert state["record"] is True
    worktree = src.parent / f"{src.name}-proposal-clearer-cap-rule"
    assert not (worktree / "sessions" / "private").exists() and not (worktree / "record.md").exists()
    assert "sessions/private" not in git(worktree, "show", "--name-only", "--format=", "HEAD")
    code, text = review_it(src, folder, "--slug", "again")
    assert "session notes" in text and "I did not apply or commit them" in text


def test_review_reports_no_record_when_none_was_attached(world, tmp_path):
    src, _ = world
    workspace = reader_with_a_session(world)
    assert propose(workspace, "--whys", whys(tmp_path))[0] == 0
    state = json.loads(review_it(src, folder_of(tmp_path), "--json")[1])
    assert state["record"] is False


def test_a_zip_carries_the_record_too(world, tmp_path):
    workspace = reader_with_a_session(world)
    assert propose(workspace, "--whys", whys(tmp_path), "--zip", "--with-record", READER_ID)[0] == 0
    archive = tmp_path / "proposals" / "2026-10-18-clearer-cap-rule.zip"
    names = zipfile.ZipFile(archive).namelist()
    assert sorted(n.split("/")[-1] for n in names) == ["changes.patch", "proposal.md", "record.md"]
    assert proposals.read(archive).record is True


def test_with_record_for_a_session_with_no_notes_here_is_refused_and_writes_nothing(world, tmp_path):
    workspace = reader_with_a_session(world)
    code, text = propose(workspace, "--whys", whys(tmp_path), "--with-record", "2026-10-18-nothing")
    assert code != 0 and "2026-10-18-nothing" in text and "not on this machine" in text
    assert not (tmp_path / "proposals").exists()


@pytest.mark.parametrize("bad", ["../x", "a/b", ".."])
def test_with_record_takes_an_id_not_a_path(world, tmp_path, bad):
    workspace = reader_with_a_session(world)
    code, text = propose(workspace, "--whys", whys(tmp_path), "--with-record", bad)
    assert code != 0 and "session id" in text
    assert not (tmp_path / "proposals").exists()


def test_a_home_path_in_the_attached_record_stops_the_proposal(world, tmp_path):
    workspace = reader_with_a_session(world)
    private = workspace / "sessions" / "private" / f"{READER_ID}.md"
    private.write_text(private.read_text(encoding="utf-8") + "\nSee /Users/sam/Documents/notes.txt\n", encoding="utf-8")
    code, text = propose(workspace, "--whys", whys(tmp_path), "--with-record", READER_ID)
    assert code != 0 and "private path" in text
    assert not (tmp_path / "proposals").exists() or not list((tmp_path / "proposals").iterdir())
