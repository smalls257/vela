"""Skills relay vela's size verdicts; none branches on a band, types a stage, or changes a privacy step."""
import re

import pytest

from conftest import REPO

SKILLS = REPO / "plugin" / "skills"
REFS = REPO / "plugin" / "references"
TEXTS = sorted(SKILLS.rglob("*.md")) + sorted(REFS.rglob("*.md"))


def text(rel):
    return (REPO / "plugin" / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize("path", TEXTS, ids=lambda p: str(p.relative_to(REPO)))
def test_no_skill_branches_on_a_band(path):
    # what the test is about, and nothing broader: "a small change" or "a large page" is ordinary prose
    assert not re.search(r"\b(?:small|medium|large) plan\b|\bband\b", path.read_text(encoding="utf-8"), re.I)


@pytest.mark.parametrize("path", TEXTS, ids=lambda p: str(p.relative_to(REPO)))
def test_no_skill_types_a_stage(path):
    assert not re.search(r"\bstage:|\btyped stage\b", path.read_text(encoding="utf-8"), re.I)


def test_grill_asks_what_the_gate_asks_and_carries_no_vault_condition():
    # The route (`vela decide --options-none`) and the release-date condition live in the gate's output, not the skill.
    grill = text("skills/grill/SKILL.md")
    assert "gives an `ask`" in grill and "no target" not in grill


def test_boundary_offers_one_alternative_only_when_real_and_reads_the_existence_lines_once():
    boundary = text("skills/boundary/SKILL.md")
    assert "2 or 3" not in boundary and "--existence" in boundary


def test_close_runs_the_auto_fixes():
    assert "--fix auto" in text("skills/close/SKILL.md")


def test_start_relays_the_size_and_records_a_lead_set_size():
    start = text("references/START.md")
    assert "vela size set" in start and "--because" in start
