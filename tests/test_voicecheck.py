"""planner voicecheck: a voice rewrite may change words, never the IDs, numbers, dates,
wikilinks, code spans or table cells they carry."""
import pathlib
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
    assert voicecheck.describe(result) == ["missing: 10 minutes (number), before line 1"]


def test_an_id_the_draft_did_not_have_is_added():
    result = voicecheck.compare(DRAFT, DRAFT.replace("through `get`.", "through `get` and CON-001."))
    assert voicecheck.describe(result) == ["added: CON-001 (id), after line 1"]


def test_moving_a_token_fails_even_when_none_is_lost():
    after = ("It calls CON-003 on 2026-11-20. Booking holds a seat for 10 minutes ([[CAP-014-hold-a-seat|CAP-014]]), "
             "60% of the time, through `get`.\n\n| Contract | Calls |\n|---|---|\n| CON-003 | 2 |\n")
    result = voicecheck.compare(DRAFT, after)
    assert not result.missing and not result.added
    assert voicecheck.describe(result) == ["moved: 10 minutes (number) at before line 1 now has CON-003 (id) in its place, after line 1"]


def test_a_changed_table_cell_is_missing_and_added():
    result = voicecheck.compare(DRAFT, DRAFT.replace("| CON-003 | 2 |", "| CON-003 | 3 |"))
    assert voicecheck.describe(result) == ["missing: 2 (cell), before line 5", "added: 3 (cell), after line 5"]


def test_tokens_come_in_document_order_by_kind():
    assert kinds(DRAFT.split("\n")[0]) == [("number", "10 minutes"), ("link", "[[CAP-014-hold-a-seat|CAP-014]]"),
                                           ("id", "CON-003"), ("date", "2026-11-20"), ("number", "60%"), ("code", "`get`")]


def test_ids_are_not_numbers_and_a_link_or_code_span_is_one_token():
    assert kinds("G12, CAP-001.FR2, APP-call-centre, concern-testing, SRC-01, R-01, 1,200 seats, v2") == [
        ("id", "G12"), ("id", "CAP-001.FR2"), ("id", "APP-call-centre"), ("id", "concern-testing"),
        ("id", "SRC-01"), ("id", "R-01"), ("number", "1,200"), ("version", "v2")]
    assert kinds("[[booking-building-blocks#CON-001 Booking API|CON-001]] and `CON-002`") == [
        ("link", "[[booking-building-blocks#CON-001 Booking API|CON-001]]"), ("code", "`CON-002`")]


def test_crlf_line_endings_change_nothing():
    assert voicecheck.compare(DRAFT, DRAFT.replace("\n", "\r\n")).same


def flagged(before, after):
    return not voicecheck.compare(before, after).same


@pytest.mark.parametrize("before, after", [
    ("# 2026 plan", "# 2027 plan"), ("## 10 minute rule", "## 20 minute rule"), ("Use v2.1 here.", "Use v2.2 here."), ("Use v2 here.", "Use v3 here."), ("Use v2.1 here.", "Use 2.1 here."),
    ("Takes 10 ms.", "Takes 10 s."), ("Hold 10 minutes.", "Hold 10 hours."), ("a 10ms hold", "a 10s hold"),
    ("5xx errors", "4xx errors"), ("the 3rd step", "the 4th step"), ("HTTP2 now", "HTTP3 now"), ("p99 latency", "p95 latency"),
    ("Costs £4 each.", "Costs £5 each."), ("Costs £4 each.", "Costs $4 each."), ("Costs £4 each.", "Costs 4 each."),
    ("Needs 3-5 people.", "Needs 3-6 people."), ("Needs 3-5 people.", "Needs 5 people."), ("-5 degrees", "5 degrees"), ("about ~10 seats", "about 10 seats"),
    ("at 2026-11-20T10:00", "at 2026-11-20T11:00"), ("size 10 MB", "size 10 GB"),
    ("see DEC-004 here", "see DEC-005 here"), ("UNK-001.a1", "UNK-001.a2"), ("CAP-001.FR2", "CAP-001.FR3"),
    ("use ``a`b`` ok", "use ``a`c`` ok"), ("[x](https://a.com/v1)", "[x](https://a.com/v2)"),
    ("see https://a.com/10", "see https://a.com/11"), ("![[img.png]]", "![[img2.png]]"), ("- idea ^c01", "- idea ^c02"),
    ("commit 1f3a9c0e", "commit 2f3a9c0e"),
])
def test_a_changed_fact_is_flagged(before, after):
    assert flagged(before, after)


