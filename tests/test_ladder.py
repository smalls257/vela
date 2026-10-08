"""planner ladder: the stage an app's pages reach, against its hand-typed stage. Read-only, and never a prompt."""
from conftest import REPO, run

FIXTURE = REPO / "examples" / "unified-booking"


def test_the_example_vault_reaches_every_stage_it_types():
    code, out = run("ladder", "--vault", str(FIXTURE))
    assert code == 0
    lines = out.splitlines()[1:]
    assert lines and all(line.split(" | ")[1] == "stage epics" and line.split(" | ")[2] == "pages reach epics"
                         for line in lines), out


def write_app(vault, state, extra="", stage="target"):
    (vault / ".planner.yaml").write_text("initiative: INI-001\ntitle: T\n", encoding="utf-8")
    (vault / "05-building-blocks").mkdir(exist_ok=True)
    (vault / "05-building-blocks" / "coach-building-blocks.md").write_text(
        f"---\nid: APP-coach\ntype: app-building-blocks\ntitle: Coach\nstate: {state}\nchange: new\nstage: {stage}\n"
        f"owner: \"@lead\"\nauthored: authored\nsources: [SRC-01]\n---\n# Coach\n\nRuns lessons.\n\n"
        "| Container | Job | Contracts served or used | Proposed by | State |\n|---|---|---|---|---|\n"
        "| Lessons | Runs lessons | none | lead | assumption |\n" + extra, encoding="utf-8")


def test_a_decided_app_page_reaches_contracts_and_says_what_handoff_needs(tmp_path):
    write_app(tmp_path, "decided")
    code, out = run("ladder", "--vault", str(tmp_path))
    assert "APP-coach | stage target | pages reach contracts | next stage needs: its runtime page has no section on failure" in out
    status = run("status", "--vault", str(tmp_path), "--today", "2026-01-15")[1]
    assert "APP-coach | stage target | pages reach contracts |" in status


def test_status_says_nothing_when_the_pages_reach_no_further_than_the_stage(tmp_path):
    write_app(tmp_path, "assumption", stage="boundaries")  # no flow names it, so boundaries holds; contracts does not
    assert "pages reach" not in run("status", "--vault", str(tmp_path), "--today", "2026-01-15")[1]


def test_close_reports_the_stage_as_a_line_and_never_asks():
    close = (REPO / "plugin" / "skills" / "close" / "SKILL.md").read_text(encoding="utf-8")
    assert "**Stage:** run `python3 .claude/skills/planner/bin/planner ladder`" in close
    assert "never a question" in close
