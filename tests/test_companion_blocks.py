"""The panels as blocks: every word, mark and tone comes from vela, in the order the approved mockup shows."""
import json
import shutil

import pytest

from companion_flow import STEPS
from companion_vault import grill_session, run_companion
from conftest import REPO, run
from vela import companionblocks, companionrender, companionsession

EXAMPLE = REPO / "examples" / "unified-booking"


def types(blocks):
    return [b["type"] for b in blocks]


def flat(line):
    return "".join(p.get("t", "<bar>") for p in line)


def session_dict(**over):
    """A session dict built by hand: the blocks are a function of it, no vault or clock needed."""
    base = {"version": 1, "kind": "session", "as_of": "2026-10-24T10:41", "capture": 14, "notes": "read",
            "session": {"id": "s", "title": "Grill: hold", "modes": ["grill"], "opened": "2026-10-24"},
            "about": "Settle it.", "decided": [], "said_yes": [], "open": [], "agenda": [],
            "next": {"text": "", "id": "", "source": "none", "left_after": 0}, "touched": [], "diagram": None,
            "band": "", "warnings": []}
    return {**base, **over}


@pytest.fixture(scope="module")
def grill(tmp_path_factory):
    root = grill_session(tmp_path_factory.mktemp("blocks"))
    code, out = run_companion(root, "session", "--json")
    assert code == 0, out
    return json.loads(out)


def test_the_session_blocks_come_in_the_mockups_order(grill):
    assert types(grill["blocks"]) == ["card", "next", "section", "section", "section", "diagram", "lines"]
    assert [b.get("key") for b in grill["blocks"] if b["type"] == "section"] == ["decided", "waiting", "open"]


def test_the_header_card_holds_the_title_the_notes_and_the_agenda_bar(grill):
    card = grill["blocks"][0]
    assert (card["title"], card["right"], card["tone"]) == ("Grill: hold, pay, confirm", "14 notes · 10:41", "info")
    assert card["lines"][0] == [{"t": "Settle how a crossing is held, paid and confirmed.", "tone": "dim"}]
    assert card["lines"][1] == [{"t": "Agenda  ", "tone": "plain"}, {"bar": [3, 4]}, {"t": "  3 of 4 done", "tone": "dim"}]


def test_next_names_the_move_its_id_and_where_it_came_from(grill):
    assert grill["blocks"][1] == {"type": "next", "chip": "NEXT", "text": "Pricing runtime", "id": "RUN-pricing",
                                  "note": "last item on the agenda"}


def test_rows_carry_their_own_mark_tone_chip_and_sub_line(grill):
    decided, waiting, opened = [b for b in grill["blocks"] if b["type"] == "section"]
    assert decided["rows"][0] == {"mark": "✔", "tone": "good", "name": "Hold, pay, confirm", "id": "FLO-001",
                                  "note": "was assumption", "chip": None, "sub": None,
                                  "page": "06-runtime/flows/FLO-001-hold-pay-confirm.md"}
    assert (waiting["title"], waiting["rows"][0]["mark"], waiting["rows"][0]["tone"]) == ("Yes given, waiting", "◷", "warn")
    assert flat(waiting["rows"][0]["sub"]) == "held by Tidepay outcome wording · Booking senior"
    new = opened["rows"][0]
    assert (opened["title"], new["mark"], new["tone"], new["chip"], new["note"]) == (
        "Open questions", "?", "new", {"t": "NEW", "tone": "new"}, "Booking senior")


def test_the_diagram_block_holds_the_flow_at_four_widths(grill):
    block = next(b for b in grill["blocks"] if b["type"] == "diagram")
    assert (block["title"], block["id"]) == ("Flow: Hold, pay, confirm", "FLO-001")
    assert sorted(block["drawings"]) == ["48", "60", "72", "96"] and "others" in block["folded"]["48"]
    assert block["alt"] == "Hold, pay, confirm: 7 steps." and "columns" not in block["alt"] and "96" not in block["folded"]
    assert "text" not in grill["diagram"]


def test_pages_changed_links_each_page_and_the_dashboard_line_closes_the_panel(grill):
    lines = grill["blocks"][-1]["lines"]
    links = [p["page"] for p in lines[0] if "page" in p]
    assert links == ["06-runtime/flows/FLO-001-hold-pay-confirm.md", "11-unknowns-and-risks.md"]
    assert lines[-1] == [{"t": companionblocks.DASHBOARD_LINE, "tone": "dim"}]


def test_the_band_spans_say_exactly_what_the_band_says(grill):
    assert "".join(s["t"] for s in grill["band_spans"]) == grill["band"]
    assert [s["tone"] for s in grill["band_spans"]][:1] == ["strong"]


