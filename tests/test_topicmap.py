"""The running topic map's core (`vela/topicmap.py`): kinds from the catalog, the roster and its positions, waiting items,
and the timing `moves` holds. Pure, so none of these needs a vault, a clock or git."""
import pytest

from conftest import REPO
from vela import catalog, say, topicmap

SEED = REPO / "plugin" / "catalog" / "questions.yaml"


@pytest.fixture(scope="module")
def kinds():
    return catalog.parse_catalog(catalog.load_yaml(SEED.read_text(encoding="utf-8"))).kinds


def fresh():
    return topicmap.new_state("2026-10-16-demo")


def test_the_catalog_kinds_are_generic_and_hold_every_focus_area(kinds):
    cat = catalog.parse_catalog(catalog.load_yaml(SEED.read_text(encoding="utf-8")))
    assert cat.kind_names == ("goals", "people", "systems", "data", "rules", "dates", "money", "risks", "owners")
    held = {code for k in cat.kinds for code in k.areas}
    assert held == set(cat.area_codes)
    for k in cat.kinds:  # near reads both ways, so the map never strands a kind
        assert all(k.name in cat.kind(other).near for other in k.near), k.name


def test_an_area_no_kind_holds_is_a_catalog_error():
    data = catalog.load_yaml(SEED.read_text(encoding="utf-8"))
    data["kinds"]["money"]["areas"] = []
    with pytest.raises(catalog.CatalogError, match="area FIN sits under no kind"):
        catalog.parse_catalog(data)
    data["kinds"]["money"]["near"] = ["money", "cash"]
    with pytest.raises(catalog.CatalogError, match="'cash'"):
        catalog.parse_catalog(data)


def test_next_points_at_the_emptiest_kind_near_the_last_topic(kinds):
    state = fresh()
    topicmap.add_note(state, kinds, "goals", "Cut the wait for a refund to a day.")
    topicmap.add_note(state, kinds, "money", "Refunds come out of the store budget.")
    topicmap.add_note(state, kinds, "dates", "The new year sale is the deadline.")
    topicmap.add_note(state, kinds, "goals", "Fewer complaints.")
    first = topicmap.moves(state, kinds)[0]
    # goals is near people, dates, money and risks; dates and money have one each, people and risks none
    assert (first.move, first.data["kind"], first.data["near_last"]) == ("ask-kind", "people", True)


def test_a_group_named_twice_and_never_asked_ranks_before_the_kinds(kinds):
    state = fresh()
    topicmap.add_note(state, kinds, "goals", "Faster refunds.")
    topicmap.name_group(state, "the support desk")
    topicmap.name_group(state, "The Support  Desk")
    topicmap.name_group(state, "finance")
    found = topicmap.moves(state, kinds)
    assert [(m.move, m.data.get("group") or m.data.get("kind")) for m in found[:3]] == [
        ("ask-new-group", "the support desk"), ("ask-kind", "dates"), ("ask-new-group", "finance")]
    assert state["groups"][0]["named"] == 2  # one group, however the lead spelled it


def test_next_asks_a_group_not_yet_heard_on_the_current_topic(kinds):
    state = fresh()
    topicmap.add_position(state, "sales", "approval speed", "a discount approved the same day", "deals cool")
    topicmap.name_group(state, "finance")
    first = topicmap.moves(state, kinds)[0]
    assert (first.move, first.data["group"], first.data["topic"]) == ("ask-group", "finance", "approval speed")


def test_two_positions_on_one_topic_are_put_side_by_side_with_both_holders(kinds):
    state = fresh()
    topicmap.add_position(state, "sales", "approval speed", "same-day approval", "deals cool")
    topicmap.add_position(state, "finance", "Approval speed", "review at the weekly meeting", basis=topicmap.GUESS)
    first = topicmap.moves(state, kinds)[0]
    assert first.move == "side-by-side"
    assert [h["group"] for h in first.data["holders"]] == ["sales", "finance"]
    assert "sales wants same-day approval because deals cool" in first.text and "(the lead's guess)" in first.text
    topicmap.open_item(state, kinds, topicmap.CONFLICT, "Sales and finance differ on approval speed.",
                       topic="approval speed")
    assert all(m.move != "side-by-side" for m in topicmap.moves(state, kinds))


