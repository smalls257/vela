"""The sim's starting snapshots carry no line the current templates have retired.

The Violation this prevents is a Fossil Comment seeded into every run: `plugin/catalog/template-lines-retired.txt`
lists the opening sentences older templates wrote (W368 still recognizes them), yet the `empty` and `after-*`
snapshots a run starts from kept them, so a new run's index pages opened with "One page per decision, named
`ADR-nnnn-<slug>.md`." and the precision judge scored the line as padding (full3 P12).

The empty `unexamined` rows on the per-concern pages are gone too: an app on the "Not looked at yet:" line counts as
unexamined (E315 reads the line), which is what `add app-stub` writes.
"""
import re

from conftest import REPO

SNAPSHOTS = REPO / "tests" / "sim"  # the starting snapshots and the scaled probes' snapshots both
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



def test_every_snapshot_vault_passes_vela_check_with_no_error():
    """Including the concern pages, whose unlooked-at apps sit on the one "Not looked at yet:" line (E315 reads it)."""
    from conftest import check
    bad = {}
    for goals in sorted(SNAPSHOTS.rglob("01-goals.md")):
        code, out = check(goals.parent, "2026-10-19")
        errors = [l for l in out.splitlines() if re.search(r" E\d+ ", l)]
        if errors:
            bad[str(goals.parent.relative_to(SNAPSHOTS))] = errors[:2]
    assert bad == {}
