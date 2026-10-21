import re

from conftest import check, edit, findings, run

GOALS = "01-goals.md"
MATRIX = "08-concerns/08-concerns.md"
TESTING = "08-concerns/concern-testing.md"


def untimed(output):
    """Check output without its run time, which differs between two runs on a busy machine."""
    return re.sub(r" Took [0-9.]+ s\.", "", output)


def render(vault, *extra):
    return run("render", "--vault", str(vault), *extra)


def snapshot(vault):
    return {p.relative_to(vault).as_posix(): p.read_bytes() for p in vault.rglob("*.md")}


def test_render_is_a_no_op_on_a_clean_vault(mini):
    before = snapshot(mini)
    code, out = render(mini)
    assert code == 0, out
    assert "0 blocks changed" in out
    assert snapshot(mini) == before


def test_two_renders_give_identical_bytes(mini):
    edit(mini / "11-unknowns-and-risks.md", "- **Ask by:** 2026-02-01", "- **Ask by:** 2026-02-08")
    render(mini)
    first = snapshot(mini)
    render(mini)
    assert snapshot(mini) == first


def test_source_change_makes_a_block_stale_then_render_fixes_it(mini):
    edit(mini / "11-unknowns-and-risks.md", "- **Ask by:** 2026-02-01", "- **Ask by:** 2026-02-08")
    _, out = check(mini)
    assert sorted(findings(out)) == [("W402", GOALS), ("W402", "11-unknowns-and-risks.md")]
    code, out = render(mini)
    assert code == 0
    assert "01-goals.md: where-it-stands" in out
    first, second = check(mini), check(mini)
    assert first[0] == 0
    assert untimed(first[1]) == untimed(second[1])
    assert findings(check(mini)[1]) == []


def test_hand_edit_is_an_error_and_render_refuses(mini):
    edit(mini / MATRIX, "| [[stock-building-blocks\\|Stock]] | unchanged |", "| [[stock-building-blocks\\|Stock]] | addressed |")
    _, out = check(mini)
    assert findings(out) == [("E401", MATRIX)]
    before = snapshot(mini)
    code, out = render(mini)
    assert code == 1
    assert "wrote nothing" in out
    assert snapshot(mini) == before


def test_discard_edits_overwrites_and_prints_what_was_lost(mini):
    edit(mini / MATRIX, "| [[stock-building-blocks\\|Stock]] | unchanged |", "| [[stock-building-blocks\\|Stock]] | addressed |")
    code, out = render(mini, "--discard-edits")
    assert code == 0
    assert "discarded a hand edit in 'concern-matrix'" in out
    assert "| addressed |" in out
    assert findings(check(mini)[1]) == []


def test_missing_cell_renders_unexamined_no_row(mini):
    edit(mini / TESTING, "| [[stock-building-blocks\\|Stock]] | unchanged | Existing tests hold |\n", "")
    render(mini)
    assert "| [[stock-building-blocks\\|Stock]] | not reviewed yet (no line for this app) |" in (mini / MATRIX).read_text(encoding="utf-8")


def test_new_empty_block_is_filled(mini):
    edit(mini / "05-building-blocks/stock-building-blocks.md", "### CON-002 Stock level",
         "## Contracts this app consumes\n\n<!-- generated:contracts-consumed sha=00000000: do not edit, run vela render -->\n"
         "<!-- /generated:contracts-consumed -->\n\n## Contracts this app provides\n\n### CON-002 Stock level")
    _, out = check(mini)
    assert findings(out) == [("W402", "05-building-blocks/stock-building-blocks.md")]
    render(mini)
    text = (mini / "05-building-blocks/stock-building-blocks.md").read_text(encoding="utf-8")
    assert "<!-- generated:contracts-consumed sha=" in text and "\nThis app doesn't use any contract yet.\n" in text


def test_block_on_the_wrong_page(mini):
    edit(mini / "README.md", "# Mini shop vault\n", "# Mini shop vault\n\n<!-- generated:concern-matrix sha=00000000: do not edit, run vela render -->\n"
         "<!-- /generated:concern-matrix -->\n")
    _, out = check(mini)
    assert findings(out) == [("E403", "README.md")]


def test_unknown_block_name(mini):
    edit(mini / "README.md", "# Mini shop vault\n", "# Mini shop vault\n\n<!-- generated:traceability sha=00000000: do not edit, run vela render -->\n"
         "<!-- /generated:traceability -->\n")
    _, out = check(mini)
    assert findings(out) == [("E403", "README.md")]


def test_render_writes_nothing_while_a_page_cannot_parse(mini):
    edit(mini / "11-unknowns-and-risks.md", "- **Ask by:** 2026-02-01", "- **Ask by:** 2026-02-08")
    edit(mini / "README.md", "title: Mini shop vault", "title: Mini: shop vault")
    before = snapshot(mini)
    code, out = render(mini)
    assert code == 1
    assert "E102" in out
    assert snapshot(mini) == before


def test_where_it_stands_lists_open_unknowns_with_owner_and_ask_by(mini):
    text = (mini / GOALS).read_text(encoding="utf-8")
    assert "| [[11-unknowns-and-risks#UNK-001 Till test rig\\|Till test rig (UNK-001)]] | @mini-qa | 2026-02-01 | nothing yet |" in text
    assert "**Last session:** January 10, 2026" in text


def test_where_it_stands_counts_blocking_unknowns(mini):
    edit(mini / "11-unknowns-and-risks.md", "- **Opened:** 2026-01-10\n", "- **Opened:** 2026-01-10\n- **Blocks:** [[till-building-blocks|Till]]\n")
    render(mini)
    text = (mini / GOALS).read_text(encoding="utf-8")
    assert "| [[till-building-blocks\\|Till]] | named in scope | 1 | 0 | 1 of 1 |" in text


def test_render_keeps_crlf_line_endings(mini):
    path = mini / "11-unknowns-and-risks.md"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    code, out = check(mini)
    assert code == 0 and findings(out) == [], out
    path.write_bytes(path.read_bytes().replace(b"- **Ask by:** 2026-02-01", b"- **Ask by:** 2026-02-08"))
    render(mini)
    data = path.read_bytes()
    assert b"\r\n" in data and b"\n" not in data.replace(b"\r\n", b"")
    assert findings(check(mini)[1]) == []


def test_every_generated_diagram_carries_a_key_for_the_styles_it_drew():
    """The user: "don't understand why some things are highlighted, dashed, solid". A generated diagram says, under it,
    what its colors, dashes and arrows mean, for the styles it drew only."""
    import pathlib
    from vela import diagrams
    graph = diagrams.Graph((diagrams.Node("n_a", "A", "app", None, "a"), diagrams.Node("x_b", "B", "external", None, "b")),
                           (diagrams.Edge("n_a", "x_b", "CON-001"),))
    line = diagrams.key_line(graph)
    assert line.startswith("Key: ") and "outside this initiative" in line and "an arrow is a contract" in line
    assert "retired" not in line and "green" not in line  # styles not drawn are not listed
    page = (pathlib.Path(__file__).resolve().parents[1] / "examples" / "unified-booking" / "03-context-and-scope.md").read_text(encoding="utf-8")
    import re
    blocks = re.findall(r"<!-- generated:[a-z-]+ sha=\w+[^>]*-->(.*?)<!-- /generated", page, re.S)
    drawn = [b for b in blocks if "```mermaid" in b]
    assert drawn and all("\nKey: " in b for b in drawn), "every generated diagram in the shipped example has its key"
