"""Keep it alive: last_verified, verified_by, stale_after_days and the three freshness warnings.
None of them is ever an error, so a stale vault never blocks a PR."""
import shutil

from conftest import REPO, check, edit, findings

GOALS = "01-goals.md"
FIXTURE = REPO / "examples" / "unified-booking"


def verify(mini, date, by='"@mini-lead"'):
    edit(mini / GOALS, "authored: mixed\n", f"authored: mixed\nlast_verified: {date}\nverified_by: {by}\n")


def test_a_page_verified_long_ago_warns_and_exits_0(mini):
    verify(mini, "2025-11-01")
    code, out = check(mini)
    assert code == 0
    assert findings(out) == [("W704", GOALS)]
    assert f"{GOALS}:10: W704 Nobody has rechecked" in out and "since 2025-11-01, 75 days ago; pages are due a recheck every 60 days." in out


def test_an_unquoted_yaml_date_counts_as_a_date(mini):
    verify(mini, "2026-01-10")  # unquoted: YAML reads a date object, and parse turns it back into YYYY-MM-DD text
    assert "last_verified: 2026-01-10\n" in (mini / GOALS).read_text(encoding="utf-8")
    code, out = check(mini)
    assert code == 0 and findings(out) == []


def test_a_page_verified_inside_the_window_is_quiet(mini):
    verify(mini, "2025-11-16")
    assert findings(check(mini)[1]) == []


def test_a_page_never_verified_is_not_judged(mini):
    assert findings(check(mini)[1]) == []


def test_a_bad_last_verified_or_verified_by_is_an_error(mini):
    verify(mini, "last week", by="Jason")
    code, out = check(mini)
    assert code == 1
    assert sorted(findings(out)) == [("E105", GOALS), ("E106", GOALS)]


def test_stale_after_days_sets_the_window(mini):
    verify(mini, "2025-11-01")
    edit(mini / ".planner.yaml", "title: Mini shop\n", "title: Mini shop\nstale_after_days: 90\n")
    assert findings(check(mini)[1]) == []


def test_a_bad_stale_after_days_is_a_tool_failure(mini):
    for bad in ("sixty", "0", "true", "[60]"):
        (mini / ".planner.yaml").write_text(f"initiative: INI-900\ntitle: Mini shop\nstale_after_days: {bad}\n", encoding="utf-8")
        code, out = check(mini)
        assert code == 2 and "stale_after_days" in out, bad


def test_an_old_source_row_warns(mini):
    code, out = check(mini, today="2026-03-10")
    assert code == 0
    assert ("W716", "sources.md") in findings(out)
    assert "SRC-01 is dated 2026-01-02, 67 days ago; sources are due a recheck every 60 days." in out


def test_a_source_row_with_no_date_warns_instead_of_passing(mini):
    edit(mini / "sources.md", "| 2026-01-02 |", "| January |")
    code, out = check(mini)
    assert code == 0
    assert findings(out) == [("W716", "sources.md")]
    assert "has Date 'January', which is not a YYYY-MM-DD date, so its age cannot be judged." in out


def test_no_closed_session_for_30_days_warns_once(mini):
    code, out = check(mini, today="2026-02-10")
    assert code == 0
    assert ("W711", "sessions/2026-01-10-shop-api.md") in findings(out)
    assert "The last session closed on 2026-01-10, 31 days ago." in out
    assert [c for c, _ in findings(out)].count("W711") == 1


def test_an_open_session_does_not_count_as_closed(mini):
    edit(mini / "sessions" / "2026-01-10-shop-api.md", "status: closed", "status: open")
    _, out = check(mini, today="2026-02-06")
    assert "The last session closed on 2026-01-05, 32 days ago." in out


def test_a_vault_with_no_closed_session_is_not_judged(mini):
    for path in (mini / "sessions").glob("*.md"):
        edit(path, "status: closed", "status: open")
    assert "W711" not in check(mini, today="2027-01-01")[1]


def test_the_fixture_is_clean_with_its_window_and_stale_with_the_default(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    edit(vault / ".planner.yaml", "stale_after_days: 180\n", "")
    code, out = check(vault, today="2026-11-20")
    assert code == 0
    assert {c for c, _ in findings(out)} == {"W716"}


def test_a_future_last_verified_warns_as_a_typo(mini):
    verify(mini, "2027-01-15")
    code, out = check(mini)
    assert code == 0
    assert findings(out) == [("W704", GOALS)]
    assert "goals last_verified is dated in the future (2027-01-15); check for a typo." in out


def test_a_future_source_date_warns_as_a_typo(mini):
    edit(mini / "sources.md", "| 2026-01-02 |", "| 2062-01-02 |")
    code, out = check(mini)
    assert code == 0
    assert findings(out) == [("W716", "sources.md")]
    assert "SRC-01 is dated in the future (2062-01-02); check for a typo." in out


def test_a_future_closed_session_warns_instead_of_hiding_the_gap(mini):
    code, out = check(mini, today="2025-12-01")
    assert ("W711", "sessions/2026-01-10-shop-api.md") in findings(out)
    assert "The last closed session is dated in the future (2026-01-10); check for a typo." in out


def test_conventions_say_a_future_date_is_a_typo_warning():
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert ("A `last_verified`, a source `Date` or the last closed session dated after today is not fresh: "
            "W704, W716 or W711 says it is \"dated in the future (<date>); check for a typo.\"") in conventions
