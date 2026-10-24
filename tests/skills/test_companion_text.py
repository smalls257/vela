"""What the companion skill says, pinned in one place (plan Task 12)."""
import re
import shlex

from conftest import REPO

SKILL = REPO / "plugin" / "skills" / "companion" / "SKILL.md"


def text():
    return SKILL.read_text(encoding="utf-8")


def test_the_session_panel_rides_on_the_write():
    skill = text()
    assert "companion session --html" in skill and "same Bash command" in skill and "same message" in skill
    assert "Never publish in a message of its own" in skill


def test_the_answer_leads_with_vela_s_headline():
    skill = text()
    assert "headline" in skill and "word for word" in skill and "not_recorded" in skill
    assert "Say no number the panel doesn't show." in skill


def test_every_view_is_named_and_none_is_the_way_out():
    skill = text()
    for view in ("track", "stuck", "needs", "left", "who", "flow", "page"):
        assert f"--view {view}" in skill or f"{view} (" in skill, view
    assert "--view none" in skill and "/vela:ask" in skill


def test_claude_never_writes_the_panel():
    assert "exactly as written" in text() and "Never write or edit its HTML" in text()


def test_show_me_where_we_are_is_the_only_turn_of_its_own():
    assert "Show me where we are" in text() and "because they asked" in text()


def test_no_artifact_is_said_once():
    assert "I can't show the panel here." in text() and "never claim the panel updated" in text()


def test_the_description_has_no_tag():
    front = text().split("---", 2)[1]
    assert not re.search(r"<[^<>\n]*>", front)


def test_it_names_only_commands_that_exist():
    from vela import cli
    parser = cli.build_parser()
    calls = re.findall(r"scripts/run-vela (companion [^`;>]*)", text())
    assert calls
    for call in calls:
        _, extras = parser.parse_known_args(shlex.split(re.sub(r"<[^>]*>", "X", call)))
        assert not extras, (call, extras)
