"""The user can override any rule, and an override is never invisible.

Each override test starts from a broken copy of the reference fixture that a plain
check would fail, adds the Override bullet, and checks the error became its warning.
A malformed override must stay an error, so a typo never silently fails to override.
"""
import json
import re
import shutil

import pytest

from conftest import REPO, check, edit, findings, run, skill_text
from vela import override
from vela.parse import Bullet

FIXTURE = REPO / "examples" / "unified-booking"
PLUGIN = REPO / "plugin"
TODAY = "2026-11-20"
CAP = "capabilities/CAP-021-amend-or-cancel.md"
PRICING = "05-building-blocks/pricing-building-blocks.md"
DECISION = "- **Decision:** [[2026-08-12-goals-and-data]]\n"
CONFIRMED = "- **Confirmed by:** @hl-pricing-senior on 2026-08-12\n"


@pytest.fixture
def ub(tmp_path):
    dest = tmp_path / "unified-booking"
    shutil.copytree(FIXTURE, dest)
    return dest


def broken(vault):
    code, out = run("render", "--vault", str(vault))
    assert code == 0, out
    return check(vault, TODAY)


def codes(vault):
    return findings(broken(vault)[1])


def on_cap(vault, bullet):
    edit(vault / CAP, DECISION, DECISION + bullet + "\n")


def block_cap_021(vault):
    edit(vault / "11-unknowns-and-risks.md",
         "- **State:** resolved\n- **Blocks:** [[FLO-001-hold-pay-confirm|FLO-001]] design, "
         "[[ADR-0002-ferrymaster-ledger-of-record|ADR-0002]], [[EPC-031-holds-and-confirms|EPC-031]]\n",
         "- **State:** open\n- **Ask by:** 2026-12-01\n- **Blocks:** [[CAP-021-amend-or-cancel|CAP-021]]\n")


def parse(value):
    return override.parse_override(Bullet("Override", value, 7, (), "", False))


# ------------------------------------------------------------------ grammar

def test_a_well_formed_override_parses_every_part():
    found = parse('GATE-4, grill, "Shape offers 2 or 3 options" by @hl-solution-lead on 2026-11-20: '
                  "the board meets Monday: UNK-001 cannot wait")
    assert found.problem == ""
    assert found.rules == ("GATE-4", "grill", '"Shape offers 2 or 3 options"')
    assert (found.by, found.date) == ("@hl-solution-lead", "2026-11-20")
    assert found.reason == "the board meets Monday: UNK-001 cannot wait"
    assert found.codes == {"E316", "E303", "E317"}


@pytest.mark.parametrize("value, problem", [
    ("", "is empty"),
    ("GATE-4 on 2026-11-20: board meeting", "names no @handle"),
    ("GATE-4 by @hl-solution-lead: board meeting", "has no 'on YYYY-MM-DD' date"),
    ("GATE-4 by @hl-solution-lead on 2026-11-20", "gives no reason"),
    ("GATE-4 by @hl-solution-lead on 2026-02-30: board meeting", "not a real date"),
    ("gate-4 by @hl-solution-lead on 2026-11-20: board meeting", "did you mean GATE-4?"),
    ("GATE-6 by @hl-solution-lead on 2026-11-20: board meeting", "'GATE-6'"),
    ("GATE-4; grill by @hl-solution-lead on 2026-11-20: board meeting", "not names separated by ', '"),
    ("by @hl-solution-lead on 2026-11-20: board meeting", "names no rule before 'by'"),
])
def test_a_malformed_override_names_its_problem(value, problem):
    found = parse(value)
    assert problem in found.problem
    assert found.rules == () and found.codes == set()


def test_a_malformed_override_is_an_error_and_overrides_nothing(ub):
    on_cap(ub, "- **Override:** gate-4 by @hl-solution-lead on 2026-11-20: the board meets Monday")
    block_cap_021(ub)
    code, out = broken(ub)
    assert code == 1
    assert sorted(findings(out)) == [("E316", CAP), ("E321", CAP)]
    assert "did you mean GATE-4?" in out and "so it overrides nothing" in out


