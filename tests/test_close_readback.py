"""The read-back at close (Task 10): the lead keeps, rewords or cuts every sentence that goes on record in their name,
and the gate waits for `--done`. A sentence edited after `--done` reopens it."""
import json

from conftest import run
from vela import closegate, closereadback
from vela.decisions import consent
from sharing import git, make_vault, with_remote
import session_files

RECORD = "2026-10-20-grill-stock"
STOCK = "05-building-blocks/stock-building-blocks.md"
DECISION = f'- **Decision:** [[{RECORD}]] c01, @priya: "Yes, one till API for the web and the kiosks."'
WHY = "- **Why:** Because the kiosks can't run two APIs."
MARK = " → keep: [[stock-building-blocks#CON-002 Stock level|CON-002]] (decided)"
CAPTURES = (
    f'- [thought] (@priya) "Yes, one till API for the web and the kiosks." says yes{MARK} ^c01',
    '- [thought] (@priya) "Because the kiosks can\'t run two APIs." → park ^c02',
    '- [thought] (@cto-ana) "Fine by me." → park ^c08',
    '- [thought] (@priya) "Yes, say it as one till API for everything." → park ^c09',
)
ROW = f"| CON-002 | fact | decided | [[{RECORD}#^c01]] |"


def record_text():
    lines = ["---", f"id: {RECORD}", "type: session", "date: 2026-10-20", "modes: [grill]", "status: open",
             "summary: In progress.", "---", "", "# 2026-10-20 Stock grill", "", "## Captures", "", *CAPTURES, "",
             "## Changes", "", "| ID | From | To | Source |", "|---|---|---|---|", ROW]
    return "\n".join(lines) + "\n"


def closing_vault(tmp_path):
    vault = make_vault(tmp_path)
    with_remote(tmp_path, vault)
    git(vault, "switch", "-q", "-c", f"session/{RECORD}")
    session_files.write_record(vault, RECORD, record_text())
    git(vault, "add", "sessions")
    git(vault, "commit", "-q", "-m", f"Open session {RECORD}")
    assert run("close", "sync-main", "--vault", str(vault), "--today", "2026-10-20")[0] == 0
    (vault / ".vela").mkdir(exist_ok=True)
    (vault / ".vela" / "handle").write_text("priya\n", encoding="utf-8")
    page = vault / STOCK
    decided = f"- **State:** decided\n{DECISION}\n{WHY}\n- **Tested by:** the stock read test on both sides"
    page.write_text(page.read_text(encoding="utf-8").replace("- **State:** fact", decided, 1), encoding="utf-8")
    assert run("render", "--vault", str(vault))[0] == 0
    return vault


def readback(vault, *flags):
    return run("close", "readback", *flags, "--vault", str(vault))


def gate_kinds(vault):
    code, out = run("close", "gate", "--vault", str(vault), "--json", "--today", "2026-10-20")
    return {p["kind"] for p in json.loads(out)["problems"]}


def page_text(vault):
    return (vault / STOCK).read_text(encoding="utf-8")


def test_gate_waits_for_the_read_back_and_clears_after_done(tmp_path):
    vault = closing_vault(tmp_path)
    assert closegate.READBACK in gate_kinds(vault)
    code, out = run("close", "gate", "--vault", str(vault), "--for-lead", "--today", "2026-10-20")
    assert "I haven't read back the wording that goes on record in your name yet." in out
    assert readback(vault, "--done")[0] == 0
    assert closegate.READBACK not in gate_kinds(vault)


def test_the_list_names_the_decision_and_the_why(tmp_path):
    vault = closing_vault(tmp_path)
    code, out = readback(vault, "--json")
    found = {(s["item"], s["line"]): s for s in json.loads(out)["sentences"]}
    assert found[("CON-002", "decision")]["words"] == "Yes, one till API for the web and the kiosks."
    assert found[("CON-002", "decision")]["number"] == 1
    assert found[("CON-002", "why")]["words"] == "Because the kiosks can't run two APIs."
    assert found[("CON-002", "why")]["number"] == 2
    code, out = readback(vault, "--for-lead")
    assert code == 0 and "Stock level" in out and "CON-002" not in out and "^c" not in out


def test_a_reword_must_be_an_excerpt_or_an_approved_wording(tmp_path):
    vault = closing_vault(tmp_path)
    before = page_text(vault)
    code, out = readback(vault, "--reword", "CON-002", "--line", "decision", "--words", "a new thing")
    assert code == 1
    assert "readback-words-not-yours" in out and "run again with --approved ^cNN" in out
    assert page_text(vault) == before
    assert readback(vault, "--reword", "CON-002", "--line", "decision", "--words", "one till API")[0] == 0
    assert f'c01, @priya: "one till API"' in page_text(vault)
    words = "one till API for everything"
    assert readback(vault, "--reword", "CON-002", "--line", "decision", "--words", words)[0] == 1
    code, out = readback(vault, "--reword", "CON-002", "--line", "decision", "--words", words, "--approved", "^c09")
    assert code == 0, out
    assert f'[[{RECORD}]] c09, @priya: "{words}"' in page_text(vault)


