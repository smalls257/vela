"""The sim's starting snapshots carry no line the current templates have retired.

The Violation this prevents is a Fossil Comment seeded into every run: `plugin/catalog/template-lines-retired.txt`
lists the opening sentences older templates wrote (W368 still recognizes them), yet the `empty` and `after-*`
snapshots a run starts from kept them, so a new run's index pages opened with "One page per decision, named
`ADR-nnnn-<slug>.md`." and the precision judge scored the line as padding (full3 P12).

The empty `unexamined` rows on the per-concern pages are gone too: an app with no row counts as unexamined, which is
what `add app-stub` leaves (it writes no row and no sentence).
"""
import re

from conftest import REPO

SNAPSHOTS = REPO / "tests" / "sim"  # the starting snapshots and the scaled probes' snapshots both
RETIRED = REPO / "plugin" / "catalog" / "template-lines-retired.txt"


RESULTS = SNAPSHOTS / "results"  # git-ignored run outputs: what past runs wrote, not what a run starts from


def tracked(paths):
    return sorted(p for p in paths if RESULTS not in p.parents)


def snapshot_pages():
    return tracked(SNAPSHOTS.rglob("*.md"))


def test_the_retired_list_is_read_and_the_snapshots_exist():
    assert [l for l in RETIRED.read_text(encoding="utf-8").split("\n") if l.strip()]
    assert len(snapshot_pages()) > 100


def test_no_snapshot_page_carries_a_retired_template_line():
    retired = {l for l in RETIRED.read_text(encoding="utf-8").split("\n") if l.strip()}
    found = [f"{page.relative_to(SNAPSHOTS)}: {line}" for page in snapshot_pages()
             for line in page.read_text(encoding="utf-8").split("\n") if line in retired]
    assert found == []


def test_the_shipped_template_writes_no_retired_line():
    """What `vela init` copies is the generation path itself; a retired line there would seed every new vault."""
    retired = {l for l in RETIRED.read_text(encoding="utf-8").split("\n") if l.strip()}
    found = [f"{p.relative_to(REPO)}: {l}" for p in sorted((REPO / "plugin" / "template").rglob("*.md"))
             for l in p.read_text(encoding="utf-8").split("\n") if l in retired]
    assert found == []


def test_every_snapshot_vault_passes_vela_check_with_no_error():
    """Including the concern pages, whose unlooked-at apps have no row."""
    from conftest import check
    bad = {}
    for goals in tracked(SNAPSHOTS.rglob("01-goals.md")):
        code, out = check(goals.parent, "2026-10-19")
        errors = [l for l in out.splitlines() if re.match(r"\S+:\d+: E\d+ ", l)]
        if errors:
            bad[str(goals.parent.relative_to(SNAPSHOTS))] = errors[:2]
    assert bad == {}
