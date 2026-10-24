"""vela next on a small plan: Discover, a grill on the strategy, Boundary with requirements and shares, then grills."""
import shutil

from conftest import REPO, edit, run
from sizing_vault import choose, from_template, write_plan
from vela import cli, progress

TODAY = "2026-10-23"


def next_line(root):
    code, out = run("next", "--vault", str(root), "--today", TODAY)
    assert code == 0, out
    return out


def decided_strategy(tmp_path, config=""):
    root = from_template(tmp_path)
    write_plan(root, capabilities=["new"], config=config)
    edit(root / "04-solution-strategy.md", "state: inkling", "state: decided")
    return root


def test_small_decided_strategy_goes_to_boundary_with_its_requirements(tmp_path):
    out = next_line(decided_strategy(tmp_path))
    assert "/vela:boundary" in out and "/vela:requirements" not in out


def test_medium_decided_strategy_still_writes_requirements_first(tmp_path):
    assert "/vela:requirements" in next_line(decided_strategy(tmp_path, choose("medium")))


def test_small_undecided_strategy_with_a_source_goes_to_its_grill(tmp_path):
    root = from_template(tmp_path)
    write_plan(root, capabilities=["new"])
    edit(root / "04-solution-strategy.md", "state: inkling", "state: inkling\nsources: [SRC-01]")
    assert "/vela:grill 04-solution-strategy" in next_line(root)


def test_small_rule_three_suggests_a_grill_and_medium_a_shape(tmp_path):
    root = write_plan(tmp_path, apps=[("jobs-api", "new")])
    page = root / "05-building-blocks" / "jobs-api-building-blocks.md"
    edit(page, "state: inkling\n", "state: assumption\nsources: [SRC-01]\n")
    row = progress.grid(cli.load_vault(root), TODAY)[0]
    assert (row.rule, row.mode) == (3, "grill") and "anything else was on the table" in row.reason
    write_plan(root, apps=[("jobs-api", "new")], config=choose("medium"))
    edit(page, "state: inkling\n", "state: assumption\nsources: [SRC-01]\n")
    assert progress.grid(cli.load_vault(root), TODAY)[0].mode == "shape"


SNAPSHOTS = REPO / "tests" / "sim" / "snapshots" / "trading-coach"
CAP_1 = "capabilities/CAP-001-teach-a-stock-lesson.md"


SNAPSHOT_DAY = "2026-10-11"  # the day the snapshots were taken, before their open question is overdue


def snapshot(tmp_path, name, config=""):
    root = tmp_path / "v"
    shutil.copytree(SNAPSHOTS / name, root)
    set_size(root, config)
    return root


def set_size(root, config):
    text = (root / ".vela.yaml").read_text(encoding="utf-8").split("size:")[0]
    (root / ".vela.yaml").write_text(text + config, encoding="utf-8")


def said_on(root):
    return run("next", "--vault", str(root), "--today", SNAPSHOT_DAY)[1]


def test_small_unallocated_requirement_goes_to_boundary_not_allocate(tmp_path):
    root = snapshot(tmp_path, "after-80b", choose("small"))
    (root / CAP_1).write_text((SNAPSHOTS / "after-capture-boundary" / CAP_1).read_text(encoding="utf-8"), encoding="utf-8")
    out = said_on(root)
    assert "say which app owns" in out and "/vela:boundary" in out and "/vela:allocate" not in out


def test_small_undated_release_is_asked_in_the_grill(tmp_path):
    root = snapshot(tmp_path, "after-capture-boundary", choose("small"))
    (root / "04b-releases.md").write_text((REPO / "plugin" / "template" / "04b-releases.md").read_text(encoding="utf-8"),
                                          encoding="utf-8")
    for gone in [*(root / "13-epics").glob("EPC-*.md"), *(c for c in (root / "capabilities").glob("CAP-*.md") if not c.name.startswith("CAP-001"))]:
        gone.unlink()  # releases are dated before the epics are written, and every capability left has requirements
    small = said_on(root)
    assert "for the whole plan" not in small and "/vela:releases" not in small
    set_size(root, choose("medium"))
    assert "/vela:releases" in said_on(root)
