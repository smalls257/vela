"""vela health and the weekly workflow that posts it as the "Vault health" issue."""
import os
import re
import subprocess

import yaml

from conftest import REPO, check, edit, findings, run

WORKFLOW = REPO / "template" / ".github" / "workflows" / "vela-weekly.yml"


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


# The workflow. It cannot run against a live repo here, so its script runs against a stand-in gh.

def workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_workflow_runs_weekly_with_issue_permission_only():
    data = workflow()
    triggers = data.get("on", data.get(True))
    assert triggers["schedule"] == [{"cron": "0 7 * * 1"}] and "workflow_dispatch" in triggers
    assert data["permissions"] == {"contents": "read", "issues": "write"}
    steps = data["jobs"]["vault-health"]["steps"]
    assert "python .claude/skills/vela/scripts/vela health > vault-health.md" in [s.get("run") for s in steps]
    assert steps[-1]["env"] == {"GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}"}


# Exits with FAKE_FAIL's value when the subcommand named in FAKE_FAIL_ON is called.
FAKE_GH = """#!/bin/sh
echo "$@" >> "$GH_LOG"
if [ "$1 $2" = "$FAKE_FAIL_ON" ]; then echo "gh: boom" >&2; exit 1; fi
if [ "$1 $2" = "issue list" ]; then printf '%s' "$FAKE_ISSUE"; fi
"""


def run_issue_step(tmp_path, existing, fail_on="none"):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "gh").write_text(FAKE_GH, encoding="utf-8")
    os.chmod(bin_dir / "gh", 0o755)
    (tmp_path / "vault-health.md").write_text("# Vault health\n", encoding="utf-8")
    log = tmp_path / "gh.log"
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "GH_LOG": str(log), "FAKE_ISSUE": existing,
           "FAKE_FAIL_ON": fail_on}
    script = workflow()["jobs"]["vault-health"]["steps"][-1]["run"]
    result = subprocess.run(["bash", "-e", "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True)
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return result, calls


def test_first_run_creates_the_issue(tmp_path):
    result, calls = run_issue_step(tmp_path, "")
    assert result.returncode == 0, result.stderr
    assert calls[-1] == "issue create --title Vault health --body-file vault-health.md"


def test_later_runs_edit_the_open_issue(tmp_path):
    result, calls = run_issue_step(tmp_path, "17\n")
    assert result.returncode == 0, result.stderr
    assert calls[-1] == "issue edit 17 --body-file vault-health.md"
    assert not [c for c in calls if c.startswith("issue create")]


def test_a_failed_lookup_fails_the_job_instead_of_opening_a_duplicate(tmp_path):
    result, calls = run_issue_step(tmp_path, "17\n", fail_on="issue list")
    assert result.returncode != 0
    assert not [c for c in calls if c.startswith("issue create") or c.startswith("issue edit")]


def test_a_failed_edit_fails_the_job(tmp_path):
    assert run_issue_step(tmp_path, "17\n", fail_on="issue edit")[0].returncode != 0


def test_a_failed_create_fails_the_job(tmp_path):
    assert run_issue_step(tmp_path, "", fail_on="issue create")[0].returncode != 0


def test_workflow_queues_runs_instead_of_canceling_one_mid_write():
    assert workflow()["concurrency"] == {"group": "vault-health", "cancel-in-progress": False}


def test_a_source_date_cannot_mention_or_link(mini):
    edit(mini / "sources.md", "| 2026-01-02 |", "| @ceo #12 |")
    code, out = run("health", "--vault", str(mini), "--today", "2026-03-10")
    assert code == 0, out
    assert "@ceo" not in out and "#12" not in out
    assert "SRC-01" in out.split("## Stale sources")[1]


def test_future_dates_show_in_health_as_typos(mini):
    edit(mini / "01-goals.md", "authored: mixed\n", "authored: mixed\nlast_verified: 2027-01-15\nverified_by: \"@mini-lead\"\n")
    edit(mini / "sources.md", "| 2026-01-02 |", "| 2062-01-02 |")
    _, out = run("health", "--vault", str(mini), "--today", "2025-12-01")
    assert "| 01-goals.md | 2027-01-15 (in the future; check for a typo) |" in out
    assert "| SRC-01 | Stock read API documentation | 2062-01-02 (in the future; check for a typo) |" in out
    assert "The last closed session is dated in the future (2026-01-10); check for a typo." in out
