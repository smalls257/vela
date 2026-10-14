"""The explorer's fixed layout: no box is drawn over another, a lead can put a box anywhere from the page and it stays
there, and an outside party is drawn under its own name.

What these prevent. A Distributed Monolith in miniature: pins.py, the page's drag (layout.js) and the helper's
POST /pins each hold the one rule for what a legal layout is, so a layout one accepts and another refuses would draw
boxes on top of each other. The cases (pins.MOVE_CASES) run here against pins.py and over the helper's socket;
#selftest in tests/test_explorer_browser.py plays the same table, with check_move's answers, against the page's copy. The party names come from the vault's own words,
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


def apart(found, kinds=None):
    """True when no two boxes, as drawn, come within pins.GAP of one another. Without kinds a key is a party when it
    starts PTY- (the test vaults' naming), an app otherwise."""
    kinds = kinds or {k: "partner" if k.startswith("PTY-") else "app" for k in found if pins.is_node(k)}
    return pins.check_move(found, kinds) == ""


# --------------------------------------------------------------------------- where new boxes go

@pytest.mark.parametrize("parties", [1, 3, 8, 21])
def test_outside_parties_never_share_a_place_however_many_there_are(tmp_path, parties):
    apps = ["a", "b"]
    n, c = nodes(apps, parties), contracts(apps, parties)
    found, added, _, _, moved = pins.pinned(tmp_path / "p.json", n, c)
    assert len(added) == parties + 2 and not moved
    assert apart(found, {x["key"]: x["kind"] for x in n})


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
    assert apart(found) and json.loads(path.read_text(encoding="utf-8")) == found


def test_a_party_a_reader_put_above_the_apps_stays_there_when_it_is_clear_of_them():
    n = nodes(["a", "b"], 1)
    mine = {"APP-a": [0, 0], "APP-b": [1, 2], "PTY-01": [4, 0]}
    assert pins.settle(mine, {x["key"]: x["kind"] for x in n}) == (mine, [])


def test_a_box_that_stands_clear_is_never_moved_even_between_cells():
    n = nodes(["a", "b"], 1)
    mine = {"APP-a": [3, 2], "APP-b": [0.4, 1.25], "PTY-01": [1.62, 0.5]}
    assert pins.settle(mine, {x["key"]: x["kind"] for x in n}) == (mine, [])


def test_a_new_box_takes_a_whole_cell_clear_of_boxes_dropped_between_cells(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"APP-a": [0.3, 0.2], "PTY-01": [0.5, 1.4]}), encoding="utf-8")
    found, added, _, _, moved = pins.pinned(path, nodes(["a", "b"], 1), contracts(["a", "b"], 1))
    assert added == ["APP-b"] and not moved and found["APP-a"] == [0.3, 0.2]
    assert all(float(x).is_integer() for x in found["APP-b"]) and apart(found)


def test_cluster_pins_are_not_boxes_and_do_not_count_as_stale_or_take_a_cell(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"APP-a": [0, 0], "grp:Billing": [0, 0], "grp:Core": [1, 0]}), encoding="utf-8")
    found, added, stale, _, moved = pins.pinned(path, nodes(["a", "b"], 0), [])
    assert stale == [] and not moved and found["grp:Billing"] == [0, 0] and found["APP-b"] != found["APP-a"]


# --------------------------------------------------------------------------- the rule, as the page and the helper hold it

KINDS = {"APP-a": "app", "APP-b": "app", "PTY-01": "partner"}


