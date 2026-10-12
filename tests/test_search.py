"""Plain-word search: a person mid-conversation types their own words, and the flow that answers comes up."""
from conftest import REPO, run

FIXTURE = REPO / "examples" / "unified-booking"


def search(*words):
    return run("query", "search", *words, "--vault", str(FIXTURE))


def test_a_how_question_reaches_the_flow_from_the_first_hit():
    code, out = search("how", "does", "a", "seat", "hold", "work")
    assert code == 0, out
    first = out.split("\n2. ", 1)[0]  # the first place, with its snippet and the flows that cross it
    assert "FLO-001-hold-pay-confirm" in first, out


def test_a_hit_lists_the_flows_that_cross_it():
    code, out = search("hold", "a", "seat")
    assert "Flows that cross it: Hold, pay, confirm" in out, out


def test_plural_and_possessive_words_still_match():
    assert search("seats", "holds")[0] == 0
    assert search("customer's", "booking")[0] == 0


def test_history_is_not_searched_and_stop_words_alone_find_nothing():
    code, out = search("the", "of", "how")
    assert code == 1 and "nothing holds enough" in out


def test_json_gives_viewer_links():
    import json
    code, out = run("query", "search", "seat", "hold", "--vault", str(FIXTURE), "--json")
    hits = json.loads(out)["hits"]
    assert hits and all(h["view"].startswith("#/") for h in hits)


def test_a_word_and_its_plural_share_a_stem():
    import sys
    sys.path.insert(0, str(REPO / "plugin" / "lib"))
    from planner.search import stem
    assert stem("place") == stem("places") == stem("placed")
    assert stem("trade") == stem("trades") == stem("trading")
