"""The --summary line opens the pull request before anyone has read it back, so both skills tell it to quote no one."""
from conftest import REPO

SENTENCE = "it quotes no one: say what was filed, never what anyone said."


def test_close_and_challenge_tell_the_summary_to_quote_no_one():
    for skill in ("close", "challenge"):
        text = (REPO / "plugin" / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert SENTENCE in text, skill
