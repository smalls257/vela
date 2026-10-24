"""The voice test for what a lead hears (the October 14 voice audit, structural gap 6): every `--for-lead` output the
skills relay, run over the test vaults, passes the leak check and the conversation voice's shape: the answer first,
then about four things (`say.LEAD_LIMIT`), the rest behind "N more; want them?", the lead spoken to and never about,
and no git words or model bookkeeping.

The Violation this exists to prevent is the Paper Tiger: say.py's rules held in a unit test of `say` while a command
built its own lines around them. So the shape is checked on what each command actually handed to `say.lead_lines`,
recorded by wrapping it, not on a hand-built Result.
"""
import shutil

import pytest

from conftest import REPO, run
from sharing import git, make_vault, with_remote
from vela import say
import session_files

HERON = REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-full-1"
BOOKING = REPO / "examples" / "unified-booking"
TODAY = "2026-10-14"
RECORD = "2026-10-20-grill-stock"
# Words the lead never hears from a command: third person about them, git's own voice, the model's bookkeeping.
NEVER = ("the lead", "Git said", "Changes row", "commit it", "--", "vela ")


@pytest.fixture
def heard(monkeypatch):
    """Every (result, lines said) that reached `say.lead_lines` while the test ran."""
    said = []
    real = say.lead_lines

    def recording(result, resolver, more=False):
        lines = real(result, resolver, more=more)
        said.append((result, resolver, more, lines))
        return lines
    monkeypatch.setattr(say, "lead_lines", recording)
    return said


def assert_lead_voice(out, heard):
    """The shape every lead-facing output keeps."""
    assert "vela bug" not in out, out
    for line in out.splitlines():
        assert say.leak_in(line) is None, (say.leak_in(line), line)
        assert not any(word in line for word in NEVER), line
    assert heard, "the command printed for the lead without going through say"
    for result, resolver, more, lines in heard:
        answer = resolver.plain(result.answer) if result.answer else ""
        if answer:
            assert lines[0] == answer, lines  # the answer first
        items = say.lead_items(result, resolver)
        if not more:
            listed = [line for line in lines if line in items and line != answer]
            assert len(listed) <= say.LEAD_LIMIT + 1, lines  # about four; a fifth only instead of "one more"
        hidden = len([i for i in items if i != answer]) - len([line for line in lines if line in items
                                                                 and line != answer])
        if hidden > 0:
            assert f"{say.count_words(hidden, capital=True)} more; want them?" in lines, lines


def copy_of(tmp_path, source, name):
    return session_files.split_copy(source, tmp_path / name)


READ_ONLY = [
    (HERON, ("check", "--today", TODAY, "--for-lead")),
    (HERON, ("check", "--gate", "decide", "--item", "CON-001", "--today", TODAY, "--for-lead")),
    (HERON, ("check-slice", "FLO-001", "--today", TODAY, "--for-lead")),
    (HERON, ("check-slice", "--all", "--today", TODAY, "--for-lead")),
    (HERON, ("handoff", "preview", "APP-heron", "--today", TODAY, "--for-lead")),
    (HERON, ("next", "--today", TODAY, "--for-lead")),
    (HERON, ("releases", "brief", "--for-lead")),
    (HERON, ("releases", "tracer-candidates", "--for-lead")),
    (HERON, ("questions", "--digest", "--session", "2026-10-11-privacy-m365-device-line", "--for-lead")),
    (HERON, ("epics", "frontier", "--team", "@agent-lead", "--for-lead")),
    (BOOKING, ("check", "--today", TODAY, "--for-lead")),
    (BOOKING, ("handoff", "preview", "APP-kiosks", "--today", TODAY, "--for-lead")),
    (BOOKING, ("handoff", "verify", "APP-booking", "--for-lead")),
    (BOOKING, ("next", "--today", TODAY, "--for-lead")),
    (BOOKING, ("releases", "brief", "--for-lead")),
]


@pytest.mark.parametrize("source,argv", READ_ONLY, ids=[f"{s.name}:{' '.join(a[:3])}" for s, a in READ_ONLY])
def test_every_relayed_command_speaks_in_the_lead_voice(tmp_path, heard, source, argv):
    vault = copy_of(tmp_path, source, "vault")
    code, out = run(*argv, "--vault", str(vault))
    assert code in (0, 1, 3), out
    assert out.strip(), argv
    assert_lead_voice(out, heard)


def session(tmp_path):
    vault = make_vault(tmp_path)
    with_remote(tmp_path, vault)
    git(vault, "switch", "-q", "-c", f"session/{RECORD}")
    record = ["---", f"id: {RECORD}", "type: session", "title: \"Grill: stock\"", "date: 2026-10-20",
              "modes: [grill]", "status: open", "summary: In progress.", "---", "", "# 2026-10-20 Stock grill", "",
              "## Captures", "", '- [unknown] (claude) Does the till count stock twice? ^c01',
              '- [wild] (@priya) "What if stock counted itself?" ^c02', "", "## Changes", "",
              "| ID | From | To | Source |", "|---|---|---|---|", ""]
    session_files.write_record(vault, RECORD, "\n".join(record))
    git(vault, "add", "sessions")
    git(vault, "commit", "-q", "-m", f"Open session {RECORD}")
    return vault


