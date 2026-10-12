"""Fixes to the explorer dashboard found in the 2026-10-12 platform review (docs/research/2026-10-12-platform-review.md).
Each test names the ledger ID it guards."""
import pathlib
import re
import shutil

from planner import cli
from planner.explorer import asks_data
from planner.explorer.pages_data import HEADING as PAGE_HEADING
from planner.explorer.record import Keys, inline_html
from planner.search import HEADING as SEARCH_HEADING
from test_reading_load import HERON


def shown(text):
    vault = cli.load_vault(HERON)
    return inline_html(text, Keys(vault), vault.page("EPC-001-calendar"))


def test_e21_asterisks_inside_code_spans_stay_literal_and_do_not_italicise_what_follows():
    out = shown("Run `*.md` and `*.py` checks, and *really* mean it")
    assert "<code>*.md</code>" in out and "<code>*.py</code>" in out
    assert out.count("<em>") == 1 and "<em>really</em>" in out
    assert "<em>" not in re.sub(r"<em>really</em>", "", out)


def test_e21_a_double_star_glob_in_code_is_not_bold():
    out = shown("Match `**/x` and `**/y`")
    assert "<strong>" not in out and "<code>**/x</code>" in out


def test_e36_a_markdown_link_keeps_its_web_address_and_opens_in_a_new_tab():
    out = shown("See [API spec](https://developer.example.com/openapi.yaml) and [mail us](mailto:a@example.com)")
    assert '<a class="ext" href="https://developer.example.com/openapi.yaml" target="_blank" rel="noopener noreferrer">API spec</a>' in out
    assert 'href="mailto:a@example.com"' in out


def test_e36_a_link_that_is_not_http_or_mailto_shows_its_label_only_and_cannot_carry_markup():
    out = shown('[click](javascript:alert(1)) and [x](https://e.com/"onclick="y)')
    assert "javascript" not in out and 'onclick="y' not in out and "click" in out


def test_e41_a_heading_that_ends_in_a_hash_keeps_it_in_the_reader_and_in_search():
    for pattern in (PAGE_HEADING, SEARCH_HEADING):
        assert pattern.match("## Port to C#").group(2) == "Port to C#"
        assert pattern.match("### CON-004 Wallet#").group(2) == "CON-004 Wallet#"
        assert pattern.match("## Title ##").group(2) == "Title"
        assert pattern.match("## Title #").group(2) == "Title"


def test_e20_an_ask_by_that_is_not_a_whole_date_is_not_sent_as_a_date(tmp_path):
    vault_dir = tmp_path / "vault"
    shutil.copytree(HERON, vault_dir)
    page = vault_dir / "11-unknowns-and-risks.md"
    lines = page.read_text(encoding="utf-8").split("\n")
    targets = [i for i, line in enumerate(lines) if line.startswith("- **Ask by:** 2026-10-18")][:2]
    lines[targets[0]] = '- **Ask by:** "><b>x</b>'
    lines[targets[1]] = "- **Ask by:** 2026-10-18 (maybe)"
    page.write_text("\n".join(lines), encoding="utf-8")
    vault = cli.load_vault(vault_dir)
    asks = asks_data.asks(vault, Keys(vault), "2026-10-12")
    odd = [a for a in asks if a["askByRaw"]]
    assert {a["askByRaw"] for a in odd} == {'"><b>x</b>', "2026-10-18 (maybe)"}
    assert all(a["askBy"] == "" for a in odd), "a value that is not a whole date must not be sent as one"
    assert any(re.fullmatch(r"\d{4}-\d{2}-\d{2}", a["askBy"]) for a in asks), "a whole date still goes through"


def test_e20_every_date_the_board_draws_goes_through_esc():
    source = (pathlib.Path(__file__).resolve().parent.parent / "plugin/lib/planner/explorer/assets/js/view-asks.js").read_text(encoding="utf-8")
    bare = [m.group(0) for m in re.finditer(r"\$\{day\([^}]*\)\}", source)]
    assert not bare, f"day() output goes into a template without esc(): {bare}"
