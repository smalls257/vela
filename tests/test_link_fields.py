"""`links:` on a page, **Links:** on an item, `icon:` on an app page, and .planner.yaml's link_templates.
Planner reads and checks them and never fetches one (links.py)."""
import pytest

from conftest import check, edit, findings
from planner import cli, links

STOCK = "05-building-blocks/stock-building-blocks.md"
FRONT = "sources: [SRC-01]\n---"
POLICY = "- **Change policy:** the existing read API, no change.\n"


def test_a_clean_vault_with_links_and_an_icon_passes(mini):
    edit(mini / STOCK, FRONT, "sources: [SRC-01]\nicon: catalogue\nlinks: {GitHub: \"https://github.example.com/mini/stock\", "
                              "Jira: STOCK-4}\n---")
    edit(mini / STOCK, POLICY, POLICY + "- **Links:** [API spec](https://docs.example.com/stock/openapi.yaml), "
                                        "[Docs](https://docs.example.com/stock)\n")
    (mini / ".planner.yaml").write_text("initiative: INI-900\ntitle: Mini shop\n"
                                        "link_templates: {Jira: \"https://jira.example.com/browse/{key}\"}\n", encoding="utf-8")
    code, out = check(mini)
    assert code == 0, out
    vault = cli.load_vault(mini)
    page = next(p for p in vault.pages if p.path == STOCK)
    assert links.of_page(page, vault.config) == ([links.Link("GitHub", "https://github.example.com/mini/stock"),
                                                  links.Link("Jira", "https://jira.example.com/browse/STOCK-4")], [])
    assert links.of_item(vault.item("CON-002")) == ([links.Link("API spec", "https://docs.example.com/stock/openapi.yaml"),
                                                    links.Link("Docs", "https://docs.example.com/stock")], [])


@pytest.mark.parametrize("front", [
    "links: https://github.example.com/mini/stock",          # not a map
    "links: {GitHub: github.example.com/mini/stock}",       # no scheme, and no template for GitHub
    "links: {Jira: \"javascript:alert(1)\"}",                # not http(s)
    "links: {Jira: STOCK-4}",                                # a key, but no link_templates entry
    "icon: Payments Card",                                   # not one short lower-case word
])
def test_unreadable_links_and_icons_are_e105(mini, front):
    edit(mini / STOCK, FRONT, f"sources: [SRC-01]\n{front}\n---")
    code, out = check(mini)
    assert code == 1 and findings(out) == [("E105", STOCK)], out


def test_an_item_links_bullet_needs_markdown_http_links(mini):
    edit(mini / STOCK, POLICY, POLICY + "- **Links:** see the spec on the wiki, [Old](ftp://files.example.com/x)\n")
    _, out = check(mini)
    assert findings(out) == [("E105", STOCK)] and "CON-002's link 'Old' is not an http(s) or file:// URL" in out, out


def test_a_bad_template_is_reported_where_links_are_used(mini):
    (mini / ".planner.yaml").write_text("initiative: INI-900\ntitle: Mini shop\nlink_templates: {Jira: \"https://jira.example.com/browse\"}\n",
                                        encoding="utf-8")
    assert findings(check(mini)[1]) == []  # nobody uses it, so nothing breaks
    edit(mini / STOCK, FRONT, "sources: [SRC-01]\nlinks: {Jira: STOCK-4}\n---")
    _, out = check(mini)
    assert "link_templates Jira is not an http(s) URL with {key}" in out and set(findings(out)) == {("E105", STOCK)}, out
