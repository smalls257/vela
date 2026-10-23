"""The pull request lists receipts and what changed, never what anyone said (private sessions, Task 11).

The Violation the new body exists to prevent is a Leaky Narrative of the record: the old Consent list pasted every
capture's words into a place the whole team reads. The body now carries the receipts as the pages hold them, the
state moves with a citation, the day the lead said yes to sending, and only the lines the lead picked at the
read-back. `vela records show` is the lead's own way to paste one of their own lines when a reviewer asks."""
import json

from conftest import run
from test_close_pr import created, fake_gh, pr, pushed
from test_close_push import RECORD, YES_WORDS, add_yes
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


def test_the_body_carries_receipts_and_no_capture_text(tmp_path, monkeypatch):
    _, body = body_of(tmp_path, monkeypatch)
    assert "**Decisions**" in body and "Sent with your yes on October 20, 2026." in body
    assert f"- Stock level: [[{RECORD}]]" in body
    assert f"- Stock level: fact to decided, [[{RECORD}]] c01" in body
    assert "Consent" not in body and YES_WORDS not in body and "Yes, send it." not in body
    assert body.index("**Decisions**") < body.index("**What changed**") < body.index("Sent with your yes")


def test_in_their_words_holds_only_the_picked_quotes(tmp_path, monkeypatch):
    _, body = body_of(tmp_path, monkeypatch, picked=[{"number": 1, "words": YES_WORDS, "item": "CON-002"}])
    assert "**In their words**" in body
    assert f'- Stock level: "{YES_WORDS}"' in body
    assert body.index("Sent with your yes") < body.index("**In their words**")
    (tmp_path / "again").mkdir()
    _, none = body_of(tmp_path / "again", monkeypatch)
    assert "In their words" not in none


def test_a_pending_part_is_said():
    meta = {"captures_sha256": {1: privaterecord.PENDING, 2: "ab" * 32}}
    assert prbody.fingerprint_notes(meta, 2) == ["Part 1's notes are on the other machine and aren't fingerprinted yet."]
    assert prbody.fingerprint_notes({"captures_sha256": {1: "ab" * 32}}, 1) == []
    facts = prbody.Facts(summary="s", decisions=[], push_line="Sent.", fingerprint_note=["Part 1's notes are on the "
                                                                                         "other machine and aren't fingerprinted yet."])
    body = prbody.body(facts)
    assert body.index("Sent.") < body.index("Part 1's notes")


def test_push_words_says_the_day():
    assert prbody.push_words("2026-10-14") == "Sent with your yes on October 14, 2026."


def test_the_pending_wording_is_one_constant():
    assert prbody.FINGERPRINT_PENDING.format(n=3) == "Part 3's notes are on the other machine and aren't fingerprinted yet."


def test_kept_and_not_read_back_name_items_only(tmp_path):
    from vela import cli
    vault, _ = pushed(tmp_path)
    loaded = cli.load_vault(vault)
    text = ('- [thought] (claude) "A hunch about stock." → keep: [[stock-building-blocks#CON-002 Stock level|CON-002]]'
            " (decided) ^c01\n")
    assert prbody.kept_on_claude(text, loaded) == ["- Stock level"]
    assert prbody.not_read_back(["CON-002"], loaded, set()) == [
        "- Stock level: its owner hasn't heard the wording read back."]


def test_show_pastes_only_the_leads_words(tmp_path):
    from test_close_push import sent_session
    vault, _ = sent_session(tmp_path)
    other = add_yes(vault, words=OTHER_WORDS, origin="@cto-ana")
    before = tree_bytes(vault)
    assert run("records", "show", RECORD, "c01", "--vault", str(vault)) == (0, f'"{YES_WORDS}"\n')
    code, out = run("records", "show", RECORD, other.lstrip("^"), "--vault", str(vault))
    assert code == 1 and "Those are someone else's words" in out and OTHER_WORDS not in out
    code, out = run("records", "show", RECORD, "2.c01", "--vault", str(vault))
    assert code == 1 and "That note is on the other machine." in out
    assert tree_bytes(vault) == before