def test_the_markdown_is_the_blocks_in_plain_text(grill):
    md = companionrender.markdown(grill)
    order = ["**Grill: hold, pay, confirm**", "NEXT  Pricing runtime", "**Decided this session** (2)",
             "**Yes given, waiting** (1)", "**Open questions** (1)", "**Flow: Hold, pay, confirm**", "Pages changed"]
    assert [md.index(w) for w in order] == sorted(md.index(w) for w in order)


def test_an_unreadable_session_is_a_warn_card_then_warnings_never_an_empty_decided_section():
    got = companionsession.unreadable({"id": "x", "title": "Grill: x", "modes": [], "date": "2026-10-24"}, "no git", "2026-10-24", "10:00")
    blocks = companionblocks.session_blocks(got)
    assert types(blocks) == ["card", "lines"] and blocks[0]["tone"] == "warn"
    assert flat(blocks[0]["lines"][0]) == companionblocks.UNREADABLE and flat(blocks[1]["lines"][0]) == "no git"
    assert [s["t"] for s in companionblocks.band_spans(got)][2] == "notes can't be read here"


def test_nothing_decided_or_open_is_said_in_a_dim_row():
    blocks = companionblocks.session_blocks(session_dict(agenda=[]))
    decided, opened = [b for b in blocks if b["type"] == "section"]
    assert decided["rows"][0]["name"] == "Nothing decided yet." and decided["rows"][0]["tone"] == "dim"
    assert opened["rows"][0]["name"] == "Nothing open." and not any(line[0].get("bar") for line in blocks[0]["lines"])


def test_a_suggestion_of_vela_moves_its_date_into_the_note():
    move = {"text": "Name an owner (vela's suggestion as of October 24)", "id": "", "source": "vela", "left_after": 0}
    block = companionblocks.next_block(session_dict(next=move))
    assert (block["text"], block["note"]) == ("Name an owner", "vela's suggestion as of October 24")


def test_an_older_open_question_shows_its_days_not_a_new_chip():
    item = {"id": "UNK-1", "name": "Q", "who": "Lead", "new_this_session": False, "open_days": 3}
    row = companionblocks.open_row(item)
    assert row["chip"] is None and row["note"] == "Lead · 3 days"


def test_many_pages_changed_list_one_per_line_and_count_the_rest():
    touched = [{"page": f"p{n}.md", "name": f"Page {n}", "change": "changed"} for n in range(9)]
    lines = companionblocks.pages_changed(touched)
    assert len(lines) == 1 + companionblocks.MORE_PAGES + 1 and flat(lines[-1]) == "  + 3 more"
    assert companionblocks.pages_changed(None) == []


def test_a_long_band_keeps_its_hint_and_fits():
    data = session_dict(decided=[], open=[], next={"text": "x" * 200, "id": "", "source": "agenda", "left_after": 0})
    spans = companionblocks.band_spans(data)
    assert len("".join(s["t"] for s in spans)) <= companionblocks.BAND_WIDTH and spans[-1]["t"].endswith("to open")


# --- explain -----------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def plan(tmp_path_factory):
    root = tmp_path_factory.mktemp("explain") / "plan"
    shutil.copytree(EXAMPLE, root)
    assert run("companion", "prepare", "--vault", str(root), "--today", "2026-10-24")[0] == 0
    return root


def explain(plan, *args):
    code, out = run_companion(plan, "explain", "--json", *args)
    assert code == 0, out
    return json.loads(out)


def test_stuck_is_a_red_card_a_section_per_holder_and_a_bar_of_their_waits(plan):
    got = explain(plan, "--view", "stuck")
    blocks = got["blocks"]
    assert types(blocks) == ["card", "section", "section", "bars", "card", "lines"]
    assert (blocks[0]["title"], blocks[0]["tone"]) == ("What's stuck?", "bad")
    assert [b["key"] for b in blocks[1:3]] == ["group:Platform lead", "group:Solution lead"]
    long_wait = blocks[1]["rows"][0]
    assert (long_wait["mark"], long_wait["tone"], long_wait["chip"]) == ("■", "bad", {"t": "17 days", "tone": "bad"})
    assert flat(long_wait["sub"]) == "ask by March 1, 2027"
    assert blocks[2]["rows"][0]["tone"] == "warn" and blocks[2]["rows"][0]["chip"]["tone"] == "warn"
    assert [(r["label"], r["value"], r["max"]) for r in blocks[3]["rows"]] == [("Platform lead", 17, 17), ("Solution lead", 0, 17)]


