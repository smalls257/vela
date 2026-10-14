"""The explorer for people with and without git: the role the page is built for, a reader's draft against the
baseline they opened, decisions pending an owner's approval, and the freshness stamp. The page draws all of it
(see the #selftest in test_explorer_browser.py); these check the data the build hands it."""
import json
import re
import shutil

import pytest
from conftest import run
from sharing import HOSTILE, SNAPSHOT, advance_remote, draft_workspace, git, make_vault, with_remote

from vela import attention, cli, drafts

DATA = re.compile(r'<script type="application/json" id="data">(.*?)</script>', re.S)
PAGE = "dashboard.html"


def page_data(root):
    text = (root / PAGE).read_text(encoding="utf-8")
    return json.loads(DATA.search(text).group(1)), text


def explore(root, *extra):
    code, said = run("explore", str(root), "--today", "2026-10-12", *extra)
    assert code == 0, said
    return said


@pytest.fixture
def reader(tmp_path):
    src, published, workspace = draft_workspace(tmp_path)
    explore(workspace)
    return src, published, workspace


def test_a_reader_page_carries_the_role_and_the_draft_against_the_baseline(reader):
    data, _ = page_data(reader[2])
    draft = data["draft"]
    assert data["role"] == "reader" and draft["problem"] == "" and draft["count"] == 2
    by_path = {p["path"]: p for p in draft["pages"]}
    changed = by_path["05-building-blocks/coach-building-blocks.md"]
    assert changed["status"] == "changed" and changed["key"] == "APP-coach" and changed["title"] == "Coach"
    assert (changed["added"], changed["removed"]) == (2, 1) and ["add", "- **Pending approval:** @sam, 2026-10-12"] in changed["lines"]
    added = by_path["reader-notes.md"]
    assert added["status"] == "added" and added["removed"] == 0 and added["added"] == 3 and added["key"] == "page:reader-notes"
    assert not any(p["path"].startswith(".planner/") for p in draft["pages"])


def test_a_removed_page_and_a_binary_file_are_listed_without_a_diff(reader):
    _, _, workspace = reader
    (workspace / "01-goals.md").unlink()
    (workspace / "sources").mkdir(exist_ok=True)
    (workspace / "sources" / "contract.pdf").write_bytes(b"%PDF\x00\x01binary")
    explore(workspace)
    pages = {p["path"]: p for p in page_data(workspace)[0]["draft"]["pages"]}
    assert pages["01-goals.md"]["status"] == "removed" and pages["01-goals.md"]["removed"] > 0 and pages["01-goals.md"]["key"] == ""
    assert pages["sources/contract.pdf"]["binary"] is True and pages["sources/contract.pdf"]["lines"] == []


def test_markup_in_a_changed_line_cannot_close_the_script_or_become_an_element(reader):
    _, text = page_data(reader[2])
    assert HOSTILE not in text and "</script><img" not in text
    data, _ = page_data(reader[2])
    lines = [row[1] for p in data["draft"]["pages"] for row in p["lines"]]
    assert any("</script><img src=x onerror=alert(1)>" in line for line in lines)  # the text survives as data, to be drawn as text


def test_a_pending_decision_is_lit_pending_ranked_between_held_and_never_examined(reader):
    data, _ = page_data(reader[2])
    assert data["pending"] == [{"key": "CON-001", "subject": "CON-001", "by": "@sam", "date": "2026-10-12",
                                "path": "05-building-blocks/coach-building-blocks.md"}]
    assert data["entities"]["CON-001"]["pending"] == {"by": "@sam", "date": "2026-10-12"}
    assert data["lights"]["CON-001"]["level"] == "pending" and data["lights"]["CON-001"]["reasons"][0]["kind"] == "pending"
    assert data["levels"] == list(attention.LEVELS) and data["levels"][:3] == ["warning", "caution", "pending"]
    assert data["ranked"].index("CON-001") > data["ranked"].index("CON-002")  # a held contract outranks it


def test_a_reader_page_stamps_freshness_as_of_the_build_and_names_a_newer_copy(reader):
    src, published, workspace = reader
    data, _ = page_data(workspace)
    assert data["freshness"]["role"] == "reader" and data["freshness"]["state"] == "current"
    git(src, "commit", "-q", "--allow-empty", "-m", "second")
    shutil.rmtree(published)
    assert run("publish", "--vault", str(src), "--out", str(published), "--today", "2026-10-20")[0] == 0
    explore(workspace)
    fresh = page_data(workspace)[0]["freshness"]
    assert fresh["state"] == "newer" and fresh["latest"]["date"] == "2026-10-20" and "your drafts are kept" in fresh["message"].lower()