def test_a_session_in_flight_speaks_in_the_lead_voice(tmp_path, heard):
    """The commands a grill and its close relay, on a session with something still to settle."""
    vault = session(tmp_path)
    page = vault / "05-building-blocks" / "stock-building-blocks.md"
    page.write_text(page.read_text(encoding="utf-8").replace("- **State:** fact", "- **State:** decided", 1),
                    encoding="utf-8")
    (vault / "notes.txt").write_text("scratch\n", encoding="utf-8")
    for argv in (("close", "gate", "--today", "2026-10-20"), ("marks", "plan", "--today", "2026-10-20"),
                 ("session", "open"), ("freshness",), ("next", "--today", "2026-10-20")):
        heard.clear()
        code, out = run(*argv, "--vault", str(vault), "--for-lead")
        assert code in (0, 1, 3), (argv, out)
        assert_lead_voice(out, heard)


def test_session_start_asks_one_question_at_a_time(tmp_path, heard):
    """An open session and an unnamed initiative are two stops in one call: the lead hears the first in full and
    that one more follows (conversation voice rule 2); the model still gets both in needs_lead."""
    vault = session(tmp_path)
    git(vault, "switch", "-q", "main")
    config = vault / ".vela.yaml"
    config.write_text(config.read_text(encoding="utf-8").replace("title: ", "title: New initiative #", 1),
                      encoding="utf-8")
    git(vault, "commit", "-qam", "back to the template's name")
    code, out = run("session", "start", "--vault", str(vault), "--mode", "grill", "--topic", "till", "--today",
                    "2026-10-21", "--for-lead")
    assert code == 3, out
    assert_lead_voice(out, heard)
    assert out.count("?") <= 2 and "And one more thing after that." in out, out  # one question, and its choices
    assert RECORD not in out  # a session is named by what it's about, never its slug


def test_freshness_behind_offers_to_bring_the_changes_in(tmp_path, heard):
    vault = make_vault(tmp_path)
    bare = with_remote(tmp_path, vault)
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(bare), str(other))
    for key, value in (("user.name", "Sam Lee"), ("user.email", "sam@example.com"), ("commit.gpgsign", "false")):
        git(other, "config", key, value)
    (other / "notes.md").write_text("a change on main\n", encoding="utf-8")
    git(other, "add", "notes.md")
    git(other, "commit", "-qm", "on main")
    git(other, "push", "-q", "origin", "main")
    code, out = run("freshness", "--vault", str(vault), "--for-lead")
    assert code == 3, out
    assert out.strip() == ("This copy is behind the shared plan: one change others made since you last brought it "
                           "in. Want me to bring them in before we start?")
    assert_lead_voice(out, heard)
    code, default = run("freshness", "--vault", str(vault))
    assert code == 3 and "origin/main" in default  # the default line keeps the model's facts


def test_freshness_says_each_state_without_git():
    """Every report freshness can give, in the words `--for-lead` prints: one state, one offer, no branch, remote,
    counts tail or git's own words (the October 14 voice audit, rows 46 to 55)."""
    from vela import freshness
    have = {"commit": "a1b2c3d4", "date": "2026-10-14"}
    copy = {"base_commit": "a1b2c3d4", "base_date": "2026-10-14"}
    reports = [
        freshness.reader_report({"base_commit": ""}, None, "", "", "now"),
        freshness.reader_report(copy, None, "offline", "", "now"),
        freshness.reader_report(copy, {"commit": "a1b2c3d4", "date": "2026-10-14"}, "", "", "now"),
        freshness.reader_report(copy, {"commit": "ffff0000", "date": "2026-10-16"}, "", "", "now"),
        freshness.owner_report(have, have, 0, 0, 1, "fatal: could not read from remote", "", "now", "session/x", 2),
        freshness.owner_report(have, have, 3, 0, 0, "", "", "now", "session/x", 2),
        freshness.owner_report(have, have, 0, 0, 0, "", "", "now", "main"),
        freshness.owner_report(have, None, 0, 0, 0, "", "no remote", "now", "main", problem_lead=freshness.NOT_SHARED),
    ]
    for report in reports:
        assert report.lead and say.leak_in(report.lead) is None, report.lead
        assert not any(word in report.lead for word in ("origin", "branch", "commit", "fetch", "pull")), report.lead
    assert reports[3].lead == ("A newer copy came out on October 16, 2026. Your drafts are safe; I can carry them over "
                               "to it. Want that?")
    assert reports[6].lead == "You're up to date with the shared plan."


def test_check_slice_names_the_flow_once_and_drops_the_counters(tmp_path, heard):
    vault = copy_of(tmp_path, HERON, "vault")
    code, out = run("check-slice", "FLO-001", "--vault", str(vault), "--today", TODAY, "--for-lead")
    assert code == 1, out
    assert "(FLO-001)" not in out and "states" not in out and "transitions" not in out, out
    assert out.strip() == ("A person gets a prep note before a client call isn't checked yet: its steps aren't drawn "
                           "as a sequence yet, so there's nothing to check.")
