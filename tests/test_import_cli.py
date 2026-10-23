"""`vela import` (the guided importer's queue), `vela decide --stated-in` and the kept wording: the first caller of each
subcommand the import skill runs, and the rules the user set for an import.

- A decision a document states is decided only with the lead's recorded yes, citing the document; the check accepts
  that and nothing less.
- The lead is asked about four things at a time, each with a proposed answer, and no new batch while one waits.
- Whether a document's prose is voiced is the lead's answer, recorded; until they give it, the page keeps the
  documents' words, close owes it no voiced prose, and the voice checks hold those words exactly.
"""
import json
import re

from conftest import run
from sharing import git, make_vault
from test_session_cli import TODAY, no_gh, start
from vela import closedrafts, cli, guard, importqueue, say, voicecheck, voicescore, wording
import session_files

RECORD_ID = f"{TODAY}-partner-files"
RECORD = f"sessions/{RECORD_ID}.md"
QUEUE = f".vela/import/{RECORD_ID}.json"
SOURCES = """| SRC-01 | Stock read API documentation | @stock-team | 2026-01-02 | exists | local only |
| SRC-02 | Partner guide | @partners | 2026-03-01 | exists | .inbox/partner-guide.md |
| SRC-03 | Ops runbook | @ops | 2026-09-01 | exists | .inbox/ops-runbook.md |
| SRC-04 | Architecture decision log | @cto | 2026-03-03 | exists | .inbox/adr-log.md |
"""
ADR = "09-decisions/ADR-0001-nightly-partner-file.md"
ADR_TEXT = """---
id: ADR-0001
type: decision
title: Nightly partner file
state: proposed
owner: "@mini-lead"
authored: authored
---

# Nightly partner file

Partners get one booking file a night, as the decision log records.

## History
"""
CAPTURES = [
    '- [thought] (claude) Read back: the nightly partner file, decided by the CTO on March 3 per the decision log ^c01',
    '- [answer] (@priya) "Yes, that one stands." ^c02',
    '- [answer] (@priya) "ok" ^c03',
    '- [answer] (claude) "Yes" ^c04',
    '- [answer] (@priya) "Split it the way you said: quote the terms, voice the rest." ^c05',
]


def vela_import(vault, *args):
    return run("import", args[0], "--vault", str(vault), *args[1:])


def started(tmp_path, monkeypatch, captures=()):
    vault = make_vault(tmp_path)
    no_gh(tmp_path, monkeypatch)
    register = vault / "sources.md"
    text = register.read_text(encoding="utf-8")
    register.write_text(text.replace(SOURCES.split("\n")[0] + "\n", SOURCES), encoding="utf-8")
    git(vault, "commit", "-q", "-am", "the documents registered")
    code, output = start(vault, "--mode", "discover", "--topic", "partner files")
    assert code == 0, output
    if captures:
        text = session_files.record_text(vault, RECORD_ID)
        session_files.write_record(vault, RECORD_ID, text.replace("## Captures\n", "## Captures\n\n" + "\n".join(captures) + "\n", 1))
    return vault


def saved(vault):
    return json.loads((vault / QUEUE).read_text(encoding="utf-8"))


def queue(vault, kind, text, *sources, propose="decided, citing the document", why="the document names who and when"):
    args = ["add", "--type", kind, text, "--propose", propose, "--why", why]
    for source in sources:
        args += ["--source", source]
    return vela_import(vault, *args)


# --- add, next, close, show: the first callers ------------------------------------------------------------------------

