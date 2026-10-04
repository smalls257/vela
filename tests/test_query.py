"""planner query: get, refs, find and status. Read-only, JSON or text, and an explicit not_found."""
import json

from conftest import edit, run


def ask(mini, *argv):
    code, out = run("query", *argv, "--vault", str(mini), "--json")
    return code, json.loads(out)


def test_get_an_item(mini):
    code, answer = ask(mini, "get", "CON-001")
    assert code == 0
    assert answer == {
        "id": "CON-001", "kind": "contract", "page": "05-building-blocks/shop-building-blocks.md",
        "heading": "CON-001 Sale API", "state": "decided", "owner": "@mini/shop-team", "sources": [],
        "decision": ["2026-01-10-shop-api"], "dissent": [], "blocked_by": [],
        "link": "[[shop-building-blocks#CON-001 Sale API|CON-001]]", "also": []}


def test_get_a_page_and_a_row(mini):
    _, app = ask(mini, "get", "APP-shop")
    assert (app["kind"], app["heading"], app["state"], app["link"]) == (
        "app-building-blocks", "Shop", "decided", "[[shop-building-blocks|APP-shop]]")
    _, goal = ask(mini, "get", "G1")
    assert (goal["kind"], goal["heading"], goal["state"], goal["page"]) == ("goal", "Sell from one till", "decided", "01-goals.md")
    _, source = ask(mini, "get", "SRC-01")
    assert (source["kind"], source["owner"]) == ("source", "@stock-team")


def test_an_unknown_id_is_not_found_and_exits_1(mini):
    code, answer = ask(mini, "get", "CON-099")
    assert code == 1
    assert answer == {"id": "CON-099", "not_found": True}
    code, out = run("query", "get", "con-001", "--vault", str(mini))
    assert code == 1 and out == "id: con-001\nnot_found: true\n"


def test_get_says_what_blocks_an_item(mini):
    edit(mini / "11-unknowns-and-risks.md", "- **Blocks:** nothing", "- **Blocks:** [[shop-building-blocks#CON-001 Sale API|CON-001]]")
    _, answer = ask(mini, "get", "CON-001")
    assert answer["blocked_by"] == ["UNK-001"]


def test_get_names_a_duplicate_heading(mini):
    till = mini / "05-building-blocks/till-building-blocks.md"
    edit(till, "# Till\n", "# Till\n\n### CON-001 Sale API\n\n- **State:** inkling\n")
    line = till.read_text(encoding="utf-8").split("\n").index("### CON-001 Sale API") + 1
    _, answer = ask(mini, "get", "CON-001")
    assert answer["also"] == [f"05-building-blocks/till-building-blocks.md:{line}"]


def test_text_output_is_one_line_per_field(mini):
    code, out = run("query", "get", "UNK-001", "--vault", str(mini))
    assert code == 0
    assert "heading: UNK-001 Till test rig\n" in out and "state: open\n" in out and "sources: none\n" in out


def test_refs_lists_links_and_epic_lists(mini):
    (mini / "13-epics").mkdir()
    (mini / "13-epics" / "EPC-001-sell.md").write_text(
        "---\nid: EPC-001\ntype: epic\ntitle: Sell\nstate: draft\nowner: \"@mini/shop-team\"\nauthored: mixed\n"
        "apps: [APP-shop]\ndelivers: [CON-001]\n---\n\n# EPC-001 Sell\n", encoding="utf-8")
    code, answer = ask(mini, "refs", "CON-001")
    assert code == 0
    vias = {(r["page"], r["via"]) for r in answer["refs"]}
    assert ("13-epics/EPC-001-sell.md", "delivers") in vias
    assert ("05-building-blocks/till-building-blocks.md", "link") in vias
    assert answer["refs"] == sorted(answer["refs"], key=lambda r: (r["page"], r["line"], r["via"]))


def test_refs_to_a_page_id_count_every_anchor(mini):
    _, answer = ask(mini, "refs", "APP-stock")
    assert "05-building-blocks/shop-building-blocks.md" in {r["page"] for r in answer["refs"]}


def test_refs_to_nothing_is_not_found(mini):
    assert ask(mini, "refs", "UNK-404") == (1, {"id": "UNK-404", "not_found": True})


def test_find_needs_every_word_in_any_case(mini):
    code, answer = ask(mini, "find", "SALE", "api")
    assert code == 0
    assert [m["id"] for m in answer["matches"]] == ["CON-001"]
    code, answer = ask(mini, "find", "sale", "zebra")
    assert code == 1 and answer == {"words": ["sale", "zebra"], "matches": [], "not_found": True}


def test_find_survives_a_title_that_is_not_text(mini):
    edit(mini / "05-building-blocks/till-building-blocks.md", "title: Till", "title: [Till, Desk]")
    code, answer = ask(mini, "find", "till")
    assert "UNK-001" in [m["id"] for m in answer["matches"]]