def test_an_owner_page_has_no_draft_and_stamps_commits_behind_and_uncommitted(tmp_path):
    root = make_vault(tmp_path)
    bare = with_remote(tmp_path, root)
    advance_remote(tmp_path, bare)
    (root / "scratch.md").write_text("# Scratch\n", encoding="utf-8")
    explore(root)
    data, _ = page_data(root)
    assert data["role"] == "owner" and data["draft"] is None and data["pending"] == []
    fresh = data["freshness"]
    assert fresh["role"] == "owner" and fresh["behind"] == 1 and fresh["uncommitted"] >= 1 and fresh["state"] == "newer"


def test_a_folder_that_is_neither_gets_no_role_no_draft_and_no_stamp(tmp_path):
    root = tmp_path / "vault"
    shutil.copytree(SNAPSHOT, root)
    explore(root)
    data, _ = page_data(root)
    assert (data["role"], data["draft"], data["freshness"]) == ("none", None, None)


def test_a_reader_workspace_with_no_baseline_says_why_instead_of_showing_no_changes(reader):
    _, _, workspace = reader
    shutil.rmtree(workspace / ".planner" / "baseline")
    said = explore(workspace)
    draft = page_data(workspace)[0]["draft"]
    assert draft["count"] == 0 and "baseline" in draft["problem"] and "cannot compare" in said


def test_the_helpers_freshness_answer_is_the_same_report_planner_freshness_prints(reader):
    _, _, workspace = reader
    found = cli.detect_role(workspace)
    live = cli.live_freshness(workspace, found, "2026-10-12", RuntimeError)
    code, text = run("freshness", "--vault", str(workspace), "--json", "--today", "2026-10-12")
    printed = json.loads(text)
    assert code == 0 and {k: v for k, v in live.items() if k != "checked_at"} == {k: v for k, v in printed.items() if k != "checked_at"}


# drafts.compare, the pure part
def test_compare_reports_added_removed_and_changed_by_path():
    found = drafts.compare({"a.md": b"one\ntwo\n", "b.md": b"gone\n", "c.md": b"same\n"}, {"a.md": b"one\n2\n", "c.md": b"same\n", "d.md": b"new\n"})
    assert [(c["path"], c["status"]) for c in found] == [("a.md", "changed"), ("b.md", "removed"), ("d.md", "added")]
    assert found[0]["lines"][-2:] == [["del", "two"], ["add", "2"]]


def test_a_generated_block_that_only_re_rendered_is_not_a_change_and_one_with_an_edit_beside_it_collapses():
    block = "<!-- generated:trace sha={sha}: do not edit, run planner render -->\n{body}\n<!-- /generated:trace -->\n"
    old = ("Intro\n" + block.format(sha="aaaaaaaa", body="row 1")).encode()
    churn = ("Intro\n" + block.format(sha="bbbbbbbb", body="row 1\nrow 2")).encode()
    assert drafts.compare({"p.md": old}, {"p.md": churn}) == []
    edited = ("Intro, edited\n" + block.format(sha="bbbbbbbb", body="row 1\nrow 2")).encode()
    (change,) = drafts.compare({"p.md": old}, {"p.md": edited})
    texts = [t for _, t in change["lines"]]
    assert "Intro, edited" in texts and not any("row" in t for t in texts)


def test_only_a_line_ending_change_still_shows_as_a_change_and_says_so():
    (change,) = drafts.compare({"p.md": b"a\nb\n"}, {"p.md": b"a\r\nb\r\n"})
    assert change["lines"] == [["hunk", "only line endings or the final newline differ"]]


def test_a_nul_byte_or_invalid_utf8_is_binary_and_a_long_diff_is_cut():
    assert drafts.compare({}, {"x.bin": b"a\x00b"})[0]["binary"] and drafts.compare({}, {"y.md": b"\xff\xfe"})[0]["binary"]
    (long,) = drafts.compare({}, {"z.md": ("line\n" * (drafts.MAX_DIFF_LINES + 50)).encode()})
    assert long["truncated"] and len(long["lines"]) == drafts.MAX_DIFF_LINES


def test_explore_serve_hands_the_helper_a_live_freshness_check(reader, monkeypatch):
    from vela.explorer import serve
    seen = {}
    monkeypatch.setattr(serve, "serve", lambda *a, **kw: seen.update(kw))
    explore(reader[2], "--serve", "--no-open")
    report = seen["freshness"]()
    assert report["role"] == "reader" and report["state"] == "current" and report["have"]["commit"]
