"""/planner:challenge: a senior's challenge after handoff becomes an open unknown they own,
which blocks the item, and a Dissent line on it. The item keeps its state and text."""
import json
import shutil

import yaml

from conftest import REPO, edit, findings, run
from planner import schema

PLUGIN = REPO / "plugin"
SKILL = PLUGIN / "skills" / "challenge" / "SKILL.md"
FIXTURE = REPO / "examples" / "unified-booking"


def skill_text():
    return SKILL.read_text(encoding="utf-8")


def test_challenge_is_a_session_mode_the_check_knows():
    assert "challenge" in schema.SESSION_MODES
    meta = yaml.safe_load(skill_text().split("---\n", 2)[1])
    assert meta["name"] == "challenge" and meta["disable-model-invocation"] is True
    assert "| Challenge (`challenge`)" in (PLUGIN / "references" / "MODES.md").read_text(encoding="utf-8")
    assert "Epics, Challenge or Answer." in (PLUGIN / "references" / "START.md").read_text(encoding="utf-8")


def test_challenge_never_changes_the_item_and_never_decides():
    text = skill_text()
    assert "Never touch the item's `state:`, `**State:**`, wording, criteria or any other line." in text
    assert "Never change the challenged item's state or text. Only the `**Dissent:**` line is added." in text
    assert "Never decide, resolve, reopen or set back anything. Only a Grill decides" in text
    assert "never argue the item's side" in text


def test_challenge_resolves_the_id_and_shows_what_changed_since_handoff():
    text = skill_text()
    assert "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner query get <ID> --json" in text
    assert "If it says `not_found`, stop" in text and "Do not guess another ID." in text
    assert "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/planner handoff verify <APP-id>" in text
    assert "Never cite an ID that `planner query get` reports `not_found`." in text


def test_challenge_writes_an_unknown_the_senior_owns():
    text = skill_text()
    assert "- **Owner:** @<senior handle> (<their role>)" in text
    assert "- **Blocks:** [[<page>#<heading>|<ID>]]" in text
    assert "- **Dissent:** <senior handle>, <today>: <the reason in a few words>" in text
    assert "Never name anyone but the senior as the unknown's owner." in text
    assert "next free `UNK-nnn`" in text and "git branch -r --list 'origin/session/*'" in text


def test_challenge_asks_the_solution_lead_in_a_pr():
    text = skill_text()
    assert "The reviewer is the solution lead: the `owner:` of `01-goals.md`." in text
    assert "a contract to `assumption`, an epic to `reopened`" in text
    assert "Never use `git add -A`." in text and "Never say a PR exists unless `gh` printed its URL." in text


def test_tech_design_points_the_senior_at_challenge():
    ref = (PLUGIN / "references" / "TECH-DESIGN-FROM-VAULT.md").read_text(encoding="utf-8")
    assert "`/planner:challenge <vault ID>`" in ref
    assert "planner handoff verify <APP-id> --vault <vault>" in ref


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
    (vault / "sessions" / "2026-11-21-challenge-con-001.md").write_text(RECORD, encoding="utf-8")
    assert run("render", "--vault", str(vault))[0] == 0
    code, out = run("check", "--vault", str(vault), "--today", "2026-11-21")
    assert code == 1
    assert findings(out) == [("E316", "05-building-blocks/booking-building-blocks.md")]
    assert "CON-001 is decided, but open unknown UNK-009 blocks it." in out
    code, out = run("handoff", "verify", "APP-booking", "--vault", str(vault))
    assert code == 1
    assert "changed: CON-001 (provides, 05-building-blocks/booking-building-blocks.md): text changed" in out
    assert "added: UNK-009 (unknown, 11-unknowns-and-risks.md, open)" in out
    _, answer = run("query", "get", "CON-001", "--vault", str(vault), "--json")
    answer = json.loads(answer)
    assert answer["state"] == "decided" and answer["blocked_by"] == ["UNK-009"]


def test_the_pr_says_the_red_check_is_deliberate_and_blocks_the_merge():
    text = skill_text()
    assert "E316 is deliberate." in text
    assert "blocks the merge wherever planner-check is a required check" in text
    assert "either by resolving `UNK-nnn` with a Grill or by setting the item back" in text
    assert "For an epic, setting it back means `reopened`." in text
    conv = (REPO / "template" / "CONVENTIONS.md").read_text(encoding="utf-8")
    assert "deliberate" in conv and "blocks the merge" in conv


def test_handoff_verify_exit_2_has_two_cases_and_the_skill_shows_the_message():
    text = skill_text()
    assert "show the tool's message" in text
    assert 'If it says "does not exist", there is no manifest' in text
    assert "could not be read, and go on without claiming anything" in text


def test_the_next_unknown_number_is_highest_plus_one_and_the_session_id_names_the_item():
    text = skill_text()
    assert "highest `UNK-nnn` in use plus one" in text and "Never fill a gap." in text
    assert "git show <branch>:11-unknowns-and-risks.md" in text
    assert "at the end of `## Unknowns`, before `## Risks`" in text.replace("Add the entry at", "at")
    assert "`<date>-challenge-<id-lowercased>`" in text
    assert "E316 fires once per unit" in text


def _challenged_vault(tmp_path, blocks):
    vault = tmp_path / "ub"
    shutil.copytree(FIXTURE, vault)
    edit(vault / "11-unknowns-and-risks.md", "## Risks\n", UNKNOWN.replace(
        "[[booking-building-blocks#CON-001 Booking API|CON-001]]", blocks))
    (vault / "sessions" / "2026-11-21-challenge-con-001.md").write_text(RECORD, encoding="utf-8")
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
