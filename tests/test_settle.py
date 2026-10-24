"""Settle anywhere: `vela decide` decides in any session, and every protection it carries still runs there."""
import json
import re
import subprocess

import pytest

import session_files
from conftest import REPO, edit, run
from vela import closegate, override, say, schema
from test_decide import (CAPTURES, RECORD, RECORD_ID, STOCK, STRATEGY, TODAY, block_con_002, decide_con_002, filed,
                         git_init, git_log, in_session_with_modes, item, make_vault, plan)

LIB = REPO / "plugin" / "lib" / "vela"
EVERY_MODE = ["dump", "discover", "shape", "boundary", "requirements", "allocate", "releases", "grill", "epics",
              "answer", "shape, boundary"]


def decide(root, *flags):
    return run("decide", "CON-002", *flags, "--vault", str(root), "--today", TODAY, "--json")


@pytest.mark.parametrize("modes", EVERY_MODE)
def test_any_session_decides_with_a_read_back_a_yes_and_a_why(tmp_path, modes):
    root = make_vault(tmp_path)
    in_session_with_modes(root, modes)
    git_init(root)
    code, out = decide(root, "--readback", "^c01", "--yes", "^c02", "--why", "^c03", "--provider", "^c07")
    assert code == 0, out
    assert re.search(r"### CON-002[\s\S]*?- \*\*State:\*\* decided", (root / STOCK).read_text(encoding="utf-8"))
    assert git_log(root)[0] == f"{modes.split(',')[0].strip()}: CON-002 decided"
    assert "Ready to decide" not in session_files.record_text(root, RECORD_ID)


def test_outside_a_grill_the_read_back_and_the_yes_are_still_needed(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "shape")
    code, out = decide(root, "--yes", "^c02", "--provider", "^c07")
    assert code == 1 and json.loads(out)["refusals"][0]["rule"] == "decide-unfilled"
    code, out = decide(root, "--readback", "^c03", "--yes", "^c02", "--provider", "^c07")
    assert code == 1 and "consent-yes-before-readback" in [r["rule"] for r in json.loads(out)["refusals"]]
    code, out = decide(root, "--readback", "^c01", "--yes", "^c04", "--provider", "^c07")  # ^c04 is a bare "ok"
    assert code == 1


def test_outside_a_grill_the_gate_still_runs_and_the_lead_can_set_it_aside(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "boundary")
    block_con_002(root)
    code, out = decide(root, "--readback", "^c01", "--yes", "^c02", "--provider", "^c07")
    assert code == 1 and "GATE-4" in [r["rule"] for r in json.loads(out)["refusals"]]
    git_init(root)
    code, out = decide(root, "--readback", "^c01", "--yes", "^c02", "--provider", "^c07",
                       "--override", "GATE-4", "--reason-from", "^c06", "--until", "2026-11-01")
    assert code == 0, out


def owned_by_the_stock_team(root):
    edit(root / STOCK, "- **Tested by:** consumer tests in the shop pipeline.",
         "- **Owner:** @stock-team\n- **Tested by:** consumer tests in the shop pipeline.")


def test_the_owners_yes_outside_a_grill_is_checked_in_code_and_deciding_for_them_is_on_their_behalf(tmp_path):
    """GATE-5 was the grill skill's alone; now any session decides, so decide refuses a yes that isn't the owner's
    unless the lead decides on their behalf, which is noted (W324) until they confirm."""
    root = make_vault(tmp_path)
    in_session_with_modes(root, "boundary")
    owned_by_the_stock_team(root)
    git_init(root)
    code, out = decide(root, "--readback", "^c01", "--yes", "^c02", "--provider", "^c07")
    refusal = json.loads(out)["refusals"][0]
    assert code == 1 and refusal["rule"] == "GATE-5" and "on their behalf" in refusal["plain"], out
    code, out = decide(root, "--readback", "^c01", "--yes", "^c02", "--provider", "^c07", "--on-behalf", "@stock-team",
                       "--override", "GATE-5", "--reason-from", "^c06")
    assert code == 0, out
    assert "- **Decided by:** @priya, on behalf of @stock-team" in (root / STOCK).read_text(encoding="utf-8")


def test_the_owners_own_yes_needs_no_on_behalf(tmp_path):
    root = make_vault(tmp_path, captures=CAPTURES + ['- [answer] (@stock-team) "Yes, as read." ^c13'])
    in_session_with_modes(root, "boundary")
    owned_by_the_stock_team(root)
    git_init(root)
    code, out = decide(root, "--readback", "^c01", "--yes", "^c13", "--provider", "^c07")
    assert code == 0, out
    assert "on behalf" not in (root / STOCK).read_text(encoding="utf-8")


