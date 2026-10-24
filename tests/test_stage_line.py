"""W408: an old `stage:` line is said to be ignored, and `check --fix auto` removes it (no shim reads it first)."""
import shutil

from conftest import REPO, run
from vela import cli, ladder, stagefix

FIXTURE = REPO / "tests" / "fixtures" / "small-two-apps"
TODAY = "2026-10-23"


def with_stage(tmp_path, value="epics"):
    root = tmp_path / "plan"
    shutil.copytree(FIXTURE, root)
    page = root / "05-building-blocks" / "scheduler-building-blocks.md"
    text = page.read_text(encoding="utf-8")
    page.write_text(text.replace("\n---\n", f"\nstage: {value}\n---\n", 1), encoding="utf-8")
    return root, page


def test_an_old_stage_line_draws_a_finding_and_is_not_read(tmp_path):
    root, page = with_stage(tmp_path)
    out = run("check", "--vault", str(root), "--today", TODAY)[1]
    line = next(l for l in out.splitlines() if "W408" in l)
    assert page.name in line and "works the stage out from the pages" in line
    vault = cli.load_vault(root)
    app = next(p for p in vault.apps if p.path.endswith(page.name))
    assert ladder.stage(vault, app) != "epics", "the old line decides nothing"


def test_fix_auto_removes_only_that_line(tmp_path):
    root, page = with_stage(tmp_path)
    before = page.read_text(encoding="utf-8")
    code, out = run("check", "--fix", "auto", "--vault", str(root), "--today", TODAY)
    assert code == 0, out
    assert page.read_text(encoding="utf-8") == before.replace("stage: epics\n", "")
    assert "W408" not in run("check", "--vault", str(root), "--today", TODAY)[1]
    assert run("check", "--fix", "W408", "--vault", str(root), "--today", TODAY)[0] == 0, "nothing left is not a failure"


def test_a_plan_without_the_line_has_nothing_to_remove():
    assert stagefix.plan(cli.load_vault(FIXTURE)) == ()
