"""The stage is what an app's pages reach (ladder.allows). Nothing types it and nothing reads a typed one."""
import re

from conftest import REPO, run
from test_ladder import write_app
from vela import cli, gates, handoffwarn, ladder, progress, schema

LIB = REPO / "plugin" / "lib" / "vela"


def test_the_stage_is_what_the_pages_reach(tmp_path):
    write_app(tmp_path, "decided")
    vault = cli.load_vault(tmp_path)
    assert ladder.stage(vault, vault.apps[0]) == "contracts"
    assert progress.grid(vault, "2026-01-15")[0].stage == "contracts"


def test_no_app_page_types_a_stage():
    assert "stage" not in schema.PAGE_TYPES["app-building-blocks"]["optional"]
    assert "stage" not in schema.ENUMS and "E319" not in schema.CODES
    assert schema.STAGES == ("baseline", "target", "boundaries", "contracts", "handoff", "epics")


def test_a_stray_stage_line_is_read_by_nothing(tmp_path):
    write_app(tmp_path, "decided")
    page = tmp_path / "05-building-blocks" / "coach-building-blocks.md"
    page.write_text(page.read_text(encoding="utf-8").replace("change: new\n", "change: new\nstage: epics\n"),
                    encoding="utf-8")
    vault = cli.load_vault(tmp_path)
    assert ladder.stage(vault, vault.apps[0]) == "contracts"


def test_decide_gate_one_reads_the_derived_stage(tmp_path):
    write_app(tmp_path, "assumption", sources="[]")
    vault = cli.load_vault(tmp_path)
    found = gates.verdict(vault, None, "APP-coach", "2026-01-15")
    assert [r.rule for r in found.reasons][:1] == ["GATE-1"]
    assert "still at the baseline stage" in found.reasons[0].plain


def test_handoff_lines_follow_the_derived_stage(tmp_path):
    write_app(tmp_path, "decided")
    vault = cli.load_vault(tmp_path)
    assert not handoffwarn.at_handoff(vault, vault.apps[0])  # contracts, not handoff, and not handed off


def test_vela_ladder_and_status_say_one_stage(tmp_path):
    write_app(tmp_path, "decided")
    out = run("ladder", "--vault", str(tmp_path))[1]
    assert ("(APP-coach) | stage: contracts | held back from the next stage by: its runtime page has no section on "
            "what happens when things fail") in out
    status = run("status", "--vault", str(tmp_path), "--today", "2026-01-15")[1]
    assert "Coach (APP-coach) | stage: contracts |" in status and "already meet" not in status


def test_nothing_reads_a_typed_stage():
    hits = [f"{p.relative_to(REPO)}:{n}" for p in LIB.rglob("*.py")
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if re.search(r"""meta(?:\.get\(|\[)["']stage["']""", line) or "ahead_of_stage" in line]
    assert hits == []


def test_no_vault_in_the_repo_types_a_stage():
    roots = [REPO / "plugin" / "template", REPO / "examples" / "unified-booking", REPO / "tests" / "fixtures"]
    hits = [str(p.relative_to(REPO)) for root in roots for p in root.rglob("*.md")
            if re.search(r"^stage: ", p.read_text(encoding="utf-8"), re.M)]
    assert hits == []
