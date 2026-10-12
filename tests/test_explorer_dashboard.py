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


# ------------------------------------------------------------ E17 and E30: links the page offers to the files

def test_e30_a_home_folder_name_in_the_path_does_not_drop_the_link(tmp_path, monkeypatch):
    from planner.explorer import build
    home = tmp_path / "home" / "work"
    vault = home / "proj" / "work" / "vault"
    vault.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    site = home / "proj" / "site"
    site.mkdir()
    assert build.relative_href(vault / "x.md", vault) == "x.md"
    assert build.relative_href(home / "proj" / "work" / "team" / "d.md", site) == "../work/team/d.md"


def test_e30_a_path_that_would_name_the_home_folder_is_still_left_out(tmp_path, monkeypatch):
    from planner.explorer import build
    home = tmp_path / "home" / "work"
    (home / "vault").mkdir(parents=True)
    elsewhere = tmp_path / "site"
    elsewhere.mkdir()
    monkeypatch.setenv("HOME", str(home))
    assert build.relative_href(home / "vault" / "x.md", elsewhere) is None


def test_e17_a_design_inside_the_vault_is_openable_when_served_and_one_outside_is_not(tmp_path):
    from planner.explorer import build
    vault = tmp_path / "vault"
    (vault / "docs" / "tech-design").mkdir(parents=True)
    inside = vault / "docs" / "tech-design" / "a.md"
    outside = tmp_path / "team" / "b.md"
    inside.write_text("x", encoding="utf-8")
    outside.parent.mkdir()
    outside.write_text("x", encoding="utf-8")
    assert build.vault_path(inside, vault) == "docs/tech-design/a.md"
    assert build.vault_path(outside, vault) == ""


# ------------------------------------------------------------ E18: the id the browser keeps a vault's marks under

def test_e18_a_vault_id_in_the_config_scopes_the_browser_state_and_survives_a_retitle(tmp_path):
    from planner.explorer import build
    old = build.vault_id("INI-001", "New initiative")
    assert build.vault_id("INI-001", "New initiative", "v-9f3c0a17d4e2b6") == "v-9f3c0a17d4e2b6"
    assert build.vault_id("INI-001", "Renamed", "v-9f3c0a17d4e2b6") == "v-9f3c0a17d4e2b6"
    assert build.vault_id("INI-001", "Renamed") != old, "without an id the old rule still applies"


def test_e18_two_vaults_with_the_same_initiative_and_title_get_different_ids_once_each_has_one(tmp_path):
    from planner.explorer import build
    ids = []
    for name, vault_id in (("a", "v-11111111111111"), ("b", "v-22222222222222")):
        copy = tmp_path / name
        shutil.copytree(HERON, copy)
        config = copy / ".planner.yaml"
        config.write_text(config.read_text(encoding="utf-8") + f"vault_id: {vault_id}\n", encoding="utf-8")
        vault = cli.load_vault(copy)
        ids.append(build.extract(vault, copy, "2026-10-12")["vaultId"])
    assert ids == ["v-11111111111111", "v-22222222222222"]


def test_e18_the_page_carries_the_old_id_so_the_browser_can_move_what_it_saved(tmp_path):
    from planner.explorer import build
    copy = tmp_path / "v"
    shutil.copytree(HERON, copy)
    before = build.extract(cli.load_vault(copy), copy, "2026-10-12")
    assert before["legacyVaultId"] == ""
    config = copy / ".planner.yaml"
    config.write_text(config.read_text(encoding="utf-8") + "vault_id: v-11111111111111\n", encoding="utf-8")
    after = build.extract(cli.load_vault(copy), copy, "2026-10-12")
    assert after["vaultId"] == "v-11111111111111" and after["legacyVaultId"] == before["vaultId"]


def test_e18_a_vault_id_that_cannot_scope_a_key_is_refused_not_ignored(tmp_path):
    import pytest

    from planner.explorer import build
    copy = tmp_path / "v"
    shutil.copytree(HERON, copy)
    config = copy / ".planner.yaml"
    config.write_text(config.read_text(encoding="utf-8") + "vault_id: 'a b:c'\n", encoding="utf-8")
    with pytest.raises(build.ExplorerError, match="vault_id"):
        build.extract(cli.load_vault(copy), copy, "2026-10-12")


def test_e18_an_owner_without_a_vault_id_is_told_to_add_one_and_the_build_edits_nothing(tmp_path):
    from conftest import run
    from sharing import commit_snapshot
    root = commit_snapshot(tmp_path)
    before = (root / ".planner.yaml").read_text(encoding="utf-8")
    code, said = run("explore", str(root), "--today", "2026-10-12")
    assert code == 0, said
    assert re.search(r"`vault_id: v-[0-9a-f]{14}`", said), said
    assert (root / ".planner.yaml").read_text(encoding="utf-8") == before, "a build must not leave an uncommitted change or make two folders differ"
    (root / ".planner.yaml").write_text(before + "vault_id: v-11111111111111\n", encoding="utf-8")
    code, said = run("explore", str(root), "--today", "2026-10-12")
    assert code == 0 and "vault_id" not in said


def test_e18_a_readers_workspace_is_never_edited_by_explore(tmp_path):
    from conftest import run
    from sharing import draft_workspace
    _, _, workspace = draft_workspace(tmp_path)
    before = (workspace / ".planner.yaml").read_text(encoding="utf-8")
    code, said = run("explore", str(workspace), "--today", "2026-10-12")
    assert code == 0, said
    assert (workspace / ".planner.yaml").read_text(encoding="utf-8") == before