# What each of pins.MOVE_CASES should get, worked by hand from the frame (380 px a column, 128 a row, parties 104
# lower) and the box (190 by 70, 20 apart): boxes closer than 210 px across and 90 px down are drawn over one another.
OVERLAPS = {
    "two apps in one place": True,
    "two apps half a column apart in one row": True,  # 190 px across
    "two apps 0.6 of a column apart in one row": False,  # 228 px
    "two apps 0.6 of a row apart in one column": True,  # 77 px down
    "two apps 0.75 of a row apart in one column": False,  # 96 px
    "two apps close on a diagonal": True,
    "two apps just clear on a diagonal": False,
    "a party pinned in an app's own cell, drawn a band below it": False,  # 104 px down
    "a party a quarter row above an app": True,  # 104 - 32 = 72 px down
    "a party above every app, clear of them": False,  # the old rule kept parties below the apps; only overlap counts now
    "whole cells, with a cluster key": False,
}


@pytest.mark.parametrize("name,layout", pins.MOVE_CASES, ids=[c[0] for c in pins.MOVE_CASES])
def test_a_layout_is_refused_only_when_two_boxes_would_be_drawn_over_one_another(name, layout):
    says = pins.check_move(layout, pins.MOVE_KINDS)
    assert ("would overlap" in says) == OVERLAPS[name] and (says == "") != OVERLAPS[name], says


def test_the_selftest_gets_every_case_with_check_moves_answer():
    cases = pins.move_cases()
    assert [c["name"] for c in cases] == list(OVERLAPS) and all(bool(c["says"]) == OVERLAPS[c["name"]] for c in cases)


def test_the_rule_measures_a_party_where_it_is_drawn_a_band_below_its_row():
    assert pins.drawn([1, 2], "partner") == (380, 2 * 128 + 104) and pins.drawn([1, 2], "app") == (380, 256)


@pytest.mark.parametrize("bad", [
    {}, [], {"APP-a": [0]}, {"APP-a": ["0", 0]}, {"APP-a": [True, 0]}, {"APP-a": [-1, 0]}, {"APP-a": [10 ** 9, 0]},
    {"APP-nope": [0, 0]}, {"x" * 400: [0, 0]},
])
def test_the_helper_refuses_pins_that_are_not_cells_of_boxes_the_vault_pins(bad):
    with pytest.raises(ValueError):
        pins.validate(bad, {"APP-a"})


def test_the_helper_takes_new_cluster_keys_and_whole_numbers_as_integers():
    assert pins.validate({"APP-a": [2.0, 1], "grp:New": [0, 0]}, {"APP-a"}) == {"APP-a": [2, 1], "grp:New": [0, 0]}


def test_the_helper_keeps_a_position_between_cells_as_it_was_sent():
    assert pins.validate({"APP-a": [2.375, 1.25], "grp:New": [0.5, 3.125]}, {"APP-a"}) == {"APP-a": [2.375, 1.25], "grp:New": [0.5, 3.125]}


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
    headers = {"Host": host or f"{serve.LOOPBACK}:{server.server_port}", "Cookie": f"{serve.cookie_name(server.server_port)}={server.key}"}
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


def test_a_box_dropped_between_cells_is_saved_where_it_was_dropped(helper):
    server, vault, _ = helper
    status, body = move(server, [2.375, 0.25])
    assert status == 200 and body["pins"]["APP-a"] == [2.375, 0.25]
    assert json.loads((vault / PINS).read_text(encoding="utf-8"))["APP-a"] == [2.375, 0.25]


@pytest.mark.parametrize("cell", [[1, 0], [1.5, 0], [0.5, 1.3]])
def test_a_save_that_would_overlap_two_boxes_is_refused_and_the_file_is_untouched(helper, cell):
    server, vault, _ = helper
    before = (vault / PINS).read_bytes()
    status, body = move(server, cell)
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
    data = json.loads(DATA.search((root / "dashboard.html").read_text(encoding="utf-8")).group(1))
    assert apart(found, {n["key"]: n["kind"] for n in data["nodes"]}) and len(found) == 4
    assert data["pins"]["frame"] == {**pins.FRAME, "boxW": pins.BOX["w"], "boxH": pins.BOX["h"], "gap": pins.GAP, "slack": pins.SLACK}
    assert "cases" not in data["pins"], "only a selftest build carries the rule's cases"
