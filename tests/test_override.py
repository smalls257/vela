"""The user can override any rule, and an override is never invisible.

Each override test starts from a broken copy of the reference fixture that a plain
check would fail, adds the Override bullet, and checks the error became its warning.
A malformed override must stay an error, so a typo never silently fails to override.
"""
import json
import re
import shutil

import pytest

from conftest import REPO, check, edit, findings, run
from vela import override
from vela.parse import Bullet
import session_files

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
    found = parse('E316, E303, "Shape offers 2 or 3 options" by @hl-solution-lead on 2026-11-20: '
                  "the board meets Monday: UNK-001 cannot wait")
    assert found.problem == ""
    assert found.rules == ("E316", "E303", '"Shape offers 2 or 3 options"')
    assert (found.by, found.date) == ("@hl-solution-lead", "2026-11-20")
    assert found.reason == "the board meets Monday: UNK-001 cannot wait"
    assert found.codes == {"E316", "E303"}


@pytest.mark.parametrize("value, problem", [
    ("", "is empty"),
    ("E316 on 2026-11-20: board meeting", "names no @handle"),
    ("E316 by @hl-solution-lead: board meeting", "has no 'on YYYY-MM-DD' date"),
    ("E316 by @hl-solution-lead on 2026-11-20", "gives no reason"),
    ("E316 by @hl-solution-lead on 2026-02-30: board meeting", "not a real date"),
    ("gate-1 by @hl-solution-lead on 2026-11-20: board meeting", "did you mean GATE-1?"),
    ("GATE-6 by @hl-solution-lead on 2026-11-20: board meeting", "'GATE-6'"),
    ("E316; E303 by @hl-solution-lead on 2026-11-20: board meeting", "not names separated by ', '"),
    ("by @hl-solution-lead on 2026-11-20: board meeting", "names no rule before 'by'"),
])
def test_a_malformed_override_names_its_problem(value, problem):
    found = parse(value)
    assert problem in found.problem
    assert found.rules == () and found.codes == set()


def test_a_malformed_override_is_an_error_and_overrides_nothing(ub):
    on_cap(ub, "- **Override:** gate-1 by @hl-solution-lead on 2026-11-20: the board meets Monday")
    block_cap_021(ub)
    code, out = broken(ub)
    assert code == 1
    assert sorted(findings(out)) == [("E316", CAP), ("E321", CAP)]
    assert "did you mean GATE-1?" in out and "so it overrides nothing" in out


def test_a_label_one_typo_away_is_an_error_not_prose(ub):
    on_cap(ub, "- **Overide:** E316 by @hl-solution-lead on 2026-11-20: the board meets Monday")
    edit(ub / PRICING, CONFIRMED, "- **Confirmd by:** @hl-pricing-senior on 2026-08-12\n")
    found = codes(ub)
    assert ("E321", CAP) in found
    assert ("E322", PRICING) in found


def test_malformed_decided_by_and_confirmed_by_are_errors(ub):
    edit(ub / PRICING, "- **Decided by:** @hl-solution-lead, on behalf of @harborline/revenue-team\n",
         "- **Decided by:** the solution lead, for Revenue\n")
    edit(ub / PRICING, CONFIRMED, "- **Confirmed by:** @hl-pricing-senior in August\n")
    assert codes(ub) == [("E322", PRICING), ("E322", PRICING)]


def test_rules_never_crash_on_odd_override_values(ub):
    for value in ("", "   ", '"" by @x on 2026-11-20: y', "E316 by @ on 9999-99-99: ", "ünïcödé by @x on 2026-11-20: z"):
        on_cap(ub, f"- **Override:** {value}")
    code, out = broken(ub)
    assert code == 1 and "Traceback" not in out
    assert {c for c, _ in findings(out)} == {"E321"}


# ------------------------------------------------------------- downgrades

def test_e316_override_turns_e316_into_w316(ub):
    block_cap_021(ub)
    on_cap(ub, "- **Override:** E316 by @hl-solution-lead on 2026-11-20: the board signs off Monday; UNK-001 stays open")
    code, out = broken(ub)
    assert code == 0
    assert findings(out) == [("W316", CAP)]
    assert "Accepted as an exception: E316 by @hl-solution-lead on 2026-11-20: the board signs off Monday" in out


def test_the_e316_code_itself_can_be_named(ub):
    block_cap_021(ub)
    on_cap(ub, "- **Override:** E316 by @hl-solution-lead on 2026-11-20: the board signs off Monday")
    assert codes(ub) == [("W316", CAP)]


def test_e303_override_turns_it_into_w303(ub):
    edit(ub / CAP, DECISION, "- **Override:** E303 by @hl-solution-lead on 2026-11-20: decided at the steering group, no session\n")
    code, out = broken(ub)
    assert code == 0 and findings(out) == [("W303", CAP)]


