from conftest import check, edit, findings

SHOP = "05-building-blocks/shop-building-blocks.md"
UNK = "11-unknowns-and-risks.md"


def test_missing_page(mini):
    edit(mini / "README.md", "[[01-goals|Goals]]", "[[01-gaols|Goals]]")
    _, out = check(mini)
    assert findings(out) == [("E201", "README.md")]


def test_anchor_must_equal_the_full_heading(mini):
    edit(mini / UNK, "[[shop-building-blocks#CON-001 Sale API|CON-001]]", "[[shop-building-blocks#CON-001|CON-001]]")
    _, out = check(mini)
    assert findings(out) == [("E202", UNK)]
    assert "Use [[shop-building-blocks#CON-001 Sale API]]." in out


def test_anchor_to_a_missing_heading(mini):
    edit(mini / UNK, "[[shop-building-blocks#CON-001 Sale API|CON-001]]", "[[shop-building-blocks#CON-009 Refunds|CON-009]]")
    _, out = check(mini)
    assert findings(out) == [("E202", UNK)]


def test_block_reference_must_exist(mini):
    path = mini / "sessions" / "2026-01-10-shop-api.md"
    edit(path, "[[2026-01-10-shop-api#^c01]]", "[[2026-01-10-shop-api#^c02]]")
    _, out = check(mini)
    assert findings(out) == [("E202", "sessions/2026-01-10-shop-api.md")]


def test_same_page_anchor(mini):
    edit(mini / UNK, "- **Mitigation:** keep the old till for a month.",
         "- **Mitigation:** keep the old till for a month. See [[#UNK-001 Till rig|UNK-001]].")
    _, out = check(mini)
    assert findings(out) == [("E202", UNK)]


def test_links_in_code_are_ignored(mini):
    edit(mini / "README.md", "Start at", "Write `[[no-such-page]]` to link. Start at")
    code, out = check(mini)
    assert code == 0, out


def test_links_to_conventions_are_allowed(mini):
    (mini / "CONVENTIONS.md").write_text("# Conventions\n", encoding="utf-8")
    edit(mini / "README.md", "Start at", "Read [[CONVENTIONS]]. Start at")
    code, out = check(mini)
    assert code == 0, out


def test_duplicate_basename_in_another_folder(mini):
    (mini / "06-runtime" / "README.md").write_text("---\nid: readme-2\ntype: index\ntitle: Again\nauthored: authored\n---\n# Again\n", encoding="utf-8")
    _, out = check(mini)
    assert findings(out) == [("E204", "06-runtime/README.md")] or findings(out) == [("E204", "README.md")]


def test_basenames_clash_ignoring_case(mini):
    (mini / "06-runtime" / "readme.md").write_text("---\nid: readme-2\ntype: index\ntitle: Again\nauthored: authored\n---\n# Again\n", encoding="utf-8")
    _, out = check(mini)
    assert [c for c, _ in findings(out)] == ["E204"]


def test_epic_list_ids_must_exist(mini):
    (mini / "EPC-001-sell.md").write_text(
        "---\nid: EPC-001\ntype: epic\ntitle: Sell\nstate: draft\nowner: \"@mini/shop-team\"\nauthored: authored\n"
        "apps: [APP-shop]\ndelivers: [CON-001, CAP-404]\n---\n# EPC-001 Sell\n", encoding="utf-8")
    _, out = check(mini)
    assert ("E207", "EPC-001-sell.md") in findings(out)
    assert "CAP-404" in out


def test_source_ids_must_be_in_the_register(mini):
    edit(mini / "05-building-blocks/stock-building-blocks.md", "- **Source:** SRC-01", "- **Source:** SRC-02")
    _, out = check(mini)
    assert findings(out) == [("E207", "05-building-blocks/stock-building-blocks.md")]


def test_link_with_a_path_or_md_suffix_gets_a_basename_hint(mini):
    edit(mini / "README.md", "[[01-goals|Goals]]", "[[05-building-blocks/shop-building-blocks.md|Goals]]")
    _, out = check(mini)
    assert findings(out) == [("E201", "README.md")]
    assert "Link by basename alone: [[shop-building-blocks]]." in out


def test_malformed_epic_list_values_become_findings(mini):
    (mini / "EPC-001-sell.md").write_text(
        "---\nid: EPC-001\ntype: epic\ntitle: Sell\nstate: draft\nowner: \"@mini/shop-team\"\nauthored: authored\n"
        "apps: [[APP-shop], {a: b}]\ndelivers: oops\n---\n# EPC-001 Sell\n", encoding="utf-8")
    code, out = check(mini)
    assert code != 2, out
    assert ("E207", "EPC-001-sell.md") in findings(out)
