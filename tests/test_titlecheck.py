"""The session-name check: a title that names a person is refused at start, before anything is written. Team
handles are not people. The people come from the plan's own owners, grill owners and joins, the lead, and the
origins in this machine's private files."""
import json

from conftest import MINI
from vela import cli, titlecheck
from test_session_cli import owner, start, head


def mini_people(*, names=(), origins=(), handle="maria"):
    return titlecheck.people(cli.load_vault(MINI), handle, set(names), set(origins))


def test_title_check_skips_team_handles_and_catches_people():
    people = mini_people(names={"maria lopez"})
    assert "till-team" not in people and "stock-team" in people  # @mini/till-team is a team; @stock-team is a handle
    assert titlecheck.named("Till options", people) == []
    assert titlecheck.named("Stock team", people) == []  # a part of @stock-team is an ordinary word
    assert titlecheck.named("Lopez follow-up", people) == ["lopez"]  # a word of a display name
    assert titlecheck.named("Maria", people) == ["maria"]  # the lead's own handle


def test_a_hyphen_part_of_a_handle_is_an_ordinary_word_unless_it_is_a_handle_itself():
    people = {"agent-lead", "stock-team", "jo", "al"}
    assert titlecheck.named("Desk agent calendar", people) == []
    assert titlecheck.named("Stock level", people) == []
    assert titlecheck.named("Jo follow-up", people) == ["jo"]
    assert titlecheck.named("Al and the bank", people) == ["al"]  # a whole handle, however short


def test_origins_in_a_private_file_are_people_unless_they_are_roles_or_claude():
    text = ("- [said] (Priya Nair) words ^c1\n- [said] (client) words ^c2\n- [idea] (claude) words ^c3\n"
            "- [said] (claude, from Raj Rao) words ^c4\n- [said] (@dee) words ^c5\n")
    assert titlecheck.origins_in(text) == {"Priya Nair", "Raj Rao", "@dee"}


def test_start_refuses_a_title_that_names_a_person(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)  # git's user.name here is Priya Nair
    before = head(vault)
    code, out = start(vault, "--mode", "grill", "--topic", "Priya pushback", "--json")
    assert code == 3, out
    assert json.loads(out)["needs_lead"][0]["question"] == titlecheck.TITLE_QUESTION
    assert not list((vault / "sessions" / "private").glob("*priya*")) and head(vault) == before
    assert not list((vault / "sessions").glob("*priya*"))
    assert start(vault, "--mode", "grill", "--topic", "Pushback on options")[0] == 0


def test_a_person_a_private_file_quotes_cannot_be_the_title(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    private = vault / "sessions" / "private"
    private.mkdir(parents=True, exist_ok=True)
    (private / "2026-10-01-older.md").write_text("- [said] (Dana Okafor) words ^c1\n", encoding="utf-8")
    code, out = start(vault, "--mode", "grill", "--topic", "Okafor concerns", "--for-lead")
    assert code == 3 and titlecheck.TITLE_QUESTION in out and "I matched on okafor" in out


def test_the_same_name_said_twice_is_the_leads_override_and_is_recorded(tmp_path, monkeypatch):
    """The lead may override any rule: the second ask goes ahead, the stub says so, and the first refusal says how."""
    vault = owner(tmp_path, monkeypatch)
    code, out = start(vault, "--mode", "grill", "--topic", "Priya pushback", "--for-lead")
    assert code == 3 and "say the same name again" in out.lower()
    assert not list((vault / "sessions").glob("*priya*"))
    code, out = start(vault, "--mode", "grill", "--topic", "priya pushback", "--json")
    assert code == 0, out
    stub = next((vault / "sessions").glob("*priya*.md")).read_text(encoding="utf-8")
    assert "title_override: " in stub


def test_a_different_name_after_a_refusal_is_checked_afresh(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    assert start(vault, "--mode", "grill", "--topic", "Priya pushback")[0] == 3
    assert start(vault, "--mode", "grill", "--topic", "Priya again")[0] == 3
    assert start(vault, "--mode", "grill", "--topic", "Pushback on options")[0] == 0
    stub = next((vault / "sessions").glob("*pushback-on-options*.md")).read_text(encoding="utf-8")
    assert "title_override" not in stub