def test_e318_and_e304_overrides_on_contracts(ub):
    booking = ub / "05-building-blocks" / "booking-building-blocks.md"
    edit(booking, "- **Tested by:** each channel runs consumer-driven contract tests in its own pipeline.",
         "- **Override:** E318 by @hl-solution-lead on 2026-11-20: the test plan lands with EPC-033\n- **Notes:** each channel runs consumer-driven contract tests in its own pipeline.")
    vessel = ub / "05-building-blocks" / "vessel-schedule-building-blocks.md"
    edit(vessel, "- **Source:** SRC-06\n", "- **Override:** E304 by @hl-solution-lead on 2026-11-20: marine ops told us in person; the document follows\n")
    assert sorted(codes(ub)) == [("W304", "05-building-blocks/vessel-schedule-building-blocks.md"),
                                 ("W318", "05-building-blocks/booking-building-blocks.md")]


def test_an_override_covers_only_its_own_scope(ub):
    """A page-level E316 does not reach a contract under the page's headings."""
    edit(ub / "11-unknowns-and-risks.md",
         "- **State:** resolved\n- **Blocks:** [[FLO-001-hold-pay-confirm|FLO-001]] design, "
         "[[ADR-0002-ferrymaster-ledger-of-record|ADR-0002]], [[EPC-031-holds-and-confirms|EPC-031]]\n",
         "- **State:** open\n- **Ask by:** 2026-12-01\n- **Blocks:** [[pricing-building-blocks|APP-pricing]]\n")
    edit(ub / PRICING, "- **Decision:** [[2026-07-28-solution-strategy]]\n\nPricing quotes",
         "- **Decision:** [[2026-07-28-solution-strategy]]\n- **Override:** E316 by @hl-solution-lead on 2026-11-20: fares do not wait on UNK-001\n\nPricing quotes")
    assert sorted(codes(ub)) == [("E316", PRICING), ("W316", PRICING)]


# ------------------------------------------------------------- not needed

def test_an_override_of_a_rule_the_item_keeps_is_not_needed(ub):
    on_cap(ub, "- **Override:** E316, E303 by @hl-solution-lead on 2026-11-20: just in case")
    code, out = broken(ub)
    assert code == 0 and findings(out) == [("W323", CAP)]
    assert "Override not needed: CAP-021 does not break E316, E303" in out


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


def test_on_behalf_unconfirmed_warns_nothing(ub):
    """The owner's confirmation is optional: an unconfirmed on-behalf decision is read, never warned about."""
    edit(ub / PRICING, CONFIRMED, "")
    code, out = broken(ub)
    assert code == 0 and findings(out) == [] and "hasn't confirmed" not in out
    assert query(ub, "get", "CON-003")[1]["decided_by"]["confirmed"] is False


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
    on_cap(ub, "- **Override:** E303 by @hl-solution-lead on 2026-11-20: steering group")
    _, page = query(ub, "get", "CAP-021")
    assert page["override"][0]["rules"] == ["E303"]


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


def test_conventions_know_the_override_bullets():
    conventions = (REPO / "plugin" / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
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


def test_an_owner_confirming_after_handoff_changes_nothing_the_senior_accepted(ub):
    edit(ub / PRICING, CONFIRMED, "")
    code, out = run("handoff", "verify", "APP-booking", "--vault", str(ub))
    assert code == 0 and "0 things changed, 0 added and 0 removed" in out, out
    edit(ub / PRICING, "- **Decided by:** @hl-solution-lead", "- **Decided by:** @hl-booking-senior")
    code, out = run("handoff", "verify", "APP-booking", "--vault", str(ub))
    assert code == 1 and "(CON-003): its wording changed" in out


def test_a_bare_decided_by_is_the_owners_own_decision_and_needs_no_confirmation(ub):
    """What accepting a reader's proposal writes: well formed (no E322) and not 'on behalf'."""
    text = (ub / PRICING).read_text(encoding="utf-8")
    heading = re.search(r"^### CON-\d+ .*$", text, re.M).group(0)
    (ub / PRICING).write_text(text.replace(heading, heading + "\n\n- **Decided by:** @hl-pricing-senior", 1), encoding="utf-8")
    _, out = check(ub, TODAY)
    assert ("E322", PRICING) not in findings(out)
    (ub / PRICING).write_text((ub / PRICING).read_text(encoding="utf-8").replace("Decided by:** @hl-pricing-senior", "Decided by:** pricing senior", 1), encoding="utf-8")
    assert ("E322", PRICING) in findings(check(ub, TODAY)[1])


@pytest.mark.parametrize("old", ["grill", "E317", "W317"])
def test_a_retired_rule_says_it_is_gone_and_to_delete_the_bullet(old):
    problem = override._rule_problem([old])
    assert "that rule is gone" in problem and "delete this bullet" in problem
    assert "Use GATE-1" not in problem
