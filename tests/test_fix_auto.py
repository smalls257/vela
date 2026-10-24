"""check --fix auto: W326 and W358 in one pass; W358 only when exactly one capability page holds the answer."""
import shutil

from conftest import REPO, run
from vela import cli, w358fix

FIXTURE = REPO / "tests" / "fixtures" / "small-two-apps"
FLOW = ("---\nid: FLO-001\ntype: flow\ntitle: Book a job\nstate: assumption\nowner: \"@mo\"\nauthored: authored\n---\n\n"
        "# Book a job\n\n1. A caller books a job through the Jobs API.\n")


def with_flow(tmp_path):
    root = tmp_path / "plan"
    shutil.copytree(FIXTURE, root)
    (root / "06-runtime" / "flows").mkdir(parents=True, exist_ok=True)
    (root / "06-runtime" / "flows" / "FLO-001-book-a-job.md").write_text(FLOW, encoding="utf-8")
    return root


def test_one_capability_is_the_one_answer(tmp_path):
    root = with_flow(tmp_path)
    assert [c.after for c in w358fix.plan(cli.load_vault(root))] == ["capabilities: [CAP-001]"]
    code, out = run("check", "--fix", "auto", "--vault", str(root), "--today", "2026-10-23")
    assert code == 0, out
    assert "capabilities: [CAP-001]" in (root / "06-runtime" / "flows" / "FLO-001-book-a-job.md").read_text(encoding="utf-8")
    assert "W358" not in run("check", "--vault", str(root), "--today", "2026-10-23")[1]


def test_two_capabilities_have_no_one_answer(tmp_path):
    root = with_flow(tmp_path)
    (root / "capabilities" / "CAP-002-cancel-a-job.md").write_text(
        (root / "capabilities" / "CAP-001-run-a-job-on-time.md").read_text(encoding="utf-8")
        .replace("CAP-001", "CAP-002").replace("Run a job on time", "Cancel a job"), encoding="utf-8")
    assert w358fix.plan(cli.load_vault(root)) == ()
