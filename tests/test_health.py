"""vela health: the Markdown report a person runs by hand."""
import re

from conftest import check, edit, findings, run


def stale(mini):
    edit(mini / "01-goals.md", "authored: mixed\n", "authored: mixed\nlast_verified: 2025-11-01\nverified_by: \"@mini-lead\"\n")


def test_report_lists_what_check_found_and_exits_0(mini):
    stale(mini)
    code, out = run("health", "--vault", str(mini), "--today", "2026-03-10")
    assert code == 0, out
    assert out.startswith("# Vault health\n\nMade by `vela health` on 2026-03-10, from ")
    assert "`vela check` found 0 errors and 4 warnings." in out
    assert "| UNK-001 Till test rig | @mini-qa | 2026-02-01 |" in out
    assert "| 01-goals.md | 2025-11-01 | @\u200dmini-lead | @mini-lead |" in out
    assert "| SRC-01 | Stock read API documentation | 2026-01-02 | @stock-team |" in out
    assert "The last session closed on 2026-01-10, 59 days ago. That is over 30 days." in out
    assert "9 of 10 pages don't record when someone last checked them" in out


def test_report_and_check_agree(mini):
    stale(mini)
    _, out = run("health", "--vault", str(mini), "--today", "2026-03-10")
    codes = [c for c, _ in findings(check(mini, today="2026-03-10")[1])]
    assert codes.count("W705") == out.split("## Stale pages")[0].count("| UNK-")
    assert codes.count("W716") == out.split("## Stale sources")[1].split("## Sessions")[0].count("| SRC-")


def test_a_healthy_vault_says_none(mini):
    code, out = run("health", "--vault", str(mini), "--today", "2026-01-15")
    assert code == 0
    assert out.count("None.") == 3
    assert "The last session closed on 2026-01-10, 5 days ago." in out and "over 30 days" not in out


def test_a_pipe_in_a_name_cannot_break_the_table(mini):
    edit(mini / "11-unknowns-and-risks.md", "### UNK-001 Till test rig", "### UNK-001 Till | rig")
    _, out = run("health", "--vault", str(mini), "--today", "2026-03-10")
    assert "| UNK-001 Till \\| rig | @mini-qa | 2026-02-01 |" in out


def test_an_owner_bullet_pings_only_its_leading_handle(mini):
    edit(mini / "11-unknowns-and-risks.md", "- **Owner:** @mini-qa\n", "- **Owner:** @mini-qa and ping @ceo\n")
    _, out = run("health", "--vault", str(mini), "--today", "2026-03-10")
    assert "| UNK-001 Till test rig | @mini-qa | 2026-02-01 |" in out and "@ceo" not in out


def test_an_owner_with_no_handle_reads_no_owner_recorded(mini):
    edit(mini / "11-unknowns-and-risks.md", "- **Owner:** @mini-qa\n", "- **Owner:** whoever is free\n")
    _, out = run("health", "--vault", str(mini), "--today", "2026-03-10")
    assert "| UNK-001 Till test rig | no owner recorded | 2026-02-01 |" in out


def test_other_free_text_cannot_mention_or_link(mini):
    edit(mini / "01-goals.md", "authored: mixed\n", "authored: mixed\nlast_verified: 2025-11-01\nverified_by: \"@ceo see #12\"\n")
    edit(mini / "11-unknowns-and-risks.md", "### UNK-001 Till test rig", "### UNK-001 Ask @cto about #7")
    _, out = run("health", "--vault", str(mini), "--today", "2026-03-10")
    for bad in ("@ceo", "@cto", "#12", "#7"):
        assert bad not in out


def test_an_impossible_session_date_is_skipped_not_a_crash(mini):
    session = next(mini.glob("sessions/*.md"))
    text = session.read_text(encoding="utf-8")
    session.write_text(re.sub(r"(?m)^date: .*$", 'date: "2026-02-30"', text, count=1), encoding="utf-8")
    code, out = run("health", "--vault", str(mini), "--today", "2026-03-10")
    assert code == 0, out


def test_a_future_session_does_not_read_as_negative_days(mini):
    _, out = run("health", "--vault", str(mini), "--today", "2025-12-01")
    assert "dated in the future (2026-01-10)" in out and "days ago" not in out.split("## Sessions")[1]


def test_an_empty_last_verified_is_not_verified(mini):
    edit(mini / "01-goals.md", "authored: mixed\n", "authored: mixed\nlast_verified: \"\"\n")
    _, out = run("health", "--vault", str(mini), "--today", "2026-01-15")
    assert "10 of 10 pages don't record when someone last checked them" in out


def test_findings_that_map_to_no_row_are_counted_not_dropped():
    from vela import health
    class V:  # no pages, so no finding can map to a row
        pages, unknowns, sessions = [], [], []
    found = [type("F", (), {"path": "gone.md", "line": 3, "code": "W704", "is_error": False})()]
    out = health.report(V, found, "2026-03-10", "abc")
    assert "1 findings not shown; run `vela check`." in out


def test_bad_date_is_a_tool_failure(mini):
    assert run("health", "--vault", str(mini), "--today", "monday")[0] == 2