def test_a_label_one_typo_away_is_an_error_not_prose(ub):
    on_cap(ub, "- **Overide:** GATE-4 by @hl-solution-lead on 2026-11-20: the board meets Monday")
    edit(ub / PRICING, CONFIRMED, "- **Confirmd by:** @hl-pricing-senior on 2026-08-12\n")
    found = codes(ub)
    assert ("E321", CAP) in found
    assert ("E322", PRICING) in found and ("W324", PRICING) in found


def test_malformed_decided_by_and_confirmed_by_are_errors(ub):
    edit(ub / PRICING, "- **Decided by:** @hl-solution-lead, on behalf of @harborline/revenue-team\n",
         "- **Decided by:** the solution lead, for Revenue\n")
    edit(ub / PRICING, CONFIRMED, "- **Confirmed by:** @hl-pricing-senior in August\n")
    assert codes(ub) == [("E322", PRICING), ("E322", PRICING)]


def test_rules_never_crash_on_odd_override_values(ub):
    for value in ("", "   ", '"" by @x on 2026-11-20: y', "GATE-4 by @ on 9999-99-99: ", "ünïcödé by @x on 2026-11-20: z"):
        on_cap(ub, f"- **Override:** {value}")
    code, out = broken(ub)
    assert code == 1 and "Traceback" not in out
    assert {c for c, _ in findings(out)} == {"E321"}


# ------------------------------------------------------------- downgrades

def test_gate_4_override_turns_e316_into_w316(ub):
    block_cap_021(ub)
    on_cap(ub, "- **Override:** GATE-4 by @hl-solution-lead on 2026-11-20: the board signs off Monday; UNK-001 stays open")
    code, out = broken(ub)
    assert code == 0
    assert findings(out) == [("W316", CAP)]
    assert "Accepted as an exception: GATE-4 by @hl-solution-lead on 2026-11-20: the board signs off Monday" in out


def test_the_e316_code_itself_can_be_named(ub):
    block_cap_021(ub)
    on_cap(ub, "- **Override:** E316 by @hl-solution-lead on 2026-11-20: the board signs off Monday")
    assert codes(ub) == [("W316", CAP)]


def test_grill_override_turns_e303_into_w303(ub):
    edit(ub / CAP, DECISION, "- **Override:** grill by @hl-solution-lead on 2026-11-20: decided at the steering group, not in a Grill\n")
    code, out = broken(ub)
    assert code == 0 and findings(out) == [("W303", CAP)]


def test_grill_override_turns_e317_into_w317(ub):
    (ub / "sessions" / "2026-11-10-amend-requirements.md").write_text(
        "---\nid: 2026-11-10-amend-requirements\ntype: session\ndate: 2026-11-10\nmodes: [requirements]\n"
        "status: closed\nsummary: Wrote amend and cancel requirements as assumptions.\n---\n\n# Requirements: amend\n",
        encoding="utf-8")
    edit(ub / CAP, DECISION, "- **Decision:** [[2026-11-10-amend-requirements]]\n"
         "- **Override:** grill by @hl-solution-lead on 2026-11-10: the lead decided FR1 in the requirements session\n")
    assert codes(ub) == [("W317", CAP)]


def test_e318_and_e304_overrides_on_contracts(ub):
    booking = ub / "05-building-blocks" / "booking-building-blocks.md"
    edit(booking, "- **Tested by:** each channel runs consumer-driven contract tests in its own pipeline.",
         "- **Override:** E318 by @hl-solution-lead on 2026-11-20: the test plan lands with EPC-033\n- **Notes:** each channel runs consumer-driven contract tests in its own pipeline.")
    vessel = ub / "05-building-blocks" / "vessel-schedule-building-blocks.md"
    edit(vessel, "- **Source:** SRC-06\n", "- **Override:** E304 by @hl-solution-lead on 2026-11-20: marine ops told us in person; the document follows\n")
    assert sorted(codes(ub)) == [("W304", "05-building-blocks/vessel-schedule-building-blocks.md"),
                                 ("W318", "05-building-blocks/booking-building-blocks.md")]


