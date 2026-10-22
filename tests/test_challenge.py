"""/vela:challenge: a senior's challenge after handoff becomes an open unknown they own,
which blocks the item, and a Dissent line on it. The item keeps its state and text."""
import json
import shutil


from conftest import REPO, edit, findings, run
from vela import schema
import session_files

FIXTURE = REPO / "examples" / "unified-booking"


def test_challenge_is_a_session_mode_the_check_knows():
    assert "challenge" in schema.SESSION_MODES


# What the skill writes, applied to a copy of the fixture: the check turns red with E316 and
# the senior's handoff verify names the change. The contract itself is untouched.

UNKNOWN = """### UNK-009 Hold expiry under load

- **Question:** Does a 10-minute hold survive a kiosk queue at peak?
- **Owner:** @hl-port-senior (Port Systems senior)
- **Opened:** 2026-11-21 challenge by @hl-port-senior
- **State:** open
- **Ask by:** 2026-12-05
- **Blocks:** [[booking-building-blocks#CON-001 Booking API|CON-001]]
- **Notes:** Challenge after handoff. Case: 40 people queue at Dover on a Friday. Proposed: hold for 20 minutes at kiosks.

## Risks
"""
RECORD = """---
id: 2026-11-21-challenge-con-001
type: session
title: "Challenge: CON-001"
date: 2026-11-21
modes: [challenge]
status: closed
summary: Port Systems senior challenges the 10-minute hold on CON-001.
---

# 2026-11-21 Challenge: CON-001

## Captures

- [worry] (@hl-port-senior) Does a 10-minute hold survive a kiosk queue at peak? → keep: [[11-unknowns-and-risks#UNK-009 Hold expiry under load|UNK-009]] (open) ^c01

## Changes

| ID | From | To | Source |
|---|---|---|---|
| UNK-009 | - | open | [[2026-11-21-challenge-con-001#^c01]] |
"""


def test_what_a_challenge_writes_turns_the_check_red_and_verify_names_it(tmp_path):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    edit(vault / "11-unknowns-and-risks.md", "## Risks\n", UNKNOWN)
    edit(vault / "05-building-blocks" / "booking-building-blocks.md", "- **Decision:** [[2026-08-26-kiosks-and-rollout]]\n",
         "- **Decision:** [[2026-08-26-kiosks-and-rollout]]\n- **Dissent:** @hl-port-senior, 2026-11-21: a 10-minute hold "
         "is too short for a peak kiosk queue (see [[11-unknowns-and-risks#UNK-009 Hold expiry under load|UNK-009]])\n")
    session_files.write_record(vault, "2026-11-21-challenge-con-001", RECORD)
    assert run("render", "--vault", str(vault))[0] == 0
    code, out = run("check", "--vault", str(vault), "--today", "2026-11-21")
    assert code == 1
    assert findings(out) == [("E316", "05-building-blocks/booking-building-blocks.md")]
    assert "CON-001 is decided, but open unknown UNK-009 blocks it." in out
    code, out = run("handoff", "verify", "APP-booking", "--vault", str(vault))
    assert code == 1
    assert "changed: interface it offers" in out and "(CON-001): its wording changed" in out
    assert "added: open question" in out and "(UNK-009), on 11-unknowns-and-risks.md, open" in out
    _, answer = run("query", "get", "CON-001", "--vault", str(vault), "--json")
    answer = json.loads(answer)
    assert answer["state"] == "decided" and answer["blocked_by"] == ["UNK-009"]


def _challenged_vault(tmp_path, blocks):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    edit(vault / "11-unknowns-and-risks.md", "## Risks\n", UNKNOWN.replace(
        "[[booking-building-blocks#CON-001 Booking API|CON-001]]", blocks))
    session_files.write_record(vault, "2026-11-21-challenge-con-001", RECORD)
    assert run("render", "--vault", str(vault))[0] == 0
    return vault


def test_an_epic_challenge_gives_one_e316_and_the_hint_says_reopened(tmp_path):
    vault = _challenged_vault(tmp_path, "[[EPC-031-holds-and-confirms|EPC-031]]")
    code, out = run("check", "--vault", str(vault), "--today", "2026-11-21")
    assert code == 1
    assert findings(out) == [("E316", "13-epics/EPC-031-holds-and-confirms.md")]
    assert "EPC-031 is decided, but open unknown UNK-009 blocks it." in out
    assert "set it to reopened" in out and "back to assumption" not in out


def test_a_contract_challenge_hint_still_says_assumption(tmp_path):
    vault = _challenged_vault(tmp_path, "[[booking-building-blocks#CON-001 Booking API|CON-001]]")
    _, out = run("check", "--vault", str(vault), "--today", "2026-11-21")
    assert "set it back to assumption" in out


def test_an_app_page_challenge_gives_one_e316_per_decided_unit(tmp_path):
    vault = _challenged_vault(tmp_path, "[[booking-building-blocks|APP-booking]]")
    code, out = run("check", "--vault", str(vault), "--today", "2026-11-21")
    assert code == 1
    found = findings(out)
    assert len(found) > 1 and {code_ for code_, _ in found} == {"E316"}
    assert "APP-booking is decided, but open unknown UNK-009 blocks it." in out
    assert "CON-001 is decided, but open unknown UNK-009 blocks it." in out
