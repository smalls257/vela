"""The explorer's fixed layout: no two boxes share a place, a lead's layout can be moved from the page, and an outside
party is drawn under its own name.

What these prevent. A Distributed Monolith in miniature: pins.py, the page's drag (layout.js) and the helper's
POST /pins each hold the one rule for what a legal layout is, so a layout one accepts and another refuses would draw
boxes on top of each other. The cases below run the rule in pins.py and over the helper's socket; #selftest in
tests/test_explorer_browser.py plays the same cases in the page. The party names come from the vault's own words,
so a Leaky Narrative (a sentence on a box) is checked against the heron-desk snapshot, whose contracts name two of
their providers in running text.
"""
import http.client
import json
import re
import shutil
import threading

import pytest

from conftest import REPO, run
from planner.explorer import build, pins, serve

HERON = REPO / "tests/sim/snapshots/heron-desk/after-full-1"
PINS = ".planner/explorer-pins.json"
DATA = re.compile(r'<script type="application/json" id="data">(.*?)</script>', re.S)


def nodes(apps, parties):
    return ([{"key": f"APP-{a}", "kind": "app", "title": a} for a in apps]
            + [{"key": f"PTY-{p:02d}", "kind": "partner", "title": f"Party {p}"} for p in range(1, parties + 1)])


def contracts(apps, parties):
    """Every party provides one contract to the first app, so every party is drawn under it."""
    return [{"id": f"CON-{p:03d}", "provider": f"PTY-{p:02d}", "providerKind": "party", "consumers": [f"APP-{apps[0]}"]}
            for p in range(1, parties + 1)]


def apart(found, keys):
    """True when no two of the keys stand within one column of each other in one row."""
    cells = sorted((found[k][1], found[k][0]) for k in keys)
    return all(r1 != r2 or c2 - c1 >= pins.MIN_APART for (r1, c1), (r2, c2) in zip(cells, cells[1:]))


# --------------------------------------------------------------------------- where new boxes go

@pytest.mark.parametrize("parties", [1, 3, 8, 21])
def test_outside_parties_never_share_a_place_however_many_there_are(tmp_path, parties):
    apps = ["a", "b"]
    n, c = nodes(apps, parties), contracts(apps, parties)
    found, added, _, _, moved = pins.pinned(tmp_path / "p.json", n, c)
    assert len(added) == parties + 2 and not moved
    assert apart(found, found)
    assert pins.check_move(found, {x["key"]: x["kind"] for x in n}) == ""


def test_a_long_row_of_parties_wraps_instead_of_running_on(tmp_path):
    found = pins.pinned(None, nodes(["a"], 9), contracts(["a"], 9))[0]
    rows = {found[f"PTY-{p:02d}"][1] for p in range(1, 10)}
    widest = max(found[f"PTY-{p:02d}"][0] for p in range(1, 10))
    assert len(rows) >= 3 and widest < pins.MIN_PARTY_ROW_WIDTH, (rows, widest)


def test_a_party_row_keeps_the_order_the_layout_gave_it_between_builds(tmp_path):
    path = tmp_path / "p.json"
    first = pins.pinned(path, nodes(["a"], 4), contracts(["a"], 4))[0]
    again, added, _, _, moved = pins.pinned(path, nodes(["a"], 6), contracts(["a"], 6))
    assert added == ["PTY-05", "PTY-06"] and not moved
    assert all(again[k] == v for k, v in first.items()), "a pinned box moved when two more arrived"


# --------------------------------------------------------------------------- pins that already overlap

def test_pins_that_stand_on_one_another_are_settled_and_the_file_says_which(tmp_path):
    """The heron-desk build once pinned three parties at columns 0.0, 0.4 and 0.6 of one row, 76 px apart, drawn 176 wide."""
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"APP-a": [0, 0], "PTY-01": [0.0, 1], "PTY-02": [0.4, 1], "PTY-03": [0.6, 1]}), encoding="utf-8")
    n = nodes(["a"], 3)
    found, added, _, _, moved = pins.pinned(path, n, contracts(["a"], 3))
    assert not added and moved == ["PTY-02", "PTY-03"], moved
    assert found["PTY-01"] == [0.0, 1], "the first box in a place keeps it"
    assert apart(found, found) and json.loads(path.read_text(encoding="utf-8")) == found


def test_a_party_pinned_above_the_apps_is_lowered_to_the_last_row_of_apps():
    n = nodes(["a", "b"], 1)
    settled, moved = pins.settle({"APP-a": [0, 0], "APP-b": [1, 2], "PTY-01": [4, 0]}, {x["key"]: x["kind"] for x in n})
    assert moved == ["PTY-01"] and settled["PTY-01"][1] == 2


