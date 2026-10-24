"""The data the dashboard's Waiting for a decision view draws (explorer/grills_data.py): one row per grill, every ID a key the page knows.

    python3 -m pytest -q tests/test_explorer_grills.py

The Violation these guard against is a Leaky Narrative on the page: that an epic's key is its page ID, that a source is
a Library row, that a grill owner lives in `.vela.yaml` are decided here and in vela/grills.py, so they are tested
against a vault, not discovered in script. The browser side is test_explorer_grills_browser.py.
"""
import re

from grills_vault import TODAY, booking_grills
from vela import cli
from vela.explorer import build

IDLIKE = re.compile(r"\b(?:UNK|CAP|CON|EPC|APP|RUN|FLO|SLC|ADR|SRC)-\d|\^c\d")


def extract(tmp_path):
    root = booking_grills(tmp_path)
    data = build.extract(cli.load_vault(root), root, TODAY)
    return data, {r["id"]: r for r in data["grills"]["rows"]}


def test_every_waiting_grill_is_a_row_in_its_groups_order(tmp_path):
    data, rows = extract(tmp_path)
    assert [(r["id"], r["group"]) for r in data["grills"]["rows"]] == [
        ("CON-003", "said-yes"), ("CON-001", "ready"), ("EPC-039", "ready"), ("CON-002", "one-away")]


def test_rows_name_things_by_the_keys_the_page_uses(tmp_path):
    data, rows = extract(tmp_path)
    assert all(rows[i]["key"] in data["entities"] for i in rows)
    assert rows["CON-001"]["holdsUp"][0] == "EPC-031" and all(k in data["entities"] for k in rows["CON-001"]["holdsUp"])
    assert rows["CON-001"]["apps"] == ["APP-booking", "APP-website", "APP-call-center", "APP-kiosks"]  # the app that provides it, then those that call it
    assert rows["CON-001"]["sources"] == ["lib:SRC-01"] and rows["CON-002"]["sources"] == []  # a source is the Library row the page opens
    assert rows["EPC-039"]["holdsUp"] == []  # nothing waits on an epic


def test_the_people_are_those_the_rows_name_and_none_is_guessed(tmp_path):
    data, rows = extract(tmp_path)
    assert data["grills"]["people"] == ["@harborline/booking-team", "@hl-booking-senior", "@hl-solution-lead"]
    assert rows["CON-001"]["owner"] == ["@hl-solution-lead"] and rows["CON-001"]["ownerSet"] is True
    assert rows["CON-001"]["join"] == ["@hl-booking-senior"]
    assert rows["EPC-039"]["owner"] == ["@harborline/booking-team"] and rows["EPC-039"]["ownerSet"] is False
    assert data["grills"]["problems"] == []


def test_the_date_of_the_yes_but_not_its_words_and_the_one_missing_thing_ride_with_their_rows(tmp_path):
    _, rows = extract(tmp_path)
    assert rows["CON-003"]["yes"] == {"date": "2026-10-20"}
    away = rows["CON-002"]["missing"]
    assert away["due"] == "2027-03-01" and away["owed_by"] == ["@hl-platform-lead"] and "finance reconciliation" in away["question"]
    assert not IDLIKE.search(away["plain"] + away["fix"] + away["question"] + " ".join(rows["CON-002"]["settles"]))


def test_an_owner_entry_the_page_cannot_read_is_carried_as_a_problem(tmp_path):
    root = booking_grills(tmp_path)
    with open(root / ".vela.yaml", "a", encoding="utf-8") as config:
        config.write('  "CON-009":\n    owner: "not a handle"\n')
    data = build.extract(cli.load_vault(root), root, TODAY)
    assert len(data["grills"]["problems"]) == 1 and "CON-009" in data["grills"]["problems"][0]
    assert "CON-009" not in {r["id"] for r in data["grills"]["rows"]}


def test_a_vault_with_nothing_waiting_has_an_empty_list(tmp_path):
    import shutil
    from conftest import REPO
    root = tmp_path / "decided"
    shutil.copytree(REPO / "examples" / "unified-booking", root)
    data = build.extract(cli.load_vault(root), root, TODAY)
    assert data["grills"] == {"rows": [], "people": [], "problems": []}
