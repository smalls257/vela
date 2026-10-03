from conftest import check, edit, findings

TESTING = "08-concerns/concern-testing.md"


def primary(out):
    return sorted(f for f in findings(out) if f[0] != "W402")


def test_missing_cell(mini):
    edit(mini / TESTING, "| [[stock-building-blocks\\|Stock]] | unchanged | Existing tests hold |\n", "")
    _, out = check(mini)
    assert primary(out) == [("E315", TESTING)]
    assert "APP-stock" in out


def test_bad_cell_state(mini):
    edit(mini / TESTING, "| unchanged | Existing tests hold |", "| fine | Existing tests hold |")
    _, out = check(mini)
    assert primary(out) == [("E301", TESTING)]


def test_na_needs_a_reason(mini):
    edit(mini / TESTING, "| unchanged | Existing tests hold |", "| n/a | |")
    _, out = check(mini)
    assert primary(out) == [("E301", TESTING)]


def test_unknown_cell_needs_an_unknown_link(mini):
    edit(mini / TESTING, "| unknown | Waiting on [[11-unknowns-and-risks#UNK-001 Till test rig\\|UNK-001]] |",
         "| unknown | Waiting on the QA team |")
    _, out = check(mini)
    assert primary(out) == [("E301", TESTING)]


def test_cell_row_without_app_link(mini):
    edit(mini / TESTING, "| [[stock-building-blocks\\|Stock]] |", "| Stock |")
    _, out = check(mini)
    assert primary(out) == [("E301", TESTING), ("E315", TESTING)]


def test_new_app_with_no_cell_anywhere(mini):
    (mini / "05-building-blocks" / "web-building-blocks.md").write_text(
        "---\nid: APP-web\ntype: app-building-blocks\ntitle: Web\nstate: inkling\nchange: new\nstage: baseline\n"
        "owner: \"@mini/web-team\"\nauthored: authored\n---\n# Web\n", encoding="utf-8")
    _, out = check(mini)
    assert primary(out) == [("E315", TESTING)]


def test_cell_linking_a_page_that_is_not_an_app(mini):
    edit(mini / TESTING, "| [[stock-building-blocks\\|Stock]] |", "| [[11-unknowns-and-risks\\|Stock]] |")
    _, out = check(mini)
    assert ("E301", TESTING) in primary(out)
    assert "not an app page" in out
