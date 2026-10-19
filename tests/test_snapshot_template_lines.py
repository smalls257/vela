"""The sim's starting snapshots carry no line the current templates have retired.

The Violation this prevents is a Fossil Comment seeded into every run: `plugin/catalog/template-lines-retired.txt`
lists the opening sentences older templates wrote (W368 still recognizes them), yet the `empty` and `after-*`
snapshots a run starts from kept them, so a new run's index pages opened with "One page per decision, named
`ADR-nnnn-<slug>.md`." and the precision judge scored the line as padding (full3 P12). The boundary stub likewise no
longer writes an empty `unexamined` row per app, only the page's "Not looked at yet:" line (full3 P3-P6).
"""
import pathlib
import re

from conftest import REPO

SNAPSHOTS = REPO / "tests" / "sim" / "snapshots"
RETIRED = REPO / "plugin" / "catalog" / "template-lines-retired.txt"
EMPTY_UNEXAMINED_ROW = re.compile(r"^\| \[\[[^\]]*\]\] \| unexamined \|(?: Nobody has looked at this yet\.)? \|$")


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


def test_no_snapshot_concern_page_carries_an_empty_unexamined_row():
    found = [str(page.relative_to(SNAPSHOTS)) for page in snapshot_pages()
             if page.name.startswith("concern-") and pathlib.Path(page).parent.name == "08-concerns"
             and any(EMPTY_UNEXAMINED_ROW.match(l) for l in page.read_text(encoding="utf-8").split("\n"))]
    assert found == []
