"""`vela map` (the running topic map): the first caller of each subcommand the dump, discover and grill skills will run.
The map is a working file under `.vela/map/`, so it outlives the model's memory and is never staged."""
import json

from conftest import run
from sharing import make_vault
from test_session_cli import TODAY, no_gh, start
from vela import guard

MAP = f".vela/map/{TODAY}-refunds.json"


def vela_map(vault, *args):
    return run("map", args[0], "--vault", str(vault), *args[1:])


def started(tmp_path, monkeypatch):
    vault = make_vault(tmp_path)
    no_gh(tmp_path, monkeypatch)
    code, output = start(vault, "--mode", "dump", "--topic", "refunds")
    assert code == 0, output
    return vault


def saved(vault):
    return json.loads((vault / MAP).read_text(encoding="utf-8"))


def test_add_tags_a_note_names_a_group_and_records_a_position(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    assert vela_map(vault, "add", "--kind", "goals", "Refunds paid within a day.") == (
        0, "added goals: Refunds paid within a day.\n")
    assert vela_map(vault, "add", "--group", "finance")[0] == 0
    code, output = vela_map(vault, "add", "--group", "sales", "--topic", "approval speed", "--position",
                            "same-day approval", "--reason", "deals cool", "--json")
    assert code == 0 and json.loads(output)["position"]["basis"] == "stated"
    state = saved(vault)
    assert [n["kind"] for n in state["notes"]] == ["goals"]
    assert [g["name"] for g in state["groups"]] == ["finance", "sales"]
    assert state["last"] == {"kind": "goals", "topic": "approval speed"}
    assert guard.never_rule(MAP) is guard.TOOL_STATE  # a close never stages it


def test_add_refuses_words_with_no_kind_and_an_unknown_kind(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    code, output = vela_map(vault, "add", "Refunds.")
    assert code == 1 and "need a --kind" in output
    code, output = vela_map(vault, "add", "--kind", "cash", "Refunds.", "--for-lead")
    assert (code, output) == (1, "Something went wrong on my side; I'll fix it and try again.\n")
    assert not (vault / MAP).exists()


def test_open_numbers_items_and_warns_once_three_wait(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    for n, text in enumerate(("Who signs off refunds.", "Whether the bank allows it."), start=1):
        assert vela_map(vault, "open", "--type", "gap", text) == (0, f"#{n} waiting (gap)\n")
    code, output = vela_map(vault, "open", "--type", "belief", "Partners always take an hourly file.", "--json")
    assert code == 0 and json.loads(output)["waiting"] == 3
    assert "summarize before opening another thread" in json.loads(output)["lines"][1]


def test_close_settles_a_waiting_item_and_refuses_a_missing_one(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    vela_map(vault, "open", "--type", "fact", "The date of the board meeting.")
    assert vela_map(vault, "close", "1", "--as", "recorded", "--how", "an open question for finance") == (
        0, "#1 recorded\n")
    assert saved(vault)["waiting"][0]["how"] == "an open question for finance"
    code, output = vela_map(vault, "close", "1")
    assert code == 1 and "already recorded" in output


def test_next_suggests_the_pair_side_by_side_then_the_unasked_group(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    vela_map(vault, "add", "--group", "sales", "--topic", "approval speed", "--position", "same day")
    vela_map(vault, "add", "--group", "finance", "--topic", "approval speed", "--position", "weekly review")
    vela_map(vault, "add", "--group", "legal")
    code, output = vela_map(vault, "next", "--json")
    moves = json.loads(output)["moves"]
    assert code == 0 and [m["move"] for m in moves[:2]] == ["side-by-side", "ask-group"]
    assert [h["group"] for h in moves[0]["holders"]] == ["sales", "finance"] and moves[1]["group"] == "legal"


def test_next_says_summarize_first_and_nothing_new_when_four_items_wait(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    vela_map(vault, "add", "--kind", "goals", "Faster refunds.")
    vela_map(vault, "add", "--group", "finance")
    for n in range(4):
        vela_map(vault, "open", "--type", "gap", f"Open point {n}.")
    code, output = vela_map(vault, "next", "--json")
    moves = json.loads(output)["moves"]
    assert code == 0 and [m["move"] for m in moves] == ["summarize"] and len(moves[0]["waiting"]) == 4
    assert vela_map(vault, "next")[1].startswith("1. [summarize] 4 items wait: summarize first")


def test_show_for_lead_reads_back_covered_empty_and_about_four_waiting(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    for kind in ("goals", "people", "systems", "data", "rules", "risks", "owners"):
        vela_map(vault, "add", "--kind", kind, f"Something on {kind}.")
    for n in range(6):
        vela_map(vault, "open", "--type", "gap", f"Open point {n}.")
    code, output = vela_map(vault, "show", "--for-lead")
    assert code == 0
    assert output.splitlines() == [
        "So far we've covered goals, people, systems, data, rules, risks and owners. Nothing yet on dates or money.",
        "To check: Open point 0.", "To check: Open point 1.", "To check: Open point 2.", "To check: Open point 3.",
        "Two more; want them?", "Which of these is wrong?"]
    assert len(vela_map(vault, "show", "--for-lead", "--more")[1].splitlines()) == 8


def test_show_with_nothing_yet_writes_no_file(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    assert vela_map(vault, "show", "--for-lead") == (0, "Nothing's on the map yet.\n")
    assert not (vault / MAP).exists()


def test_no_open_session_exits_1_and_an_unreadable_map_exits_2(tmp_path, monkeypatch):
    code, output = vela_map(make_vault(tmp_path / "bare"), "next")
    assert (code, output) == (1, "No session is open, so there's no topic map to keep.\n")
    vault = started(tmp_path, monkeypatch)
    (vault / MAP).parent.mkdir(parents=True, exist_ok=True)
    (vault / MAP).write_text("{broken", encoding="utf-8")
    assert vela_map(vault, "show", "--for-lead") == (2, "I couldn't read or save the session's topic map.\n")
