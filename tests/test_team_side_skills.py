"""The team-side skills: the design reference a senior follows from a vault, and the work-breakdown skill (S19, S33, S35, S37)."""
from conftest import REPO


def test_work_breakdown_gives_every_story_the_same_fields_and_confirms_splits():
    skill = (REPO / "integrations" / "work-breakdown" / "skill" / "SKILL.md").read_text(encoding="utf-8")
    assert "IDs only" in skill and "A lettered split" in skill and "## Not planned" in skill
    assert "Never split, merge, drop or reorder stories without reading the change back" in skill
    assert "the result is in the session notes" in skill
