"""Pending approval: a reader's decision stays `decided` but carries a marker, check lists the markers in one
warning and never an error, a malformed marker is E322, and the library reads the markers back for later tools."""
import re

from conftest import check, edit, findings, run

STOCK = "05-building-blocks/stock-building-blocks.md"
SHOP = "05-building-blocks/shop-building-blocks.md"
MARK = "- **Pending approval:** @sam, 2026-10-18\n"
SOURCE = "- **Source:** SRC-01\n"


def mark_stock_contract(mini, line=MARK):
    edit(mini / STOCK, SOURCE, SOURCE + line)


def test_one_marker_gives_one_warning_naming_the_item_and_exits_0(mini):
    mark_stock_contract(mini)
    code, out = check(mini)
    assert code == 0
    assert findings(out) == [("W327", STOCK)]
    assert "1 item pending approval: CON-002 (@sam, 2026-10-18)." in out


def test_several_markers_are_one_warning_listing_each(mini):
    mark_stock_contract(mini)
    page = mini / SHOP
    page.write_text(page.read_text(encoding="utf-8").rstrip("\n") + "\n\n## History\n\n- **Pending approval:** @ana, 2026-10-19\n",
                    encoding="utf-8")
    code, out = check(mini)
    assert code == 0
    assert [c for c, _ in findings(out)] == ["W327"]
    assert "2 items pending approval: APP-shop (@ana, 2026-10-19); CON-002 (@sam, 2026-10-18)." in out


def test_a_marker_under_history_belongs_to_its_item(mini):
    page = mini / STOCK
    page.write_text(page.read_text(encoding="utf-8").rstrip("\n") + "\n\n## History\n\n#### CON-002\n\n" + MARK, encoding="utf-8")
    code, out = check(mini)
    assert code == 0 and "CON-002 (@sam, 2026-10-18)" in out


def test_no_marker_no_warning(mini):
    code, out = check(mini)
    assert "W327" not in out and "E322" not in out


def test_a_marker_with_no_handle_is_e322(mini):
    mark_stock_contract(mini, "- **Pending approval:** 2026-10-18\n")
    code, out = check(mini)
    assert code == 1
    assert findings(out) == [("E322", STOCK)]
    assert "names no @handle first" in out


def test_a_marker_with_an_impossible_date_is_e322(mini):
    mark_stock_contract(mini, "- **Pending approval:** @sam, 2026-13-45\n")
    code, out = check(mini)
    assert code == 1 and "not a real date" in out


def test_a_marker_with_no_date_is_e322(mini):
    mark_stock_contract(mini, "- **Pending approval:** @sam\n")
    code, out = check(mini)
    assert code == 1 and "has no ', YYYY-MM-DD' date" in out


def test_a_typo_in_the_label_is_e322_not_prose(mini):
    mark_stock_contract(mini, "- **Pending aproval:** @sam, 2026-10-18\n")
    code, out = check(mini)
    assert code == 1 and findings(out) == [("E322", STOCK)]
    assert "looks like **Pending approval:**" in out


def test_the_item_stays_decided_state_is_not_touched(mini):
    mark_stock_contract(mini)
    assert "- **State:** fact\n" in (mini / STOCK).read_text(encoding="utf-8")


def test_the_library_reads_the_markers_for_later_phases(mini):
    from planner import cli, pending
    mark_stock_contract(mini)
    vault = cli.load_vault(mini)
    [one] = pending.items(vault)
    assert (one.item, one.by, one.date, one.path) == ("CON-002", "@sam", "2026-10-18", STOCK)
    page = next(p for p in vault.pages if p.path == STOCK)
    assert pending.pending_for(page, "CON-002").by == "@sam"
    assert pending.pending_for(page, "") is None
    assert one.as_dict()["subject"] == "CON-002"


def test_malformed_markers_are_not_items(mini):
    from planner import cli, pending
    mark_stock_contract(mini, "- **Pending approval:** nobody\n")
    vault = cli.load_vault(mini)
    assert pending.items(vault) == []
    [bad] = pending.all_bullets(vault)
    assert bad.problem and bad.as_dict()["malformed"] is True


def test_check_header_counts_the_warning(mini):
    mark_stock_contract(mini)
    _, out = run("check", "--vault", str(mini), "--today", "2026-01-15")
    assert re.search(r"0 errors, \d+ warnings", out)