def test_one_side_known_or_both_agreeing_is_never_a_clash(kinds):
    state = fresh()
    topicmap.add_position(state, "sales", "approval speed", "same day")
    assert topicmap.clashes(state) == []
    topicmap.add_position(state, "finance", "approval speed", "Same  day")
    assert topicmap.clashes(state) == []


@pytest.mark.parametrize("count", [3, 4])
def test_next_never_opens_a_new_thread_while_three_or_four_items_wait(kinds, count):
    state = fresh()
    topicmap.add_position(state, "sales", "approval speed", "same day")
    topicmap.add_position(state, "finance", "approval speed", "weekly")
    topicmap.name_group(state, "legal")
    for n in range(count):
        topicmap.open_item(state, kinds, topicmap.GAP, f"Gap number {n}.")
    found = topicmap.moves(state, kinds)
    assert [m.move for m in found] == ["summarize"]
    assert len(found[0].data["waiting"]) == count
    assert found[0].data["pairs"][0]["topic"] == "approval speed"  # folded into the summary, not a new thread


def test_settling_one_reopens_new_threads(kinds):
    state = fresh()
    for n in range(3):
        topicmap.open_item(state, kinds, topicmap.BELIEF, f"Belief {n}.")
    topicmap.close_item(state, 2, topicmap.SET_ASIDE, "the lead said it doesn't matter")
    assert topicmap.moves(state, kinds)[0].move == "ask-kind"
    with pytest.raises(topicmap.MapRefused, match="already set-aside"):
        topicmap.close_item(state, 2)
    with pytest.raises(topicmap.MapRefused, match="no waiting item #9"):
        topicmap.close_item(state, 9)


def test_an_item_past_the_limit_is_still_written(kinds):
    """Refusing the fifth would drop it: the Silent Fallback the map exists to stop. `moves` holds the timing."""
    state = fresh()
    for n in range(5):
        topicmap.open_item(state, kinds, topicmap.FACT, f"Fact {n}.")
    assert [i["n"] for i in topicmap.waiting(state)] == [1, 2, 3, 4, 5]


def test_words_the_lead_would_see_as_plumbing_are_refused(kinds):
    state = fresh()
    for text in ("see .vela/map/x.json", "run vela check first", "use --force"):
        with pytest.raises(topicmap.MapRefused, match="the way the lead would say it"):
            topicmap.add_note(state, kinds, "goals", text)
    with pytest.raises(topicmap.MapRefused, match="kind 'cash'"):
        topicmap.add_note(state, kinds, "cash", "Refunds.")
    assert state["notes"] == []


def test_the_read_back_says_what_is_covered_what_is_empty_and_what_waits(kinds):
    state = fresh()
    topicmap.add_note(state, kinds, "goals", "Faster refunds.")
    topicmap.name_group(state, "finance")
    topicmap.add_note(state, kinds, "systems", "The till app.")
    topicmap.add_note(state, kinds, "data", "Card numbers.")
    topicmap.add_note(state, kinds, "rules", "The refund policy.")
    topicmap.add_note(state, kinds, "risks", "A refund run twice.")
    topicmap.add_note(state, kinds, "owners", "Priya owns the till.")
    topicmap.open_item(state, kinds, topicmap.GAP, "Whether the bank allows same-day refunds.")
    back = topicmap.readback(state, kinds)
    assert back.answer() == ("So far we've covered goals, people, systems, data, rules, risks and owners. "
                             "Nothing yet on dates or money.")
    assert back.items() == ["To check: Whether the bank allows same-day refunds.",
                            "We haven't heard where finance stands yet."]
    assert topicmap.readback(fresh(), kinds).answer() == "Nothing's on the map yet."
    for line in [back.answer(), *back.items()]:
        assert say.leak_in(line) is None, line


def test_a_state_this_version_did_not_write_is_unreadable():
    for text in ("not json", '{"version": 2}', '{"version": 1, "notes": []}'):
        with pytest.raises(topicmap.MapUnreadable):
            topicmap.parse(text)
    assert topicmap.parse(topicmap.dumps(fresh())) == fresh()
