"""The load measure (overhaul plan 8.1): words a session loads before its first question."""
import sys

from conftest import REPO

sys.path.insert(0, str(REPO / "tools"))
import skill_load  # noqa: E402


def test_skill_load_counts_start_modes_review_and_skill():
    found = skill_load.measure("grill")
    assert set(found["files"]) == set(skill_load.SHARED) | {"plugin/skills/grill/SKILL.md"}
    assert found["total"] == sum(found["files"].values()) + found["conventions"]


def test_a_grill_reads_conventions_by_section_not_whole():
    """Task 30: once every cite goes through `vela conventions`, a grill no longer loads the whole rule book."""
    found = skill_load.measure("grill")
    whole = len((REPO / skill_load.CONVENTIONS).read_text(encoding="utf-8").split())
    assert "sections" in found["conventions_how"] and found["conventions"] < whole / 2