@pytest.mark.parametrize("before, after", [
    ("- 10 seats\n- CON-001\n", "* 10 seats\n* CON-001\n"), ("## 3. Intro\n", "## Intro\n"), ("## 3.1 Intro\n", "## Intro\n"), ("- a\n- b\n", "1. a\n2. b\n"),
    ("1. a\n2. b\n", "1. a\n1. b\n"), ("## 1. Intro\n", "## Intro\n"), ("## 1.2 Intro 10\n", "### Intro 10\n"),
    ("It is not here.", "It isn't here."), ("It can't hold.", "It cannot hold."), ("A 10 B.\n\nC 2.\n", "A 10 B.\n\nC 2.\n"),
    ("The CON-001 call.", "The call, CON-001."), ("Needs 3-5 people.", "Needs 3-5 people!"),
])
def test_layout_and_wording_changes_pass(before, after):
    assert voicecheck.compare(before, after).same


def test_a_hyphen_range_and_a_datetime_protect_every_number():
    assert kinds("Needs 3-5 people at 2026-11-20T10:00, -5 degrees, 10 ms.") == [
        ("number", "3"), ("number", "5"), ("date", "2026-11-20T10:00"), ("number", "-5"), ("number", "10 ms")]


def test_a_currency_symbol_stays_on_its_number():
    assert kinds("Costs £4 or $5.50 or 6€") == [("number", "£4"), ("number", "$5.50"), ("number", "6")]


def test_list_markers_and_heading_numbers_are_not_tokens():
    assert kinds("1. first\n- second\n## 2. Third\n10) tenth") == []


def test_frontmatter_is_compared_line_by_line():
    page = "---\nid: CON-001\nstate: draft\nowners: [a, b]\n---\nBody.\n"
    result = voicecheck.compare(page, page.replace("state: draft", "state: decided"))
    assert voicecheck.describe(result) == ["missing: state: draft (frontmatter), before line 3",
                                           "added: state: decided (frontmatter), after line 3"]
    assert voicecheck.compare(page, page.replace("Body.", "Prose.")).same


@pytest.mark.parametrize("before, after", [
    ("A is held. We do not release it.", "A is held.\n\nWe do not release it."),
    ("We do not hold.\n\nWe do not release.\n", "We do not hold, and we do not release.\n"),
    ("It is not A.\n\nIt is B.\n", "It is B.\n\nIt is not A.\n"),
])
def test_moving_negations_between_paragraphs_is_not_a_change(before, after):
    assert not voicecheck.compare(before, after).negation


def test_a_dropped_negation_is_flagged_per_file():
    result = voicecheck.compare("It does not hold the seat.\n\nIt waits.\n", "It holds the seat.\n\nIt waits.\n")
    assert voicecheck.describe(result) == [
        "negation: 1 negation words before, 0 after (negation)"]
    assert flagged("A is not held.\n\nB is held.\n\nC is held.\n", "A is held.\n\nB is held.\n\nC is held, not.\n") is False
    assert flagged("A is not held.\n\nB is not held.\n", "A is held.\n\nB is not held.\n")
    assert flagged("We never ship.\n", "We ship, never mind. We cannot stop.\n")
    assert not flagged("It isn't safe, and it won't last.", "It is not safe, and it will not last.")
    assert not flagged("Run `no` now.", "Run `no` today.")


# A negation the reviewer named as redundant (design session 16, 16-D5, route C).

HERON_BEFORE = ("Heron does not read a mailbox, and it writes no morning digest. Nobody keeps the digest in the first release.\n\n"
                "Whether it needs only each person's sign-in is open.\n")
HERON_AFTER = ("Heron does not read a mailbox, and it writes no morning digest.\n\n"
               "Whether it needs only each person's sign-in is open.\n")
NAMED = "Nobody keeps the digest in the first release."


def test_a_removed_negation_fails_until_the_reviewer_names_the_sentence():
    assert voicecheck.describe(voicecheck.compare(HERON_BEFORE, HERON_AFTER)) == [
        "negation: 3 negation words before, 2 after (negation)"]
    assert voicecheck.compare(HERON_BEFORE, HERON_AFTER, [NAMED]).same


def test_naming_a_sentence_excuses_only_its_own_negation():
    worse = HERON_AFTER.replace("does not read", "reads")
    assert voicecheck.describe(voicecheck.compare(HERON_BEFORE, worse, [NAMED])) == [
        "negation: 2 negation words before, 1 after (negation)"]