def test_later_lists_the_yes_and_decides_nothing(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "shape")
    before = (root / STOCK).read_text(encoding="utf-8")
    code, out = decide(root, "--later", "--yes", "^c02")
    assert code == 0, out
    assert (root / STOCK).read_text(encoding="utf-8") == before
    assert f"## Ready to decide\n\n- CON-002: the lead said yes in {RECORD_ID} (^c02)" in session_files.record_text(root, RECORD_ID)
    brief = json.loads(run("session", "brief", "--vault", str(root), "--today", TODAY, "--json")[1])
    assert [(e["id"], e["session"]) for e in brief["ready_to_decide"]] == [("CON-002", RECORD_ID)]
    assert decide(root, "--later", "--yes", "^c02")[0] == 0
    assert session_files.record_text(root, RECORD_ID).count("- CON-002: the lead said yes") == 1, "listed once"


def test_later_needs_the_yes_and_is_not_a_settle(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "shape")
    assert decide(root, "--later")[0] == 1
    assert decide(root, "--later", "--yes", "^c02", "--readback", "^c01")[0] == 1


def rules_of(out):
    return [r["rule"] for r in json.loads(out)["refusals"]]


def test_later_refuses_an_item_the_vault_does_not_hold(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "shape")
    before = session_files.record_text(root, RECORD_ID)
    code, out = run("decide", "NOPE-999", "--later", "--yes", "^c02", "--vault", str(root), "--today", TODAY, "--json")
    assert code == 1 and rules_of(out) == ["decide-missing"]
    assert session_files.record_text(root, RECORD_ID) == before


def test_later_keeps_only_a_plain_yes_the_lead_typed(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "shape")
    before = session_files.record_text(root, RECORD_ID)
    code, out = decide(root, "--later", "--yes", "^c99")  # no such capture
    assert code == 1 and rules_of(out) == ["consent-capture-missing"]
    code, out = decide(root, "--later", "--yes", "^c04")  # a bare "ok"
    assert code == 1 and rules_of(out) == ["consent-bare-non-yes"]
    code, out = decide(root, "--later", "--yes", "^c01")  # Claude's read-back
    assert code == 1 and rules_of(out) == ["consent-not-a-person"]
    assert session_files.record_text(root, RECORD_ID) == before


def test_later_says_it_writes_no_reasons_or_options_and_does_not_drop_them_silently(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "shape")
    before = session_files.record_text(root, RECORD_ID)
    for flags in (["--picked", "A=^c01", "--rejected", "B=^c02"], ["--why", "^c03"], ["--dissent", "^c03"]):
        code, out = decide(root, "--later", "--yes", "^c02", *flags)
        assert code == 1 and rules_of(out) == ["decide-later-writes-nothing"], flags
    code, out = run("decide", "--reopen", "CON-002", "--later", "--yes", "^c02", "--vault", str(root), "--today", TODAY,
                    "--json")
    assert code == 1 and rules_of(out) == ["decide-later-writes-nothing"]
    assert session_files.record_text(root, RECORD_ID) == before


def test_settling_later_drops_it_off_the_list(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "shape")
    decide(root, "--later", "--yes", "^c02")
    git_init(root)
    assert decide_con_002(root)[0] == 0
    brief = json.loads(run("session", "brief", "--vault", str(root), "--today", TODAY, "--json")[1])
    assert brief["ready_to_decide"] == []


def test_nothing_reads_a_sessions_modes_to_decide():
    gone = ("can_decide", "CANNOT_DECIDE", "cannot_decide_here", "StubUnreadable", "decide-not-in-this-session")
    hits = [f"{p.relative_to(REPO)}:{n}" for p in LIB.rglob("*.py")
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if any(g in line for g in gone)]
    assert hits == []


def test_the_grill_rule_and_e317_are_gone():
    assert "E317" not in schema.CODES and "W317" not in schema.CODES
    assert "grill" not in schema.OVERRIDE_RULES and "grill" not in schema.STANDING_RULES
    assert "E317" not in schema.OVERRIDE_CODES and "grill" not in say.RULE_WORDS and "E317" not in say.RULE_WORDS


def test_an_old_grill_override_is_an_unknown_rule():
    parsed = override.parse("grill by @dana on 2026-10-24: the steering group decided it")
    assert parsed.problem


def test_close_says_which_session_in_plain_words():
    class Named:
        def name_of(self, ident):
            return "Job due"
    said = closegate._lead_message("CON-003 is decided, but no **Decision:** bullet links the session that decided it.",
                                   Named())
    assert said == "Job due is decided, but nothing says which session decided it."


