"""An override of a standing rule carries the date it ends (plan 4.4).

A standing override (an open blocking unknown, a missing case table) with no end covers the rule forever, so a red
check stays green long after the lead's reason stopped holding: a Silent Fallback with a signature on it. These
tests pin the `until` grammar, the standing and event classes, E398 for a standing override past its end, and the
date a refusal offers (never writes).
"""
import shutil

import pytest

from conftest import REPO, edit, findings, run
from vela import cli, override, schema
from vela.parse import Bullet

FIXTURE = REPO / "examples" / "unified-booking"
HERON = REPO / "tests" / "fixtures" / "team-skills" / "heron"
FLOWCHECK = REPO / "tests" / "fixtures" / "flowcheck"
TODAY = "2026-11-20"
CAP = "capabilities/CAP-021-amend-or-cancel.md"
DECISION = "- **Decision:** [[2026-08-12-goals-and-data]]\n"


def parse(value):
    return override.parse_override(Bullet("Override", value, 7, (), "", False))


@pytest.fixture
def ub(tmp_path):
    dest = tmp_path / "unified-booking"
    shutil.copytree(FIXTURE, dest)
    return dest


def blocked_with(vault, bullet):
    """CAP-021 decided while an open unknown blocks it (E316), with `bullet` on the item."""
    edit(vault / CAP, DECISION, DECISION + bullet + "\n")
    edit(vault / "11-unknowns-and-risks.md",
         "- **State:** resolved\n- **Blocks:** [[FLO-001-hold-pay-confirm|FLO-001]] design, "
         "[[ADR-0002-ferrymaster-ledger-of-record|ADR-0002]], [[EPC-031-holds-and-confirms|EPC-031]]\n",
         "- **State:** open\n- **Ask by:** 2026-12-01\n- **Blocks:** [[CAP-021-amend-or-cancel|CAP-021]]\n")
    code, out = run("render", "--vault", str(vault))
    assert code == 0, out
    return run("check", "--vault", str(vault), "--today", TODAY)


# ------------------------------------------------------------------ grammar

def test_until_parses_and_old_grammar_still_parses():
    found = parse("E316 by @lead on 2026-10-20 until 2026-11-30: the board meets Monday: UNK-001 cannot wait")
    assert found.problem == ""
    assert (found.rules, found.by, found.date, found.until) == (("E316",), "@lead", "2026-10-20", "2026-11-30")
    assert found.reason == "the board meets Monday: UNK-001 cannot wait"
    assert found.as_dict()["until"] == "2026-11-30"
    assert "until 2026-11-30" in found.describe()

    old = parse("E316 by @lead on 2026-10-20: the board meets Monday")
    assert old.problem == "" and old.until is None
    assert "until" not in old.as_dict()  # readers that pin today's dict see no new key on an old bullet

    # "until" in the reason is the lead's words, never an end date
    words = parse("E316 by @lead on 2026-10-20: wait until 2026-12-01 for legal")
    assert words.until is None and words.reason == "wait until 2026-12-01 for legal"


@pytest.mark.parametrize("value, problem", [
    ("E316 by @lead on 2026-10-20 until 2026-02-30: why", "not a real date"),
    ("E316 by @lead on 2026-10-20 until next month: why", "'until YYYY-MM-DD'"),
    ("E316 by @lead on 2026-10-20 until 2026-10-01: why", "before the day it was written"),
])
def test_a_bad_until_is_malformed_never_ignored(value, problem):
    found = parse(value)
    assert problem in found.problem and found.rules == ()


# ------------------------------------------------------------------ classes

def test_the_two_classes():
    for rule in ("E316", "E303", "E304", "E316", "E318", "E805", '"case table"',
                 '"F8 CON-020 declined until 2026-10-01"'):
        assert override.is_standing(rule), rule
    for rule in ("GATE-1", "GATE-2", "GATE-3", "GATE-5", '"Shape offers 2 or 3 options"'):
        assert not override.is_standing(rule), rule
    assert set(schema.STANDING_RULES) | set(schema.EVENT_RULES) == set(schema.OVERRIDE_RULES)


def test_standing_override_before_until_covers(ub):
    ov = parse("E316 by @lead on 2026-10-20 until 2026-12-31: the board meets Monday")
    assert override.covers(ov, "2026-12-31") and not override.covers(ov, "2027-01-01")
    code, out = blocked_with(ub, "- **Override:** E316 by @hl-solution-lead on 2026-11-01 until 2026-12-31: the board meets Monday")
    found = findings(out)
    assert ("W316", CAP) in found and ("E316", CAP) not in found and ("E398", CAP) not in found
    assert "until 2026-12-31" in out


def test_standing_override_past_until_is_e398(ub):
    code, out = blocked_with(ub, "- **Override:** E316 by @hl-solution-lead on 2026-10-01 until 2026-11-01: the board meets Monday")
    assert code == 1
    found = findings(out)
    assert ("E398", CAP) in found and ("E316", CAP) in found  # a past until covers nothing: the rule bites again
    assert ("W316", CAP) not in found and ("W323", CAP) not in found
    e398 = next(line for line in out.splitlines() if " E398 " in line)
    assert "ended on 2026-11-01" in e398 and "E316" in e398
    assert schema.CODES["E398"] == "an override has passed its end date"


def test_an_old_standing_override_with_no_until_still_covers(ub):
    ov = parse("E316 by @lead on 2026-10-20: the board meets Monday")
    assert override.covers(ov, "2099-01-01")
    code, out = blocked_with(ub, "- **Override:** E316 by @hl-solution-lead on 2026-11-01: the board meets Monday")
    assert ("W316", CAP) in findings(out) and ("E398", CAP) not in findings(out)


def test_event_override_needs_no_until():
    ov = parse("GATE-5 by @lead on 2020-01-01: the owner was away and agreed by phone")
    assert ov.problem == "" and ov.until is None
    assert not any(override.is_standing(r) for r in ov.rules)
    assert override.covers(ov, "2099-01-01")
    # an until on an event override ends nothing: the gate was passed or not at the moment of deciding
    assert override.covers(parse("GATE-5 by @lead on 2020-01-01 until 2020-02-01: away"), "2099-01-01")


def test_a_malformed_override_covers_nothing():
    assert not override.covers(parse("gate-4 by @lead on 2026-10-20: why"), TODAY)


# ------------------------------------------------------------------ flow check

def test_flowcheck_until_inside_quotes_still_works(tmp_path):
    ov = parse('"F8 CON-020 declined until 2026-10-01" by @lead on 2026-09-13: next sprint')
    assert ov.problem == "" and ov.until is None
    assert override.is_standing(ov.rules[0])
    assert override.ends(ov) == "2026-10-01"
    assert override.covers(ov, "2026-10-01") and not override.covers(ov, "2026-10-02")

    vault = tmp_path / "v"
    shutil.copytree(FLOWCHECK / "05-hold-never-released", vault)
    flow = next((vault / "06-runtime" / "flows").glob("*.md"))
    flow.write_text(flow.read_text(encoding="utf-8") + '\n## History\n\n- **Override:** "F8 CON-020 declined until 2026-10-01" '
                    "by @lead on 2026-09-13: next sprint\n", encoding="utf-8")
    out = run("check", "--vault", str(vault), "--today", "2026-10-13")[1]
    assert len([line for line in out.splitlines() if " E398 " in line]) == 1  # the flow checker's, never a second
