"""Answering a challenge: START opens an answer session on the challenge's own branch, a Grill
(or the lead setting the item back) works there, and close pushes to that branch and comments
on the open challenge PR instead of opening a new one."""
from conftest import REPO, check, edit, findings, skill_text
from vela import schema

PLUGIN = REPO / "plugin"
SESSION = "sessions/2026-01-10-shop-api.md"


def read(*parts):
    return REPO.joinpath(*parts).read_text(encoding="utf-8")


def section(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0]


def test_answer_is_a_session_mode_the_check_knows(mini):
    assert "answer" in schema.SESSION_MODES
    assert "| Answer (`answer`)" in read("plugin", "references", "MODES.md")
    assert "| `answer` |" in read("plugin", "references", "MODES.md")
    assert "Epics, Challenge or Answer." in read("plugin", "references", "START.md")
    assert "`challenge`, `answer`." in read("template", "CONVENTIONS.md")
    edit(mini / SESSION, "modes: [grill]", "modes: [answer, grill]")
    assert findings(check(mini)[1]) == []


def test_an_answer_session_without_a_grill_cannot_decide(mini):
    edit(mini / SESSION, "modes: [grill]", "modes: [answer]")
    assert "E303" in {code for code, _ in findings(check(mini)[1])}


def test_start_answers_a_challenge_on_its_own_branch():
    start = read("plugin", "references", "START.md")
    answer = section(start, "## Answer a challenge", "## Captures during the session") + read("plugin", "references", "ANSWER-A-CHALLENGE.md")
    assert "ANSWER-A-CHALLENGE.md" in section(start, "## Answer a challenge", "## Closing a session")  # START points; the steps load only when needed
    assert 'gh pr list --search "Challenge: <ID>" --state open --json number,headRefName,title' in answer
    assert "title ends with exactly `Challenge: <ID>`" in answer
    assert "instead of `git switch main`" in answer
    assert "git switch <headRefName>" in answer and "git pull --ff-only" in answer
    assert "`<date>-answer-<id-lowercased>`" in answer
    assert "modes: [answer]" in answer and "Answer: <ID>" in answer
    assert "Do not run `git switch -c`" in answer
    assert "If none is open, or more than one, stop" in answer


def test_start_and_close_find_an_answer_record_on_a_shared_branch():
    command = "git grep -l '^status: open' <branch> -- sessions/"
    assert command in read("plugin", "references", "START.md")
    # close finds it through `vela session open`, which reads every record on a shared branch
    # (tests/test_session_open.py::test_two_records_on_one_branch_finds_the_open_one)
    assert "vela session open --switch" in section(skill_text("close"), "## 1.", "## 2.")


def test_grill_and_challenge_send_the_lead_to_the_answer_path():
    grill = read("plugin", "skills", "grill", "SKILL.md")
    assert "take its \"Answer a challenge\" path" in section(grill, "## 1.", "## 2.")
    challenge = read("plugin", "skills", "challenge", "SKILL.md")
    assert "Run `/vela:grill` and name this PR or <ID>" in challenge
    assert "opens an answer session on this branch" in challenge


def test_close_pushes_an_answer_to_the_challenge_branch_and_comments_on_its_pr():
    close = skill_text("close")
    assert "git push origin <branch>" in section(close, "## 7.", "## 8.")
    pr = section(close, "## 8.", "\n## 9") if "\n## 9" in close else close.split("## 8.", 1)[1]
    assert "do not open a new PR" in pr
    assert "gh pr comment <number> --body-file <file>" in pr
    assert "E316 for <ID> should now be gone" in pr


def test_every_text_accepts_reopened_to_decided_for_an_epic():
    row = "| EPC-nnn | reopened | decided |"
    for text in (read("plugin", "skills", "epics", "SKILL.md"), read("plugin", "skills", "grill", "SKILL.md"),
                 read("template", "CONVENTIONS.md"), read("plugin", "skills", "challenge", "SKILL.md")):
        assert row in text
    assert "GATE-2 reads `draft` or `reopened`" in read("plugin", "skills", "epics", "SKILL.md")
    assert "An epic is at `draft` or `reopened`" in read("plugin", "skills", "grill", "SKILL.md")
    assert "A Grill decides a `reopened` epic as it decides a `draft` one" in read("template", "CONVENTIONS.md")