def test_the_not_in_the_plan_card_is_dim_and_the_footer_offers_only_views_that_answer(plan):
    blocks = explain(plan, "--view", "stuck")["blocks"]
    assert (blocks[4]["title"], blocks[4]["tone"]) == ("Not in the plan", "dim")
    ask, picture = blocks[5]["lines"]
    assert flat(ask) == "Also ask  what's left? · who holds what?"   # no release dates, no viewer: two views can't answer
    assert picture[-1] == {"t": "dashboard.html in this folder", "tone": "info", "page": "dashboard.html#asks"}


def test_no_explain_block_ever_says_on_track(plan):
    for view in ("track", "stuck", "left", "who", "none"):
        assert "on track" not in json.dumps(explain(plan, "--view", view)["blocks"]).lower()


def test_left_draws_a_bar_per_app_scaled_to_its_own_total(plan):
    bars = next(b for b in explain(plan, "--view", "left")["blocks"] if b["type"] == "bars")
    assert all(r["tone"] == "good" and r["max"] >= 1 for r in bars["rows"]) and bars["rows"][0]["text"] == "4 of 4"


def test_a_view_with_one_number_draws_no_bars(plan):
    assert "bars" not in types(explain(plan, "--view", "needs", "--as", "@hl-solution-lead")["blocks"])
    assert "bars" not in types(explain(plan, "--view", "track")["blocks"])


def test_a_viewer_with_only_a_handle_is_not_named_on_the_card(plan):
    got = explain(plan, "--view", "needs", "--as", "@hl-solution-lead")
    assert got["blocks"][0]["right"] == ""


def test_a_viewer_with_a_role_is_named_on_the_card(plan):
    got = explain(plan, "--view", "stuck")
    got["viewer"] = {"handle": "@hl-director", "role": "director"}
    assert companionblocks.explain_blocks(got)[0]["right"] == "as the director"


def test_the_flow_view_is_a_card_and_the_drawing_with_no_item_list(plan):
    blocks = explain(plan, "--view", "flow", "--about", "Hold, pay, confirm")["blocks"]
    assert types(blocks) == ["card", "diagram", "lines"] and blocks[0]["title"] == "Hold, pay, confirm"
    assert blocks[1]["id"] == "FLO-001"


def lit_digest(lights):
    """A digest whose apps are lit as given, so the stuck view has a map to draw."""
    apps = [{"key": key, "name": key.title(), "domain": ""} for key in lights]
    return {"version": 3, "title": "T", "made": {"date": "2026-10-24"}, "today": "2026-10-24", "names": {}, "asks": [],
            "stuck": [], "needs": {"lines": []}, "slices": [], "progress": [], "flows": [], "pages": [], "apps": apps,
            "app_lights": lights, "releases": []}


def stuck_with(lights):
    from vela import companionexplain
    data = companionexplain.explain(lit_digest(lights), "stuck", "", companionexplain.Viewer("", ""), None, "2026-10-24")
    return companionrender.with_renders(data)


def test_the_lit_map_is_a_diagram_block_with_no_character_drawing_and_words_for_the_terminal():
    got = stuck_with({"booking": "warning", "tidepay": "caution", "ledger": "dark"})
    assert got["diagram"]["kind"] == "map" and got["diagram"]["svg"].startswith("<svg")
    block = next(b for b in got["blocks"] if b["type"] == "diagram")
    assert block["svg"] is True and block["drawings"] == {} and block["title"] == "Where the questions sit"
    assert block["alt"] == "Apps with open questions: Booking (warning), Tidepay (caution)."


def test_a_map_with_nothing_lit_draws_no_diagram_at_all():
    got = stuck_with({"booking": "dark"})
    assert got["diagram"] is None and "diagram" not in types(got["blocks"])


def test_an_off_agenda_item_counts_as_handled_in_the_agenda_bar():
    agenda = [{"id": "A", "name": "A", "status": "decided"}, {"id": "B", "name": "B", "status": "off-agenda"},
              {"id": "C", "name": "C", "status": "open"}]
    assert companionblocks.agenda_line(agenda)[1:] == [{"bar": [2, 3]}, {"t": "  2 of 3 done", "tone": "dim"}]


def test_a_flow_with_no_steps_draws_no_header_over_nothing():
    assert companionblocks.diagram_block({"kind": "sequence", "of": "FLO-1", "name": "Empty", "steps": []}) is None


def left_data(items):
    return {"view": "left", "items": items, "groups": []}