def test_a_named_sentence_that_carried_a_fact_still_fails():
    before = "It sends nothing. Nobody keeps 12 digests.\n"
    result = voicecheck.compare(before, "It sends nothing.\n", ["Nobody keeps 12 digests."])
    assert voicecheck.describe(result) == ["missing: 12 (number), before line 1"]


def test_a_name_that_is_not_in_the_text_or_was_not_removed_is_an_error():
    with pytest.raises(voicecheck.NotRedundant, match="not in the text before"):
        voicecheck.compare(HERON_BEFORE, HERON_AFTER, ["Nobody keeps the dashboard."])
    with pytest.raises(voicecheck.NotRedundant, match="still in the text after"):
        voicecheck.compare(HERON_BEFORE, HERON_BEFORE, [NAMED])


def test_the_cli_takes_redundant_and_prints_who_asked(tmp_path):
    before, after = tmp_path / "before.md", tmp_path / "after.md"
    before.write_text(HERON_BEFORE, encoding="utf-8")
    after.write_text(HERON_AFTER, encoding="utf-8")
    assert run("voicecheck", str(before), str(after))[0] == 1
    code, out = run("voicecheck", str(before), str(after), "--redundant", NAMED)
    assert code == 0 and f"removed as redundant, named by the reviewer: {NAMED}" in out
    assert run("voicecheck", str(before), str(after), "--redundant", "Nobody keeps the dashboard.")[0] == 2


# Through the CLI.

def test_non_utf8_input_exits_2(tmp_path):
    good, bad = tmp_path / "good.md", tmp_path / "bad.md"
    good.write_text("x 1\n", encoding="utf-8")
    bad.write_bytes(b"x \xff 1\n")
    assert run("voicecheck", str(good), str(bad))[0] == 2
    assert run("voicecheck", str(bad), str(good))[0] == 2

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
    subprocess.run(GIT + ["init", "-q"], cwd=tmp_path, check=True, timeout=60)
    (tmp_path / "page.md").write_text(DRAFT, encoding="utf-8")
    (tmp_path / "other.md").write_text("Nothing protected here.\n", encoding="utf-8")
    subprocess.run(GIT + ["add", "-A"], cwd=tmp_path, check=True, timeout=60)
    subprocess.run(GIT + ["commit", "-qm", "draft: prose for s"], cwd=tmp_path, check=True, timeout=60)
    return tmp_path


def test_range_against_the_working_tree(repo):
    (repo / "page.md").write_text(DRAFT.replace("It calls", "Booking calls"), encoding="utf-8")
    assert run("voicecheck", "--range", "HEAD", "--vault", str(repo))[0] == 0
    (repo / "page.md").write_text(DRAFT.replace("10 minutes", "ten minutes"), encoding="utf-8")
    code, out = run("voicecheck", "--range", "HEAD", "--vault", str(repo))
    assert code == 1
    assert out.splitlines() == ["planner voicecheck: 1 files compared, 1 with protected tokens changed.",
                                "page.md: missing: 10 minutes (number), before line 1"]


def test_range_between_two_commits(repo):
    (repo / "page.md").write_text(DRAFT.replace("CON-003 on", "CON-004 on"), encoding="utf-8")
    subprocess.run(GIT + ["commit", "-qam", "draft: voice rewrite for s"], cwd=repo, check=True, timeout=60)
    code, out = run("voicecheck", "--range", "HEAD~1..HEAD", "--vault", str(repo))
    assert code == 1
    assert "page.md: missing: CON-003 (id), before line 1" in out and "page.md: added: CON-004 (id), after line 1" in out


def commit_all(repo, message):
    subprocess.run(GIT + ["add", "-A"], cwd=repo, check=True, timeout=60)
    subprocess.run(GIT + ["commit", "-qm", message], cwd=repo, check=True, timeout=60)


def test_range_reads_non_ascii_and_spaced_names(repo):
    (repo / "café.md").write_text("Hold 10 minutes.\n", encoding="utf-8")
    (repo / "with space.md").write_text("Hold 10 minutes.\n", encoding="utf-8")
    commit_all(repo, "add")
    (repo / "café.md").write_text("Hold ten minutes.\n", encoding="utf-8")
    (repo / "with space.md").write_text("Hold ten minutes.\n", encoding="utf-8")
    code, out = run("voicecheck", "--range", "HEAD", "--vault", str(repo))
    assert code == 1
    assert out.splitlines() == ["planner voicecheck: 2 files compared, 2 with protected tokens changed.",
                                "café.md: missing: 10 minutes (number), before line 1",
                                "with space.md: missing: 10 minutes (number), before line 1"]


