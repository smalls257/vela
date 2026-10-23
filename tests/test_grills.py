"""The grills waiting list (vela/grills.py): which items a Grill could run on, in which group, and who runs each.

The Violation these tests guard is a Distributed Monolith between the gate, the lead's kept yes and the owner: a
dashboard that asked each in its own way would list a grill the gate refuses or lose a yes the lead gave.
"""
import yaml

from conftest import edit
from grills_vault import TODAY, make
from vela import cli, gates, grillowners, grills


def load(tmp_path, config_extra=None):
    root = make(tmp_path)
    if config_extra:
        edit(root / ".vela.yaml", "title: Mini shop\n", "title: Mini shop\n" + config_extra)
    vault = cli.load_vault(root)
    verdicts = {i: gates.verdict(vault, None, i, TODAY) for i in grills.judged_ids(vault)}
    return vault, {g.id: g for g in grills.waiting(vault, verdicts, TODAY)}


def test_each_group_holds_the_right_item_and_two_things_away_is_left_out(tmp_path):
    _, found = load(tmp_path)
    assert found["CON-013"].group == grills.SAID_YES
    assert found["CON-010"].group == grills.READY
    assert found["CON-011"].group == grills.ONE_AWAY
    assert "CON-012" not in found  # no options and no case table: two things away is the plan, not a queue
    assert [g.group for g in found.values()] == sorted((g.group for g in found.values()), key=grills.GROUPS.index)


def test_a_kept_yes_carries_the_date_and_the_session_but_not_the_words(tmp_path):
    _, found = load(tmp_path)
    assert found["CON-013"].yes == {"session": "2026-01-12-shape-extras", "date": "2026-01-12", "title": "Shape: the shop's extras"}
    assert found["CON-013"].since == {"date": "2026-01-12", "session": "2026-01-12-shape-extras",
                                      "title": "Shape: the shop's extras", "kept": True}
    assert found["CON-010"].yes == {}


def test_the_one_missing_thing_says_who_owes_it_and_by_when(tmp_path):
    _, found = load(tmp_path)
    missing = found["CON-011"].missing
    assert missing["rule"] == "GATE-4"
    assert missing["owed_by"] == ["@mini-qa"] and missing["due"] == "2026-02-01"
    assert "test till" in missing["plain"]
    assert found["CON-010"].missing == {}


def test_the_owner_is_the_items_own_unless_a_grill_owner_is_set(tmp_path):
    _, found = load(tmp_path)
    assert found["CON-010"].owner == ("@mini/shop-team",) and not found["CON-010"].owner_set
    _, found = load(tmp_path / "again", 'grills:\n  "CON-010":\n    owner: "@mini-lead"\n    join: ["@mini-qa"]\n')
    assert found["CON-010"].owner == ("@mini-lead",) and found["CON-010"].owner_set
    assert found["CON-010"].join == ("@mini-qa",)
    assert found["CON-011"].owner == ("@mini/shop-team",)  # a grill owner on one item moves no other


def test_what_it_settles_is_the_options_on_the_table(tmp_path):
    _, found = load(tmp_path)
    assert found["CON-010"].settles == ("Keep it in the shop (picked)", "receipt delivery in the till: rejected, the shop has the data")


def test_what_it_holds_up_is_the_epics_on_its_app_and_the_apps_it_sits_on(tmp_path):
    _, found = load(tmp_path)
    assert found["CON-010"].holds_up == ("EPC-001",)
    assert found["CON-010"].apps == ("APP-shop", "APP-till")  # the app that provides it, then the one that consumes it


def test_an_item_the_lead_said_yes_to_and_has_since_decided_is_not_waiting(tmp_path):
    root = make(tmp_path)
    edit(root / "05-building-blocks" / "shop-building-blocks.md", "- **State:** assumption\n- **Options considered:** Keep it in the shop (picked); loyalty points in the till",
         "- **State:** decided\n- **Options considered:** Keep it in the shop (picked); loyalty points in the till")
    vault = cli.load_vault(root)
    assert "CON-013" not in {m["id"] for m in grills.yes_marks(vault)}


def test_an_owner_entry_that_cannot_be_read_is_named_and_left_out(tmp_path):
    config = yaml.safe_load('grills:\n  "CON-010":\n    owner: "not a handle"\n  "CON-011":\n    owner: "@ok"\n    color: red\n')
    found, problems = grillowners.read(config)
    assert found == {} and len(problems) == 2
    assert "CON-010" in problems[0] and "not a handle" in problems[0]
    assert "CON-011" in problems[1]
