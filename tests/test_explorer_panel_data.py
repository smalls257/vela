"""The right-hand panel's content for a team's design, worked out ahead of the page (explorer/panel_data.py).

Each test names the Violation it guards. A panel that shows `CON-002` is a Leaky Narrative; one that ties a risk to a
component the design never tied it to is a Paper Tiger drawn tidy; one that fills a missing section with a guess is a
Silent Fallback. The page's own clicks are tested in the browser (selftest-inside.js, test_explorer_panel_browser.py).
"""
import pathlib
import re
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "plugin" / "lib"))

from vela import cli  # noqa: E402
from vela.explorer import build, design_data, panel_data  # noqa: E402

HERON = REPO / "tests" / "sim" / "snapshots" / "heron-desk" / "after-design-2"
APP = "APP-desktop-agent"
CODE = re.compile(r"\b(?:CAP-\d{3}(?:\.FR\d+)?|CON-\d{3}|UNK-\d{3}|EPC-\d{3}(?:[. ]AC\d+)?|CST-\d+|PTY-\d{2,3}|OQ-\d{3}|D-\d{3}|ADR-\d{4}|FLO-\d{3})\b")
ID_KEYS = {"id", "key", "ids", "index", "flow"}  # the places an ID may travel, for a link to use


def extract(root):
    vault = cli.load_vault(root)
    designs = design_data.designs_for([f"{APP}={root / 'docs' / 'tech-design' / 'desktop-agent.md'}"])
    return vault, build.extract(vault, root, "2026-10-12", None, designs, None, None)


@pytest.fixture(scope="module")
def heron():
    vault, data = extract(HERON)
    return vault, data, data["insidePanel"][APP]