def test_range_compares_a_renamed_file_with_its_old_self(repo):
    filler = "".join(f"Filler line {word} that keeps the two versions alike.\n" for word in "abcdefghij")
    (repo / "page.md").write_text(DRAFT + filler, encoding="utf-8")
    commit_all(repo, "longer page")
    subprocess.run(GIT + ["mv", "page.md", "renamed.md"], cwd=repo, check=True, timeout=60)
    (repo / "renamed.md").write_text(DRAFT.replace("10 minutes", "ten minutes") + filler, encoding="utf-8")
    commit_all(repo, "rename and rewrite")
    code, out = run("voicecheck", "--range", "HEAD~1..HEAD", "--vault", str(repo))
    assert code == 1
    assert out.splitlines() == ["planner voicecheck: 1 files compared, 1 with protected tokens changed.",
                                "renamed.md: missing: 10 minutes (number), before line 1"]


def test_range_counts_a_new_and_a_deleted_file(repo):
    (repo / "new.md").write_text("Fresh 5.\n", encoding="utf-8")
    (repo / "other.md").unlink()
    commit_all(repo, "add and remove")
    code, out = run("voicecheck", "--range", "HEAD~1..HEAD", "--vault", str(repo))
    assert code == 1 and "new.md: added: 5 (number), after line 1" in out
    assert out.splitlines()[0] == "planner voicecheck: 2 files compared, 2 with protected tokens changed."  # a deleted file loses its "Nothing"


def test_show_tells_a_missing_path_from_a_git_failure(repo):
    from planner import cli
    assert cli.show(repo, "HEAD", "nowhere.md") == ""
    assert cli.show(repo, "HEAD", "other.md") == "Nothing protected here.\n"
    with pytest.raises(cli.ToolError):
        cli.show(repo, "no-such-ref", "other.md")


def test_show_finds_a_path_that_starts_with_a_colon(repo):
    from planner import cli
    (repo / ":odd.md").write_text("Hold 10 minutes.\n", encoding="utf-8")
    commit_all(repo, "colon")
    assert cli.show(repo, "HEAD", ":odd.md") == "Hold 10 minutes.\n"
    (repo / ":odd.md").write_text("Hold ten minutes.\n", encoding="utf-8")
    assert run("voicecheck", "--range", "HEAD", "--vault", str(repo))[0] == 1


def test_a_range_that_reads_as_a_git_option_is_refused(repo):
    for spec in ("--output=/tmp/voicecheck-pwn", "HEAD..--stat", "-p"):
        code, out = run("voicecheck", f"--range={spec}", "--vault", str(repo))
        assert code == 2 and "git option" in out
    assert not (pathlib.Path("/tmp/voicecheck-pwn")).exists()


def test_a_non_utf8_file_in_a_commit_exits_2(repo):
    (repo / "page.md").write_bytes(b"caf\xe9 10\n")
    commit_all(repo, "latin-1")
    assert run("voicecheck", "--range", "HEAD~1..HEAD", "--vault", str(repo))[0] == 2


def test_tool_failures_exit_2(repo, tmp_path):
    assert run("voicecheck")[0] == 2
    assert run("voicecheck", str(repo / "page.md"))[0] == 2
    assert run("voicecheck", str(repo / "page.md"), str(repo / "page.md"), "--range", "HEAD")[0] == 2
    assert run("voicecheck", str(repo / "nowhere.md"), str(repo / "page.md"))[0] == 2
    code, out = run("voicecheck", "--range", "no-such-ref", "--vault", str(repo))
    assert code == 2 and "no-such-ref" in out
    assert run("voicecheck", "--range", "..HEAD", "--vault", str(repo))[0] == 2


def test_close_and_the_reviewer_carry_the_redundant_route():
    root = pathlib.Path(__file__).resolve().parent.parent / "plugin"
    close = (root / "skills" / "close" / "SKILL.md").read_text(encoding="utf-8")
    reviewer = (root / "agents" / "voice-reviewer.md").read_text(encoding="utf-8")
    assert '--redundant "<sentence>"' in close and "named by the reviewer" in close or "the reviewer named as redundant" in close
    assert "Redundant sentences" in reviewer and "Redundant sentence (exact)" in reviewer
