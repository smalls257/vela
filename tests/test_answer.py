"""Answering a challenge: START opens an answer session on the challenge's own branch, a Grill
(or the lead setting the item back) works there, and close pushes to that branch and comments
on the open challenge PR instead of opening a new one."""
from conftest import REPO, check, edit, findings
from vela import schema

PLUGIN = REPO / "plugin"
SESSION = "sessions/2026-01-10-shop-api.md"


def read(*parts):
    return REPO.joinpath(*parts).read_text(encoding="utf-8")


def test_answer_is_a_session_mode_the_check_knows(mini):
    assert "answer" in schema.SESSION_MODES
    assert "`challenge`, `answer`." in read("plugin", "template", "CONVENTIONS.md")
    edit(mini / SESSION, "modes: [grill]", "modes: [answer, grill]")
    assert findings(check(mini)[1]) == []


def test_an_answer_session_without_a_grill_cannot_decide(mini):
    edit(mini / SESSION, "modes: [grill]", "modes: [answer]")
    assert "E303" in {code for code, _ in findings(check(mini)[1])}


def test_conventions_accept_reopened_to_decided_for_an_epic():
    assert "| EPC-nnn | reopened | decided |" in read("plugin", "template", "CONVENTIONS.md")
    assert "A Grill decides a `reopened` epic as it decides a `draft` one" in read("plugin", "template", "CONVENTIONS.md")
