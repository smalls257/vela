import pytest

from conftest import check, edit, findings

SHOP = "05-building-blocks/shop-building-blocks.md"


@pytest.mark.parametrize("old, new, code", [
    ("---\nid: APP-shop\n", "id: APP-shop\n", "E101"),
    ("title: Shop\n", "title: Shop: the app\n", "E102"),
    ("title: Shop\n", "", "E103"),
    ("type: app-building-blocks\n", "type: app-page\n", "E104"),
    ("authored: mixed\n", "authored: by hand\n", "E105"),
    ("change: new\n", "change: brand-new\n", "E105"),
    ('owner: "@mini/shop-team"\n', "owner: Shop team\n", "E105"),
    ("initiative: INI-900\n", "initiative: INI-901\n", "E105"),
    ("id: APP-shop\n", "id: APP-Shop\n", "E107"),
    ("id: APP-shop\n", "id: APP-shops\n", "E107"),
])
def test_app_page_frontmatter(mini, old, new, code):
    edit(mini / SHOP, old, new)
    exit_code, out = check(mini)
    assert exit_code == 1
    assert {c for c, _ in findings(out) if _ == SHOP} == {code}, out


def test_session_mode_and_date(mini):
    path = mini / "sessions" / "2026-01-05-till-needs.md"
    edit(path, "modes: [requirements]", "modes: [requirements, chat]")
    edit(path, "date: 2026-01-05", "date: 2026-01-04")
    _, out = check(mini)
    assert sorted(findings(out)) == [("E105", "sessions/2026-01-05-till-needs.md"), ("E107", "sessions/2026-01-05-till-needs.md")]


def test_handed_off_format(mini):
    edit(mini / SHOP, "stage: contracts\n", "stage: contracts\nhanded_off: Shop senior\n")
    _, out = check(mini)
    assert findings(out) == [("E105", SHOP)]


def test_list_field_must_be_a_list(mini):
    edit(mini / "01-goals.md", 'sources: ["2026-01-10-shop-api"]', "sources: 2026-01-10-shop-api")
    _, out = check(mini)
    assert findings(out) == [("E105", "01-goals.md")]


def test_duplicate_page_id(mini):
    edit(mini / "06-runtime" / "flows" / "FLO-001-buy.md", "id: FLO-001\n", "id: FLO-002\n")
    _, out = check(mini)
    assert findings(out) == [("E107", "06-runtime/flows/FLO-001-buy.md")]


def test_two_pages_with_one_id(mini):
    (mini / "06-runtime" / "flows" / "FLO-001-buy-again.md").write_text(
        (mini / "06-runtime" / "flows" / "FLO-001-buy.md").read_text(encoding="utf-8"), encoding="utf-8")
    _, out = check(mini)
    assert findings(out) == [("E108", "06-runtime/flows/FLO-001-buy-again.md")]


def test_unquoted_handle_says_to_quote_it(mini):
    edit(mini / SHOP, 'owner: "@mini/shop-team"\n', "owner: @mini/shop-team\n")
    _, out = check(mini)
    assert {c for c, p in findings(out) if p == SHOP} == {"E102"}
    assert "starts with @" in out
