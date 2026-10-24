"""The page index: names, states, blockers and flow steps per page, re-parsed only where a page changed."""
import json
import os
import shutil

from conftest import REPO
from vela import pageindex
from vela.edge import companionstore

EXAMPLE = REPO / "examples" / "unified-booking"


def copy(tmp_path):
    root = tmp_path / "plan"
    shutil.copytree(EXAMPLE, root)
    return root


def test_an_item_is_named_as_the_plan_names_it(tmp_path):
    index = companionstore.page_index(copy(tmp_path))
    names = pageindex.names(index)
    assert names["CON-007"].name == "Tidepay payment outcome"
    assert names["CON-007"].page == "05-building-blocks/booking-building-blocks.md"
    assert (names["FLO-001"].name, names["FLO-001"].state) == ("Hold, pay, confirm", "decided")
    assert names["UNK-008"].state == "open"


def test_a_flow_keeps_its_numbered_steps(tmp_path):
    index = companionstore.page_index(copy(tmp_path))
    steps = index["pages"]["06-runtime/flows/FLO-001-hold-pay-confirm.md"]["steps"]
    assert [s["n"] for s in steps][:3] == [1, 2, 3] and "Hold a seat" in steps[1]["text"]


def test_who_holds_a_question_is_the_dashboards_rule():
    from vela import askwho
    from vela.explorer import asks_data
    assert asks_data.who_to_ask is askwho.who_to_ask


def test_only_changed_pages_are_parsed_again(tmp_path, monkeypatch):
    root = copy(tmp_path)
    companionstore.page_index(root)
    parsed = []
    real = pageindex.entries
    monkeypatch.setattr(pageindex, "entries", lambda path, text: parsed.append(path) or real(path, text))
    page = root / "11-unknowns-and-risks.md"
    page.write_text(page.read_text(encoding="utf-8").replace("## Risks", "### UNK-009 Tidepay outcome wording\n\n"
                    "- **Question:** What does Tidepay call a payment it is still checking?\n"
                    "- **Owner:** @hl-booking-senior (Booking senior)\n- **Opened:** 2026-10-24 Grill\n"
                    "- **State:** open\n- **Blocks:** [[booking-building-blocks#CON-007 Tidepay payment outcome|CON-007]]\n\n"
                    "## Risks", 1), encoding="utf-8")
    index = companionstore.page_index(root)
    assert parsed == ["11-unknowns-and-risks.md"]
    assert pageindex.blocking(index, "CON-007") == ["UNK-009"]
    assert pageindex.who(index, "UNK-009") == "Booking senior"


def test_a_deleted_page_leaves_the_index(tmp_path):
    root = copy(tmp_path)
    companionstore.page_index(root)
    os.remove(root / "06-runtime/flows/FLO-003-notify-on-change.md")
    assert "FLO-003" not in pageindex.names(companionstore.page_index(root))


def test_a_broken_index_is_rebuilt_and_says_so(tmp_path):
    root = copy(tmp_path)
    (root / ".vela" / "companion").mkdir(parents=True, exist_ok=True)
    (root / ".vela" / "companion" / "pages.json").write_text("{not json", encoding="utf-8")
    index = companionstore.page_index(root)
    assert index["rebuilt"] and pageindex.names(index)["FLO-001"].name == "Hold, pay, confirm"
    assert json.loads((root / ".vela" / "companion" / "pages.json").read_text(encoding="utf-8"))["version"] == 1