def test_status_is_the_planner_status_grid(mini):
    code, answer = ask(mini, "status", "--today", "2026-01-15")
    assert code == 0
    assert answer["today"] == "2026-01-15"
    assert [a["app"] for a in answer["apps"]] == ["APP-till", "APP-shop", "APP-stock"]
    _, text = run("status", "--vault", str(mini), "--today", "2026-01-15")
    for app in answer["apps"]:
        assert f"next: {app['next']} {app['subject']}".strip() + f". {app['reason']}" in text or app["next"] == "none"


def test_query_writes_nothing(mini):
    before = {p: p.read_bytes() for p in mini.rglob("*") if p.is_file()}
    for argv in (("get", "CON-001"), ("refs", "CON-001"), ("find", "till"), ("status",)):
        run("query", *argv, "--vault", str(mini))
    assert {p: p.read_bytes() for p in mini.rglob("*") if p.is_file()} == before


def test_query_needs_a_question():
    assert run("query")[0] == 2
    assert run("query", "get")[0] == 2


def test_refs_counts_plain_id_mentions_on_the_fixture():
    import pathlib
    fixture = pathlib.Path(__file__).resolve().parent.parent / "examples" / "unified-booking"
    _, src = ask(fixture, "refs", "SRC-02")
    assert src["refs"] and "02-constraints.md" in {r["page"] for r in src["refs"]}
    _, con = ask(fixture, "refs", "CON-001")
    pages = {r["page"] for r in con["refs"]}
    assert "13-epics/EPC-033-website-to-booking.md" in pages
    assert any(r["page"].startswith("sessions/") and r["via"] == "mention" for r in con["refs"])
    assert ("05-building-blocks/booking-building-blocks.md", "mention") not in {(r["page"], r["via"]) for r in con["refs"]
                                                                                if r["line"] == 1}


def test_a_mention_needs_the_whole_id_and_skips_fences_and_its_own_heading(mini):
    note = mini / "05-building-blocks/till-building-blocks.md"
    edit(note, "# Till\n", "# Till\n\nSee CON-001 here. Not CON-0012 or CON-001.FR1 or CON-001-x.\n\n```\nCON-001 in code\n```\n")
    _, answer = ask(mini, "refs", "CON-001")
    mentions = [r for r in answer["refs"] if r["via"] == "mention" and r["page"] == "05-building-blocks/till-building-blocks.md"]
    text = note.read_text(encoding="utf-8").split("\n")
    assert [text[r["line"] - 1] for r in mentions].count("See CON-001 here. Not CON-0012 or CON-001.FR1 or CON-001-x.") == 1
    assert len(mentions) == 1
    assert all("CON-001 Sale API" not in text[r["line"] - 1] for r in answer["refs"] if r["via"] == "mention")
    assert all("in code" not in text[r["line"] - 1] for r in mentions)


def test_refs_does_not_change_the_case_of_a_link_anchor(mini):
    edit(mini / "05-building-blocks/till-building-blocks.md", "# Till\n", "# Till\n\n[[shop-building-blocks#con-001 sale api|x]]\n")
    _, answer = ask(mini, "refs", "CON-001")
    lines = mini.joinpath("05-building-blocks/till-building-blocks.md").read_text(encoding="utf-8").split("\n")
    assert not any(r["via"] == "link" and "con-001 sale" in lines[r["line"] - 1] for r in answer["refs"]
                   if r["page"] == "05-building-blocks/till-building-blocks.md")


def test_find_with_only_blank_words_is_a_tool_error(mini):
    code, out = run("query", "find", " ", "--vault", str(mini))
    assert code == 2 and "not blank" in out


def test_find_searches_goal_constraint_and_source_rows(mini):
    _, answer = ask(mini, "find", "sell", "from")
    assert [(m["id"], m["kind"]) for m in answer["matches"] if m["id"] == "G1"] == [("G1", "goal")]


def test_find_stop_mainframe_returns_the_goal_on_the_fixture():
    import pathlib
    fixture = pathlib.Path(__file__).resolve().parent.parent / "examples" / "unified-booking"
    _, answer = ask(fixture, "find", "stop", "mainframe")
    assert "G1" in [m["id"] for m in answer["matches"]]


def test_a_dotted_id_alone_on_a_line_is_not_a_mention(mini):
    note = mini / "05-building-blocks/till-building-blocks.md"
    edit(note, "# Till\n", "# Till\n\nOnly CON-001.FR1 here.\n\nEnds a sentence with CON-001.\n")
    _, answer = ask(mini, "refs", "CON-001")
    text = note.read_text(encoding="utf-8").split("\n")
    lines = [text[r["line"] - 1] for r in answer["refs"] if r["page"] == "05-building-blocks/till-building-blocks.md"]
    assert "Only CON-001.FR1 here." not in lines
    assert "Ends a sentence with CON-001." in lines