def test_a_reworded_why_stays_an_excerpt_of_what_the_lead_said(tmp_path):
    vault = closing_vault(tmp_path)
    assert readback(vault, "--reword", "CON-002", "--line", "why", "--words", "the kiosks can't run two APIs")[0] == 0
    assert "- **Why:** the kiosks can't run two APIs" in page_text(vault)
    assert readback(vault, "--reword", "CON-002", "--line", "why", "--words", "it is cheaper")[0] == 1


def test_an_approval_that_is_not_the_leads_is_refused(tmp_path):
    vault = closing_vault(tmp_path)
    before = page_text(vault)
    code, out = readback(vault, "--reword", "CON-002", "--line", "decision", "--words", "Fine by me", "--approved", "^c08")
    assert code == 1 and page_text(vault) == before


def test_editing_a_sentence_after_done_reopens_the_read_back(tmp_path):
    vault = closing_vault(tmp_path)
    assert readback(vault, "--done")[0] == 0
    assert closegate.READBACK not in gate_kinds(vault)
    assert readback(vault, "--reword", "CON-002", "--line", "why", "--words", "the kiosks can't run two APIs")[0] == 0
    assert closegate.READBACK in gate_kinds(vault)
    assert readback(vault, "--done")[0] == 0
    assert closegate.READBACK not in gate_kinds(vault)


def test_pick_refuses_someone_elses_words(tmp_path):
    vault = closing_vault(tmp_path)
    code, out = readback(vault, "--pick", "^c08", "--for-lead")
    assert code == 1 and "someone else's words" in out
    assert not (vault / ".vela" / "close" / f"{RECORD}.quotes.json").exists()


def test_a_picked_quote_joins_the_read_back_and_can_be_cut(tmp_path):
    vault = closing_vault(tmp_path)
    assert readback(vault, "--done")[0] == 0
    assert readback(vault, "--pick", "^c02")[0] == 0
    quotes = json.loads((vault / ".vela" / "close" / f"{RECORD}.quotes.json").read_text(encoding="utf-8"))
    assert quotes["quotes"][0]["words"] == "Because the kiosks can't run two APIs."
    assert closegate.READBACK in gate_kinds(vault)  # the new quote was not read back yet
    assert readback(vault, "--done")[0] == 0
    item = quotes["quotes"][0]["item"] or "^c02"
    assert readback(vault, "--reword", item, "--line", "quote", "--words", "the kiosks can't run two APIs")[0] == 0
    assert closegate.READBACK in gate_kinds(vault)
    assert readback(vault, "--cut", item, "--line", "quote")[0] == 0
    assert json.loads((vault / ".vela" / "close" / f"{RECORD}.quotes.json").read_text(encoding="utf-8")) == {"quotes": []}


def test_a_decision_can_be_reworded_but_not_cut(tmp_path):
    vault = closing_vault(tmp_path)
    before = page_text(vault)
    code, out = readback(vault, "--cut", "CON-002", "--line", "decision", "--for-lead")
    assert code == 1 and "Your decision needs your words on record, so I can reword it but not cut it." in out
    assert page_text(vault) == before


def test_a_why_line_can_be_cut(tmp_path):
    vault = closing_vault(tmp_path)
    assert readback(vault, "--cut", "CON-002", "--line", "why")[0] == 0
    assert "**Why:**" not in page_text(vault) and DECISION in page_text(vault)


def test_a_session_with_no_words_on_record_owes_no_read_back(tmp_path):
    vault = closing_vault(tmp_path)
    page = vault / STOCK
    page.write_text(page_text(vault).replace(WHY + "\n", "").replace(
        'c01, @priya: "Yes, one till API for the web and the kiosks."', "c01, @priya"), encoding="utf-8")
    assert closegate.READBACK not in gate_kinds(vault)
    assert "nothing" in readback(vault)[1].lower()


# ---- the pure half

def test_the_digest_follows_the_words():
    one = closereadback.Sentence("CON-002", "why", "p.md", 2, "because")
    two = closereadback.Sentence("CON-002", "why", "p.md", 2, "because it is cheaper")
    assert closereadback.digest([one]) == closereadback.digest([one])
    assert closereadback.digest([one]) != closereadback.digest([two])


def test_is_excerpt_ignores_case_and_curly_marks():
    assert closereadback.is_excerpt("Can’t run two APIs", "Because the kiosks can't run two APIs.")
    assert not closereadback.is_excerpt("", "anything")