def on_a_session_branch(root):
    """main holds the vault as it was; the session's branch is where the decision lands (close gate judges the
    difference)."""
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "start"],
                 ["switch", "-q", "-c", "session/x"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_a_settle_in_shape_passes_close_gate(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "shape")
    on_a_session_branch(root)
    assert decide(root, "--readback", "^c01", "--yes", "^c02", "--why", "^c03", "--provider", "^c07")[0] == 0
    gate = json.loads(run("close", "gate", "--vault", str(root), "--today", TODAY, "--json")[1])
    assert not [p for p in gate.get("problems", []) if p.get("kind") == "consent"], gate


def a_decided_adr_file(root):
    (root / ".vela").mkdir(exist_ok=True)
    (root / ".vela" / "handle").write_text("priya\n")
    path = root / "adr.json"
    path.write_text(json.dumps({"version": 1, "kind": "add", "session": RECORD_ID, "items": [
        {"type": "adr", "title": "Stock over one API", "owner": "@priya", "state": "decided", "decision": RECORD_ID,
         "capture": "^c02", "decides": "CON-002", "id": None}]}))
    return path


def consent_problems(root):
    gate = json.loads(run("close", "gate", "--vault", str(root), "--today", TODAY, "--json")[1])
    return [p for p in gate.get("problems", []) if p.get("kind") == "consent"]


def test_a_decided_record_of_a_decision_made_this_session_passes_close_gate(tmp_path):
    """Review finding 2: the record's yes is the decision's yes, and no read-back was ever kept on the record."""
    root = make_vault(tmp_path)
    in_session_with_modes(root, "grill")
    on_a_session_branch(root)
    assert decide(root, "--readback", "^c01", "--yes", "^c02", "--why", "^c03", "--provider", "^c07")[0] == 0
    code, out = run("apply", str(a_decided_adr_file(root)), "--vault", str(root), "--json")
    assert code == 0, out
    assert consent_problems(root) == []


def test_vela_add_adr_decided_knows_the_lead(tmp_path):
    """`vela add` never passed the lead, so a decided record always refused decide-lead-unknown."""
    root = make_vault(tmp_path)
    in_session_with_modes(root, "grill")
    on_a_session_branch(root)
    assert decide(root, "--readback", "^c01", "--yes", "^c02", "--why", "^c03", "--provider", "^c07")[0] == 0
    (root / ".vela").mkdir(exist_ok=True)
    (root / ".vela" / "handle").write_text("priya\n")
    code, out = run("add", "adr", "--title", "Stock over one API", "--state", "decided", "--decision", RECORD_ID,
                    "--capture", "^c02", "--decides", "CON-002", "--vault", str(root), "--today", TODAY, "--json")
    assert code == 0, out
    assert consent_problems(root) == []


def test_a_hand_set_decided_citing_that_s_decided_fails_close(tmp_path):
    root = make_vault(tmp_path, captures=['- [thought] (@priya) "That\'s decided." ^c01'])
    in_session_with_modes(root, "shape")
    on_a_session_branch(root)
    page = (root / STOCK).read_text(encoding="utf-8")
    (root / STOCK).write_text(re.sub(r"(### CON-002[\s\S]*?- \*\*State:\*\* )assumption", r"\1decided", page, count=1),
                              encoding="utf-8")
    session_files.edit_record(root, RECORD_ID, "## Captures",
                              f"## Changes\n\n| ID | From | To | Source |\n|---|---|---|---|\n"
                              f"| CON-002 | assumption | decided | [[{RECORD_ID}#^c01]] |\n\n## Captures")
    gate = json.loads(run("close", "gate", "--vault", str(root), "--today", TODAY, "--json")[1])
    assert any("never read" in p.get("plain", "") for p in gate.get("problems", [])), gate


def test_the_read_back_has_to_be_claudes_words_not_the_leads_remark(tmp_path):
    root = make_vault(tmp_path)
    in_session_with_modes(root, "shape")
    code, out = decide(root, "--readback", "^c02", "--yes", "^c03", "--provider", "^c07")  # ^c02 is the lead's
    assert code == 1 and "consent-readback-not-claudes" in rules_of(out)


def test_a_lead_capture_marked_decided_is_not_a_read_back_at_close(tmp_path):
    keep = "[[stock-building-blocks#CON-002 Stock level|CON-002]] (decided)"
    root = make_vault(tmp_path, captures=[f'- [thought] (@priya) "That\'s decided." → keep: {keep} ^c01',
                                          '- [answer] (@priya) "Yes, go." ^c02'])
    in_session_with_modes(root, "grill")
    on_a_session_branch(root)
    page = (root / STOCK).read_text(encoding="utf-8")
    (root / STOCK).write_text(re.sub(r"(### CON-002[\s\S]*?- \*\*State:\*\* )assumption", r"\1decided", page, count=1),
                              encoding="utf-8")
    session_files.edit_record(root, RECORD_ID, "## Captures",
                              f"## Changes\n\n| ID | From | To | Source |\n|---|---|---|---|\n"
                              f"| CON-002 | assumption | decided | [[{RECORD_ID}#^c02]] |\n\n## Captures")
    assert any("never read" in p["plain"] for p in consent_problems(root))


# --- settling a pick writes its options

PICK = CAPTURES + ['- [answer] (@priya) "One Shop API. That\'s decided." ^c16',
                   '- [answer] (@priya) "Two places to change for every price rule." ^c17',
                   '- [answer] (@stock-team) "The till should own its calls." ^c18']
OPTIONS = ("\n- **Options considered:** one Shop API (picked); the till calls Stock itself: rejected, two places to "
           "change\n")


def pick_vault(tmp_path):
    root = make_vault(tmp_path, captures=PICK)
    in_session_with_modes(root, "shape")
    edit(root / STRATEGY, OPTIONS, "\n")
    return root


def settle_strategy(**more):
    base = dict(why="^c03", picked="One Shop API=^c16", rejected=["The till calls Stock itself=^c17"])
    base.update(more)
    return item("solution-strategy", **base)


def test_settling_a_pick_writes_its_options_in_the_leads_words_and_decides(tmp_path):
    writes = filed(pick_vault(tmp_path), [settle_strategy()])
    page = writes[STRATEGY]
    assert "state: decided" in page
    assert ('- **Options considered:** One Shop API (picked); The till calls Stock itself: rejected, "Two places to '
            'change for every price rule."') in page
    assert page.index("**Options considered:**") < page.index("**Decision:**")
    assert "(decided) ^c16" in writes[RECORD] and "(decided) ^c17" in writes[RECORD]


def test_a_reason_someone_else_gave_goes_on_by_reference(tmp_path):
    page = filed(pick_vault(tmp_path), [settle_strategy(rejected=["The till calls Stock itself=^c18"])])[STRATEGY]
    assert "The till should own its calls" not in page
    assert f"The till calls Stock itself: rejected, the reason is in [[{RECORD_ID}]] c18" in page


def test_a_declined_reason_is_recorded_as_declined(tmp_path):
    page = filed(pick_vault(tmp_path), [settle_strategy(rejected=["The till calls Stock itself=declined"])])[STRATEGY]
    assert "The till calls Stock itself: rejected, reason declined" in page


def test_a_pick_with_nothing_set_aside_is_refused_with_its_override(tmp_path):
    _, refusals = plan(pick_vault(tmp_path), [settle_strategy(rejected=[])])
    assert "decide-options-one" in [r.rule for r in refusals]
    assert all("GATE-2" in r.override for r in refusals if r.rule == "decide-options-one")


def test_a_pick_naming_a_capture_the_record_lacks_is_refused(tmp_path):
    _, refusals = plan(pick_vault(tmp_path), [settle_strategy(rejected=["The till calls Stock itself=^c99"])])
    assert "decide-options-capture" in [r.rule for r in refusals]


def test_options_already_written_are_left_as_they_are(tmp_path):
    root = make_vault(tmp_path, captures=PICK)
    in_session_with_modes(root, "shape")
    _, refusals = plan(root, [settle_strategy()])
    assert "decide-options-written" in [r.rule for r in refusals]


def test_the_flags_reach_the_command(tmp_path):
    root = pick_vault(tmp_path)
    git_init(root)
    code, out = run("decide", "solution-strategy", "--readback", "^c01", "--yes", "^c02", "--why", "^c03",
                    "--picked", "One Shop API=^c16", "--rejected", "The till calls Stock itself=^c17",
                    "--vault", str(root), "--today", TODAY, "--json")
    assert code == 0, out
    assert git_log(root)[0] == "shape: solution-strategy decided"


def test_one_gate_name_for_deciding():
    assert "decide" in schema.GATES and "grill" not in schema.GATES
    code, _ = run("check", "--gate", "grill", "--item", "CON-001", "--vault", str(REPO / "tests" / "fixtures" / "mini"))
    assert code != 0  # argparse refuses the old name; no alias