def strings(value, path=()):
    """Every (path, text) a panel value shows, leaving out the keys an ID may travel under."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for k, v in value.items():
            if k not in ID_KEYS:
                yield from strings(v, path + (k,))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from strings(v, path + (i,))


def test_the_summary_says_what_it_is_the_stack_the_top_risks_targets_and_gaps(heron):
    _, _, panel = heron
    s = panel["summary"]
    assert s["app"] == "Desktop agent"
    assert s["what"] and len(s["what"]) <= 300 and s["what"].endswith("."), "a card at a glance says what it is in a few whole sentences"
    assert "Tauri" in s["stack"] and " · " in s["stack"], "the stack is one line"
    assert s["risks"]["total"] == 9 and s["risks"]["high"] == 2
    assert [r["severity"] for r in s["risks"]["top"]][:2] == ["high", "high"], "worst first"
    assert s["targets"][0]["concern"] == "Idle CPU" and s["targets"][0]["how"]
    assert s["gaps"]["total"] == len(s["gaps"]["items"]) and s["gaps"]["total"] > 0
    assert [x["id"] for x in s["sections"]][:3] == ["overview", "coverage", "data"] and len(s["sections"]) == 12
    counts = {x["id"]: x["count"] for x in s["sections"]}
    assert counts["risks"] == 9 and counts["stack"] == 5 and counts["overview"] is None


def test_a_component_section_has_what_it_delivers_its_contracts_its_flows_and_what_waits(heron):
    _, _, panel = heron
    c = panel["components"]["NoteClient"]
    assert c["partOf"] == "Desktop agent" and c["container"] == "Source reader"
    assert "Summarizer" in c["lead"] and c["owns"]
    assert "Write each person's digest" in c["delivers"]["requirements"], "a requirement is said by its name"
    assert c["delivers"]["contracts"] == [{"id": "CON-002", "name": "Note request"}]
    assert {e["epic"] for e in c["delivers"]["criteria"]} >= {"Show the 7:30 digest", "Show a prep note before a meeting"}
    assert c["delivers"]["total"] == len(c["delivers"]["requirements"]) + 1 + sum(len(e["items"]) for e in c["delivers"]["criteria"]) + len(c["delivers"]["other"])
    assert c["exposes"] and "requestDigest" in c["exposes"]
    links = [seg["link"] for seg in c["dependsOn"] if seg.get("link")]
    assert {"kind": "component", "name": "ConsentGate"} in links and {"kind": "outside", "name": "Summarizer"} in links
    assert [q["id"] for q in c["waiting"]] == ["OQ-003", "OQ-007", "OQ-008"]
    assert c["flows"] == [], "no key flow names NoteClient, and the panel says none rather than borrowing one"


def test_only_real_links_each_list_is_what_the_design_ties_to_the_component(heron):
    vault, data, panel = heron
    design = data["designs"][APP]
    names = [c["name"] for c in design["components"]]
    for name, c in panel["components"].items():
        affects = {q["id"] for q in design["open_questions"] if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", q["affects"], re.I)}
        assert {q["id"] for q in c["waiting"]} == affects, f"{name}: waiting is exactly the questions whose Affects names it"
        sequences = [f for f in panel["flows"] if name in f["who"]]
        assert [f["index"] for f in sequences] == [f["index"] for f in c["flows"]], f"{name}: flows are the ones that name it as a participant"
        assert not {"risks", "decisions", "adrs", "constraints"} & set(c), "a risk or a decision has no component column, so no component carries one"
        for seg in c["dependsOn"] or []:
            if seg.get("link", {}).get("kind") == "component":
                assert seg["link"]["name"] in names and seg["link"]["name"] != name
    assert panel["components"]["ConsentRecorder"]["flows"], "a flow that names ConsentRecorder shows on it"
    assert panel["components"]["ConsentRecorder"]["flows"][0]["title"].startswith("Key flow 1: ")  # an untitled flow is named by its first step


def test_a_contract_says_who_provides_and_calls_it_how_it_answers_and_the_connection(heron):
    _, _, panel = heron
    k = panel["contracts"]["CON-002"]
    assert k["name"] == "Note request" and k["provider"] == {"name": "Summarizer", "key": "APP-summarizer"}
    assert k["callers"] == ["NoteClient"]
    assert [a["when"] for a in k["answers"]] == ["slow or nothing back"] and "never shows an old note as new" in k["answers"][0]["does"]
    assert "finished note, or nothing" in k["crosses"], "the plan's own contract is beside the design's failure table"
    assert k["connection"]["direction"] == "agent calls" and k["connection"]["protocol"].startswith("HTTPS")
    assert [q["id"] for q in k["waiting"]] == ["OQ-007"]
    record = panel["contracts"]["CON-004"]
    assert record["callers"] == ["ConsentRecorder"], "a contract is called by the component whose trace carries it, not just the one its table row attaches to"
    assert record["provider"]["key"] == "APP-consent-and-identity"
    outside = panel["contracts"]["CON-001"]
    assert outside["provider"]["key"] is None and outside["provider"]["name"] == "Microsoft", "an outside company has no app to open"


def test_every_stub_line_names_its_contracts_and_the_component_that_calls_them(heron):
    _, _, panel = heron
    consent = next(link for link in panel["links"] if link["name"] == "Consent and identity")
    assert {(ln["component"], tuple(c["name"] for c in ln["contracts"])) for ln in consent["lines"]} == {("ConsentGate", ("Consent check",)), ("ConsentRecorder", ("Record consent",))}
    assert all("(" not in link["name"] for link in panel["links"]), "a system is named without its contract codes"


def test_names_not_codes_nothing_the_panel_shows_is_an_id(heron):
    _, _, panel = heron
    leaks = [(path, m.group(0)) for path, text in strings(panel) for m in [CODE.search(text)] if m]
    assert not leaks, f"codes shown: {leaks[:5]}"


def test_namer_says_an_id_once_and_a_name_the_plan_lacks_by_its_kind(heron):
    vault, data, _ = heron
    namer = panel_data.Namer(vault, data["designs"][APP])
    assert namer.say("CON-003 Consent check | down") == "Consent check | down"
    assert namer.say("calls CON-002 and CON-003") == "calls Note request and Consent check"
    assert namer.say("see CON-099") == "see a contract the plan doesn't list"
    assert namer.say("OQ-003 asks it") == "Is mail read in the first release? asks it"
    assert namer.name("EPC-033.AC1") and namer.name("EPC-033 AC1") == namer.name("EPC-033.AC1"), "an epic's criterion is named by its words, spaced or dotted"
    assert namer.name("EPC-033") == "Show the 7:30 digest"


def test_a_section_the_design_lacks_is_not_filled_in(tmp_path):
    root = tmp_path / "vault"
    shutil.copytree(HERON, root)
    doc = root / "docs" / "tech-design" / "desktop-agent.md"
    text = doc.read_text(encoding="utf-8")
    text = re.sub(r"## Tech stack\n.*?(?=\n## )", "", text, flags=re.S)
    text = re.sub(r"## NFRs *\n.*?(?=\n## )", "", text, flags=re.S)
    text = re.sub(r"## Risks & mitigations\n.*?(?=\n## )", "", text, flags=re.S)
    doc.write_text(text, encoding="utf-8")
    _, data = extract(root)
    s = data["insidePanel"][APP]["summary"]
    assert s["stack"] is None and s["targets"] == [] and s["risks"] == {"total": 0, "high": 0, "top": []}
    counts = {x["id"]: x["count"] for x in s["sections"]}
    assert counts["stack"] is None and counts["risks"] is None, "no count is made up for a section the design lacks"
    assert "tech_stack" not in s and "status" not in s, "no field the design does not record, such as a stack status"


def test_a_depends_on_naming_an_outside_system_with_and_in_its_name_stays_one_system():
    design = design_data.read_design(HERON / "docs" / "tech-design" / "desktop-agent.md")
    gate = next(c for c in design["components"] if c["name"] == "ConsentGate")
    assert gate["depends_on_other"] == ["Consent and identity over CON-003"], "'Consent and identity' is one system, not 'Consent' and 'identity'"
    assert not [p for p in design["problems"] if "'Consent'" in p["message"] or "'identity" in p["message"]]


BOOKING = REPO / "examples" / "unified-booking"


def test_a_contract_lists_every_way_it_can_answer_and_which_are_errors():
    """Paper Tiger guard: the Details of a contract on Flows says what a caller must handle, not only the success."""
    vault = cli.load_vault(BOOKING)
    hold = panel_data.contract_answers(vault)["CON-001"]
    assert [a["case"] for a in hold][:3] == ["Held", "Confirming", "Refused ledger unavailable"]
    assert [a["error"] for a in hold] == [False, False, True, True, True], "an error status is marked, a success is not"
    assert all(a["says"] for a in hold), "each answer says what it does, in words"


def test_a_contract_with_no_case_table_has_no_entry_rather_than_a_made_up_one():
    """Silent Fallback guard: a vault whose contracts have no case table must not get a tidy default answer list."""
    _, data = extract(HERON)
    assert data["contractAnswers"] == {}, "the page says Not recorded; it never fills in 'success' and 'failure'"


def test_the_answers_travel_in_the_page_data_under_the_contract_id():
    vault = cli.load_vault(BOOKING)
    data = build.extract(vault, BOOKING, "2026-11-20", None, {}, None, None)
    assert set(data["contractAnswers"]) <= {c["id"] for c in data["map"]["contracts"]}
    assert "CON-001" in data["contractAnswers"]