def test_a_curly_apostrophe_still_takes_back_a_quote_yes():
    for said in ("Yes, but don’t quote me", "Yes, but don't quote me", "Yes, but I won’t be quoted"):
        assert consent.NEGATION.search(said), said


# ---- review round 1

def test_a_why_traces_to_the_leads_capture_not_someone_elses(tmp_path):
    vault = closing_vault(tmp_path)
    page = vault / STOCK
    page.write_text(page_text(vault).replace(WHY, "- **Why:** Fine by me."), encoding="utf-8")
    code, out = readback(vault, "--json")
    why = next(s for s in json.loads(out)["sentences"] if s["line"] == "why")
    assert why["number"] == 0  # ^c08 is cto-ana's
    code, out = readback(vault, "--for-lead")
    assert "not traceable to your words" in out and "^c00" not in out
    assert readback(vault, "--reword", "CON-002", "--line", "why", "--words", "Fine")[0] == 1
    code, out = readback(vault, "--reword", "CON-002", "--line", "why", "--words", "Yes, say it as one till API",
                         "--approved", "^c09")
    assert code == 0, out


def test_two_whys_on_one_item_need_number(tmp_path):
    vault = closing_vault(tmp_path)
    page = vault / STOCK
    second = "- **Why:** Yes, one till API for the web"
    page.write_text(page_text(vault).replace(WHY, WHY + "\n" + second), encoding="utf-8")
    code, out = readback(vault, "--cut", "CON-002", "--line", "why")
    assert code == 1 and "--number" in out
    assert readback(vault, "--cut", "CON-002", "--line", "why", "--number", "c01")[0] == 0
    assert second not in page_text(vault) and WHY in page_text(vault)


def test_with_no_known_lead_everything_is_listed_but_nothing_changes(tmp_path):
    vault = closing_vault(tmp_path)
    (vault / ".vela" / "handle").unlink()
    code, out = readback(vault, "--for-lead")
    assert code == 0 and "don't know your GitHub handle" in out and "Yes, one till API" in out
    assert "vela whoami" in readback(vault)[1]
    before = page_text(vault)
    code, out = readback(vault, "--cut", "CON-002", "--line", "why")
    assert code == 1 and "don't know your GitHub handle" in out and page_text(vault) == before
    assert readback(vault, "--reword", "CON-002", "--line", "decision", "--words", "one till API")[0] == 1
    assert page_text(vault) == before


def test_a_hand_edited_quotes_file_cannot_add_words(tmp_path):
    vault = closing_vault(tmp_path)
    folder = vault / ".vela" / "close"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{RECORD}.readback.json").write_text("[]", encoding="utf-8")
    code, out = run("close", "gate", "--vault", str(vault), "--today", "2026-10-20")
    assert code == 2 and "isn't a JSON object" in out
    assert readback(vault, "--done")[0] == 0
    (folder / f"{RECORD}.quotes.json").write_text(json.dumps({"quotes": [
        {"number": 8, "words": "Fine by me.", "item": ""}, {"number": 1, "words": "We all agree", "item": ""},
        {"number": 2, "words": "kiosks can't run", "item": ""}]}), encoding="utf-8")
    code, out = readback(vault, "--json")
    quotes = [s["words"] for s in json.loads(out)["sentences"] if s["line"] == "quote"]
    assert quotes == ["kiosks can't run"]
    (folder / f"{RECORD}.quotes.json").write_text('{"quotes": 3}', encoding="utf-8")
    assert run("close", "gate", "--vault", str(vault), "--today", "2026-10-20")[0] == 2


def test_a_picked_quote_the_notes_do_not_back_stops_the_send(tmp_path):
    """Silent Fallback guard: a hand-added pick with no yes is refused at the gate, never quietly skipped."""
    vault = closing_vault(tmp_path)
    assert readback(vault, "--done")[0] == 0
    folder = vault / ".vela" / "close"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{RECORD}.quotes.json").write_text(json.dumps({"quotes": [
        {"number": 8, "words": "Fine by me.", "item": ""}]}), encoding="utf-8")
    code, out = run("close", "gate", "--vault", str(vault), "--json", "--today", "2026-10-20")
    problems = json.loads(out)["problems"]
    assert [p for p in problems if p["kind"] == "receipt" and "Fine by me." in p["detail"]]
    (folder / f"{RECORD}.quotes.json").write_text(json.dumps({"quotes": []}), encoding="utf-8")
    assert "receipt" not in gate_kinds(vault)


def test_no_handle_is_said_and_not_a_quiet_pass(tmp_path):
    vault = closing_vault(tmp_path)
    (vault / ".vela" / "handle").unlink()
    code, out = run("close", "gate", "--vault", str(vault), "--json", "--today", "2026-10-20")
    notes = json.loads(out).get("notes", [])
    assert any("I don't know your handle, so I haven't judged whose words are in the receipts." in n["plain"] for n in notes), out
