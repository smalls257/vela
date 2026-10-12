"""The team-side skills: the design reference a senior follows from a vault, and the work-breakdown skill (S19, S33, S35, S37)."""
from conftest import REPO

PLUGIN = REPO / "plugin"


def text(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")

def test_tech_design_never_reads_a_missing_program_as_no_manifest():
    ref = text("references/TECH-DESIGN-FROM-VAULT.md")
    assert "Where the planner runs from" in ref and "A missing program is never \"no manifest\"." in ref
    assert 'message "does not exist"' in ref and "Any other exit 2" in ref


def test_tech_design_says_where_its_files_land_and_what_to_do_when_it_runs_out_of_room():
    ref = text("references/TECH-DESIGN-FROM-VAULT.md")
    assert "Do not commit them to `main`" in ref and "design/<slug>" in ref and "origin/main" in ref
    assert "## Running out of room" in ref and "status: in-progress" in ref


def test_work_breakdown_gives_every_story_the_same_fields_and_confirms_splits():
    skill = (REPO / "integrations" / "work-breakdown" / "skill" / "SKILL.md").read_text(encoding="utf-8")
    assert "IDs only" in skill and "A lettered split" in skill and "## Not planned" in skill
    assert "Never split, merge, drop or reorder stories without reading the change back" in skill
    assert "the result is in the session notes" in skill
