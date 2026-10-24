"""vela ladder: the stage an app's pages reach. Read-only, and never a prompt."""
from conftest import REPO, run

FIXTURE = REPO / "examples" / "unified-booking"


def test_the_example_vault_reaches_the_last_stage():
    code, out = run("ladder", "--vault", str(FIXTURE))
    assert code == 0
    lines = out.splitlines()[1:]
    assert lines and all(line.split(" | ")[1] == "stage: epics" for line in lines), out


def write_app(vault, state, extra="", sources="[SRC-01]"):
    (vault / ".vela.yaml").write_text("initiative: INI-001\ntitle: T\n", encoding="utf-8")
    (vault / "05-building-blocks").mkdir(exist_ok=True)
    (vault / "05-building-blocks" / "coach-building-blocks.md").write_text(
        f"---\nid: APP-coach\ntype: app-building-blocks\ntitle: Coach\nstate: {state}\nchange: new\n"
        f"owner: \"@lead\"\nauthored: authored\nsources: {sources}\n---\n# Coach\n\nRuns lessons.\n\n"
        "| Container | Job | Contracts served or used | Proposed by | State |\n|---|---|---|---|---|\n"
        "| Lessons | Runs lessons | none | lead | assumption |\n" + extra, encoding="utf-8")


def test_a_decided_app_page_reaches_contracts_and_says_what_handoff_needs(tmp_path):
    write_app(tmp_path, "decided")
    code, out = run("ladder", "--vault", str(tmp_path))
    assert ("(APP-coach) | stage: contracts | held back from the next stage by: "
            "its runtime page has no section on what happens when things fail") in out
    status = run("status", "--vault", str(tmp_path), "--today", "2026-01-15")[1]
    assert "Coach (APP-coach) | stage: contracts |" in status and "already meet" not in status


def test_an_app_that_cites_no_source_stays_at_baseline(tmp_path):
    write_app(tmp_path, "assumption", sources="[]")
    assert "stage: baseline" in run("status", "--vault", str(tmp_path), "--today", "2026-01-15")[1]


def test_a_handoff_may_say_pr_pending_until_the_pr_exists(tmp_path):
    write_app(tmp_path, "decided")
    page = tmp_path / "05-building-blocks" / "coach-building-blocks.md"
    page.write_text(page.read_text(encoding="utf-8").replace("change: new\n",
                    "change: new\nhanded_off: \"Coach lead, 2026-10-09\"\nhanded_off_pr: pending\n"), encoding="utf-8")
    out = run("check", "--vault", str(tmp_path), "--today", "2026-10-09")[1]
    assert "W325" in out and "E105" not in out
