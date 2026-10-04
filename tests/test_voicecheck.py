"""planner voicecheck: a voice rewrite may change words, never the IDs, numbers, dates,
wikilinks, code spans or table cells they carry."""
import shutil
import subprocess

import pytest

from conftest import run
from planner import voicecheck

DRAFT = ("Booking holds a seat for 10 minutes ([[CAP-014-hold-a-seat|CAP-014]]). It calls CON-003 on 2026-11-20, "
         "60% of the time, through `get`.\n\n| Contract | Calls |\n|---|---|\n| CON-003 | 2 |\n")


def kinds(text):
    return [(t.kind, t.text) for t in voicecheck.tokens(text)]


def test_the_same_tokens_in_new_words_pass():
    after = DRAFT.replace("Booking holds a seat", "A seat stays with Booking").replace("It calls", "Booking calls")
    assert voicecheck.compare(DRAFT, after).same


def test_a_number_spelled_out_is_missing():
    result = voicecheck.compare(DRAFT, DRAFT.replace("10 minutes", "ten minutes"))
    assert voicecheck.describe(result) == ["missing: 10 (number), before line 1"]


def test_an_id_the_draft_did_not_have_is_added():
    result = voicecheck.compare(DRAFT, DRAFT.replace("through `get`.", "through `get` and CON-001."))
    assert voicecheck.describe(result) == ["added: CON-001 (id), after line 1"]


def test_moving_a_token_fails_even_when_none_is_lost():
    after = ("It calls CON-003 on 2026-11-20. Booking holds a seat for 10 minutes ([[CAP-014-hold-a-seat|CAP-014]]), "
             "60% of the time, through `get`.\n\n| Contract | Calls |\n|---|---|\n| CON-003 | 2 |\n")
    result = voicecheck.compare(DRAFT, after)
    assert not result.missing and not result.added
    assert voicecheck.describe(result) == ["moved: 10 (number) at before line 1 now has CON-003 (id) in its place, after line 1"]


def test_a_changed_table_cell_is_missing_and_added():
    result = voicecheck.compare(DRAFT, DRAFT.replace("| CON-003 | 2 |", "| CON-003 | 3 |"))
    assert voicecheck.describe(result) == ["missing: 2 (cell), before line 5", "added: 3 (cell), after line 5"]


def test_tokens_come_in_document_order_by_kind():
    assert kinds(DRAFT.split("\n")[0]) == [("number", "10"), ("link", "[[CAP-014-hold-a-seat|CAP-014]]"),
                                           ("id", "CON-003"), ("date", "2026-11-20"), ("number", "60%"), ("code", "`get`")]


def test_ids_are_not_numbers_and_a_link_or_code_span_is_one_token():
    assert kinds("G12, CAP-001.FR2, APP-call-centre, concern-testing, SRC-01, R-01, 1,200 seats, v2") == [
        ("id", "G12"), ("id", "CAP-001.FR2"), ("id", "APP-call-centre"), ("id", "concern-testing"),
        ("id", "SRC-01"), ("id", "R-01"), ("number", "1,200")]
    assert kinds("[[booking-building-blocks#CON-001 Booking API|CON-001]] and `CON-002`") == [
        ("link", "[[booking-building-blocks#CON-001 Booking API|CON-001]]"), ("code", "`CON-002`")]


def test_crlf_line_endings_change_nothing():
    assert voicecheck.compare(DRAFT, DRAFT.replace("\n", "\r\n")).same


# Through the CLI.

def test_two_files(tmp_path):
    before, after = tmp_path / "before.md", tmp_path / "after.md"
    before.write_text(DRAFT, encoding="utf-8")
    after.write_text(DRAFT.replace("It calls", "Booking calls"), encoding="utf-8")
    assert run("voicecheck", str(before), str(after)) == (0, "planner voicecheck: 1 files compared, 0 with protected tokens changed.\n")
    after.write_text(DRAFT.replace("2026-11-20", "20 November"), encoding="utf-8")
    code, out = run("voicecheck", str(before), str(after))
    assert code == 1
    assert out.splitlines() == ["planner voicecheck: 1 files compared, 1 with protected tokens changed.",
                                f"{after}: missing: 2026-11-20 (date), before line 1", f"{after}: added: 20 (number), after line 1"]


GIT = ["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid"]


@pytest.fixture
def repo(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    subprocess.run(GIT + ["init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "page.md").write_text(DRAFT, encoding="utf-8")
    (tmp_path / "other.md").write_text("Nothing protected here.\n", encoding="utf-8")
    subprocess.run(GIT + ["add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(GIT + ["commit", "-qm", "draft: prose for s"], cwd=tmp_path, check=True)
    return tmp_path


def test_range_against_the_working_tree(repo):
    (repo / "page.md").write_text(DRAFT.replace("It calls", "Booking calls"), encoding="utf-8")
    assert run("voicecheck", "--range", "HEAD", "--vault", str(repo))[0] == 0
    (repo / "page.md").write_text(DRAFT.replace("10 minutes", "ten minutes"), encoding="utf-8")
    code, out = run("voicecheck", "--range", "HEAD", "--vault", str(repo))
    assert code == 1
    assert out.splitlines() == ["planner voicecheck: 1 files compared, 1 with protected tokens changed.",
                                "page.md: missing: 10 (number), before line 1"]


def test_range_between_two_commits(repo):
    (repo / "page.md").write_text(DRAFT.replace("CON-003 on", "CON-004 on"), encoding="utf-8")
    subprocess.run(GIT + ["commit", "-qam", "draft: voice rewrite for s"], cwd=repo, check=True)
    code, out = run("voicecheck", "--range", "HEAD~1..HEAD", "--vault", str(repo))
    assert code == 1
    assert "page.md: missing: CON-003 (id), before line 1" in out and "page.md: added: CON-004 (id), after line 1" in out


def test_tool_failures_exit_2(repo, tmp_path):
    assert run("voicecheck")[0] == 2
    assert run("voicecheck", str(repo / "page.md"))[0] == 2
    assert run("voicecheck", str(repo / "page.md"), str(repo / "page.md"), "--range", "HEAD")[0] == 2
    assert run("voicecheck", str(repo / "nowhere.md"), str(repo / "page.md"))[0] == 2
    code, out = run("voicecheck", "--range", "no-such-ref", "--vault", str(repo))
    assert code == 2 and "no-such-ref" in out
    assert run("voicecheck", "--range", "..HEAD", "--vault", str(repo))[0] == 2