def test_an_override_covers_only_its_own_scope(ub):
    """A page-level GATE-4 does not reach a contract under the page's headings."""
    edit(ub / "11-unknowns-and-risks.md",
         "- **State:** resolved\n- **Blocks:** [[FLO-001-hold-pay-confirm|FLO-001]] design, "
         "[[ADR-0002-ferrymaster-ledger-of-record|ADR-0002]], [[EPC-031-holds-and-confirms|EPC-031]]\n",
         "- **State:** open\n- **Ask by:** 2026-12-01\n- **Blocks:** [[pricing-building-blocks|APP-pricing]]\n")
    edit(ub / PRICING, "- **Decision:** [[2026-07-28-solution-strategy]]\n\nPricing quotes",
         "- **Decision:** [[2026-07-28-solution-strategy]]\n- **Override:** GATE-4 by @hl-solution-lead on 2026-11-20: fares do not wait on UNK-001\n\nPricing quotes")
    assert sorted(codes(ub)) == [("E316", PRICING), ("W316", PRICING)]


# ------------------------------------------------------------- not needed

def test_an_override_of_a_rule_the_item_keeps_is_not_needed(ub):
    on_cap(ub, "- **Override:** GATE-4, grill by @hl-solution-lead on 2026-11-20: just in case")
    code, out = broken(ub)
    assert code == 0 and findings(out) == [("W323", CAP)]
    assert "Override not needed: CAP-021 does not break GATE-4, grill" in out


def test_gates_and_quoted_rules_the_check_cannot_see_are_never_not_needed(ub):
    on_cap(ub, '- **Override:** GATE-1, GATE-2, GATE-3, GATE-5, "Shape offers 2 or 3 options" '
               "by @hl-solution-lead on 2026-11-20: one option was all we had")
    assert codes(ub) == []


# ------------------------------------------------------------- on behalf

def test_the_fixture_decides_con_003_on_an_absent_owners_behalf_and_is_confirmed():
    text = (FIXTURE / PRICING).read_text(encoding="utf-8")
    assert "- **Override:** GATE-5 by @hl-solution-lead on 2026-07-28: " in text
    assert "- **Decided by:** @hl-solution-lead, on behalf of @harborline/revenue-team\n" in text
    assert CONFIRMED in text
    assert findings(check(FIXTURE, TODAY)[1]) == []


def test_on_behalf_unconfirmed_warns_until_confirmed(ub):
    edit(ub / PRICING, CONFIRMED, "")
    code, out = broken(ub)
    assert code == 0 and findings(out) == [("W324", PRICING)]
    assert ("@hl-solution-lead decided" in out and "(CON-003) on @harborline/revenue-team's behalf, and "
            "@harborline/revenue-team hasn't confirmed it yet." in out)
    assert "/vela:challenge" in out
    edit(ub / PRICING, "on behalf of @harborline/revenue-team\n", "on behalf of @harborline/revenue-team\n" + CONFIRMED)
    assert codes(ub) == []


def test_the_decider_cannot_confirm_for_the_owner(ub):
    edit(ub / PRICING, CONFIRMED, "- **Confirmed by:** @hl-solution-lead on 2026-08-12\n")
    assert codes(ub) == [("W324", PRICING)]


# ------------------------------------------------------------------ views

def query(vault, *argv):
    code, out = run("query", *argv, "--vault", str(vault), "--json")
    return code, json.loads(out)