def test_the_left_view_leaves_out_apps_with_nothing_planned():
    items = [{"id": "a", "name": "Booking", "decided": 3, "total": 4}, {"id": "b", "name": "Vessel schedule", "decided": 0, "total": 0},
             {"id": "c", "name": "Payments", "decided": 1, "total": 2}]
    data = left_data(items)
    assert [r["name"] for r in companionblocks.explain_sections(data)[0]["rows"]] == ["Booking", "Payments"]
    assert [r["label"] for r in companionblocks.bars_block(data)["rows"]] == ["Booking", "Payments"]


def test_track_rows_use_the_headlines_status_words_and_flag_an_overdue_slice():
    data = {"view": "track", "as_of": "2026-10-24"}
    slice_row = companionblocks.view_row(data, {"id": "S", "name": "Pay", "status": "journey passes", "overdue": "2026-10-01"})
    assert (slice_row["note"], slice_row["chip"], slice_row["tone"]) == ("past their journey check", {"t": "overdue", "tone": "bad"}, "bad")
    shipped = companionblocks.view_row(data, {"id": "R1", "name": "R1", "target": "2026-10-01", "days_out": -23, "shipped": True})
    assert (shipped["mark"], shipped["note"]) == ("✔", "shipped")
    due = companionblocks.view_row(data, {"id": "R2", "name": "R2", "target": "2026-12-01", "days_out": 38})
    assert due["note"] == "due December 1"


def test_a_group_with_no_holder_gets_a_title_and_a_bar_label():
    item = {"id": "U", "name": "Q", "open_days": 3, "holds": [], "ask_by": ""}
    data = {"view": "stuck", "as_of": "2026-10-24", "items": [item, item], "groups": [{"who": "", "items": [item, item]}]}
    assert companionblocks.explain_sections(data)[0]["title"] == companionblocks.NO_HOLDER
    assert companionblocks.bars_block(data)["rows"][0]["label"] == companionblocks.NO_HOLDER


def test_a_wide_character_title_still_fits_the_band_in_cells():
    from vela import companionchart
    data = session_dict(session={"id": "s", "title": "漢字" * 30, "modes": [], "opened": "2026-10-24"}, decided=[], open=[])
    spans = companionblocks.band_spans(data)
    assert companionchart.width_of("".join(s["t"] for s in spans)) <= companionblocks.BAND_WIDTH


def test_explain_has_a_band_of_spans_and_no_diagram_text(plan):
    got = explain(plan, "--view", "stuck")
    assert got["band_spans"][0] == {"t": "What's stuck?", "tone": "strong"} and got["band_spans"][-1]["tone"] == "bad"
    flow = explain(plan, "--view", "flow", "--about", "Hold, pay, confirm")
    assert "text" not in flow["diagram"]


def test_the_chart_reference_flow_draws_in_the_session_diagram_block():
    diagram = {"kind": "sequence", "of": "FLO-001", "name": "Hold, pay, confirm", "steps": STEPS}
    block = companionblocks.diagram_block(diagram)
    assert block["drawings"]["60"] and block["alt"].startswith("Hold, pay, confirm: 7 steps.")


# --- explain --last asks the stored question again --------------------------------------------------------------------

def stored(plan):
    return plan / ".vela" / "companion" / "explain.json"


def test_last_answers_the_stored_question_again_so_its_blocks_are_always_current(plan):
    explain(plan, "--view", "flow", "--about", "Hold, pay, confirm")
    held = json.loads(stored(plan).read_text())
    assert held["version"] == 2 and held["about"] == "Hold, pay, confirm"
    del held["blocks"]
    stored(plan).write_text(json.dumps(held))
    code, out = run_companion(plan, "explain", "--last", "--json")
    got = json.loads(out)
    assert code == 0 and got["view"] == "flow" and types(got["blocks"]) == ["card", "diagram", "lines"]


def test_last_refuses_a_file_an_older_vela_wrote_and_says_so_in_vela_words(plan):
    explain(plan, "--view", "stuck")
    held = json.loads(stored(plan).read_text())
    stored(plan).write_text(json.dumps({**held, "version": 1}))
    code, out = run_companion(plan, "explain", "--last", "--json")
    assert code == 1 and json.loads(out) == {"message": "The last answer was written by an older vela and can't be redrawn. Ask the question again."}


def test_last_with_nothing_asked_yet_says_so(tmp_path):
    root = tmp_path / "plan"
    shutil.copytree(EXAMPLE, root)
    code, out = run_companion(root, "explain", "--last", "--json")
    assert code == 1 and json.loads(out) == {"message": "Nothing has been explained yet."}


def test_every_panel_json_carries_vela_words_for_a_pane_that_cannot_draw_it(grill):
    assert grill["version"] == 2 and grill["out_of_date"] == companionblocks.OUT_OF_DATE