def test_a_box_that_stands_clear_is_never_moved():
    n = nodes(["a", "b"], 1)
    mine = {"APP-a": [3, 2], "APP-b": [0, 1], "PTY-01": [7, 5]}
    assert pins.settle(mine, {x["key"]: x["kind"] for x in n}) == (mine, [])


def test_cluster_pins_are_not_boxes_and_do_not_count_as_stale_or_take_a_cell(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"APP-a": [0, 0], "grp:Billing": [0, 0], "grp:Core": [1, 0]}), encoding="utf-8")
    found, added, stale, _, moved = pins.pinned(path, nodes(["a", "b"], 0), [])
    assert stale == [] and not moved and found["grp:Billing"] == [0, 0] and found["APP-b"] != found["APP-a"]


# --------------------------------------------------------------------------- the rule, as the page and the helper hold it

KINDS = {"APP-a": "app", "APP-b": "app", "PTY-01": "partner"}


@pytest.mark.parametrize("layout,says", [
    ({"APP-a": [0, 0], "APP-b": [0, 0], "PTY-01": [0, 1]}, "overlap"),
    ({"APP-a": [0, 0], "APP-b": [0.5, 0], "PTY-01": [0, 1]}, "overlap"),
    ({"APP-a": [0, 2], "APP-b": [1, 0], "PTY-01": [0, 1]}, "above the apps"),
])
def test_a_layout_that_would_draw_boxes_over_one_another_is_refused_with_the_reason(layout, says):
    assert says in pins.check_move(layout, KINDS)


def test_a_layout_with_every_box_in_its_own_place_passes():
    assert pins.check_move({"APP-a": [0, 0], "APP-b": [1, 0], "PTY-01": [0, 1], "grp:x": [0, 0]}, KINDS) == ""


@pytest.mark.parametrize("bad", [
    {}, [], {"APP-a": [0]}, {"APP-a": ["0", 0]}, {"APP-a": [True, 0]}, {"APP-a": [-1, 0]}, {"APP-a": [10 ** 9, 0]},
    {"APP-nope": [0, 0]}, {"x" * 400: [0, 0]},
])
def test_the_helper_refuses_pins_that_are_not_cells_of_boxes_the_vault_pins(bad):
    with pytest.raises(ValueError):
        pins.validate(bad, {"APP-a"})


def test_the_helper_takes_new_cluster_keys_and_whole_numbers_as_integers():
    assert pins.validate({"APP-a": [2.0, 1], "grp:New": [0, 0]}, {"APP-a"}) == {"APP-a": [2, 1], "grp:New": [0, 0]}


# --------------------------------------------------------------------------- POST /pins and GET /pins