def test_query_get_returns_override_decided_by_and_confirmed_by():
    code, answer = query(FIXTURE, "get", "CON-003")
    assert code == 0
    assert answer["override"] == [{"line": answer["override"][0]["line"], "rules": ["GATE-5"], "by": "@hl-solution-lead",
                                   "date": "2026-07-28", "reason": answer["override"][0]["reason"]}]
    assert answer["override"][0]["reason"].startswith("the Revenue team was in its fare review")
    assert answer["decided_by"]["by"] == "@hl-solution-lead"
    assert answer["decided_by"]["on_behalf_of"] == ["@harborline/revenue-team"]
    assert answer["decided_by"]["confirmed"] is True
    assert answer["confirmed_by"] == {"by": "@hl-pricing-senior", "date": "2026-08-12"}
    _, plain = query(FIXTURE, "get", "CON-001")
    assert (plain["override"], plain["decided_by"], plain["confirmed_by"]) == ([], None, None)


def test_query_get_marks_a_malformed_override_and_an_unconfirmed_decision(ub):
    edit(ub / PRICING, CONFIRMED, "- **Override:** GATE-9 by @hl-solution-lead on 2026-07-28: typo\n")
    _, answer = query(ub, "get", "CON-003")
    assert answer["override"][1]["malformed"] is True and "GATE-9" in answer["override"][1]["problem"]
    assert answer["decided_by"]["confirmed"] is False and answer["confirmed_by"] is None
    on_cap(ub, "- **Override:** grill by @hl-solution-lead on 2026-11-20: steering group")
    _, page = query(ub, "get", "CAP-021")
    assert page["override"][0]["rules"] == ["grill"]


def test_progress_grid_counts_override_decisions_as_decided_and_says_so():
    goals = (FIXTURE / "01-goals.md").read_text(encoding="utf-8")
    assert "| [[pricing-building-blocks\\|Pricing]] | writing epics | 0 | 0 | 0 | 3 (1 by override) | none | none |" in goals
    code, out = run("status", "--vault", str(FIXTURE), "--today", TODAY)
    assert code == 0
    assert "(APP-pricing) | stage: epics | 0 early ideas, 0 assumptions, 0 facts, 3 (1 by override) decided |" in out
    booking = next(line for line in out.splitlines() if "(APP-booking) |" in line)
    assert re.search(r", \d+ decided \|", booking) and "by override" not in booking
    _, status = query(FIXTURE, "status")
    pricing = next(a for a in status["apps"] if a["app"] == "APP-pricing")
    assert (pricing["decided"], pricing["decided_by_override"]) == (3, 1)


def test_a_malformed_override_does_not_count_in_the_grid(ub):
    edit(ub / PRICING, "- **Override:** GATE-5 by", "- **Override:** GATE5 by")
    code, out = run("status", "--vault", str(ub), "--today", TODAY)
    assert "(APP-pricing) | stage: epics | 0 early ideas, 0 assumptions, 0 facts, 3 decided |" in out


# ------------------------------------------------------------- skill text

def read(*parts):
    return (PLUGIN.joinpath(*parts)).read_text(encoding="utf-8")


START_RULE = ("The user may override any rule in these skills. Say once, in one plain sentence and without the rule's code, what the rule protects. "
              "Then do what they asked, and record an `**Override:**` bullet (or the session's Changes row note) "
              "naming the rule and their reason. Never refuse, and never ask twice.")


def test_start_holds_the_shared_override_rule_and_its_hard_stops():
    start = read("references", "START.md")
    assert START_RULE in start
    assert "Hard stops are not process rules" in start
    for stop in ("`~/.claude`", "company material", "unless the tool printed it"):
        assert stop in start
    assert "The user may override any of them" in read("references", "MODES.md")


def test_grill_offers_the_override_and_still_runs_the_rest_of_the_grill():
    grill = read("skills", "grill", "SKILL.md")
    assert "If the lead wants to decide it anyway, do it and record the override" in grill
    assert "the rest of the Grill runs as normal" in grill and "read-back" in grill
    assert "- **Decided by:** @<user's handle>, on behalf of @<owner>" in grill
    assert "This is how GATE-5 passes with the owner away." in grill
    assert "W316 instead of E316" in grill


