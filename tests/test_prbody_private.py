"""The pull request says what changed, never what anyone said (private sessions, Task 11).

The Violation the body exists to prevent is a Leaky Narrative of the record: the old Consent list pasted every
capture's words into a place the whole team reads. The body now carries no receipt, record link, capture number or
quote, even one the lead picked at the read-back. `vela records show` is the lead's own way to paste one of their own
lines when a reviewer asks."""
import json

from conftest import run
from sharing import git
from test_close_pr import created, fake_gh, pr, pushed
from test_close_push import RECORD, YES_WORDS, add_yes, push, sent_session
from vela import prbody, privaterecord

OTHER_WORDS = "We have to keep the old API until March."


def body_of(tmp_path, monkeypatch, picked=None):
    log = fake_gh(tmp_path, monkeypatch)
    vault, _ = pushed(tmp_path)
    if picked is not None:
        folder = vault / ".vela" / "close"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{RECORD}.quotes.json").write_text(json.dumps({"quotes": picked}), encoding="utf-8")
    assert pr(vault)[0] == 0
    return vault, created(log)[0]["body"]


def tree_bytes(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def test_the_body_has_no_session_words_record_link_or_capture_number(tmp_path, monkeypatch):
    _, body = body_of(tmp_path, monkeypatch, picked=[{"number": 1, "words": YES_WORDS, "item": "CON-002"}])
    assert "- Stock level: now decided" in body
    assert YES_WORDS not in body and "Yes, send it." not in body and "In their words" not in body
    assert "[[" not in body and " c01" not in body and RECORD not in body


def test_a_receipt_with_the_leads_words_on_the_page_stays_off_the_body(tmp_path, monkeypatch):
    log = fake_gh(tmp_path, monkeypatch)
    vault, _ = sent_session(tmp_path)
    page = vault / "05-building-blocks" / "stock-building-blocks.md"
    page.write_text(page.read_text(encoding="utf-8").replace(
        f"- **Decision:** [[{RECORD}]]\n", f'- **Decision:** [[{RECORD}]] c01, @lead: "{YES_WORDS}"\n', 1), encoding="utf-8")
    git(vault, "add", "05-building-blocks/stock-building-blocks.md")
    git(vault, "commit", "-q", "-m", "Word the receipt")
    assert run("close", "readback", "--done", "--vault", str(vault))[0] == 0
    assert push(vault)[0] == 0
    assert pr(vault)[0] == 0
    body = created(log)[0]["body"]
    assert "Yes, send it." not in body and YES_WORDS not in body


def test_show_pastes_only_the_leads_words(tmp_path):
    from test_close_push import sent_session
    vault, _ = sent_session(tmp_path)
    other = add_yes(vault, words=OTHER_WORDS, origin="@cto-ana")
    before = tree_bytes(vault)
    assert run("records", "show", RECORD, "c02", "--vault", str(vault)) == (0, f'"{YES_WORDS}"\n')
    code, out = run("records", "show", RECORD, other.lstrip("^"), "--vault", str(vault))
    assert code == 1 and "Those are someone else's words" in out and OTHER_WORDS not in out
    code, out = run("records", "show", RECORD, "2.c01", "--vault", str(vault))
    assert code == 1 and "That note is on the other machine." in out
    assert tree_bytes(vault) == before


def test_show_says_plainly_when_the_notes_cannot_be_read(tmp_path):
    from test_close_push import sent_session
    vault, _ = sent_session(tmp_path)
    (vault / privaterecord.private_path(RECORD)).write_bytes(b"\xff\xfe\x00bad")
    code, out = run("records", "show", RECORD, "c01", "--vault", str(vault))
    assert code == 2 and "Traceback" not in out
