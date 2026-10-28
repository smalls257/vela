"""The grills waiting list (vela/grills.py): which items a Grill could run on, in which group, and who runs each.

The Violation these tests guard is a Distributed Monolith between the gate, the lead's kept yes and the owner: a
dashboard that asked each in its own way would list a grill the gate refuses or lose a yes the lead gave.
"""
from pathlib import Path

import yaml

from conftest import edit
from grills_vault import TODAY, make
from vela import cli, gates, grillowners, grills, say


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
    assert found["CON-011"].group == grills.READY, "an open question under it is noted when it is settled, not a wait"
    assert found["CON-012"].group == grills.ONE_AWAY, "no options are asked for a contract, so only its case table is missing"
    assert found["CON-012"].missing["rule"] == "case table"
    assert [g.group for g in found.values()] == sorted((g.group for g in found.values()), key=grills.GROUPS.index)


def test_a_kept_yes_carries_the_date_and_the_session_but_not_the_words(tmp_path):
    _, found = load(tmp_path)
    assert found["CON-013"].yes == {"session": "2026-01-12-shape-extras", "date": "2026-01-12", "title": "Shape: the shop's extras"}
    assert found["CON-013"].since == {"date": "2026-01-12", "session": "2026-01-12-shape-extras",
                                      "title": "Shape: the shop's extras", "kept": True}
    assert found["CON-010"].yes == {}


def test_an_item_with_an_open_question_is_ready_and_missing_nothing(tmp_path):
    vault, found = load(tmp_path)
    assert found["CON-011"].missing == {} and found["CON-010"].missing == {}
    assert gates.verdict(vault, None, "CON-011", TODAY).open_blockers
    asked = found["CON-011"].open_question
    assert asked["owed_by"] == ["@mini-qa"] and asked["due"] == "2026-02-01" and "test till" in asked["question"]
    assert found["CON-010"].open_question == {}


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


# ------------------------------------------------------------------ what settling agrees to (the Heron plan)

HERON = Path(__file__).parent / "fixtures" / "team-skills" / "heron-plan"


def heron_agrees(ident):
    vault = cli.load_vault(HERON)
    return grills.agrees(vault, ident, say.Resolver(vault))


def test_a_requirement_agrees_to_its_statement_and_its_first_two_details_and_counts_the_rest():
    found = heron_agrees("CAP-001.FR1")
    assert found["lead"].startswith("Where a meeting has a Teams transcript that Heron is allowed to read, Heron reads it")
    assert found["lead"].endswith("when a note is thin for that reason.")
    assert found["details"] == ["Heron reads a transcript only if the organizer turned transcripts on and the tenant administrators have approved reading them.",
                                "Heron reads a transcript only for a person who was in that meeting and has switched Heron on, and stops reading once they withdraw."]
    assert len(found["more"]) == 3 and found["more"][-1] == "Heron reads no transcript of a meeting the person was not in."
    assert "Trace" not in " ".join(found["details"] + found["more"]), "a nested Trace line is not a detail"
    assert found["page"] is False and "picked" not in found


def test_a_page_agrees_to_its_opening_and_the_it_does_not_sentences_it_states():
    found = heron_agrees("APP-desktop-agent")
    assert found["lead"].startswith("The Desktop agent runs on a person's own laptop.") and found["lead"].count(". ") <= 2
    assert found["points"][0] == "It does not write the digest or the prep note: the Summarizer does."
    assert all(p.startswith("It does not") for p in found["points"]) and found["page"] is True
    assert "[[" not in found["lead"] + " ".join(found["points"]), "links read as names"


def test_an_option_picked_says_how_many_others_were_set_aside_and_no_pick_lists_the_choice():
    found = heron_agrees("APP-summarizer")
    assert found["picked"] == "Three apps" and found["setAside"] >= 1 and "choosing" not in found
    assert grills._agrees_option_line(["A: rejected, no", "B: rejected, no"]) == {"choosing": ["A", "B"]}
    assert grills._agrees_option_line(["Only one"]) == {}


def test_a_contract_agrees_to_its_description_and_what_crosses_the_boundary():
    found = heron_agrees("CON-001")
    assert found["lead"].startswith("The Desktop agent reads the signed-in person's calendar entries")
    assert found["points"][0].startswith("Crosses the boundary: In: the agent's read request")
    assert found["details"] == [] and found["more"] == []


# ------------------------------------------------------------------ reading the plan's words honestly

class _Page:
    def __init__(self, text):
        self.text = text

    def page_bullets(self, label):
        return []


def agrees_of_text(monkeypatch, text):
    monkeypatch.setattr(grills, "_unit", lambda vault, ident: (None, _Page(text)))

    class Plain:
        plain = staticmethod(lambda s: s)
    return grills.agrees(None, "APP-x", Plain())


def test_it_does_not_lines_written_as_bullets_after_the_opening_are_found(monkeypatch):
    found = agrees_of_text(monkeypatch, "# Till\n\nThe till takes payment in the shop.\n\n"
                           "- It does not keep stock.\n- It doesn't send receipts: the shop does.\n- It is quick.\n\n## Later\n\n- It does not belong here.\n")
    assert found["lead"] == "The till takes payment in the shop."
    assert found["points"] == ["It does not keep stock.", "It doesn't send receipts: the shop does."]


def test_it_does_not_sentences_in_the_opening_paragraph_are_still_found(monkeypatch):
    found = agrees_of_text(monkeypatch, "# Till\n\nThe till takes payment. It prints a slip. It opens the drawer. It does not keep stock.\n")
    assert found["points"] == ["It does not keep stock."]


def test_a_sentence_is_not_cut_after_an_abbreviation():
    kept_whole = ("Pay by card, e.g. Visa, or cash.", "Ask Dr. Reyes about it.", "Mr. Lee runs the U.S. branch.", "Open at 9 a.m. Shut at 5 p.m. daily.",
                  "It is cheaper vs. the old till.", "That is, i.e. The Till, the one by the door.")
    for text in kept_whole:
        assert grills._sentences(text) == [text]
    assert grills._sentences("Ask Dr. Reyes about it. Then go.") == ["Ask Dr. Reyes about it.", "Then go."]
    assert grills._sentences("Stop. Go.") == ["Stop.", "Go."]