def test_epics_close_challenge_and_ask_know_the_bullets():
    epics, close = read("skills", "epics", "SKILL.md"), skill_text("close")
    challenge, ask = read("skills", "challenge", "SKILL.md"), read("skills", "ask", "SKILL.md")
    assert "Keep every `**Override:**`, `**Decided by:**` and `**Confirmed by:**` bullet" in epics
    assert "Keep every `**Override:**`, `**Decided by:**` and `**Confirmed by:**` bullet as written" in close
    assert "**Overrides:**" in close and "fix its grammar, never delete it" in close
    assert "on behalf of @owner" in challenge and "`decided_by`" in challenge
    assert '"decided by override: <rule>, by @x"' in ask and '"on behalf of @owner, not yet confirmed"' in ask
    conventions = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert "## Overrides" in conventions and "raises `/vela:challenge` on the item" in conventions


# A refusal of the user's explicit instruction on rule grounds. The owner's own right to refuse, and git refusing a
# merge, are not Claude refusing the user.
ALLOWED_REFUSE = ("The owner may refuse", "If they refuse", "A merge refuses", "Never refuse, and never ask twice")


def test_no_skill_tells_claude_to_refuse_a_process_override():
    docs = sorted((PLUGIN / "skills").glob("*/SKILL.md")) + sorted((PLUGIN / "references").glob("*.md"))
    for doc in docs:
        for line in doc.read_text(encoding="utf-8").splitlines():
            stripped = line
            for allowed in ALLOWED_REFUSE:
                stripped = stripped.replace(allowed, "")
            assert not re.search(r"\brefus", stripped, re.I), f"{doc.relative_to(REPO)}: {line}"


def test_every_never_list_is_a_default_the_user_can_override_because_start_says_so_once():
    start = (PLUGIN / "references" / "START.md").read_text(encoding="utf-8")
    assert 'every "never" and "must not" in the skills' in start and "Never refuse, and never ask twice." in start
    for doc in sorted((PLUGIN / "skills").glob("*/SKILL.md")):
        text = doc.read_text(encoding="utf-8")
        assert "These are the defaults" not in text, doc.parent.name  # said once, in START, so the copies cannot drift
        if "\n## Never\n" in text:
            section = text.split("\n## Never\n", 1)[1]
            assert not re.search(r"cannot be overridden|may not be overridden|no override", section, re.I), doc.parent.name


def test_an_owner_confirming_after_handoff_changes_nothing_the_senior_accepted(ub):
    edit(ub / PRICING, CONFIRMED, "")
    code, out = run("handoff", "verify", "APP-booking", "--vault", str(ub))
    assert code == 0 and "0 things changed, 0 added and 0 removed" in out, out
    edit(ub / PRICING, "- **Decided by:** @hl-solution-lead", "- **Decided by:** @hl-booking-senior")
    code, out = run("handoff", "verify", "APP-booking", "--vault", str(ub))
    assert code == 1 and "(CON-003): its wording changed" in out


def test_a_bare_decided_by_is_the_owners_own_decision_and_needs_no_confirmation(ub):
    """What accepting a reader's proposal writes: well formed (no E322), and not 'on behalf', so no W324."""
    text = (ub / PRICING).read_text(encoding="utf-8")
    heading = re.search(r"^### CON-\d+ .*$", text, re.M).group(0)
    (ub / PRICING).write_text(text.replace(heading, heading + "\n\n- **Decided by:** @hl-pricing-senior", 1), encoding="utf-8")
    _, out = check(ub, TODAY)
    assert ("E322", PRICING) not in findings(out) and ("W324", PRICING) not in findings(out)
    (ub / PRICING).write_text((ub / PRICING).read_text(encoding="utf-8").replace("Decided by:** @hl-pricing-senior", "Decided by:** pricing senior", 1), encoding="utf-8")
    assert ("E322", PRICING) in findings(check(ub, TODAY)[1])