@pytest.fixture
def helper(tmp_path):
    vault = tmp_path / "vault"
    (vault / ".planner").mkdir(parents=True)
    (vault / PINS).write_text(json.dumps({"APP-a": [0, 0], "APP-b": [1, 0], "PTY-01": [0, 1]}), encoding="utf-8")
    page = tmp_path / "page.html"
    page.write_text("<!doctype html><title>x</title>", encoding="utf-8")
    lines = []
    server = serve.Server(vault, page, 0, "haiku", 3, lines.append, pins=vault / PINS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, vault, lines
    server.shutdown()
    server.server_close()
    thread.join(5)


def call(server, method, path, body=None, host=None, origin="same"):
    conn = http.client.HTTPConnection(serve.LOOPBACK, server.server_port, timeout=15)
    headers = {"Host": host or f"{serve.LOOPBACK}:{server.server_port}"}
    if origin == "same":
        headers["Origin"] = f"http://{serve.LOOPBACK}:{server.server_port}"
    elif origin:
        headers["Origin"] = origin
    conn.request(method, path, body=json.dumps(body) if body is not None else None, headers={**headers, "Content-Type": "application/json"})
    response = conn.getresponse()
    return response.status, json.loads(response.read().decode("utf-8"))


def move(server, cell, key="APP-a", **extra):
    pinned = {"APP-a": [0, 0], "APP-b": [1, 0], "PTY-01": [0, 1], key: cell}
    return call(server, "POST", "/pins", {"pins": pinned, "kinds": {"APP-a": "app", "APP-b": "app", "PTY-01": "partner"}}, **extra)


def test_a_dragged_layout_is_saved_to_the_vaults_pins_file_and_read_back(helper):
    server, vault, lines = helper
    status, body = move(server, [4, 0])
    assert status == 200 and body["file"] == PINS and body["pins"]["APP-a"] == [4, 0]
    assert json.loads((vault / PINS).read_text(encoding="utf-8"))["APP-a"] == [4, 0]
    assert call(server, "GET", "/pins", origin=None)[1]["pins"]["APP-a"] == [4, 0]
    assert any("layout saved" in line for line in lines), lines
    assert not list(vault.glob(".planner/*.tmp")), "the scratch file was left behind"


def test_a_save_that_would_overlap_two_boxes_is_refused_and_the_file_is_untouched(helper):
    server, vault, _ = helper
    before = (vault / PINS).read_bytes()
    status, body = move(server, [1, 0])
    assert status == 400 and "overlap" in body["error"]
    assert (vault / PINS).read_bytes() == before


def test_a_save_may_not_invent_a_box_or_grow_the_file(helper):
    server, vault, _ = helper
    before = (vault / PINS).read_bytes()
    status, body = move(server, [3, 3], key="APP-invented")
    assert status == 400 and "not a node" in body["error"]
    assert (vault / PINS).read_bytes() == before


def test_a_save_from_another_origin_or_with_none_is_refused(helper):
    server, vault, _ = helper
    before = (vault / PINS).read_bytes()
    assert move(server, [4, 0], origin="http://evil.example")[0] == 403
    assert move(server, [4, 0], origin=None)[0] == 403
    assert move(server, [4, 0], host="evil.example")[0] == 403
    assert (vault / PINS).read_bytes() == before


def test_a_helper_started_without_a_pins_file_says_so_instead_of_saving_nowhere(tmp_path):
    vault = tmp_path / "v"
    vault.mkdir()
    page = tmp_path / "p.html"
    page.write_text("x", encoding="utf-8")
    server = serve.Server(vault, page, 0, "haiku", 3, lambda line: None)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert move(server, [4, 0])[0] == 404
        assert call(server, "GET", "/pins", origin=None)[0] == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)


def test_a_body_that_is_not_the_agreed_shape_is_a_400_that_says_what_to_send(helper):
    server, _, _ = helper
    status, body = call(server, "POST", "/pins", {"cells": 1})
    assert status == 400 and '"pins"' in body["error"]


# --------------------------------------------------------------------------- party names

@pytest.mark.parametrize("said,drawn", [
    ("Stripe", "Stripe"),
    ("Stripe (external)", "Stripe"),
    ("the pilot user, on their own laptop", "the pilot user"),
    ("Okta, the identity provider the firm already uses", "Okta"),
    ("Salesforce - the CRM", "Salesforce"),
    ("the call tools the pilot team and its clients use, not yet known", "the call tools the pilot team and its clients use"[:build.NAME_CAP].rsplit(" ", 1)[0] + "…"),
])
def test_a_provider_written_as_a_sentence_is_drawn_by_its_first_words(said, drawn):
    assert build.external_title(said) == drawn


@pytest.fixture(scope="module")
def heron(tmp_path_factory):
    root = tmp_path_factory.mktemp("heron") / "vault"
    shutil.copytree(HERON, root)
    code, said = run("explore", str(root), "--today", "2026-10-11")
    assert code == 0, said
    page = (root / "dashboard.html").read_text(encoding="utf-8")
    data = json.loads(DATA.search(page).group(1))
    return root, said, data["map"]["externals"]


def test_the_heron_vault_names_two_of_its_providers_in_running_text_and_the_page_says_so(heron):
    """What the vault holds: 03-context-and-scope.md has PTY-01 Microsoft and PTY-02 Zoom; CON-002 and CON-003 give
    their Provider as a sentence, not a link to a party. The page cannot invent names, so it draws the first words,
    keeps the sentence on hover, and the build says which contract to fix."""
    root, said, externals = heron
    titles = {x["said"]: x["title"] for x in externals}
    assert titles["the pilot user, on their own laptop"] == "the pilot user"
    assert all("," not in x["title"] and x["title"].startswith("the ") for x in externals)
    assert "CON-002 names its provider in running text" in said and "Outside parties in 03-context-and-scope.md" in said
    assert "CON-003 names its provider in running text" in said
    context = (root / "03-context-and-scope.md").read_text(encoding="utf-8")
    assert "### PTY-01 Microsoft" in context and "### PTY-02 Zoom" in context


def test_the_heron_boxes_stand_apart_in_the_pins_the_build_wrote(heron):
    root, _, _ = heron
    found = json.loads((root / PINS).read_text(encoding="utf-8"))
    assert apart(found, found) and len(found) == 4
