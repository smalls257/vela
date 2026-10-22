"""The lists a session stub carries in its frontmatter: `ready`, `challenges` and `harvest_declined`.

The Violation these tests guard is a Distributed Monolith between a record's body and the readers of its header: the
Grills view, `session brief`, close and the voice harvest all ask "what is waiting, what was challenged, what was
declined" and must get the same answer from the header alone, because once the words move to a private file the body
is not there to ask. The Grills view also carries the date of a yes and never its words.
"""
import json

from conftest import run
from grills_vault import TODAY as GRILLS_TODAY, make as make_grills_vault
from sharing import git
from test_decide import RECORD_ID, decide_con_002, in_session_with_modes, make_vault as make_decide_vault
from test_session_cli import TODAY, no_gh, owner, start
from test_voice_cli import PAGE, SESSION, harvest, harvest_list, voice  # noqa: F401 (harvest is a fixture)
from vela import cli, grills, privaterecord, voiceplan
from vela.edge import voicegit
import session_files


def test_a_kept_yes_lands_in_the_ready_list(tmp_path):
    root = make_decide_vault(tmp_path)
    in_session_with_modes(root, "shape")
    assert decide_con_002(root)[0] == 1
    meta = privaterecord.stub_meta(session_files.record_text(root, RECORD_ID))
    assert privaterecord.listed(meta, "ready") == ("CON-002",)
    decide_con_002(root)
    meta = privaterecord.stub_meta(session_files.record_text(root, RECORD_ID))
    assert privaterecord.listed(meta, "ready") == ("CON-002",), "listed once however often the yes is repeated"


def test_session_brief_reads_the_ready_list_from_the_header(tmp_path):
    root = make_decide_vault(tmp_path)
    in_session_with_modes(root, "shape")
    decide_con_002(root)
    text = session_files.record_text(root, RECORD_ID)
    body_only = text.replace("ready: [\"CON-002\"]\n", "")
    assert body_only != text and "- CON-002: the lead said yes" in body_only
    session_files.write_record(root, RECORD_ID, body_only)
    code, output = run("session", "brief", "--vault", str(root), "--today", GRILLS_TODAY, "--json")
    assert json.loads(output)["ready_to_decide"] == [], "the body line alone no longer counts"
    session_files.write_record(root, RECORD_ID, text)
    code, output = run("session", "brief", "--vault", str(root), "--today", GRILLS_TODAY, "--json")
    assert [(e["id"], e["session"]) for e in json.loads(output)["ready_to_decide"]] == [("CON-002", RECORD_ID)]


def test_grills_said_yes_has_the_date_and_no_words(tmp_path):
    vault = cli.load_vault(make_grills_vault(tmp_path))
    rows = grills.yes_marks(vault)
    assert rows and all(set(r) == {"id", "session", "date", "title"} for r in rows)
    assert {r["id"] for r in rows} == {"CON-013"}
    assert all(r["date"] for r in rows)


def test_a_challenge_session_lists_its_item_at_start(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    code, output = start(vault, "--mode", "challenge", "--topic", "CON-001")
    assert code == 0, output
    meta = privaterecord.stub_meta(session_files.record_text(vault, f"{TODAY}-con-001"))
    assert privaterecord.listed(meta, "challenges") == ("CON-001",)


def test_a_session_that_is_not_a_challenge_lists_none(tmp_path, monkeypatch):
    vault = owner(tmp_path, monkeypatch)
    assert start(vault, "--mode", "grill", "--topic", "stock")[0] == 0
    meta = privaterecord.stub_meta(session_files.record_text(vault, f"{TODAY}-stock"))
    assert privaterecord.listed(meta, "challenges") == ()


def test_a_decline_travels_in_the_list(harvest):  # noqa: F811
    root, _, _ = harvest
    candidate = harvest_list(root)[1]["candidates"][0]
    code, out = voice(root, "harvest", "decline", "7", candidate["page"], candidate["hash"])
    assert code == 0, out
    found = voiceplan.declined(voicegit.record_metas(root))
    assert (7, PAGE, candidate["hash"]) in found
    meta = privaterecord.stub_meta(session_files.record_text(root, SESSION))
    assert privaterecord.listed(meta, "harvest_declined") == (f"PR 7 {PAGE} {candidate['hash']}",)


def test_the_decline_check_reads_the_header_not_the_body():
    line = "Harvest declined: PR 41 apps/kiosk.md 4be1c09a7d2e"
    body_only = {"id": "r1"}
    assert voiceplan.declined([body_only]) == set()
    header = {"id": "r1", "harvest_declined": ["PR 41 apps/kiosk.md 4be1c09a7d2e"]}
    assert voiceplan.declined([header]) == {(41, "apps/kiosk.md", "4be1c09a7d2e")}
    assert voiceplan.decline_line(41, "apps/kiosk.md", "4be1c09a7d2e") == line