def test_add_queues_an_item_with_its_sources_and_proposal_and_never_stages_the_file(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    assert queue(vault, "decision", "Partners get one booking file a night.", "SRC-04") == (0, "#1 queued (decision)\n")
    item = saved(vault)["items"][0]
    assert (item["sources"], item["state"], item["proposal"]) == (["SRC-04"], "waiting", "decided, citing the document")
    assert guard.never_rule(QUEUE) is guard.TOOL_STATE


def test_add_refuses_an_unregistered_source_a_one_sided_clash_and_plumbing_in_the_words(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    code, output = queue(vault, "decision", "Something.", "SRC-09")
    assert code == 1 and "isn't in the sources register" in output
    code, output = queue(vault, "clash", "Nightly or hourly.", "SRC-02")
    assert code == 1 and "both sources" in output
    code, output = vela_import(vault, "add", "--type", "stale", "Read .inbox/partner-guide.md for the date.", "--source", "SRC-02",
                               "--propose", "ask", "--why", "it may have moved", "--for-lead")
    assert (code, output) == (1, say.MY_SIDE + "\n")
    assert not (vault / QUEUE).exists()


def test_next_hands_out_at_most_four_clashes_first_each_with_a_proposal(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    for n in range(4):
        queue(vault, "decision", f"Decision {n} was approved.", "SRC-04")
    queue(vault, "clash", "The guide says nightly; the runbook says hourly.", "SRC-02", "SRC-03",
          propose="the runbook wins", why="it is newer and the ops team runs the file")
    queue(vault, "stale", "The guide's partner count is from March.", "SRC-02", propose="ask partners for the count",
          why="three partners joined since")
    code, output = vela_import(vault, "next", "--json")
    data = json.loads(output)
    assert code == 0 and [i["type"] for i in data["batch"]] == ["clash", "stale", "decision", "decision"]
    assert len(data["batch"]) == importqueue.BATCH == say.LEAD_LIMIT and data["waiting"] == 2
    assert [i["state"] for i in saved(vault)["items"]].count("asked") == 4


def test_next_for_lead_says_each_with_the_proposal_and_names_sources_by_title(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    queue(vault, "clash", "The guide says nightly; the runbook says hourly.", "SRC-02", "SRC-03",
          propose="the runbook wins", why="it is newer")
    code, output = vela_import(vault, "next", "--for-lead")
    assert code == 0
    assert output.splitlines() == [
        "One thing from the documents to settle, with what I'd do.",
        "Partner guide and Ops runbook disagree: The guide says nightly; the runbook says hourly. I'd say: the "
        "runbook wins, because it is newer.",
        "Yes to these, or which would you change?"]


def test_no_new_batch_while_one_waits_then_the_next_four_once_it_is_settled(tmp_path, monkeypatch):
    """The batch-of-four rule: the lead never holds more than about four open things at once."""
    vault = started(tmp_path, monkeypatch)
    for n in range(6):
        queue(vault, "decision", f"Decision {n} was approved.", "SRC-04")
    first = json.loads(vela_import(vault, "next", "--json")[1])["batch"]
    again = json.loads(vela_import(vault, "next", "--json")[1])
    assert again["reopened"] and [i["n"] for i in again["batch"]] == [i["n"] for i in first]
    for item in first[:3]:
        assert vela_import(vault, "close", str(item["n"]), "--as", "decided")[0] == 0
    assert json.loads(vela_import(vault, "next", "--json")[1])["batch"] == [
        i for i in saved(vault)["items"] if i["n"] == first[3]["n"]]
    vela_import(vault, "close", str(first[3]["n"]), "--as", "assumption", "--how", "the lead isn't sure")
    rest = json.loads(vela_import(vault, "next", "--json")[1])
    assert not rest["reopened"] and [i["n"] for i in rest["batch"]] == [5, 6]


def test_close_takes_only_an_asked_item_and_an_outcome_its_type_allows(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    queue(vault, "clash", "Nightly or hourly.", "SRC-02", "SRC-03")
    code, output = vela_import(vault, "close", "1", "--as", "open")
    assert code == 1 and "hasn't been asked yet" in output
    vela_import(vault, "next")
    code, output = vela_import(vault, "close", "1", "--as", "decided")
    assert code == 1 and "a clash ends as chosen, open, set-aside" in output
    assert vela_import(vault, "close", "1", "--as", "open", "--how", "one open question naming both")[1] == (
        "#1 open; batch done: import next for more\n")
    code, output = vela_import(vault, "close", "1", "--as", "chosen")
    assert code == 1 and "already open" in output


def test_show_for_lead_reads_back_settled_asked_and_waiting(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    assert vela_import(vault, "show", "--for-lead") == (0, "Nothing from the documents is queued yet.\n")
    for n in range(5):
        queue(vault, "decision", f"Decision {n} was approved.", "SRC-04")
    vela_import(vault, "next")
    vela_import(vault, "close", "1", "--as", "decided")
    code, output = vela_import(vault, "show", "--for-lead")
    lines = output.splitlines()
    assert code == 0 and lines[0] == "From the documents: one settled, three with you now, one still to ask."
    assert len(lines) == 5 and lines[-1] == "Which of these is wrong?" and "SRC-" not in output


def test_no_open_session_exits_1(tmp_path, monkeypatch):
    vault = make_vault(tmp_path)
    assert vela_import(vault, "next") == (1, "No session is open, so there's no import queue to keep.\n")


# --- decided with the lead's yes, citing the document -----------------------------------------------------------------

def with_adr(vault):
    path = vault / ADR
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ADR_TEXT, encoding="utf-8")
    git(vault, "add", ADR)
    git(vault, "commit", "-q", "-m", "import: the decision log's first entry")
    return path


def check_codes(vault):
    code, output = run("check", "--vault", str(vault))
    return set(re.findall(r"\b([EW]\d{3})\b", output))


def test_a_stated_decision_is_decided_with_the_yes_citing_the_document(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch, CAPTURES)
    path = with_adr(vault)
    code, output = run("decide", "ADR-0001", "--readback", "^c01", "--yes", "^c02", "--stated-in", "SRC-04",
                       "--vault", str(vault), "--today", TODAY, "--json")
    assert code == 0, output
    text = path.read_text(encoding="utf-8")
    assert "state: decided" in text and f"- **Decision:** [[{RECORD_ID}]], as SRC-04 states" in text
    assert f"| ADR-0001 | proposed | decided | [[{RECORD_ID}#^c02]] |" in session_files.record_text(vault, RECORD_ID)
    assert git(vault, "log", "-1", "--format=%s") == "import: ADR-0001 decided, as SRC-04 states"
    assert "E303" not in check_codes(vault)


def test_a_stated_decision_without_a_real_yes_is_refused_and_nothing_written(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch, CAPTURES)
    path = with_adr(vault)
    for yes in ("^c03", "^c04"):  # a bare "ok", and Claude's own "Yes"
        code, _ = run("decide", "ADR-0001", "--readback", "^c01", "--yes", yes, "--stated-in", "SRC-04",
                      "--vault", str(vault), "--today", TODAY)
        assert code == 1
    code, output = run("decide", "ADR-0001", "--readback", "^c01", "--yes", "^c02", "--stated-in", "SRC-09",
                       "--vault", str(vault), "--today", TODAY)
    assert code == 1 and "decide-stated-in" in output
    assert path.read_text(encoding="utf-8") == ADR_TEXT


def test_a_decided_page_citing_no_source_still_needs_a_grill(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch, CAPTURES)
    path = with_adr(vault)
    path.write_text(ADR_TEXT.replace("state: proposed", "state: decided") + f"\n- **Decision:** [[{RECORD_ID}]]\n",
                    encoding="utf-8")
    assert "E303" in check_codes(vault)
    path.write_text(ADR_TEXT.replace("state: proposed", "state: decided")
                    + f"\n- **Decision:** [[{RECORD_ID}]], as SRC-09 states\n", encoding="utf-8")
    assert "E303" in check_codes(vault)  # a source that isn't in the register states nothing


# --- the voice question: asked, recorded, applied per page --------------------------------------------------------------

PAGE = "03-context-and-scope.md"
KEPT_PAGE = """---
id: context
type: initiative-section
title: Context
state: fact
owner: "@mini-lead"
authored: authored
sources: [SRC-02]
---

# Context

Partners get the booking file each night.

> "The supplier shall deliver the booking file by 02:00 UTC." ([[sources#SRC-02|Partner guide]])
"""


def test_wording_needs_the_leads_own_answer_and_page_applies_it(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch, CAPTURES)
    (vault / PAGE).write_text(KEPT_PAGE, encoding="utf-8")
    for bad in ("^c03", "^c04", "^c99"):
        code, output = vela_import(vault, "wording", "--as", "split", "--yes", bad)
        assert code == 1, bad
    assert vela_import(vault, "wording", "--as", "split", "--yes", "^c05")[0] == 0
    code, output = vela_import(vault, "page", PAGE, "--source", "SRC-02", "--json")
    assert code == 0 and PAGE in json.loads(output)["wrote"]
    meta = (vault / PAGE).read_text(encoding="utf-8")
    assert "source-wording: split" in meta and f'source-wording-yes: "[[{RECORD_ID}]] c05"' in meta
    assert "E361" not in check_codes(vault)


def test_until_the_lead_answers_a_page_keeps_the_documents_words(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch, CAPTURES)
    (vault / PAGE).write_text(KEPT_PAGE, encoding="utf-8")
    code, output = vela_import(vault, "page", PAGE, "--source", "SRC-02", "--for-lead")
    assert (code, output) == (0, "That page keeps the documents' words as written.\n")
    text = (vault / PAGE).read_text(encoding="utf-8")
    assert "source-wording: keep" in text and "source-wording-yes" not in text


def test_one_sources_keep_is_never_voiced_because_anothers_was(tmp_path, monkeypatch):
    state = importqueue.new_state("s")
    importqueue.set_wording(state, "voice", "^c05")
    importqueue.set_wording(state, "keep", "^c06", "SRC-03")
    assert importqueue.wording_for(state, ["SRC-02"]) == ("voice", "^c05")
    assert importqueue.wording_for(state, ["SRC-02", "SRC-03"]) == ("keep", "^c06")
    assert importqueue.wording_for(importqueue.new_state("s"), ["SRC-02"]) == ("keep", "")


def test_a_voiced_page_with_no_answer_on_record_fails_the_check(tmp_path, monkeypatch):
    """No voiced rewrite without a recorded answer: a page set to split or voice by hand with no reference to a
    session in the plan is E361. Whether the capture is the lead's own words is `vela import wording`'s test, made
    where the notes are, because the notes never reach a clone."""
    vault = started(tmp_path, monkeypatch, CAPTURES)
    voiced = KEPT_PAGE.replace("sources: [SRC-02]\n", "sources: [SRC-02]\nsource-wording: voice\n")
    (vault / PAGE).write_text(voiced, encoding="utf-8")
    assert "E361" in check_codes(vault)
    for bad in (f'"[[{RECORD_ID}#^c05]]"', '"[[no-such-session]] c05"', '"c05"'):
        (vault / PAGE).write_text(voiced.replace("source-wording: voice\n", f"source-wording: voice\nsource-wording-yes: {bad}\n"),
                                  encoding="utf-8")
        assert "E361" in check_codes(vault), bad
    (vault / PAGE).write_text(voiced.replace("source-wording: voice\n", "source-wording: voice\n"
                                             f'source-wording-yes: "[[{RECORD_ID}]] c05"\n'), encoding="utf-8")
    assert "E361" not in check_codes(vault)


def test_close_owes_no_voiced_prose_on_a_kept_page_and_lists_it(tmp_path, monkeypatch):
    vault = started(tmp_path, monkeypatch)
    kept = KEPT_PAGE.replace("sources: [SRC-02]\n", "sources: [SRC-02]\nsource-wording: keep\n")
    (vault / PAGE).write_text(kept, encoding="utf-8")
    after = cli.load_vault(vault)
    found = closedrafts.owed(closedrafts.vault_before(after, {PAGE: None}), after, {PAGE: None})
    assert PAGE not in [p.page for p in found.paragraphs] and found.kept == [PAGE]
    (vault / PAGE).write_text(kept.replace("source-wording: keep", "source-wording: split"), encoding="utf-8")
    after = cli.load_vault(vault)
    found = closedrafts.owed(closedrafts.vault_before(after, {PAGE: None}), after, {PAGE: None})
    assert PAGE in [p.page for p in found.paragraphs] and found.kept == []


def test_kept_wording_versus_voiced_text_in_the_voice_checks():
    """A split page: the quoted terms are the documents' own (never scored, held exactly by the rewrite check); its
    own sentence is the plan's voice and may be rewritten."""
    split = KEPT_PAGE.replace("sources: [SRC-02]\n", "sources: [SRC-02]\nsource-wording: split\n")
    assert [p.text for p in voicescore.paragraphs(split)] == ["Partners get the booking file each night."]
    reworded = split.replace("Partners get the booking file each night.", "Each night, partners receive the file.")
    assert voicecheck.compare(split, reworded).same
    smoothed = split.replace("shall deliver the booking file by", "sends the booking file before")
    assert [t.kind for t in voicecheck.compare(split, smoothed).missing] == ["source"]
    kept = split.replace("source-wording: split", "source-wording: keep")
    assert voicescore.paragraphs(kept) == []
    assert not voicecheck.compare(kept, kept.replace("Partners get", "Partners receive")).same
    voiced = split.replace("source-wording: split", "source-wording: voice")
    assert wording.wording_of({"source-wording": "voice"}) == "voice"
    assert voicecheck.compare(voiced, voiced.replace("shall deliver", "delivers")).same
