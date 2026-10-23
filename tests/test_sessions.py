"""The pure halves of `vela session start` and `vela record add` (overhaul Task 6b): no git, no gh, no clock.

Each rule here was a sentence in START.md or ANSWER-A-CHALLENGE.md a model followed by hand; the tests pin the rule's
reason in their names."""
import pytest

from vela import privaterecord, records, sessions


def text(record_id, status, modes):
    return (f"---\nid: {record_id}\ntype: session\ndate: {record_id[:10]}\nmodes: [{', '.join(modes)}]\n"
            f"status: {status}\nsummary: s.\n---\n\n# {record_id}\n\n## Captures\n")


def test_two_records_on_one_branch_finds_the_open_one():
    """An answer session shares its challenge's branch: the closed challenge record is not the open session."""
    branch = "refs/heads/session/2026-10-10-challenge-con-001"
    found = [(branch, "sessions/2026-10-10-challenge-con-001.md",
              text("2026-10-10-challenge-con-001", "closed", ["challenge"])),
             (branch, "sessions/2026-10-12-answer-con-001.md", text("2026-10-12-answer-con-001", "open", ["answer"]))]
    open_records, problems = sessions.find_open(found)
    assert problems == []
    assert [(r.id, r.branch) for r in open_records] == [
        ("2026-10-12-answer-con-001", "session/2026-10-10-challenge-con-001")]


def test_answer_pr_title_must_end_with_exact_id():
    """gh's search matches `CON-0010` for `CON-001`; only the exact title suffix counts."""
    prs = [{"number": 7, "headRefName": "session/2026-10-10-challenge-con-0010", "title": "2026-10-10 Challenge: CON-0010"},
           {"number": 8, "headRefName": "session/2026-10-11-challenge-con-001", "title": "2026-10-11 Challenge: CON-001"},
           {"number": 9, "headRefName": "session/x", "title": "2026-10-11 Challenge: XCON-001"}]
    assert [p["number"] for p in sessions.challenge_matches(prs, "CON-001")] == [8]
    assert [p["number"] for p in sessions.challenge_matches(prs, "CON-0010")] == [7]
    assert sessions.challenge_matches(prs, "CON-002") == []


def test_a_pr_number_must_be_an_open_challenge():
    good = {"number": 8, "headRefName": "session/b", "title": "2026-10-11 Challenge: CON-001", "state": "OPEN"}
    assert sessions.challenged_id(good) == "CON-001"
    assert sessions.challenged_id({**good, "state": "MERGED"}) is None
    assert sessions.challenged_id({**good, "title": "Open session 2026-10-11"}) is None
    assert sessions.challenged_id({**good, "title": "Challenge: CON-001"}) is None  # no date: not one challenge wrote


def test_new_id_takes_the_next_free_suffix():
    taken = {"2026-10-14-desk-agent-calendar", "2026-10-14-desk-agent-calendar-2"}
    assert sessions.new_id("2026-10-14", "Desk agent: calendar!", taken.__contains__) == \
        "2026-10-14-desk-agent-calendar-3"
    assert sessions.answer_id("2026-10-14", "CON-001", set().__contains__) == "2026-10-14-answer-con-001"
    with pytest.raises(ValueError):
        sessions.new_id("2026-10-14", "!!!", set().__contains__)


def test_only_a_dirty_path_the_pull_changes_is_clobbered():
    """A change the pull doesn't touch is carried into the session; one it would overwrite needs the lead."""
    dirty = ["01-goals.md", ".vela/handle", "sessions/x.md"]
    incoming = ["01-goals.md", "02-constraints.md"]
    assert sessions.clobbered(dirty, incoming) == ["01-goals.md"]
    assert sessions.carried(dirty, incoming) == ["sessions/x.md"]  # vela's own .vela/ output is never mentioned


def test_title_line_is_replaced_and_the_rest_kept():
    yaml_text = "initiative: INI-900\ntitle: New initiative\n# a comment\n"
    assert sessions.with_title(yaml_text, "Heron desk") == 'initiative: INI-900\ntitle: "Heron desk"\n# a comment\n'
    assert sessions.with_title("initiative: INI-900\n", "Heron") == 'initiative: INI-900\ntitle: "Heron"\n'
    assert sessions.is_unnamed({"title": "New initiative"}) and not sessions.is_unnamed({"title": "Heron"})


def test_a_new_stub_reads_as_an_open_session_and_the_notes_hold_the_sections():
    stub = privaterecord.new_stub("2026-10-14-x", "Grill: x", "2026-10-14", ["grill"])
    record, why = sessions.read("", "sessions/2026-10-14-x.md", stub)
    assert why is None and (record.status, record.modes, record.title) == ("open", ("grill",), "Grill: x")
    body = privaterecord.new_private("2026-10-14-x", "Grill: x", "2026-10-14", 1)
    assert "## Captures\n" in body and "| ID | From | To | Source |" in body


def test_with_branch_puts_the_line_after_status():
    stub = privaterecord.new_stub("2026-10-14-x", "Grill: x", "2026-10-14", ["grill"])
    assert "status: open\nbranch: main\n" in sessions.with_branch(stub, "main")
    again = sessions.with_branch(sessions.with_branch(stub, "main"), "other")
    assert again.count("branch:") == 1 and "branch: other\n" in again


def test_capture_number_counts_every_number_ever_seen():
    body = "## Captures\n\n- [idea] (claude) a ^c01\n\n## Changes\n\n| CON-1 | a | b | [[x#^c07]] |\n"
    assert records.numbers_in(body) == {1, 7}
    assert records.next_number(records.numbers_in(body), {9}) == 10
    assert records.next_number(set()) == 1


def test_capture_line_and_its_place():
    line = records.capture_line("idea", "@priya", '"A shared calendar."', 3)
    assert line == '- [idea] (@priya) "A shared calendar." ^c03'
    body = "# x\n\n## Captures\n\n- [idea] (claude) a ^c01\n\n## Changes\n\n| ID |\n"
    assert records.append(body, line) == ("# x\n\n## Captures\n\n- [idea] (claude) a ^c01\n" + line +
                                          "\n\n## Changes\n\n| ID |\n")
    empty = "# x\n\n## Captures\n\n## Changes\n"
    assert records.append(empty, line) == "# x\n\n## Captures\n\n" + line + "\n\n## Changes\n"


def test_capture_line_refuses_what_would_not_parse():
    for tag, origin, words in (("Idea!", "claude", "x"), ("idea", "a (b)", "x"), ("idea", "", "x"),
                               ("idea", "claude", "two\nlines"), ("idea", "claude", "ends ^c04"), ("idea", "claude", "")):
        with pytest.raises(records.CaptureRefused):
            records.capture_line(tag, origin, words, 1)
    with pytest.raises(records.CaptureRefused):
        records.append("# x\n", "- [idea] (claude) a ^c01")
