"""The sim's starting snapshots carry no line the current templates have retired.

The Violation this prevents is a Fossil Comment seeded into every run: `plugin/catalog/template-lines-retired.txt`
lists the opening sentences older templates wrote (W368 still recognizes them), yet the `empty` and `after-*`
snapshots a run starts from kept them, so a new run's index pages opened with "One page per decision, named
`ADR-nnnn-<slug>.md`." and the precision judge scored the line as padding (full3 P12).

Not covered: the empty `unexamined` rows on the per-concern pages. `vela check` still raises E315 for an app with no
cell, so removing them from the snapshots made the clean-check tests fail; that is a rule decision, not a stale line.
"""
from conftest import REPO

SNAPSHOTS = REPO / "tests" / "sim" / "snapshots"
RETIRED = REPO / "plugin" / "catalog" / "template-lines-retired.txt"


def snapshot_pages():
    return sorted(SNAPSHOTS.rglob("*.md"))


def test_the_retired_list_is_read_and_the_snapshots_exist():
    assert [l for l in RETIRED.read_text(encoding="utf-8").split("\n") if l.strip()]
    assert len(snapshot_pages()) > 100


def test_no_snapshot_page_carries_a_retired_template_line():
    retired = {l for l in RETIRED.read_text(encoding="utf-8").split("\n") if l.strip()}
    found = [f"{page.relative_to(SNAPSHOTS)}: {line}" for page in snapshot_pages()
             for line in page.read_text(encoding="utf-8").split("\n") if line in retired]
    assert found == []

